Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Directorio base de la aplicación
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = scriptDir

' Ejecutar el launcher bat en modo oculto (usa Python/Electron portables)
launcher = Chr(34) & scriptDir & "\launch.bat" & Chr(34)
objShell.Run "cmd /c " & launcher, 0, False

Set objShell = Nothing
Set fso = Nothing
