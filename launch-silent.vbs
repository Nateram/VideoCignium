Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtener directorio del script
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Cambiar al directorio de la aplicación
objShell.CurrentDirectory = scriptDir

' Ejecutar npm start sin mostrar ventana (0 = oculto)
objShell.Run "cmd /c npm start", 0, False

Set objShell = Nothing
Set fso = Nothing
