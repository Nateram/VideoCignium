; Script de Inno Setup para Detector de Movimiento
; Empaqueta Python, Electron, FFmpeg, YOLO y todas las dependencias

#define MyAppName "Detector de Movimiento"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Detector de Movimiento"
#define MyAppExeName "DetectorMovimiento.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-4321-8765-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=DetectorMovimiento-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=electron\icon.ico
UninstallDisplayIcon={app}\electron\icon.ico
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=admin
DisableProgramGroupPage=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
; Tamaño aproximado (ajustar según tu instalación)
ExtraDiskSpaceRequired=1073741824

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; === ELECTRON Y NODE ===
Source: "node_modules\*"; DestDir: "{app}\node_modules"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "electron\*"; DestDir: "{app}\electron"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "package.json"; DestDir: "{app}"; Flags: ignoreversion

; === PYTHON SCRIPTS ===
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; === TEMPLATES Y STATIC ===
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

; === FFMPEG ===
Source: "ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build\*"; DestDir: "{app}\ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build"; Flags: ignoreversion recursesubdirs createallsubdirs

; === YOLO MODEL ===
Source: "yolov10n.pt"; DestDir: "{app}"; Flags: ignoreversion

; === ARCHIVOS DE CONFIGURACIÓN ===
Source: "timestamp_roi_config.json"; DestDir: "{app}"; Flags: ignoreversion; AfterInstall: CreateDataDirs

; === PYTHON EMBEBIDO (descomentar si decides incluir Python) ===
; Source: "python-embed\*"; DestDir: "{app}\python-embed"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\logs"
Name: "{app}\data_local"
Name: "{app}\static\uploads"
Name: "{app}\static\uploads\temp"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Instalar dependencias de Python después de la instalación
Filename: "python"; Parameters: "-m pip install -r ""{app}\requirements.txt"""; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; StatusMsg: "Instalando dependencias de Python..."; Description: "Instalar dependencias de Python"
; Lanzar la aplicación después de instalar
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CreateDataDirs();
begin
  // Crear directorios necesarios en tiempo de instalación
  ForceDirectories(ExpandConstant('{app}\logs'));
  ForceDirectories(ExpandConstant('{app}\data_local'));
  ForceDirectories(ExpandConstant('{app}\static\uploads'));
  ForceDirectories(ExpandConstant('{app}\static\uploads\temp'));
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  PythonInstalled: Boolean;
  NodeInstalled: Boolean;
begin
  Result := True;
  
  // Verificar si Python está instalado
  PythonInstalled := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  if not PythonInstalled then
  begin
    if MsgBox('Python no está instalado en el sistema.' + #13#10 + 
              '¿Desea abrir la página de descargas de Python?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('', 'https://www.python.org/downloads/', '', '', SW_SHOW, ewNoWait, ResultCode);
      Result := False;
      Exit;
    end
    else
    begin
      MsgBox('Python es requerido para ejecutar esta aplicación.' + #13#10 + 
             'La instalación se cancelará.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
  
  // Verificar si Node.js está instalado
  NodeInstalled := Exec('node', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  if not NodeInstalled then
  begin
    if MsgBox('Node.js no está instalado en el sistema.' + #13#10 + 
              '¿Desea abrir la página de descargas de Node.js?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('', 'https://nodejs.org/', '', '', SW_SHOW, ewNoWait, ResultCode);
      Result := False;
      Exit;
    end
    else
    begin
      MsgBox('Node.js es requerido para ejecutar esta aplicación.' + #13#10 + 
             'La instalación se cancelará.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Crear acceso directo personalizado
    CreateShellLink(
      ExpandConstant('{app}\{#MyAppExeName}'),
      ExpandConstant('{app}\launch.bat'),
      '',
      ExpandConstant('{app}'),
      '',
      ExpandConstant('{app}\electron\icon.ico'),
      0,
      SW_SHOW
    );
  end;
end;
