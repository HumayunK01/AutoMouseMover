@echo off
set "SCRIPT="%TEMP%\%RANDOM%-%RANDOM%_shortcut.vbs""
echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Auto Mouse Mover.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0AutoMouseMover.exe" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.IconLocation = "%~dp0AutoMouseMover.exe,0" >> %SCRIPT%
echo oLink.Description = "Automated Cursor Mover & Keep-Awake Tool" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%
echo [SUCCESS] Shortcut "Auto Mouse Mover" created on your Desktop!
pause
