# Update-DockerPortProxy.ps1
# Purpose: Maintain Windows portproxy mappings for WSL2 using CSV configuration
# Requires Administrator privileges
# Usage: .\Update-DockerPortProxy.ps1 [-CsvPath <path>] [-ListenAddress <address>]

param(
    [string]$CsvPath = "$PSScriptRoot\port-mappings.csv",
    [string]$ListenAddress = "0.0.0.0"
)

Write-Host "=== WSL2 Port-Proxy Manager (CSV-based) ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Please right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Wait for WSL to be ready
Write-Host "Detecting WSL IP address..." -ForegroundColor Yellow
$maxTries = 15
$WSL_IP = $null

for ($i = 1; $i -le $maxTries; $i++) {
    $WSL_IP = (wsl hostname -I 2>$null).Split(' ')[0]
    if ($WSL_IP) { break }
    Write-Host "  Attempt $i/$maxTries..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $WSL_IP) {
    Write-Host "ERROR: Could not retrieve WSL IP address." -ForegroundColor Red
    Write-Host "Make sure WSL is running: wsl --list --running" -ForegroundColor Yellow
    exit 1
}

Write-Host "WSL IP detected: $WSL_IP" -ForegroundColor Green
Write-Host ""

# Check if CSV file exists
if (-not (Test-Path $CsvPath)) {
    Write-Host "ERROR: CSV file not found: $CsvPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Creating example CSV file..." -ForegroundColor Yellow

    $exampleCsv = @"
Port,Service,Description
22,SSH,SSH access to WSL
3000,Gitea Web,Gitea web interface
5001,App,Your application
"@

    $exampleCsv | Out-File -FilePath $CsvPath -Encoding UTF8
    Write-Host "Created: $CsvPath" -ForegroundColor Green
    Write-Host "Please edit the file and run this script again." -ForegroundColor Yellow
    exit 0
}

# Read port mappings from CSV
Write-Host "Reading port mappings from: $CsvPath" -ForegroundColor Yellow
try {
    $portMappings = Import-Csv -Path $CsvPath
    Write-Host "Loaded $($portMappings.Count) port mappings" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to read CSV file" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Configuring Port Proxies ===" -ForegroundColor Cyan
Write-Host ""

# Helper function to (re)create a rule
function Set-PortProxyRule {
    param (
        [int]$ListenPort,
        [int]$ConnectPort,
        [string]$RuleName,
        [string]$ListenAddress = "0.0.0.0"
    )

    # Delete existing mapping (suppress errors if not exists)
    netsh interface portproxy delete v4tov4 listenport=$ListenPort listenaddress=$ListenAddress 2>$null | Out-Null

    # Add new mapping
    $result = netsh interface portproxy add v4tov4 listenport=$ListenPort listenaddress=$ListenAddress connectport=$ConnectPort connectaddress=$WSL_IP

    if ($LASTEXITCODE -eq 0) {
        $msg = "  [" + $RuleName + "] " + $ListenAddress + ":" + $ListenPort + " -> " + $WSL_IP + ":" + $ConnectPort
        Write-Host $msg -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to create port proxy for $RuleName" -ForegroundColor Red
    }
}

# Process each port mapping from CSV
foreach ($mapping in $portMappings) {
    $port = [int]$mapping.Port
    $service = $mapping.Service

    if ($port -gt 0) {
        Set-PortProxyRule -ListenPort $port -ConnectPort $port -RuleName $service -ListenAddress $ListenAddress
    }
}

Write-Host ""
Write-Host "=== Configuring Firewall Rules ===" -ForegroundColor Cyan
Write-Host ""

# Create firewall rules for each port
$firewallCreated = 0
$firewallExists = 0

foreach ($mapping in $portMappings) {
    $port = [int]$mapping.Port
    $service = $mapping.Service
    $ruleName = "WSL2 " + $service + " " + $port

    if ($port -gt 0) {
        $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

        if (-not $existingRule) {
            try {
                New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow | Out-Null
                Write-Host "  Created firewall rule: $ruleName" -ForegroundColor Green
                $firewallCreated++
            } catch {
                Write-Host "  Failed to create firewall rule: $ruleName" -ForegroundColor Red
            }
        } else {
            Write-Host "  Firewall rule exists: $ruleName" -ForegroundColor Gray
            $firewallExists++
        }
    }
}

Write-Host ""
if ($firewallCreated -gt 0) {
    Write-Host "Created $firewallCreated new firewall rules" -ForegroundColor Green
}
if ($firewallExists -gt 0) {
    Write-Host "$firewallExists firewall rules already existed" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Configuration Complete ===" -ForegroundColor Cyan
Write-Host ""

# Display active port mappings
Write-Host "Active Port Proxies:" -ForegroundColor Cyan
$activeProxies = netsh interface portproxy show v4tov4

if ($activeProxies) {
    $activeProxies | ForEach-Object { Write-Host $_ -ForegroundColor White }
} else {
    Write-Host "  (none)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Service URLs ===" -ForegroundColor Cyan
Write-Host ""

# Get the actual Windows IP address for display
$windowsIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*WSL*" -and $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object -First 1).IPAddress

foreach ($mapping in $portMappings) {
    $port = $mapping.Port
    $service = $mapping.Service
    $description = $mapping.Description

    if ($port -gt 0) {
        Write-Host "  $service ($description)" -ForegroundColor Yellow
        Write-Host "    http://" -NoNewline -ForegroundColor Gray
        Write-Host $windowsIP -NoNewline -ForegroundColor White
        Write-Host ":" -NoNewline -ForegroundColor Gray
        Write-Host $port -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=== Notes ===" -ForegroundColor Cyan
Write-Host "  - WSL IP addresses change on reboot" -ForegroundColor Yellow
Write-Host "  - Run this script after restarting WSL" -ForegroundColor Yellow
Write-Host "  - Edit '$CsvPath' to add/remove ports" -ForegroundColor Yellow
Write-Host ""
Write-Host "To remove all port proxies:" -ForegroundColor Gray
Write-Host "  netsh interface portproxy reset" -ForegroundColor White
Write-Host ""
