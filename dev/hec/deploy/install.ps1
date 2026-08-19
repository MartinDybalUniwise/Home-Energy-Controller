# Instalace Home Energy Controller na Windows.
# Spouštět z kořene repozitáře:  powershell -ExecutionPolicy Bypass -File dev\hec\deploy\install.ps1
param([string]$TaskName = "HomeEnergyController")

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..\..\..").Path
Write-Host "Kořen instalace: $root"

$version = & py -3 -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$version -lt [version]"3.11") { throw "Vyžaduje Python 3.11+, nalezen $version" }

& py -3 -m pip install -r "$root\requirements.txt"
& py -3 "$root\dev\run.py" --init

# Úloha v Plánovači spustí systém při přihlášení; služba Windows je volitelná později.
$action  = New-ScheduledTaskAction -Execute "py" -Argument "-3 `"$root\dev\run.py`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

Write-Host ""
Write-Host "Hotovo. Spuštění nyní:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "Rozhraní:               http://localhost:8080"
Write-Host "Tajemství doplňte do $root\.env"
