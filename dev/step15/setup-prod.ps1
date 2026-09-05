[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ExpectedHost = "192.168.2.115",
    [string]$InstallRoot = "/opt/home-energy-controller",
    [string]$ServiceName = "hec.service",
    [string]$ApprovedCommit,
    [string]$BackupRoot = "/var/lib/hec/backups",
    [switch]$Apply,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

function Invoke-RequiredCommand {
    param(
        [string]$Name,
        [string[]]$Arguments = @()
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        throw "Required command is missing: $Name"
    }

    & $command.Source @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Name"
    }
}

function Get-RequiredOutput {
    param(
        [string]$Name,
        [string[]]$Arguments = @()
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        throw "Required command is missing: $Name"
    }

    $output = (& $command.Source @Arguments | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
        throw "Command failed or returned no output: $Name"
    }

    return $output
}

if (-not $IsLinux) {
    throw "This script must run under PowerShell 7 on the Linux production host."
}

if ($Restart -and -not $Apply) {
    throw "-Restart requires -Apply."
}

if ($Apply -and [string]::IsNullOrWhiteSpace($ApprovedCommit)) {
    throw "-ApprovedCommit is required with -Apply."
}

$hostAddresses = Get-RequiredOutput -Name "hostname" -Arguments @("-I")
if ($hostAddresses -notmatch [regex]::Escape($ExpectedHost)) {
    throw "Expected host address $ExpectedHost was not found in the host address list."
}

foreach ($commandName in @("git", "python3", "systemctl", "curl")) {
    if ($null -eq (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required command is missing: $commandName"
    }
}

if (-not (Test-Path -LiteralPath $InstallRoot -PathType Container)) {
    throw "Install root does not exist: $InstallRoot"
}

Set-Location -LiteralPath $InstallRoot
$requiredPaths = @(
    ".git",
    "requirements.txt",
    "dev/run.py",
    "dev/hec/config/config.json"
)
foreach ($requiredPath in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required path is missing: $InstallRoot/$requiredPath"
    }
}

$currentCommit = Get-RequiredOutput -Name "git" -Arguments @("rev-parse", "HEAD")
$worktreeState = & git status --porcelain
if ($worktreeState) {
    throw "The production checkout is not clean. Resolve it before setup."
}

$config = Get-Content -LiteralPath "dev/hec/config/config.json" -Raw | ConvertFrom-Json
if ($config.controller.enabled -eq $true -or $config.tng.write_enabled -eq $true) {
    throw "Refusing setup while a physical-device write path is enabled in configuration."
}

$serviceState = (& systemctl is-active $ServiceName 2>$null).Trim()
$httpStatus = (& curl --silent --show-error --output /dev/null --write-out "%{http_code}" "http://$ExpectedHost:8080/").Trim()

Write-Host "Host:          $ExpectedHost"
Write-Host "Install root:  $InstallRoot"
Write-Host "Service:       $ServiceName ($serviceState)"
Write-Host "Current SHA:   $currentCommit"
Write-Host "HTTP status:   $httpStatus"
Write-Host "Apply mode:    $Apply"

if (-not $Apply) {
    Write-Host "Check-only mode complete. No files, service state, or device state were changed."
    exit 0
}

$backupPath = Join-Path $BackupRoot (Get-Date -AsUTC -Format "yyyyMMddTHHmmssZ")
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
Copy-Item -LiteralPath ".env" -Destination (Join-Path $backupPath ".env") -ErrorAction SilentlyContinue
Copy-Item -LiteralPath "dev/hec/config/config.json" -Destination (Join-Path $backupPath "config.json")
& chmod 700 $backupPath
& chmod 600 (Join-Path $backupPath "config.json")
if (Test-Path -LiteralPath (Join-Path $backupPath ".env")) {
    & chmod 600 (Join-Path $backupPath ".env")
}

Invoke-RequiredCommand -Name "git" -Arguments @("fetch", "--prune", "origin")
Invoke-RequiredCommand -Name "git" -Arguments @("checkout", "--detach", "--force", $ApprovedCommit)
Invoke-RequiredCommand -Name "python3" -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
Invoke-RequiredCommand -Name "python3" -Arguments @("dev/run.py", "--init")

$deployedCommit = Get-RequiredOutput -Name "git" -Arguments @("rev-parse", "HEAD")
if ($deployedCommit -ne $ApprovedCommit) {
    throw "Checked-out revision does not match the approved commit."
}

if ($Restart) {
    Invoke-RequiredCommand -Name "systemctl" -Arguments @("restart", $ServiceName)
    Invoke-RequiredCommand -Name "systemctl" -Arguments @("is-active", $ServiceName)
}

$postStatus = (& curl --silent --show-error --output /dev/null --write-out "%{http_code}" "http://$ExpectedHost:8080/").Trim()
if ($postStatus -notmatch "^2") {
    throw "Post-setup HTTP check failed with status $postStatus. Use the rollback checklist."
}

Write-Host "Setup completed for SHA $deployedCommit."
Write-Host "Backup path:   $backupPath"
Write-Host "HTTP status:   $postStatus"
Write-Host "No physical-device write path was enabled by this script."