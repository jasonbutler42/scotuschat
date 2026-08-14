# scripts/dev-start.ps1
# Thin wrapper: the real implementation is scripts/dev-start.sh. The repository
# now lives inside WSL on native ext4; the stack runs WSL-native (uvicorn, vite)
# against the Windows PostgreSQL 18 service. This script only derives the WSL
# repository root from its own share-path location and shells into WSL.
# Usage: .\scripts\dev-start.ps1 [--stop|--help]

if ($PSScriptRoot -notmatch '^\\\\(wsl\.localhost|wsl\$)\\([^\\]+)\\(.+)$') {
    Write-Error "This script must be invoked from its WSL share path (\\wsl.localhost\<distro>\... or \\wsl$\<distro>\...). Got: $PSScriptRoot"
    exit 1
}

$distro = $Matches[2]
$linuxScriptDir = '/' + ($Matches[3] -replace '\\', '/')
$linuxRepoRoot = $linuxScriptDir -replace '/scripts$', ''

& wsl.exe -d $distro --cd $linuxRepoRoot -- bash ./scripts/dev-start.sh @args
exit $LASTEXITCODE
