; ChemCal 化算 — Inno Setup 安装包脚本
; 编译：ISCC.exe ChemCal.iss
; 发新版时改 AppVersion 和 OutputBaseFilename 两处（与 version.py 保持一致）

#define MyAppName "ChemCal 化算"
#define MyAppVersion "1.6.1"
#define MyAppPublisher "ChemCal Team"
#define MyAppURL "https://github.com/virmuran/ChemCal"

[Setup]
; 固定 AppId：保证升级/卸载识别同一程序，勿改动
AppId={{723971C4-BFA8-4F8D-AB78-000BAFFBC846}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/releases
DefaultDirName={autopf}\ChemCal
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=ChemCal_{#MyAppVersion}_setup
SetupIconFile=ChemCal.ico
UninstallDisplayIcon={app}\ChemCal.exe
; LZMA2 极限压缩 + 固实包：Qt DLL 压缩率约 50~60%
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "附加任务:"; Flags: checkedonce

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "dist\ChemCal\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\ChemCal.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\ChemCal.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ChemCal.exe"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 注意：用户数据在 %USERPROFILE%\.ChemCal，卸载时一律不删
