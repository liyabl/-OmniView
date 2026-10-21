@echo off
setlocal
echo This removes the OmniView 0.3 core and its runtime cache.
echo Plugins in %LOCALAPPDATA%\OmniView\plugins are kept.
choice /C YN /M "Continue"
if errorlevel 2 exit /b 0
taskkill /F /IM OmniView.exe >nul 2>nul
ping -n 2 127.0.0.1 >nul
if exist "%LOCALAPPDATA%\OmniView\0.3" rmdir /s /q "%LOCALAPPDATA%\OmniView\0.3"
if exist "%LOCALAPPDATA%\OmniView\current.txt" del /q "%LOCALAPPDATA%\OmniView\current.txt"
echo Core removed. To remove plugins too:
echo   rmdir /s /q "%LOCALAPPDATA%\OmniView\plugins"
pause
endlocal
