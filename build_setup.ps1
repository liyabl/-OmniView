$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Test-Path "dist\OmniView\OmniView.exe")) { throw "Run build_core.ps1 first" }
if (-not (Test-Path "assets\app.ico")) { throw "assets/app.ico missing" }

$SevenZip = $env:SEVENZIP
$candidates = @(
  $SevenZip,
  (Get-Command 7z.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
  (Join-Path ([Environment]::GetFolderPath('ProgramFiles')) "7-Zip\7z.exe"),
  (Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) "7-Zip\7z.exe")
) | Where-Object { $_ -and (Test-Path $_) }
$SevenZip = $candidates | Select-Object -First 1
if (-not $SevenZip) {
  throw "7-Zip not found. Install 7-Zip or set the SEVENZIP environment variable to 7z.exe."
}
New-Item -ItemType Directory -Force build | Out-Null
Remove-Item "build\payload.7z" -Force -ErrorAction SilentlyContinue
& $SevenZip a -t7z -mx=9 -y "build\payload.7z" ".\dist\OmniView\*" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "7z compress failed" }

python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name OmniView-Setup `
  --icon assets\app.ico `
  --add-data "build\payload.7z;." `
  --add-data "assets\7z;assets\7z" `
  launcher.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller launcher failed" }

New-Item -ItemType Directory -Force release | Out-Null
Copy-Item "dist\OmniView-Setup.exe" "release\OmniView-Setup.exe" -Force
if (Test-Path "packaging") {
  Copy-Item "packaging\*" "release\" -Force
}
$size = [math]::Round((Get-Item "release\OmniView-Setup.exe").Length / 1MB, 1)
Write-Host "Setup: release\OmniView-Setup.exe ($size MB)" -ForegroundColor Green

