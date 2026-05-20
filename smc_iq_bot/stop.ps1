$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $baseDir

$botPidFile = Join-Path $baseDir ".bot.pid"
$dashPidFile = Join-Path $baseDir ".dashboard.pid"

foreach ($pidFile in @($botPidFile, $dashPidFile)) {
    if (Test-Path $pidFile) {
        $pid = (Get-Content $pidFile | Select-Object -First 1).Trim()
        if ($pid -match '^\d+$') {
            Stop-Process -Id [int]$pid -Force -ErrorAction SilentlyContinue
            Write-Host ("Encerrado PID " + $pid)
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}
