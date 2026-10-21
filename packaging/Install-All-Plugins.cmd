@echo off
setlocal
set "APP=%LOCALAPPDATA%\OmniView\0.3\OmniView.exe"
if not exist "%LOCALAPPDATA%\OmniView\plugins" mkdir "%LOCALAPPDATA%\OmniView\plugins"
echo Closing running OmniView...
taskkill /F /IM OmniView.exe >nul 2>nul
ping -n 2 127.0.0.1 >nul
for %%n in (office ebook data pro raw hello) do call :install "%%n"
if exist "%APP%" (
  echo All available plugins installed. Starting OmniView...
  start "" "%APP%"
) else (
  echo OmniView core not found. Run OmniView-Setup.exe first.
  pause
)
exit /b 0

:install
set "ID=%~1"
set "SRC=%~dp0%ID%.ovp"
if not exist "%SRC%" exit /b 0
set "DEST=%LOCALAPPDATA%\OmniView\plugins\%ID%"
echo Installing %ID%...
if exist "%DEST%" rmdir /s /q "%DEST%"
mkdir "%DEST%"
tar -xf "%SRC%" -C "%DEST%"
if errorlevel 1 echo   failed: %ID%
exit /b 0
