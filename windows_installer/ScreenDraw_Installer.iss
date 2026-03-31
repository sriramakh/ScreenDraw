; ScreenDraw for Windows - Inno Setup Installer Script
; =====================================================
; This creates a professional Windows installer (.exe) with:
;   - Start Menu shortcut
;   - Desktop shortcut (optional)
;   - Uninstaller in Add/Remove Programs
;   - Auto-run on startup (optional)
;   - File association cleanup on uninstall
;
; Prerequisites:
;   1. Build the app first: pyinstaller windows_installer/ScreenDraw.spec
;   2. Generate icon: python windows_installer/generate_icon.py
;   3. Install Inno Setup: https://jrsoftware.org/isinfo.php
;   4. Compile this .iss file with Inno Setup Compiler
;
; Or just run: build_installer.bat (automates everything)

#define MyAppName "ScreenDraw"
#define MyAppVersion GetStringFileInfo("..\dist\ScreenDraw\ScreenDraw.exe", "ProductVersion")
#define MyAppPublisher "ScreenDraw"
#define MyAppURL "https://github.com/sriramakh/ScreenDraw"
#define MyAppExeName "ScreenDraw.exe"
#define MyAppDescription "Live Screen Drawing & Annotation Tool"

[Setup]
AppId={{8F4E2A1B-3C5D-4E6F-A7B8-9C0D1E2F3A4B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output installer to the installer_output folder
OutputDir=..\installer_output
OutputBaseFilename=ScreenDraw_Setup_{#MyAppVersion}
SetupIconFile=screendraw.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Require Windows 10+
MinVersion=10.0
; Request admin rights for global hotkeys
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
; Show license page only if LICENSE.txt exists
LicenseFile=
; Installer appearance
WizardImageFile=
WizardSmallImageFile=
; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Allow user to pick install mode
DisableProgramGroupPage=yes
; Version info
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start ScreenDraw automatically when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Include all files from the PyInstaller dist/ScreenDraw folder
Source: "..\dist\ScreenDraw\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Include the icon
Source: "screendraw.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\screendraw.ico"; Comment: "{#MyAppDescription}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\screendraw.ico"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
; Startup (optional)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
; Option to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any config files or logs
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"
Type: filesandordirs; Name: "{app}\*.log"

[Code]
// Kill running instances before install/uninstall
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Try to kill any running instance
  Exec('taskkill', '/F /IM ScreenDraw.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill', '/F /IM ScreenDraw.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

// Custom welcome page message
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This will install ScreenDraw on your computer.' + #13#10 + #13#10 +
    'ScreenDraw is a live screen drawing and annotation tool ' +
    'for presentations, demos, and tutorials.' + #13#10 + #13#10 +
    'Features include: Drawing tools, Spotlight, Zoom Lens, ' +
    'Laser Pointer, Click Animations, Screen Recording, and more.' + #13#10 + #13#10 +
    'Click Next to continue.';
end;
