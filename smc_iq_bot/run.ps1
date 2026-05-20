$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $baseDir

$venvPython = Join-Path $baseDir ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
$botLog = Join-Path $baseDir "bot.log"
$dashLog = Join-Path $baseDir "dashboard.log"
$botPidFile = Join-Path $baseDir ".bot.pid"
$dashPidFile = Join-Path $baseDir ".dashboard.pid"

if (Test-Path $venvPython) {
    Write-Host "Usando ambiente virtual em .venv"
} else {
    Write-Host "Ambiente virtual .venv nao encontrado. Usando Python do sistema."
}

function Start-LoggedProcess {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$LogFile,
        [string]$PidFile,
        [string]$WindowTitle
    )

    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force
    }

    $command = "& '$FilePath' $Arguments *> '$LogFile'"

    $proc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-Command", $command) `
        -WindowStyle Hidden `
        -PassThru `
        -WorkingDirectory $baseDir

    Set-Content -Path $PidFile -Value $proc.Id
    Write-Host "$WindowTitle iniciado. PID: $($proc.Id). Log: $LogFile"
}

Start-LoggedProcess -FilePath $python -Arguments "main.py" -LogFile $botLog -PidFile $botPidFile -WindowTitle "Bot"
Start-LoggedProcess -FilePath $python -Arguments "-m streamlit run dashboard/app.py" -LogFile $dashLog -PidFile $dashPidFile -WindowTitle "Dashboard"

Write-Host "Use .\stop.bat para encerrar os dois processos."
