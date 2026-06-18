<#
.SYNOPSIS
Anime TUI Windows Installer
#>

Write-Host "==> Встановлення Anime TUI..." -ForegroundColor Cyan

# 1. Check for Python
$python_exe = "python"
if (!(Get-Command "python" -ErrorAction SilentlyContinue)) {
    if (!(Get-Command "py" -ErrorAction SilentlyContinue)) {
        Write-Host "[Помилка] Python не знайдено. Будь ласка, встановіть Python 3 з офіційного сайту або через Microsoft Store." -ForegroundColor Red
        exit 1
    } else {
        $python_exe = "py"
    }
}

# 2. Check for dependencies (fzf, mpv, yt-dlp)
Write-Host "==> Перевірка системних залежностей (fzf, mpv, yt-dlp)..." -ForegroundColor Cyan
$missing_pkgs = @()

if (!(Get-Command "fzf" -ErrorAction SilentlyContinue)) { $missing_pkgs += "fzf" }
if (!(Get-Command "mpv" -ErrorAction SilentlyContinue)) { $missing_pkgs += "mpv" }
if (!(Get-Command "yt-dlp" -ErrorAction SilentlyContinue)) { $missing_pkgs += "yt-dlp" }

if ($missing_pkgs.Length -gt 0) {
    Write-Host "[Попередження] Відсутні системні пакети: $($missing_pkgs -join ', ')" -ForegroundColor Yellow
    Write-Host "Спроба автоматичного встановлення через winget..." -ForegroundColor Cyan
    
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        foreach ($pkg in $missing_pkgs) {
            Write-Host "Встановлення $pkg..."
            winget install --id "junegunn.$pkg" -e --accept-source-agreements --accept-package-agreements -h 2>$null
            if ($pkg -eq "mpv") { winget install mpv.net -e --accept-source-agreements --accept-package-agreements -h 2>$null }
            if ($pkg -eq "yt-dlp") { winget install yt-dlp -e --accept-source-agreements --accept-package-agreements -h 2>$null }
        }
    } else {
        Write-Host "[Помилка] 'winget' не знайдено. Встановіть пакети вручну або оновіть Windows." -ForegroundColor Red
        exit 1
    }
}

# 3. Create virtualenv
$install_dir = "$env:LOCALAPPDATA\anime-tui"
$venv_dir = "$install_dir\venv"

Write-Host "==> Налаштування віртуального середовища Python..." -ForegroundColor Cyan
if (!(Test-Path -Path $install_dir)) {
    New-Item -ItemType Directory -Path $install_dir | Out-Null
}

& $python_exe -m venv $venv_dir

Write-Host "==> Встановлення Python пакетів..." -ForegroundColor Cyan
& "$venv_dir\Scripts\pip.exe" install --upgrade pip
& "$venv_dir\Scripts\pip.exe" install requests climage HdRezkaApi windows-curses

# 4. Copy source code
Write-Host "==> Копіювання файлів..." -ForegroundColor Cyan
if (Test-Path -Path "$install_dir\anime_tui") {
    Remove-Item -Recurse -Force "$install_dir\anime_tui"
}
Copy-Item -Path "anime_tui" -Destination "$install_dir\anime_tui" -Recurse -Force

# 5. Create executable wrapper on Desktop
Write-Host "==> Створення ярлика на Робочому столі..." -ForegroundColor Cyan
$desktop = [Environment]::GetFolderPath("Desktop")
$bat_path = "$desktop\Anime TUI.bat"

$bat_content = @"
@echo off
set PYTHONPATH=$install_dir
"$venv_dir\Scripts\python.exe" -m anime_tui.main %*
pause
"@

Set-Content -Path $bat_path -Value $bat_content

Write-Host "[Готово!] Anime TUI успішно встановлено!" -ForegroundColor Green
Write-Host "Ви можете запустити його за допомогою ярлика 'Anime TUI' на Робочому столі." -ForegroundColor Cyan
Pause
