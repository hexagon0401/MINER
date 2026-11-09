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
Compression=lzma2/ultra64
LZMAUseSeparateProcess=yes
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
var
  RuntimeStaged, RuntimeMoved, InstallFinished: Boolean;

function InitializeUninstall(): Boolean;
begin
  Result := not CheckForMutexes('Global\MINER.Beta1.Windows');
  if not Result then MsgBox(CustomMessage('CloseMiner'), mbError, MB_OK);
end;

function PreviousInstallRecognized(): Boolean;
var Location: String;
begin
  Result := RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{CC8E6450-572D-4EC7-A85E-715E3F3A5021}_is1', 'InstallLocation', Location)
    and (CompareText(RemoveBackslashUnlessRoot(Location), ExpandConstant('{app}')) = 0)
    and FileExists(ExpandConstant('{app}\MINER.exe'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Owner: AnsiString;
begin
  Result := '';
  if DirExists(ExpandConstant('{app}\.MINER-upgrade-backup')) then begin
    if not LoadStringFromFile(ExpandConstant('{app}\.MINER-upgrade-state'), Owner) or (Owner <> 'CC8E6450-572D-4EC7-A85E-715E3F3A5021') then begin
      Result := 'Unrecognized backup directory; preserving it.'; exit;
    end;
    if not FileExists(ExpandConstant('{app}\.MINER-upgrade-complete')) then begin
      if DirExists(ExpandConstant('{app}\.MINER-upgrade-backup\_internal')) then begin
        DelTree(ExpandConstant('{app}\_internal'), True, True, True);
        if not RenameFile(ExpandConstant('{app}\.MINER-upgrade-backup\_internal'), ExpandConstant('{app}\_internal')) then begin
          Result := 'Cannot recover the previous runtime; backup preserved.'; exit;
        end;
      end;
      if FileExists(ExpandConstant('{app}\.MINER-upgrade-backup\MINER.exe')) then
        if not FileCopy(ExpandConstant('{app}\.MINER-upgrade-backup\MINER.exe'), ExpandConstant('{app}\MINER.exe'), False) then begin
          Result := 'Cannot recover the previous executable; backup preserved.'; exit;
        end;
    end;
    if not DelTree(ExpandConstant('{app}\.MINER-upgrade-backup'), True, True, True) then begin
      Result := 'Previous update files are still in use. Close MINER and retry.'; exit;
    end;
  end;
  if not DirExists(ExpandConstant('{app}\.MINER-upgrade-backup')) then begin
    DeleteFile(ExpandConstant('{app}\.MINER-upgrade-state'));
    DeleteFile(ExpandConstant('{app}\.MINER-upgrade-complete'));
  end;
  if DirExists(ExpandConstant('{app}\_internal')) and not PreviousInstallRecognized() then
    Result := 'This directory is not a registered MINER installation. Choose an empty installation directory.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Backup: String;
begin
  Backup := ExpandConstant('{app}\.MINER-upgrade-backup');
  if (CurStep = ssInstall) and PreviousInstallRecognized() then begin
    if not ForceDirectories(Backup) then RaiseException('Cannot create MINER rollback directory');
    DeleteFile(ExpandConstant('{app}\.MINER-upgrade-complete'));
    SaveStringToFile(ExpandConstant('{app}\.MINER-upgrade-state'), 'CC8E6450-572D-4EC7-A85E-715E3F3A5021', False);
    if not FileCopy(ExpandConstant('{app}\MINER.exe'), Backup + '\MINER.exe.pending', False) then
      RaiseException('Cannot preserve the previous MINER executable');
    if not RenameFile(Backup + '\MINER.exe.pending', Backup + '\MINER.exe') then RaiseException('Cannot commit rollback executable');
    RuntimeStaged := True;
    if DirExists(ExpandConstant('{app}\_internal')) then begin
      if not RenameFile(ExpandConstant('{app}\_internal'), Backup + '\_internal') then
        RaiseException('Cannot preserve the previous MINER runtime');
      RuntimeMoved := True;
    end;
  end;
  if CurStep = ssPostInstall then begin
    InstallFinished := True;
    if RuntimeStaged then begin
      SaveStringToFile(ExpandConstant('{app}\.MINER-upgrade-complete'), 'complete', False);
      if DelTree(Backup, True, True, True) then begin
        DeleteFile(ExpandConstant('{app}\.MINER-upgrade-state'));
        DeleteFile(ExpandConstant('{app}\.MINER-upgrade-complete'));
      end;
    end;
  end;
end;

procedure DeinitializeSetup();
var Backup: String;
begin
  if RuntimeStaged and not InstallFinished then begin
    Backup := ExpandConstant('{app}\.MINER-upgrade-backup');
    if RuntimeMoved then begin
      DelTree(ExpandConstant('{app}\_internal'), True, True, True);
      if not RenameFile(Backup + '\_internal', ExpandConstant('{app}\_internal')) then exit;
    end;
    if not FileCopy(Backup + '\MINER.exe', ExpandConstant('{app}\MINER.exe'), False) then exit;
    if DelTree(Backup, True, True, True) then begin
      DeleteFile(ExpandConstant('{app}\.MINER-upgrade-state'));
      DeleteFile(ExpandConstant('{app}\.MINER-upgrade-complete'));
    end;
  end;
end;
