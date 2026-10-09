; ChemCal 化算 — Inno Setup 安装包脚本
; 编译：ISCC.exe ChemCal.iss
; 发新版时改 AppVersion 和 OutputBaseFilename 两处（与 version.py 保持一致）

#define MyAppName "ChemCal 化算"
#define MyAppVersion "1.14.2"
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
; 中文语言包**随仓库分发**，不再用 compiler:Languages\ChineseSimplified.isl —— 那个前缀
; 指向 Inno 编译器安装目录，本机 Inno 7 自带这份文件，但 GitHub runner 的 Inno（6.7.1）
; 官方安装包不含简体中文（社区翻译，不在官方语言集里），云端编译必失败：
;   Error on line 36: Couldn't open include file "...\Inno Setup 6\Languages\ChineseSimplified.isl"
; 相对路径按**本脚本所在目录**解析（已实测）；这份 isl 与 Inno 6.5.0+/7.x 的消息集
; 完全一致（281 条，0 缺 0 多），云端 6.7.1 与本机 7.x 都能直接编译。
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Files]
Source: "dist\ChemCal\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\ChemCal.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\ChemCal.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ChemCal.exe"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 注意：用户数据在 %USERPROFILE%\.ChemCal，卸载时一律不删
