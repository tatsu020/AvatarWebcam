@echo off
setlocal

echo ========================================
echo AvatarWebCam - Nuitka Build Script
echo ========================================
echo.

REM 仮想環境の確認
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: No virtual environment found. Using system Python.
)

echo.
echo Installing/updating dependencies...
pip install -r requirements.txt
pip install nuitka

echo.
echo Building AvatarWebCam.exe...
echo This may take several minutes...
echo.

set "OUT_DIR=dist"
if exist "%OUT_DIR%" (
    echo Cleaning %OUT_DIR% directory...
    rmdir /S /Q "%OUT_DIR%" >nul 2>&1
)
if exist "%OUT_DIR%" (
    echo %OUT_DIR% is in use. Falling back to dist_build.
    set "OUT_DIR=dist_build"
    if exist "%OUT_DIR%" (
        echo Cleaning %OUT_DIR% directory...
        rmdir /S /Q "%OUT_DIR%" >nul 2>&1
    )
)

set "ICON_OPT="
set "ICON_PATH="
if not exist "icon.ico" (
    if exist "tools\\generate_icon.py" (
        echo Generating icon...
        python tools\\generate_icon.py
    )
)

if exist "icon.ico" (
    set "ICON_PATH=%CD%\icon.ico"
) else if exist "icon.png" (
    set "ICON_PATH=%CD%\icon.png"
)

if defined ICON_PATH (
    echo Using icon: %ICON_PATH%
    set "ICON_OPT=--windows-icon-from-ico=%ICON_PATH%"
) else (
    echo Note: icon.ico/icon.png not found. Building without custom icon.
)

set "APP_VERSION=1.0.2.0"

echo.
echo [1/2] Building Main Application Core...
python -m nuitka ^
    --standalone ^
    --lto=yes ^
    --windows-console-mode=disable ^
    --enable-plugin=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-package-data=SpoutGL ^
    --company-name="AvatarWebCam" ^
    --product-name="AvatarWebCam Core" ^
    --file-version=%APP_VERSION% ^
    --product-version=%APP_VERSION% ^
    --remove-output ^
    --output-dir=%OUT_DIR% ^
    --output-filename=AvatarWebCam_internal.exe ^
    --assume-yes-for-downloads ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Main Core Build failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Building Premium Launcher...
python -m nuitka ^
    --onefile ^
    --windows-console-mode=disable ^
    %ICON_OPT% ^
    --company-name="AvatarWebCam" ^
    --product-name="AvatarWebCam" ^
    --file-version=%APP_VERSION% ^
    --product-version=%APP_VERSION% ^
    --file-description="AvatarWebCam Launcher" ^
    --copyright="Copyright (c) 2026 tatsu020" ^
    --remove-output ^
    --output-dir=%OUT_DIR% ^
    --output-filename=AvatarWebCam.exe ^
    --assume-yes-for-downloads ^
    launcher.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Launcher Build failed!
    pause
    exit /b 1
)

echo.
echo Organizing Final Distribution...
set "FINAL_DIR=%OUT_DIR%\AvatarWebCam"
set "INTERNAL_DIR=%FINAL_DIR%\_internal"

REM 既存の出力先を掃除
if exist "%FINAL_DIR%" rmdir /S /Q "%FINAL_DIR%"
mkdir "%FINAL_DIR%"

REM 1. 本体の移動 (main.dist フォルダを _internal という名前に変えて移動)
if exist "%OUT_DIR%\main.dist" (
    move "%OUT_DIR%\main.dist" "%INTERNAL_DIR%" >nul
)

REM 2. ランチャーの移動
if exist "%OUT_DIR%\AvatarWebCam.exe" (
    move "%OUT_DIR%\AvatarWebCam.exe" "%FINAL_DIR%\AvatarWebCam.exe" >nul
)

echo.
echo Copying Documents to Root...
if exist "LICENSE" copy /Y "LICENSE" "%FINAL_DIR%\LICENSE" >nul
if exist "README.txt" copy /Y "README.txt" "%FINAL_DIR%\README.txt" >nul
if exist "README.md" copy /Y "README.md" "%FINAL_DIR%\README.md" >nul
if exist "THIRD_PARTY_NOTICES.txt" copy /Y "THIRD_PARTY_NOTICES.txt" "%FINAL_DIR%\THIRD_PARTY_NOTICES.txt" >nul
if exist "LICENSES" xcopy /E /I /Y "LICENSES" "%FINAL_DIR%\LICENSES" >nul

echo.
echo ========================================
echo Build completed successfully!
echo.
echo Output: %FINAL_DIR%
echo - Launch this: AvatarWebCam.exe
echo - Everything else is in: _internal\
echo ========================================
echo.

pause
