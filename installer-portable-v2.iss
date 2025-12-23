; Script de Inno Setup para Detector de Movimiento - VERSION PORTABLE v2
; Incluye Python portable + Electron + YOLO, optimizado para tamaño

#define MyAppName "Detector de Movimiento"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Detector de Movimiento"
#define MyAppExeName "launch-silent.vbs"

[Setup]
AppId={{A1B2C3D4-E5F6-4321-8765-ABCDEF123457}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=DetectorMovimiento-Portable-Setup-{#MyAppVersion}-v2
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=electron\icon.ico
UninstallDisplayIcon={app}\electron\icon.ico
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=admin
DisableProgramGroupPage=yes
; Espacio adicional requerido: ~3.5 GB (Python + Electron + FFmpeg + YOLO + pip-cache + easyocr-cache)
ExtraDiskSpaceRequired=3758096384

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; === PYTHON PORTABLE CON TODAS LAS DEPENDENCIAS ===
Source: "python-portable\*"; DestDir: "{app}\python-portable"; Flags: ignoreversion recursesubdirs createallsubdirs

; === ELECTRON (MÍNIMO, excluyendo archivos innecesarios) ===
; Solo copiar Electron distribuible, excluyendo source maps y archivos de desarrollo
Source: "node_modules\electron\dist\*"; DestDir: "{app}\node_modules\electron\dist"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "node_modules\electron\dist\locales\*"; DestDir: "{app}\node_modules\electron\dist\locales"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "node_modules\electron\dist\resources\*"; DestDir: "{app}\node_modules\electron\dist\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

; === DEPENDENCIAS MÍNIMAS DE NODE (tree-kill y handsontable) ===
Source: "node_modules\tree-kill\*"; DestDir: "{app}\node_modules\tree-kill"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "node_modules\handsontable\*"; DestDir: "{app}\node_modules\handsontable"; Flags: ignoreversion recursesubdirs createallsubdirs

; === ARCHIVOS PRINCIPALES ===
Source: "package.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "electron\*"; DestDir: "{app}\electron"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; === TEMPLATES Y STATIC ===
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

; === FFMPEG ===
Source: "ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build\*"; DestDir: "{app}\ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build"; Flags: ignoreversion recursesubdirs createallsubdirs

; === YOLO MODEL ===
Source: "yolov10n.pt"; DestDir: "{app}"; Flags: ignoreversion

; === EASYOCR CACHE (modelos offline) ===
; Copiar a la raíz de la app
Source: "easyocr-cache\*"; DestDir: "{app}\easyocr-cache"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copiar también dentro de python-portable para cumplir con la ruta esperada
Source: "easyocr-cache\*"; DestDir: "{app}\python-portable\easyocr-cache"; Flags: ignoreversion recursesubdirs createallsubdirs

; === PIP CACHE (paquetes predownloadeados) ===
Source: "pip-cache\*"; DestDir: "{app}\pip-cache"; Flags: ignoreversion recursesubdirs createallsubdirs

; === LAUNCHER SCRIPTS ===
Source: "launch-silent.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch-flask.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "verify-installation.bat"; DestDir: "{app}"; Flags: ignoreversion

; === VISUAL C++ REDISTRIBUTABLE (requerido por PyTorch) ===
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Dirs]
Name: "{app}\logs"
Name: "{app}\data_local"
Name: "{app}\static\uploads"
Name: "{app}\static\uploads\temp"
Name: "{app}\node_modules"
Name: "{app}\node_modules\electron"
Name: "{app}\node_modules\electron\dist"
Name: "{app}\node_modules\tree-kill"
Name: "{app}\python-portable\easyocr-cache"
Name: "{app}\easyocr-cache"
Name: "{app}\pip-cache"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "wscript.exe"; Parameters: """{app}\{#MyAppExeName}"""; IconFilename: "{app}\electron\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "wscript.exe"; Parameters: """{app}\{#MyAppExeName}"""; IconFilename: "{app}\electron\icon.ico"; Tasks: desktopicon

[Run]
; Instalar Visual C++ Redistributable (requerido por PyTorch)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Instalando Microsoft Visual C++ Redistributable..."; Flags: waituntilterminated

; Ejecutar verificación de instalación
Filename: "{app}\verify-installation.bat"; Description: "Verificar instalación"; Flags: nowait

; Lanzar la aplicación después de instalar
Filename: "wscript.exe"; Parameters: """{app}\{#MyAppExeName}"""; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption := 
    'Este instalador incluye TODAS las dependencias necesarias:' + #13#10 +
    '- Python portable con PyTorch, OpenCV, EasyOCR' + #13#10 +
    '- Microsoft Visual C++ Redistributable (para PyTorch)' + #13#10 +
    '- Electron (navegador integrado)' + #13#10 +
    '- FFmpeg' + #13#10 +
    '- Modelo YOLO' + #13#10 + #13#10 +
    'No se requiere conexión a internet.' + #13#10 +
    'Tamaño reducido: solo incluye lo esencial.';
end;
