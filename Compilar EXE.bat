@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm RemixLauncher-1.1.spec
if errorlevel 1 pause
