param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference = 'Stop'
$jobRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$log = Join-Path $jobRoot 'install.log'
$backup = $null
$installed = $false
$smoke = $null
try {
    $configPath = [System.IO.Path]::GetFullPath($Config)
    if ([System.IO.Path]::GetDirectoryName($configPath) -ne $jobRoot) { throw 'Invalid configuration path.' }
    $settings = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $target = [System.IO.Path]::GetFullPath($settings.target).TrimEnd('\')
    $staged = [System.IO.Path]::GetFullPath($settings.staged).TrimEnd('\')
    $expectedStage = Join-Path $jobRoot 'payload\AdsChecking'
    if ($staged -ne $expectedStage -or $target -eq [System.IO.Path]::GetPathRoot($target) -or
        $target -eq $jobRoot -or $jobRoot.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath (Join-Path $target 'AdsChecking.exe')) -or
        -not (Test-Path -LiteralPath (Join-Path $staged 'AdsChecking.exe'))) { throw 'Invalid installation paths.' }
    $old = Get-Process -Id $settings.pid -ErrorAction SilentlyContinue
    if ($old -and -not $old.WaitForExit(120000)) { throw 'Application did not exit.' }
    # Backup is an explicitly checked sibling, never a computed recursive-delete target.
    $parent = [System.IO.Path]::GetDirectoryName($target)
    $backup = $target + '.backup-' + [guid]::NewGuid().ToString('N')
    if ([System.IO.Path]::GetDirectoryName($backup) -ne $parent) { throw 'Invalid backup path.' }
    Move-Item -LiteralPath $target -Destination $backup
    try {
        # Copy allows staging on a different disk. Keep staging and backup for diagnosis.
        New-Item -ItemType Directory -Path $target | Out-Null
        $installed = $true
        Get-ChildItem -LiteralPath $staged -Force | Copy-Item -Destination $target -Recurse
        $marker = Join-Path $jobRoot 'smoke.txt'
        $exe = Join-Path $target 'AdsChecking.exe'
        $smoke = Start-Process -FilePath $exe -ArgumentList @('--smoke-test', ('"' + $marker + '"')) -WindowStyle Hidden -PassThru
        if (-not $smoke.WaitForExit(30000)) { $smoke.Kill(); $smoke.WaitForExit(); throw 'New application timed out.' }
        if ($smoke.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $marker)) { throw 'New application failed smoke test.' }
        Start-Process -FilePath $exe -WorkingDirectory $target -WindowStyle Hidden
        'Update installed. Previous version: ' + $backup | Set-Content -LiteralPath $log
    } catch {
        # Preserve failed files; restore the exact previous portable directory.
        if ($installed) {
            $failed = $target + '.failed-' + [guid]::NewGuid().ToString('N')
            if ([System.IO.Path]::GetDirectoryName($failed) -ne $parent) { throw 'Invalid recovery path.' }
            Move-Item -LiteralPath $target -Destination $failed
        }
        Move-Item -LiteralPath $backup -Destination $target
        Start-Process -FilePath (Join-Path $target 'AdsChecking.exe') -WorkingDirectory $target -WindowStyle Hidden
        throw
    }
} catch {
    ('Update failed: ' + $_.Exception.Message) | Set-Content -LiteralPath $log
    exit 1
}
