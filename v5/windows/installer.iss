#ifndef AppBuildVersion
  #error AppBuildVersion is required
#endif
#ifndef OutputStem
  #error OutputStem is required
#endif
#ifndef AppFileVersion
  #error AppFileVersion is required
#endif
[Setup]
AppId={{CC8E6450-572D-4EC7-A85E-715E3F3A5021}
AppName=MINER
AppVersion={#AppBuildVersion}
VersionInfoVersion={#AppFileVersion}
AppPublisher=hexagon0401
AppPublisherURL=https://github.com/hexagon0401
DefaultDirName={autopf}\MINER
DefaultGroupName=MINER
OutputDir=..\dist-windows
OutputBaseFilename={#OutputStem}-Setup
SetupIconFile=work\MINER.ico
UninstallDisplayIcon={app}\MINER.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=Global\MINER.Beta1.Windows
CloseApplications=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
[Files]
Source: "..\dist-windows\MINER\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\MINER"; Filename: "{app}\MINER.exe"
Name: "{autodesktop}\MINER"; Filename: "{app}\MINER.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "{cm:DesktopIconTask}"; Flags: unchecked
[CustomMessages]
english.DesktopIconTask=Create a desktop shortcut
korean.DesktopIconTask=바탕 화면 바로 가기 만들기
english.CloseMiner=Stop and close MINER before continuing. Restore WARP first.
korean.CloseMiner=MINER에서 중지 후 종료해 주세요. WARP 복귀를 먼저 확인해야 합니다.
[Code]
function InitializeUninstall(): Boolean;
begin
  Result := not CheckForMutexes('Global\MINER.Beta1.Windows');
  if not Result then MsgBox(CustomMessage('CloseMiner'), mbError, MB_OK);
end;
