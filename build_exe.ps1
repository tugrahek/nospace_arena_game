param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"

try {
    python -m PyInstaller --version | Out-Null
}
catch {
    Write-Host "PyInstaller bulunamadi. Once su komutu calistir:"
    Write-Host "pip install pyinstaller"
    exit 1
}

if ($OneFile) {
    Write-Host "One-file exe uretiliyor..."
    python -m PyInstaller --noconfirm --clean --onefile --windowed main.py
    Write-Host ""
    Write-Host "Hazir dosya: dist\\nospace_arena.exe"
}
else {
    Write-Host "One-folder exe uretiliyor..."
    python -m PyInstaller --noconfirm --clean nospace_arena.spec
    Write-Host ""
    Write-Host "Hazir klasor: dist\\nospace_arena\\"
    Write-Host "Exe dosyasi: dist\\nospace_arena\\nospace_arena.exe"
}
