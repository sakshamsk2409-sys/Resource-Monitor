@echo off
title LibreHardwareMonitor Launcher
echo ========================================================
echo Starting LibreHardwareMonitor with Administrator Rights...
echo ========================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '.tools\LibreHardwareMonitor\LibreHardwareMonitor.exe' -WorkingDirectory '.tools\LibreHardwareMonitor' -Verb RunAs"
if %ERRORLEVEL% EQU 0 (
    echo LibreHardwareMonitor launched successfully.
    echo Remote web server running at http://127.0.0.1:8085/data.json
) else (
    echo Failed to launch or UAC prompt was dismissed.
)
pause

