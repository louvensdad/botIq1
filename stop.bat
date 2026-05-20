@echo off
setlocal

cd /d "%~dp0smc_iq_bot"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0smc_iq_bot\stop.ps1"

endlocal
