Option Explicit

Dim shell, fso, projectRoot, pythonExe, launchScript, logsDir, logFile, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectRoot = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = projectRoot & "\venv\Scripts\python.exe"
launchScript = projectRoot & "\launch_ui.py"
logsDir = projectRoot & "\logs"
logFile = logsDir & "\launcher_output.log"

If Not fso.FolderExists(logsDir) Then
    fso.CreateFolder logsDir
End If

If Not fso.FileExists(pythonExe) Then
    MsgBox "Python virtual environment not found at:" & vbCrLf & pythonExe & vbCrLf & vbCrLf & _
        "Open the project folder and create/setup the venv first.", vbCritical, "SOC Copilot"
    WScript.Quit 1
End If

If Not fso.FileExists(launchScript) Then
    MsgBox "Launcher script not found at:" & vbCrLf & launchScript, vbCritical, "SOC Copilot"
    WScript.Quit 1
End If

command = "cmd /c ""cd /d """"" & projectRoot & """"" && """"" & pythonExe & """"" """"" & launchScript & """"" >> """"" & logFile & """"" 2>&1"""
shell.Run command, 0, False