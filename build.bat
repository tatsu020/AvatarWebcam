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

python -m nuitka ^
    --standalone ^
    --lto=yes ^
    --windows-console-mode=disable ^
    %ICON_OPT% ^
    --enable-plugin=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-package-data=SpoutGL ^
    --company-name="AvatarWebCam" ^
    --product-name="AvatarWebCam" ^
    --file-version=1.0.0.0 ^
    --product-version=1.0.0.0 ^
    --file-description="AvatarWebCam" ^
    --copyright="Copyright (c) 2026 tatsu020" ^
    --remove-output ^
    --output-dir=%OUT_DIR% ^
    --output-filename=AvatarWebCam.exe ^
    --assume-yes-for-downloads ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Organizing output folder...
set "FINAL_DIR=%OUT_DIR%\AvatarWebCam"
if exist "%FINAL_DIR%" rmdir /S /Q "%FINAL_DIR%"
mkdir "%FINAL_DIR%"

REM Nuitka出力（.dist）を bin または contents というサブフォルダに移動して隠す
REM ただし .exe は DLL と同じ場所にある必要があるため、
REM ここでは「AvatarWebCam」フォルダの直下にすべてを置きつつ、
REM ドキュメント類を目立たせる構成にします。
if exist "%OUT_DIR%\AvatarWebCam.dist" (
    xcopy /E /I /Y "%OUT_DIR%\AvatarWebCam.dist" "%FINAL_DIR%" >nul
    rmdir /S /Q "%OUT_DIR%\AvatarWebCam.dist"
)

echo.
echo Copying license and readme files to %FINAL_DIR%...
if exist "LICENSE" copy /Y "LICENSE" "%FINAL_DIR%\LICENSE" >nul
if exist "README.txt" copy /Y "README.txt" "%FINAL_DIR%\README.txt" >nul
if exist "README.md" copy /Y "README.md" "%FINAL_DIR%\README.md" >nul
if exist "THIRD_PARTY_NOTICES.txt" copy /Y "THIRD_PARTY_NOTICES.txt" "%FINAL_DIR%\THIRD_PARTY_NOTICES.txt" >nul
if exist "LICENSES" xcopy /E /I /Y "LICENSES" "%FINAL_DIR%\LICENSES" >nul

echo.
echo ========================================
echo Build completed successfully!
echo.
echo Output location: %FINAL_DIR%
echo - Launch: AvatarWebCam.exe
echo - Support files are mixed in this folder for stability.
echo ========================================
echo.

pause
