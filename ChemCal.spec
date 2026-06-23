# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('modules', 'modules'), ('data', 'data'), ('utils', 'utils'),
            ('resource_helper.py', '.'), ('data_manager.py', '.'),
            ('theme_manager.py', '.'), ('module_loader.py', '.'),
            ('base_module.py', '.'), ('crash_shield.py', '.'),
            ('version.py', '.'), ('app_styles.py', '.'),
            ('calculator_base.py', '.'), ('svg_utils.py', '.'),
            ('ChemCal.ico', '.')],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtSvgWidgets', 'PySide6.QtSvg', 'numpy', 'scipy', 'scipy.optimize', 'scipy.integrate', 'scipy.special', 'scipy.constants', 'scipy.interpolate', 'datetime', 'json', 'os', 'sys', 'math', 'reportlab', 'reportlab.pdfgen', 'reportlab.pdfgen.canvas', 'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.styles', 'reportlab.lib.units', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts', 'reportlab.platypus', 'reportlab.platypus.paragraph', 'reportlab.platypus.doctemplate', 'threading', 'time', 're', 'pathlib', 'shutil', 'pyperclip', 'sqlite3', 'modules.history_db', 'modules.reference.reference_widget', 'modules.combo_box_utils', 'utils', 'utils.docx_utils', 'fpdf', 'pandas'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChemCal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ChemCal.ico'],
)
