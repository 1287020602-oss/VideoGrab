#define MyAppName "VideoGrab"
#define MyAppVersion "2.3.2"
#define MyAppPublisher "VideoGrab"
#define MyAppExeName "VideoGrab.exe"

[Setup]
AppId={{6A4A8D9C-472F-4A5D-A2CF-E6BD83F6242A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\outputs\VideoGrab-release
OutputBaseFilename=VideoGrab-{#MyAppVersion}-Setup-x64
SetupIconFile=..\outputs\VideoGrab\assets\videograb.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
SetupLogging=yes
VersionInfoVersion=2.3.2.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=VideoGrab 安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "release-dist\VideoGrab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VideoGrab"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\VideoGrab"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""VideoGrab Mobile (Local Wi-Fi)"""; Flags: runhidden waituntilterminated; RunOnceId: "VideoGrabMobileFirewall"

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""VideoGrab Mobile (Local Wi-Fi)"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""VideoGrab Mobile (Local Wi-Fi)"" dir=in action=allow protocol=TCP localport=8765 remoteip=LocalSubnet profile=private,public"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "启动 VideoGrab"; Flags: nowait postinstall skipifsilent
