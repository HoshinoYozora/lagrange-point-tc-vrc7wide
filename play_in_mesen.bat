@echo off
rem Launch Lagrange Point (TC) Ver1.1.
rem
rem   play_in_mesen.bat                      (bundled MesenCE build - recommended)
rem   play_in_mesen.bat "D:\Mesen\Mesen.exe" (use your own Mesen instead)
rem
rem The bundled MesenCE build already contains the VRC7-Wide mapper, so the ROM
rem just runs. With an external emulator this script patches its core
rem (patch_mesen_core.py) or falls back to loading mesen_vrc7_wide.lua.
setlocal
set "HERE=%~dp0"
set "ROM=%HERE%Lagrange+Point+(TC)+Ver1.1 (VRC7-Wide).nes"
set "PATCH=%HERE%LagrangePoint-JP-to-TC-Ver1.1-vrc7wide.bps"
if not exist "%PATCH%" set "PATCH=%HERE%LagrangePointTC-Ver1.1-vrc7wide.bps"
if not exist "%PATCH%" set "PATCH=%HERE%LagrangePointTC-Ver1.1-vrc7wide.ips"

if not "%~1"=="" goto external

if exist "%HERE%MesenCE\Mesen.exe" (
  if exist "%ROM%" (
    start "" "%HERE%MesenCE\Mesen.exe" "%ROM%"
  ) else (
    rem No pre-patched ROM here: hand the patch to Mesen, which pairs it
    rem automatically with the ROM sitting in the same folder.
    start "" "%HERE%MesenCE\Mesen.exe" "%PATCH%"
  )
  goto :eof
)
echo [info] Bundled MesenCE build missing, falling back to an external Mesen.

:external
set "MESEN=%~1"
if "%MESEN%"=="" set "MESEN=%HERE%MesenCE\Mesen.exe"
if not exist "%MESEN%" (
  echo [ERROR] Mesen.exe was not found.
  echo Put the MesenCE build in a "MesenCE" folder next to this script, or pass
  echo the full path as the first argument, e.g.:
  echo    play_in_mesen.bat "D:\Mesen\Mesen.exe"
  echo MesenCE with VRC7-Wide:
  echo    https://github.com/HoshinoYozora/MesenCE/releases/tag/v2.2.1-vrc7wide
  pause
  exit /b 1
)

python "%HERE%patch_mesen_core.py" >nul 2>nul
if not errorlevel 1 goto run_native

echo [info] Emulator core not patched - using the Lua helper instead.
start "" "%MESEN%" "%ROM%" "%HERE%mesen_vrc7_wide.lua"
goto :eof

:run_native
start "" "%MESEN%" "%ROM%"
endlocal
