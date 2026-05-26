@echo off
echo Building ChemCal...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "ChemCal.spec" del "ChemCal.spec"

if not exist "main.py" (
    echo ERROR: main.py not found!
    pause
    exit /b 1
)

if not exist "resource_helper.py" (
    echo ERROR: resource_helper.py not found!
    pause
    exit /b 1
)

if not exist "modules" (
    echo WARNING: modules directory not found, creating empty structure...
    mkdir modules
    echo # Empty modules package > modules\__init__.py
)

echo Checking for required Python packages...
python -c "import pyperclip" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: pyperclip module not found!
    echo Please install it using: pip install pyperclip
    pause
    exit /b 1
)

echo Checking for multiple Qt bindings...
python -c "import PyQt5" 2>nul
if %errorlevel% == 0 (
    echo WARNING: PyQt5 is installed. This may cause conflicts with PySide6.
    echo Consider uninstalling PyQt5: pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip
    echo Or PyInstaller will try to exclude it automatically.
)

echo Building application...

pyinstaller --name="ChemCal" ^
            --windowed ^
            --onefile ^
            --icon="ChemCal.ico" ^
            --add-data="modules;modules" ^
            --add-data="resource_helper.py;." ^
            --add-data="data_manager.py;." ^
            --add-data="theme_manager.py;." ^
            --add-data="module_loader.py;." ^
            --add-data="base_module.py;." ^
            --add-data="crash_shield.py;." ^
            --add-data="ChemCal.ico;." ^
            --hidden-import="PySide6.QtCore" ^
            --hidden-import="PySide6.QtWidgets" ^
            --hidden-import="PySide6.QtGui" ^
            --hidden-import="matplotlib.backends.backend_qt5agg" ^
            --hidden-import="matplotlib.figure" ^
            --hidden-import="numpy" ^
            --hidden-import="scipy" ^
            --hidden-import="scipy.optimize" ^
            --hidden-import="scipy.integrate" ^
            --hidden-import="scipy.special" ^
            --hidden-import="scipy.constants" ^
            --hidden-import="scipy.interpolate" ^
            --hidden-import="datetime" ^
            --hidden-import="json" ^
            --hidden-import="os" ^
            --hidden-import="sys" ^
            --hidden-import="math" ^
            --hidden-import="random" ^
            --hidden-import="reportlab" ^
            --hidden-import="reportlab.pdfgen" ^
            --hidden-import="reportlab.pdfgen.canvas" ^
            --hidden-import="reportlab.lib" ^
            --hidden-import="reportlab.lib.pagesizes" ^
            --hidden-import="reportlab.lib.styles" ^
            --hidden-import="reportlab.lib.units" ^
            --hidden-import="reportlab.pdfbase" ^
            --hidden-import="reportlab.pdfbase.ttfonts" ^
            --hidden-import="reportlab.platypus" ^
            --hidden-import="reportlab.platypus.paragraph" ^
            --hidden-import="reportlab.platypus.doctemplate" ^
            --hidden-import="threading" ^
            --hidden-import="time" ^
            --hidden-import="re" ^
            --hidden-import="pathlib" ^
            --hidden-import="shutil" ^
            --hidden-import="pyperclip" ^
            --hidden-import="sqlite3" ^
            --hidden-import="modules.history_db" ^
            --hidden-import="pandas" ^
            --hidden-import="pandas._libs" ^
            --hidden-import="pandas._libs.tslibs" ^
            --hidden-import="pandas.core.dtypes.common" ^
            --hidden-import="pandas.io.formats.format" ^
            --hidden-import="pandas.plotting._matplotlib" ^
            --exclude="PyQt5" ^
            --exclude="PyQt6" ^
            --exclude="PyQt5.QtCore" ^
            --exclude="PyQt5.QtWidgets" ^
            --exclude="PyQt5.QtGui" ^
            --clean ^
            main.py

if %errorlevel% == 0 (
    echo.
    echo Build successful!
    echo Executable: dist\ChemCal.exe
    echo.
    echo Note: Application data will be stored in:
    echo   %%APPDATA%%\ChemCal\ (Windows)
    echo   ~/.local/share/ChemCal/ (Linux)
    echo   ~/Library/Application Support/ChemCal/ (macOS)
) else (
    echo.
    echo Build failed with error code %errorlevel%
    echo.
    echo Troubleshooting tips:
    echo 1. Make sure you have only one Qt binding installed
    echo    Try: pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip
    echo 2. Check if all required packages are installed
    echo    Note: pandas is now a required dependency
    echo 3. Try running: pip install -r requirements.txt
)

pause