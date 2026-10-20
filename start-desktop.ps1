$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    throw 'Python environment not found. Follow the setup instructions in README.md.'
}
& '.venv/Scripts/python.exe' -m adschecking.desktop
