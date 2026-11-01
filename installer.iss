#define AppName "Remix Launcher"
#define AppVersion "1.2.0"
#define AppExe "RemixLauncher.exe"

[Setup]
AppId={{0F923D09-F33D-4F0B-B942-A87BDA50BD01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=wesmagador
AppPublisherURL=https://github.com/wesmagador/RemixLauncher
AppSupportURL=https://github.com/wesmagador/RemixLauncher/issues
AppUpdatesURL=https://github.com/wesmagador/RemixLauncher/releases
DefaultDirName={localappdata}\Programs\Remix Launcher
DefaultGroupName=Remix Launcher
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
DisableWelcomePage=no
WizardStyle=modern
WizardSizePercent=110
SetupIconFile=launcher.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=dist\installer
OutputBaseFilename=RemixLauncher-Setup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Instalador do Remix Launcher
InfoBeforeFile=installer-info.txt

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "dist\RemixLauncher-1.2.exe"; DestDir: "{app}"; DestName: "{#AppExe}"; Flags: ignoreversion
Source: "launcher.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\launcher.ico"; AppUserModelID: "RemixLauncher.Desktop.1"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\launcher.ico"; Tasks: desktopicon; AppUserModelID: "RemixLauncher.Desktop.1"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o Remix Launcher"; Flags: nowait postinstall skipifsilent

; Não usar UninstallDelete: dados, logs, downloads e backups gerados pelo usuário
; não fazem parte dos arquivos do instalador e devem permanecer ao desinstalar.
