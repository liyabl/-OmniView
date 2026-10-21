@echo off
setlocal
set "PLUGIN=%LOCALAPPDATA%\OmniView\plugins\office"
set "APP=%LOCALAPPDATA%\OmniView\0.3\OmniView.exe"
if not exist "%~dp0office.ovp" (
  echo office.ovp not found next to this file.
  pause
  exit /b 1
)
if not exist "%LOCALAPPDATA%\OmniView" mkdir "%LOCALAPPDATA%\OmniView"
if not exist "%LOCALAPPDATA%\OmniView\plugins" mkdir "%LOCALAPPDATA%\OmniView\plugins"
echo Closing running OmniView...
taskkill /F /IM OmniView.exe >nul 2>nul
ping -n 2 127.0.0.1 >nul
echo Installing Office plugin...
if exist "%PLUGIN%" rmdir /s /q "%PLUGIN%"
mkdir "%PLUGIN%"
tar -xf "%~dp0office.ovp" -C "%PLUGIN%"
if errorlevel 1 (
  echo Extraction failed. Windows 10 1803+ is required.
  pause
  exit /b 2
)
if not exist "%PLUGIN%\plugin.json" (
  echo plugin.json missing after extraction.
  pause
  exit /b 3
)
echo Office plugin installed.
if exist "%APP%" (
  start "" "%APP%"
) else (
  echo OmniView core not found. Run OmniView-Setup.exe first.
  pause
)
endlocal
