@echo off
echo Building ChemCal...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

if not exist "main.py" (
    echo ERROR: main.py not found!
    pause
    exit /b 1
)

if not exist "modules" (
    echo WARNING: modules directory not found, creating empty structure...
    mkdir modules
    echo # Empty modules package > modules\__init__.py
)

if not exist "data" (
    echo WARNING: data directory not found, creating empty structure...
    mkdir data
)

echo Building with PyInstaller (using ChemCal.spec)...
pyinstaller ChemCal.spec

if %errorlevel% == 0 (
    echo.
    echo Build successful!
    echo Executable: dist\ChemCal.exe
) else (
    echo.
    echo Build failed with error code %errorlevel%
    echo.
    echo Troubleshooting tips:
    echo 1. Make sure you have only one Qt binding installed
    echo    Try: pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip
    echo 2. Check if all required packages are installed
    echo 3. Try running: pip install -r requirements.txt
)

pause
