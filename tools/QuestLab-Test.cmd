@echo off
rem Opens the installed Quest Lab in TEST mode: a separate everything-unlocked save
rem (your real save is never touched). Double-click, or pass --test to Quest Lab.exe yourself.
setlocal
for %%D in ("%LOCALAPPDATA%\Quest Lab" "%LOCALAPPDATA%\Programs\Quest Lab" "%ProgramFiles%\Quest Lab") do (
  for %%E in ("Quest Lab.exe" "app.exe") do (
    if exist "%%~D\%%~E" (
      start "" "%%~D\%%~E" --test
      exit /b 0
    )
  )
)
echo Could not find the installed Quest Lab. Install it first, then run this again.
pause
