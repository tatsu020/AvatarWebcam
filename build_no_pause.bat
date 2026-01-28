@echo off
setlocal

echo ========================================
echo AvatarWebcam - Nuitka Build Script (No Pause)
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
echo Building AvatarWebcam.exe...
echo This may take several minutes...
echo.

set "ICON_OPT="
set "ICON_PATH="
if not exist "icon.ico" (
    if exist "tools\\generate_icon.py" (
        echo Generating icon...
        python tools\\generate_icon.py
    )
)

if exist "icon.ico" (
    set "ICON_PATH=icon.ico"
) else if exist "icon.png" (
    set "ICON_PATH=icon.png"
)

if defined ICON_PATH (
    set "ICON_OPT=--windows-icon-from-ico=%ICON_PATH%"
)

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    %ICON_OPT% ^
    --enable-plugin=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-package-data=SpoutGL ^
    --company-name="AvatarWebcam" ^
    --product-name="AvatarWebcam" ^
    --file-version=1.0.0.0 ^
    --product-version=1.0.0.0 ^
    --file-description="VRChat Spout to Virtual Camera Bridge" ^
    --copyright="Copyright (c) 2026 tatsu020" ^
    --output-dir=dist ^
    --output-filename=AvatarWebcam.exe ^
    --assume-yes-for-downloads ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed!
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo Output: dist\AvatarWebcam.exe
echo ========================================
echo.
