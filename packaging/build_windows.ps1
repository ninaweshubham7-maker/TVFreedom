$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$SpecDirectory = Join-Path $ProjectRoot "build\pyinstaller\specs"
New-Item -ItemType Directory -Force -Path $SpecDirectory | Out-Null

python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is unavailable. Install the packaging extra with: python -m pip install .[packaging]"
}

$Arguments = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", "TVFreedomDesktop",
    "--contents-directory", ".",
    "--collect-all", "streamlit",
    "--distpath", (Join-Path $ProjectRoot "dist"),
    "--workpath", (Join-Path $ProjectRoot "build\pyinstaller"),
    "--specpath", $SpecDirectory
)

$RuntimeModules = Get-ChildItem -LiteralPath $ProjectRoot -File -Filter "*.py" |
    Where-Object { -not $_.Name.StartsWith("test_") }
foreach ($File in $RuntimeModules) {
    $Arguments += @("--add-data", "$($File.FullName);.")
}

$Arguments += @("--add-data", "$(Join-Path $ProjectRoot 'platform-tools');platform-tools")
$Arguments += @("--add-data", "$(Join-Path $ProjectRoot 'README.md');.")
$Arguments += @("--add-data", "$(Join-Path $ProjectRoot 'CHANGELOG_0.4.0-dev.md');.")

$LauncherRoot = Join-Path $ProjectRoot "launcher-android"
foreach ($File in Get-ChildItem -LiteralPath $LauncherRoot -File -Recurse) {
    $RelativePath = $File.FullName.Substring($LauncherRoot.Length).TrimStart("\")
    $PathParts = $RelativePath -split '[\\/]'
    if ($PathParts | Where-Object { $_ -in @(".gradle", ".idea", ".kotlin") }) {
        continue
    }

    $IsExpectedApk = $RelativePath -eq "app\build\outputs\apk\debug\app-debug.apk"
    if (($PathParts -contains "build") -and -not $IsExpectedApk) {
        continue
    }

    $Destination = Join-Path "launcher-android" (Split-Path -Parent $RelativePath)
    if ($Destination.EndsWith("launcher-android\.")) {
        $Destination = "launcher-android"
    }
    $Arguments += @("--add-data", "$($File.FullName);$Destination")
}

$Arguments += (Join-Path $PSScriptRoot "tvfreedom_launcher.py")
python -m PyInstaller @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$Distribution = Join-Path $ProjectRoot "dist\TVFreedomDesktop"
$Executable = Join-Path $Distribution "TVFreedomDesktop.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Expected executable was not created: $Executable"
}

$Archive = Join-Path $ProjectRoot "dist\TVFreedom-0.4.0-dev-desktop-windows-x64.zip"
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Compress-Archive -Path $Distribution -DestinationPath $Archive

Write-Output "Application: $Executable"
Write-Output "Archive: $Archive"
