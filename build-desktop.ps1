param([string]$Python = "$PSScriptRoot/.venv/Scripts/python.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name AdsChecking --exclude-module pytest --exclude-module fastapi --exclude-module uvicorn desktop_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
Copy-Item -LiteralPath 'README.md', 'LICENSE' -Destination 'dist/AdsChecking'
$marker = Join-Path $PSScriptRoot 'dist/smoke-result.txt'
if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker }
$process = Start-Process -FilePath "$PSScriptRoot/dist/AdsChecking/AdsChecking.exe" -ArgumentList @('--smoke-test', ('"' + $marker + '"')) -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(30000)) {
    $process.Kill()
    throw 'Packaged desktop smoke test timed out.'
}
if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $marker)) { throw 'Packaged desktop smoke test failed.' }
Compress-Archive -Path 'dist/AdsChecking' -DestinationPath 'dist/AdsChecking-windows-x64.zip' -Force
$hash = (Get-FileHash -LiteralPath 'dist/AdsChecking-windows-x64.zip' -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'dist/SHA256SUMS.txt'), "$hash  AdsChecking-windows-x64.zip`n")
Write-Output 'Built and smoke-tested dist/AdsChecking-windows-x64.zip'
