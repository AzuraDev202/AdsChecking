param([string]$Python = "$PSScriptRoot/.venv/Scripts/python.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name AdsChecking --icon 'adschecking/assets/app.ico' --add-data 'adschecking/assets:adschecking/assets' --add-data 'adschecking/install_update.ps1:adschecking' --exclude-module pytest --exclude-module fastapi --exclude-module uvicorn desktop_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
Copy-Item -LiteralPath 'README.md', 'LICENSE' -Destination 'dist/AdsChecking'
& $Python -c "from pathlib import Path; from adschecking.updates import APP_VERSION; Path('dist/AdsChecking/VERSION.txt').write_text(APP_VERSION, encoding='utf-8')"
if ($LASTEXITCODE -ne 0) { throw 'Could not write desktop version.' }
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
