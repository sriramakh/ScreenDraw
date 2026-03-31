@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  ScreenDraw Windows Installer Builder
echo ============================================================
echo.

:: Set paths
set "ROOT_DIR=%~dp0.."
set "INSTALLER_DIR=%~dp0"
set "ICON_FILE=%INSTALLER_DIR%screendraw.ico"
set "SPEC_FILE=%INSTALLER_DIR%ScreenDraw.spec"
set "ISS_FILE=%INSTALLER_DIR%ScreenDraw_Installer.iss"
set "OUTPUT_DIR=%ROOT_DIR%\installer_output"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Install Python 3.9+ from https://python.org
    goto :error
)

echo [1/5] Checking dependencies...
echo.

:: Install build dependencies
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller...
    pip install pyinstaller
)
pip show pillow >nul 2>&1
if errorlevel 1 (
    echo       Installing Pillow...
    pip install pillow
)

:: Install app runtime dependencies
echo       Installing app dependencies...
pip install -r "%ROOT_DIR%\requirements_windows.txt" >nul 2>&1

echo       Done.
echo.

:: Step 2: Generate icon and version info
echo [2/5] Generating app icon and version info...
if not exist "%ICON_FILE%" (
    python "%INSTALLER_DIR%generate_icon.py"
    if errorlevel 1 (
        echo [ERROR] Failed to generate icon.
        goto :error
    )
) else (
    echo       Icon already exists, skipping.
)
python "%INSTALLER_DIR%version_info.py"
echo.

:: Step 3: Build with PyInstaller
echo [3/5] Building application with PyInstaller...
echo       This may take a few minutes...
echo.

cd /d "%ROOT_DIR%"
pyinstaller --clean --noconfirm "%SPEC_FILE%"
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed.
    goto :error
)
echo.
echo       PyInstaller build complete.
echo.

:: Verify the exe was created
if not exist "%ROOT_DIR%\dist\ScreenDraw\ScreenDraw.exe" (
    echo [ERROR] ScreenDraw.exe not found in dist\ScreenDraw\
    goto :error
)

:: Copy icon to dist folder
copy /y "%ICON_FILE%" "%ROOT_DIR%\dist\ScreenDraw\" >nul 2>&1

:: Step 4: Create installer with Inno Setup
echo [4/5] Creating Windows installer with Inno Setup...
echo.

:: Find Inno Setup compiler
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else (
    :: Try to find via PATH
    where ISCC >nul 2>&1
    if not errorlevel 1 (
        set "ISCC=ISCC"
    )
)

if not defined ISCC (
    echo [WARNING] Inno Setup not found.
    echo          The standalone app has been built at:
    echo            %ROOT_DIR%\dist\ScreenDraw\ScreenDraw.exe
    echo.
    echo          To create the installer, install Inno Setup 6 from:
    echo            https://jrsoftware.org/isdl.php
    echo          Then run:
    echo            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "%ISS_FILE%"
    echo.
    goto :standalone_done
)

:: Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

"%ISCC%" "%ISS_FILE%"
if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup compilation failed.
    goto :error
)
echo.

:: Step 5: Done
echo [5/5] Build complete!
echo.
echo ============================================================
echo  OUTPUT FILES:
echo ============================================================
echo.
echo  Standalone App:
echo    %ROOT_DIR%\dist\ScreenDraw\ScreenDraw.exe
echo.
echo  Windows Installer:
echo    %OUTPUT_DIR%\ScreenDraw_Setup_1.0.0.exe
echo.
echo  Distribute the installer .exe to your users.
echo  They just double-click it to install ScreenDraw.
echo ============================================================
goto :end

:standalone_done
echo ============================================================
echo  STANDALONE BUILD COMPLETE
echo ============================================================
echo.
echo  App folder: %ROOT_DIR%\dist\ScreenDraw\
echo  Main exe:   %ROOT_DIR%\dist\ScreenDraw\ScreenDraw.exe
echo.
echo  You can zip this folder and distribute it as a portable app.
echo  Or install Inno Setup to create a proper installer.
echo ============================================================
goto :end

:error
echo.
echo Build failed. See errors above.
echo.
pause
exit /b 1

:end
echo.
pause
