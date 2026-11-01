@echo off
setlocal
cd /d "%~dp0"
set "REMIX_ISCC=%~dp0tools\InnoSetup\ISCC.exe"
if not exist "%REMIX_ISCC%" set "REMIX_ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%REMIX_ISCC%" (
  echo Instale o Inno Setup 6 ou coloque o compilador em tools\InnoSetup.
  exit /b 1
)
if not exist "dist\RemixLauncher-1.2.exe" (
  echo Compile primeiro o launcher com Compilar EXE.bat.
  exit /b 1
)
"%REMIX_ISCC%" installer.iss
if errorlevel 1 pause
