; Script de Inno Setup para Detector de Movimiento - VERSION PORTABLE COMPLETA
; Incluye Python portable con TODAS las dependencias preinstaladas

#define MyAppName "Detector de Movimiento"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Detector de Movimiento"
#define MyAppExeName "launch.bat"

[Setup]
AppId={{A1B2C3D4-E5F6-4321-8765-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=DetectorMovimiento-Portable-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=electron\icon.ico
UninstallDisplayIcon={app}\electron\icon.ico
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=admin
DisableProgramGroupPage=yes
; Espacio adicional requerido: ~3.5 GB para Python + dependencias
ExtraDiskSpaceRequired=3758096384

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; === PYTHON PORTABLE CON TODAS LAS DEPENDENCIAS ===
Source: "python-portable\*"; DestDir: "{app}\python-portable"; Flags: ignoreversion recursesubdirs createallsubdirs

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
Source: "timestamp_roi_config.json"; DestDir: "{app}"; Flags: ignoreversion

; === LAUNCHER SCRIPT ===
Source: "launch.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs"
Name: "{app}\data_local"
Name: "{app}\static\uploads"
Name: "{app}\static\uploads\temp"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\electron\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\electron\icon.ico"; Tasks: desktopicon

[Run]
; Lanzar la aplicación después de instalar (opcional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption := 
    'Este instalador incluye TODAS las dependencias necesarias:' + #13#10 +
    '- Python portable con PyTorch, OpenCV, EasyOCR' + #13#10 +
    '- Electron y Node.js' + #13#10 +
    '- FFmpeg' + #13#10 +
    '- Modelo YOLO' + #13#10 + #13#10 +
    'La instalacion ocupara aproximadamente 3.5 GB.' + #13#10 +
    'No se requiere instalar nada adicional en tu sistema.';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpReady then
  begin
    MsgBox('La instalacion puede tardar varios minutos debido al tamaño de los archivos (3.5 GB).' + #13#10 + 
           'Por favor, ten paciencia.', mbInformation, MB_OK);
  end;
end;
