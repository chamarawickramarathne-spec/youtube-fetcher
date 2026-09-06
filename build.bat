@echo off
setlocal

echo ==========================================
echo   YouTube Fetcher - Build Script (Dual Arch)
echo ==========================================
echo.

REM ── Check Py64 ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 64-bit not found in PATH.
    exit /b 1
)

REM ── Check Py32 ──
set "PY32=C:\Users\Nwick\AppData\Local\Programs\Python\Python312-32\python.exe"
if not exist "%PY32%" (
    echo ERROR: Python 32-bit not found at %PY32%
    exit /b 1
)

REM ── Inno Setup path ──
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

REM ========================================
REM  Step 1: Install dependencies (both Pythons)
REM ========================================
echo [1/7] Installing Python dependencies...
python -m pip install -r requirements.txt pyinstaller --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install x64 dependencies.
    exit /b 1
)
"%PY32%" -m pip install -r requirements.txt pyinstaller --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install x86 dependencies.
    exit /b 1
)

REM ========================================
REM  Step 2: Download resources
REM ========================================
echo [2/7] Downloading resources (yt-dlp + ffmpeg)...
python download_ytdlp.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to download resources.
    exit /b 1
)

REM ========================================
REM  Step 3: Build x64 executable
REM ========================================
echo [3/7] Building x64 executable...
if not exist "dist-x64" mkdir dist-x64
if exist "build-x64" rmdir /s /q build-x64
python -m PyInstaller youtube_fetcher-x64.spec --noconfirm --distpath dist-x64 --workpath build-x64
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller x64 build failed.
    exit /b 1
)
echo   OK: dist-x64\youtube-fetcher.exe

REM ========================================
REM  Step 4: Build x86 executable
REM ========================================
echo [4/7] Building x86 executable...
if not exist "dist-x86" mkdir dist-x86
if exist "build-x86" rmdir /s /q build-x86
"%PY32%" -m PyInstaller youtube_fetcher-x86.spec --noconfirm --distpath dist-x86 --workpath build-x86
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller x86 build failed.
    exit /b 1
)
echo   OK: dist-x86\youtube-fetcher.exe

REM ========================================
REM  Step 5: Build x64 installer
REM ========================================
echo [5/7] Building x64 installer...
if not exist "release\x64" mkdir "release\x64"
if not exist "%ISCC%" (
    echo   WARNING: Inno Setup not found. Skipping x64 installer.
    goto :skip_x64_inst
)
"%ISCC%" installer-x64.iss
if %errorlevel% neq 0 (
    echo ERROR: Inno Setup x64 build failed.
    exit /b 1
)
echo   OK: release\x64\youtube-fetcher-setup-x64.exe
:skip_x64_inst

REM ========================================
REM  Step 6: Build x86 installer
REM ========================================
echo [6/7] Building x86 installer...
if not exist "release\x86" mkdir "release\x86"
if not exist "%ISCC%" (
    echo   WARNING: Inno Setup not found. Skipping x86 installer.
    goto :skip_x86_inst
)
"%ISCC%" installer-x86.iss
if %errorlevel% neq 0 (
    echo ERROR: Inno Setup x86 build failed.
    exit /b 1
)
echo   OK: release\x86\youtube-fetcher-setup-x86.exe
:skip_x86_inst

REM ========================================
REM  Step 7: Summary
REM ========================================
echo.
echo [7/7] Build complete!
echo.
echo   Executables:
echo     x64: dist-x64\youtube-fetcher.exe
echo     x86: dist-x86\youtube-fetcher.exe
echo.
echo   Installers:
if exist "release\x64\youtube-fetcher-setup-x64.exe" echo     x64: release\x64\youtube-fetcher-setup-x64.exe
if exist "release\x86\youtube-fetcher-setup-x86.exe" echo     x86: release\x86\youtube-fetcher-setup-x86.exe
echo.

endlocal
