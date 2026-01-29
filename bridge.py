"""
AvatarWebCam - Spout to Virtual Camera Bridge
Spout受信 → 仮想カメラ出力のブリッジロジック
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Callable, Optional

import cv2
import glfw
import numpy as np
import pyvirtualcam
from OpenGL import GL
from SpoutGL import SpoutReceiver

logger = logging.getLogger(__name__)


class BridgeStatus(Enum):
    STOPPED = "stopped"
    WAITING = "waiting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class BridgeState:
    status: BridgeStatus
    message: str
    source_name: str = ""
    fps: float = 0.0
    frame: Optional[np.ndarray] = None


class SpoutBridge:
    """Spout受信→仮想カメラ出力のブリッジクラス"""

    RESOLUTIONS = {
        "480p": (854, 480),
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440),
        "2160p": (3840, 2160),
    }
    SOURCE_RESOLUTION_KEY = "source"

    def __init__(self, state_callback: Optional[Callable[[BridgeState], None]] = None):
        self._state_callback = state_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._target_source: Optional[str] = None
        self._resolution = "source"
        self._target_fps = 30
        self._preview_interval = 6  # 30fps中6フレームごと = 約5fps
        self._sender_poll_base = 0.5
        self._sender_poll_max = 5.0
        self._empty_check_interval = 10
        self._fps_log_interval = 30.0
        self._current_preview_interval = self._preview_interval
        self._preview_required = True

    def get_sender_list(self) -> list[str]:
        """利用可能なSpoutソース一覧を取得（メインスレッドから呼び出し可能）"""
        senders = []
        try:
            # 一時的にglfwを初期化してソース一覧を取得
            if not glfw.init():
                return senders

            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
            window = glfw.create_window(1, 1, "temp", None, None)
            if not window:
                glfw.terminate()
                return senders

            glfw.make_context_current(window)

            spout = SpoutReceiver()
            senders = spout.getSenderList()

            spout.releaseReceiver()
            glfw.destroy_window(window)
            glfw.terminate()

        except Exception:
            pass

        return senders

    def set_target_source(self, source_name: Optional[str]):
        """接続先のSpoutソースを設定"""
        self._target_source = source_name

    def set_resolution(self, resolution: str):
        """出力解像度を設定"""
        if resolution in self.RESOLUTIONS or resolution == self.SOURCE_RESOLUTION_KEY:
            self._resolution = resolution

    def _resolve_output_size(self, src_width: int, src_height: int) -> tuple[int, int]:
        """出力解像度を決定（ソース解像度を上限とし、設定を超えないようにする）"""
        if self._resolution == self.SOURCE_RESOLUTION_KEY:
            return src_width, src_height

        out_size = self.RESOLUTIONS.get(self._resolution)
        if not out_size:
            return src_width, src_height

        out_width, out_height = out_size
        # ソースが設定より小さい場合はソースに合わせる（アップスケールしない）
        if src_width > 0 and src_height > 0 and (src_width < out_width or src_height < out_height):
            return src_width, src_height

        return out_width, out_height

    def set_fps(self, fps: int):
        """出力FPSを設定"""
        self._target_fps = fps

    def set_preview_required(self, required: bool):
        self._preview_required = required

    def start(self):
        """ブリッジを開始"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_bridge, daemon=True)
        self._thread.start()

    def stop(self):
        """ブリッジを停止"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_running(self) -> bool:
        return self._running

    def _notify_state(self, state: BridgeState):
        """状態変更を通知"""
        if self._state_callback:
            self._state_callback(state)

    def _is_empty_frame(self, buffer: np.ndarray) -> bool:
        """空フレーム判定（サンプリングで軽量化）"""
        sample = buffer[::16, ::16, :3]
        return not sample.any()

    def _run_bridge(self):
        """ブリッジのメインループ（別スレッドで実行）"""
        spout = None
        cam = None
        window = None

        try:
            # GLFW初期化
            logger.info("GLFW初期化中...")
            if not glfw.init():
                logger.error("GLFW初期化失敗")
                self._notify_state(BridgeState(
                    BridgeStatus.ERROR, "GLFWの初期化に失敗しました"
                ))
                return
            logger.info("GLFW初期化完了")

            # 非表示ウィンドウ作成（OpenGLコンテキスト用）
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
            window = glfw.create_window(1, 1, "AvatarWebCam", None, None)
            if not window:
                logger.error("OpenGLコンテキスト作成失敗")
                self._notify_state(BridgeState(
                    BridgeStatus.ERROR, "OpenGLコンテキストの作成に失敗しました"
                ))
                glfw.terminate()
                return
            logger.info("OpenGLコンテキスト作成完了")

            glfw.make_context_current(window)
            # 垂直同期(V-Sync)を無効化してFPS制限を解除
            glfw.swap_interval(0)
            logger.info(f"ターゲットFPS: {self._target_fps}")
            self._current_preview_interval = max(1, int(self._target_fps / 5)) # 秒間約5回に調整

            # Spout受信初期化
            logger.info("SpoutReceiver初期化中...")
            spout = SpoutReceiver()
            logger.info("SpoutReceiver初期化完了")

            current_out_size: Optional[tuple[int, int]] = None
            current_target_fps: int = self._target_fps

            # フレームバッファ（動的にサイズ変更）
            buffer = None
            src_width, src_height = 0, 0
            frame_count = 0
            fps_start_time = time.time()
            fps_frame_count = 0
            current_fps = 0.0
            connected_source = ""
            empty_frame_count = 0
            sender_poll_interval = self._sender_poll_base
            next_sender_poll = 0.0
            last_fps_log_time = time.time()

            logger.info("Spoutソース待機中...")
            self._notify_state(BridgeState(
                BridgeStatus.WAITING, "Spoutソースを待機中..."
            ))

            while self._running:
                current_time = time.time()

                # 接続先を決定
                target = self._target_source
                polled_this_round = False
                if not target:
                    # 自動検出: VRCを含むソースを探す（バックオフ付き）
                    if current_time >= next_sender_poll:
                        polled_this_round = True
                        senders = spout.getSenderList()
                        if senders and frame_count % 30 == 0:
                            logger.debug(f"利用可能なソース: {senders}")
                        for name in senders:
                            if name and "VRC" in name:
                                target = name
                                break
                        if target:
                            sender_poll_interval = self._sender_poll_base
                        else:
                            sender_poll_interval = min(sender_poll_interval * 2, self._sender_poll_max)
                        next_sender_poll = current_time + sender_poll_interval
                    
                    # 検索タイミングではない場合、既に接続があればそれを継続
                    if not target and connected_source and not polled_this_round:
                        target = connected_source

                if not target:
                    # ソースが見つからない
                    if connected_source:
                        logger.warning("ソース切断")
                        connected_source = ""
                        self._notify_state(BridgeState(
                            BridgeStatus.WAITING, "Spoutソースを待機中..."
                        ))
                        logger.info("自動停止: ソース切断")
                        self._running = False
                        break
                    time.sleep(0.5)
                    continue

                # 新しいソースに接続、または設定（解像度・FPS）変更時の再初期化
                desired_out = self._resolve_output_size(spout.getSenderWidth(), spout.getSenderHeight()) if connected_source else (0,0)
                fps_changed = current_target_fps != self._target_fps
                
                if target != connected_source or (connected_source and (desired_out != current_out_size or fps_changed)):
                    if target != connected_source:
                        logger.info(f"ソース接続開始: {target}")
                        spout.setReceiverName(target)
                        connected_source = target
                    
                    empty_frame_count = 0
                    # 接続を安定させるため複数回受信を試行
                    for i in range(5):
                        spout.receiveTexture()
                        time.sleep(0.01)
                    
                    src_width = spout.getSenderWidth()
                    src_height = spout.getSenderHeight()
                    
                    if src_width > 0 and src_height > 0:
                        # バッファ確保（RGB 3チャンネル）
                        if buffer is None or buffer.shape[:2] != (src_height, src_width):
                            buffer = np.zeros((src_height, src_width, 3), dtype=np.uint8)
                            logger.info(f"バッファ確保完了: {buffer.shape}")

                        out_width, out_height = self._resolve_output_size(src_width, src_height)
                        
                        # 仮想カメラの作成/再作成
                        if cam is None or (out_width, out_height) != current_out_size or fps_changed:
                            if cam:
                                cam.close()
                            
                            current_target_fps = self._target_fps
                            # 設定FPSと同じ頻度でプレビューを更新
                            self._current_preview_interval = 1
                            
                            try:
                                cam = pyvirtualcam.Camera(
                                    width=out_width,
                                    height=out_height,
                                    fps=current_target_fps,
                                    backend='obs'
                                )
                                current_out_size = (out_width, out_height)
                                logger.info(f"仮想カメラ初期化: {out_width}x{out_height} @ {current_target_fps}fps")
                            except Exception as e:
                                logger.error(f"仮想カメラ初期化失敗: {e}")
                                self._notify_state(BridgeState(
                                    BridgeStatus.ERROR, f"仮想カメラの初期化に失敗しました: {e}"
                                ))
                                self._running = False
                                break

                        self._notify_state(BridgeState(
                            BridgeStatus.RUNNING,
                            f"接続中: {target} ({src_width}x{src_height})",
                            target
                        ))
                    else:
                        connected_source = ""
                        time.sleep(0.5)
                        continue
                if buffer is None or cam is None:
                    time.sleep(0.1)
                    continue

                # フレーム受信
                spout.receiveTexture()
                result = spout.receiveImage(buffer, GL.GL_RGB, False, 0)

                if result:
                    frame_count += 1
                    # 空フレームチェック、解像度調整などは維持
                    if frame_count % self._empty_check_interval == 0:
                        if self._is_empty_frame(buffer):
                            empty_frame_count += 1
                            if empty_frame_count > 10:
                                connected_source = ""
                                continue
                        else:
                            empty_frame_count = 0

                    frame = buffer
                    if src_width != out_width or src_height != out_height:
                        frame_rgb = cv2.resize(frame, (out_width, out_height), interpolation=cv2.INTER_LINEAR)
                    else:
                        frame_rgb = frame

                    cam.send(frame_rgb)

                    # FPS計算
                    fps_frame_count += 1
                    if current_time - fps_start_time >= 1.0:
                        current_fps = fps_frame_count / (current_time - fps_start_time)
                        if current_time - last_fps_log_time >= self._fps_log_interval:
                            logger.info(f"FPS: {current_fps:.1f}")
                            last_fps_log_time = current_time
                        fps_start_time = current_time
                        fps_frame_count = 0

                    if frame_count % self._current_preview_interval == 0:
                        preview_frame = None
                        if self._preview_required:
                            # UIが見ている時だけ縮小処理を行う
                            preview_h = 216
                            preview_w = 384
                            preview_frame = cv2.resize(frame, (preview_w, preview_h), interpolation=cv2.INTER_LINEAR)
                        
                        self._notify_state(BridgeState(
                            BridgeStatus.RUNNING, f"配信中: {target}", target, current_fps, preview_frame
                        ))
                else:
                    if connected_source:
                        connected_source = ""
                        buffer = None
                        self._notify_state(BridgeState(BridgeStatus.WAITING, "Spoutソースを待機中..."))

                # FPSを制限
                cam.sleep_until_next_frame()

        except Exception as e:
            logger.exception(f"エラー発生: {e}")
            self._notify_state(BridgeState(
                BridgeStatus.ERROR, f"エラーが発生しました: {e}"
            ))
        finally:
            # クリーンアップ
            logger.info("クリーンアップ中...")
            if cam:
                cam.close()
            if spout:
                spout.releaseReceiver()
            if window:
                glfw.destroy_window(window)
                glfw.terminate()

            self._running = False
            self._notify_state(BridgeState(
                BridgeStatus.STOPPED, "停止しました"
            ))


# スタンドアロンテスト用
if __name__ == "__main__":
    import sys

    def on_state_change(state: BridgeState):
        print(f"[{state.status.value}] {state.message}")
        if state.fps > 0:
            print(f"  FPS: {state.fps:.1f}")

    bridge = SpoutBridge(state_callback=on_state_change)

    # ソース一覧を表示
    print("利用可能なSpoutソース:")
    senders = bridge.get_sender_list()
    if senders:
        for i, name in enumerate(senders):
            print(f"  {i+1}. {name}")
    else:
        print("  (なし)")

    print("\nブリッジを開始します... (Ctrl+C で停止)")
    bridge.start()

    try:
        while bridge.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止中...")
        bridge.stop()

    print("終了しました")
