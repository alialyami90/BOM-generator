; Inno Setup script for the per-user Windows installer (plan M11, Q20; ADR 0009).
;
; Build from the repository root after PyInstaller has produced dist\bomgen\:
;   iscc /DAppVersion=0.1.0 packaging\bomgen.iss
; Output: out\installer\bomgen-setup-<version>.exe

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "BOM Generator"
#define AppExeName "BOM Generator.exe"
#define ProgId "bomgen.library"
#define ProjectProgId "bomgen.project"

[Setup]
AppId={{9B1E5C2A-4F37-4E8B-9D61-2C7A0F3B8E15}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Ali Alyami
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19044
ChangesAssociations=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
OutputDir=..\out\installer
OutputBaseFilename=bomgen-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\bomgen\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The default device library package (release.yml builds it into out\ before ISCC); the first
; start imports it into an empty library store (bomgen.app.launcher.install_bundled_library).
Source: "..\out\default.bomlib"; DestDir: "{app}\library"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; .bomlib library update packages import into the app (ADR 0008). HKA is HKCU in a per-user install.
Root: HKA; Subkey: "Software\Classes\.bomlib"; ValueType: string; ValueName: ""; ValueData: "{#ProgId}"; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\.bomlib\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "BOM Generator library update"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey
; .bomproj project files (the project export) open in the app too; registered now so the
; installer needn't change again. Until M8b the app only says it can't open them yet.
Root: HKA; Subkey: "Software\Classes\.bomproj"; ValueType: string; ValueName: ""; ValueData: "{#ProjectProgId}"; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\.bomproj\OpenWithProgids"; ValueType: string; ValueName: "{#ProjectProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\{#ProjectProgId}"; ValueType: string; ValueName: ""; ValueData: "BOM Generator project"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#ProjectProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#ProjectProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// The desktop app renders in Microsoft Edge WebView2 (ADR 0007). It ships with
// Windows 10 21H2+ and 11; when it is missing, fetch Microsoft's bootstrapper.
// A failure only warns: the command line works without WebView2.
const
  WebView2ClientKey = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2BootstrapperUrl = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';
  WebView2Bootstrapper = 'MicrosoftEdgeWebview2Setup.exe';

function WebView2VersionIn(RootKey: Integer): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(RootKey, WebView2ClientKey, 'pv', Version)
    and (Version <> '') and (Version <> '0.0.0.0');
end;

function WebView2Installed: Boolean;
begin
  Result := WebView2VersionIn(HKLM32) or WebView2VersionIn(HKCU);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  if WebView2Installed then
    Exit;
  try
    DownloadTemporaryFile(WebView2BootstrapperUrl, WebView2Bootstrapper, '', nil);
    if not Exec(ExpandConstant('{tmp}\') + WebView2Bootstrapper, '/silent /install', '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      SuppressibleMsgBox('Microsoft Edge WebView2 could not be installed (code '
        + IntToStr(ResultCode) + '). The desktop window needs it; the command line works without it.',
        mbError, MB_OK, IDOK);
  except
    SuppressibleMsgBox('Microsoft Edge WebView2 could not be downloaded: '
      + GetExceptionMessage + ' The desktop window needs it; the command line works without it.',
      mbError, MB_OK, IDOK);
  end;
end;
