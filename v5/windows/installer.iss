#define MyAppName "MINER"
[Setup]
AppId={{CC8E6450-572D-4EC7-A85E-715E3F3A5021}
AppName=MINER
AppVersion=5.0.0-beta.1.1
AppPublisher=hexagon0401
AppPublisherURL=https://github.com/hexagon0401
DefaultDirName={autopf}\MINER
DefaultGroupName=MINER
OutputDir=..\dist-windows
OutputBaseFilename=MINER-v5.0.0-beta.1.1-windows.1-Windows-x64-Setup
SetupIconFile=work\MINER.ico
UninstallDisplayIcon={app}\MINER.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=Local\MINER.Beta1.Windows
CloseApplications=no
[Files]
Source: "..\dist-windows\MINER\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\MINER"; Filename: "{app}\MINER.exe"
Name: "{autodesktop}\MINER"; Filename: "{app}\MINER.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Code]
function InitializeUninstall(): Boolean;
begin
  Result := not CheckForMutexes('Local\MINER.Beta1.Windows');
  if not Result then MsgBox('Stop and close MINER before uninstalling. WARP must be restored first.', mbError, MB_OK);
end;
