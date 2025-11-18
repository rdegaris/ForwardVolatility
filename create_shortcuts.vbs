Set WshShell = CreateObject("WScript.Shell")
DesktopPath = WshShell.SpecialFolders("Desktop")
ScriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Create shortcut for Daily Run
Set DailyLink = WshShell.CreateShortcut(DesktopPath & "\Forward Vol - Daily Scan.lnk")
DailyLink.TargetPath = ScriptPath & "\run_daily.bat"
DailyLink.WorkingDirectory = ScriptPath
DailyLink.Description = "Run daily forward volatility scanner with IB positions"
DailyLink.IconLocation = "%SystemRoot%\System32\shell32.dll,176"
DailyLink.Save

' Create shortcut for Scans Only
Set ScansLink = WshShell.CreateShortcut(DesktopPath & "\Forward Vol - Scans Only.lnk")
ScansLink.TargetPath = ScriptPath & "\run_scans_only.bat"
ScansLink.WorkingDirectory = ScriptPath
ScansLink.Description = "Run forward volatility scans only (no IB positions)"
ScansLink.IconLocation = "%SystemRoot%\System32\shell32.dll,177"
ScansLink.Save

MsgBox "Desktop shortcuts created successfully!" & vbCrLf & vbCrLf & _
       "Created:" & vbCrLf & _
       "  - Forward Vol - Daily Scan" & vbCrLf & _
       "  - Forward Vol - Scans Only", vbInformation, "Shortcuts Created"
