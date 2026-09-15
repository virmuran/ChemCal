# -*- mode: python ; coding: utf-8 -*-
# ChemCal 打包配置（onedir 模式，2026-09-14 由 onefile 迁移）
# - onedir：不再解压到 %TEMP%，启动快、杀软误报少；分发用 Inno Setup 或便携 zip
# - 已剔除死重：scipy 全家 / pandas（项目源码零引用，2026-09-14 核查）

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
            ('common_constants.py', '.'), ('reference_data.py', '.'),
            ('updater.py', '.'), ('ChemCal.ico', '.')],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtSvgWidgets', 'PySide6.QtSvg', 'numpy', 'datetime', 'json', 'os', 'sys', 'math', 'reportlab', 'reportlab.pdfgen', 'reportlab.pdfgen.canvas', 'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.styles', 'reportlab.lib.units', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts', 'reportlab.platypus', 'reportlab.platypus.paragraph', 'reportlab.platypus.doctemplate', 'threading', 'time', 're', 'pathlib', 'shutil', 'pyperclip', 'sqlite3', 'modules.history_db', 'modules.reference.reference_widget', 'modules.combo_box_utils', 'utils', 'utils.docx_utils', 'fpdf'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui',
              'scipy', 'pandas', 'matplotlib', 'tkinter', 'unittest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir：二进制交给 COLLECT，不塞进 exe
    name='ChemCal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ChemCal.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ChemCal',
)
