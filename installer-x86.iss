; Inno Setup — x86 (32-bit x86) installer
; Produces: release/x86/youtube-fetcher-setup-x86.exe

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName=YouTube Fetcher
AppVersion=2.1.0
AppPublisher=YouTube Fetcher
DefaultDirName={autopf}\YouTube Fetcher
DefaultGroupName=YouTube Fetcher
OutputDir=release\x86
OutputBaseFilename=youtube-fetcher-setup-x86
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=media\icon.ico
UninstallDisplayIcon={app}\youtube-fetcher.exe
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
Source: "dist-x86\youtube-fetcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\YouTube Fetcher"; Filename: "{app}\youtube-fetcher.exe"
Name: "{autodesktop}\YouTube Fetcher"; Filename: "{app}\youtube-fetcher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\youtube-fetcher.exe"; Description: "Launch YouTube Fetcher"; Flags: nowait postinstall skipifsilent
