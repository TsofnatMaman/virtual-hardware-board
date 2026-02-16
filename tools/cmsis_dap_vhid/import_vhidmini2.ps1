param(
    [string]$Destination = "tools\\cmsis_dap_vhid\\vhidmini2_src",
    [switch]$Force
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$localRepoSample = Join-Path $scriptRoot "windows-driver-samples\\hid\\vhidmini2"

$possibleRoots = @(
    "C:\\Program Files (x86)\\Windows Kits\\10\\Samples",
    "C:\\Program Files\\Windows Kits\\10\\Samples",
    "C:\\Program Files (x86)\\Windows Kits\\10\\Source",
    "C:\\Program Files\\Windows Kits\\10\\Source"
)

$samplePath = $null
if (Test-Path $localRepoSample) {
    $samplePath = $localRepoSample
}

foreach ($root in $possibleRoots) {
    if ($samplePath) { break }
    if (-not (Test-Path $root)) { continue }
    $match = Get-ChildItem -Path $root -Recurse -Directory -Filter "vhidmini2" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($match) {
        $samplePath = $match.FullName
        break
    }
}

if ((Test-Path $Destination) -and (-not $Force)) {
    Write-Host "Destination already exists. Nothing to do:"
    Write-Host "  $Destination"
    exit 0
}

if (-not $samplePath) {
    Write-Error "vhidmini2 sample not found. Install WDK driver samples or clone windows-driver-samples."
    exit 1
}

Write-Host "Copying vhidmini2 from:"
Write-Host "  $samplePath"
Write-Host "To:"
Write-Host "  $Destination"

if (Test-Path $Destination) {
    Remove-Item -Recurse -Force $Destination
}

New-Item -ItemType Directory -Force $Destination | Out-Null
Copy-Item -Path $samplePath\\* -Destination $Destination -Recurse -Force

Write-Host "Done."
