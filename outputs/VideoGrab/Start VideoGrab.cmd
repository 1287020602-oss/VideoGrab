@echo off
set "VIDEOGRAB_PYTHON=%~dp0..\..\work\videograb-venv\Scripts\pythonw.exe"
if not exist "%VIDEOGRAB_PYTHON%" (
  echo Please run work\bootstrap.ps1 first. See README.md.
  pause
  exit /b 1
)
start "VideoGrab" "%VIDEOGRAB_PYTHON%" "%~dp0app.py"
