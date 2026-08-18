@echo off
setlocal

echo ==========================================
echo   YouTube Fetcher - Build Script
echo ==========================================
echo.

REM 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+.
    exit /b 1
)

REM 2. Install dependencies
echo [1/5] Installing Python dependencies...
pip install -r requirements.txt pyinstaller --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)

REM 3. Download resources (yt-dlp + ffmpeg)
echo [2/5] Downloading resources...
python download_ytdlp.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to download resources.
    exit /b 1
)

REM 4. Build with PyInstaller
echo [3/5] Building executable with PyInstaller...
pyinstaller youtube_fetcher.spec --noconfirm
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

REM 5. Create installer with Inno Setup
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%ISCC%" (
    echo [4/5] Building installer with Inno Setup...
    if not exist "release" mkdir release
    "%ISCC%" installer.iss
    if %errorlevel% neq 0 (
        echo ERROR: Inno Setup build failed.
        exit /b 1
    )
) else (
    echo [4/5] WARNING: Inno Setup not found. Skipping installer.
    echo   Install from https://jrsoftware.org/isinfo.php to build installer.
)

REM 6. Done
echo [5/5] Build complete!
echo.
echo   Executable: dist\youtube-fetcher.exe
if exist "release\youtube-fetcher-setup.exe" (
    echo   Installer:  release\youtube-fetcher-setup.exe
)
echo.

endlocal
