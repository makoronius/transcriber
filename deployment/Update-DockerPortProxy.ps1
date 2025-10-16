# Update-DockerPortProxy.ps1
# Purpose: Maintain Windows portproxy mappings for WSL2 (Docker + SSH + Gitea + Portainer)
# Requires Administrator privileges

Write-Host "=== Updating WSL2 Port-Proxy Rules ===" -ForegroundColor Cyan

# Wait for WSL to be ready
$maxTries = 15
for ($i = 1; $i -le $maxTries; $i++) {
    $WSL_IP = (wsl hostname -I).Split(' ')[0]
    if ($WSL_IP) { break }
    Start-Sleep -Seconds 2
}
if (-not $WSL_IP) {
    Write-Host "ERROR: Could not retrieve WSL IP address." -ForegroundColor Red
    exit 1
}
Write-Host ("WSL IP detected: {0}" -f $WSL_IP) -ForegroundColor Yellow

# Helper function to (re)create a rule
function Set-PortProxyRule {
    param (
        [int]$ListenPort,
        [int]$ConnectPort,
        [string]$RuleName,
        [string]$ListenAddress = "0.0.0.0"
    )

    # Delete existing mapping
    netsh interface portproxy delete v4tov4 listenport=$ListenPort listenaddress=$ListenAddress 2>$null | Out-Null

    # Add new mapping
    netsh interface portproxy add v4tov4 listenport=$ListenPort listenaddress=$ListenAddress connectport=$ConnectPort connectaddress=$WSL_IP

    Write-Host ("[{0}] proxy set: {1}:{2} -> {3}:{4}" -f $RuleName, $ListenAddress, $ListenPort, $WSL_IP, $ConnectPort) -ForegroundColor Green
}

# Docker (TLS 2376)
Set-PortProxyRule -ListenPort 2376 -ConnectPort 2376 -RuleName "Docker TLS"

# SSH (22)
Set-PortProxyRule -ListenPort 22 -ConnectPort 22 -RuleName "SSH"

# Gitea Web UI (3000)
Set-PortProxyRule -ListenPort 3000 -ConnectPort 3000 -RuleName "Gitea Web"

# Gitea SSH (2222)
Set-PortProxyRule -ListenPort 2222 -ConnectPort 2222 -RuleName "Gitea SSH"

# Portainer HTTPS (9443)
Set-PortProxyRule -ListenPort 9443 -ConnectPort 9443 -RuleName "Portainer HTTPS"

# Portainer HTTP (8000)
Set-PortProxyRule -ListenPort 8000 -ConnectPort 8000 -RuleName "Portainer HTTP"

# Webhook Server (9000) - for future CI/CD
Set-PortProxyRule -ListenPort 9000 -ConnectPort 9000 -RuleName "Webhook Server"

# Firewall exceptions (only added once)
$firewallRules = @(
    @{Name="WSL2 Docker TLS 2376"; Port=2376},
    @{Name="WSL2 SSH 22"; Port=22},
    @{Name="WSL2 Gitea Web 3000"; Port=3000},
    @{Name="WSL2 Gitea SSH 2222"; Port=2222},
    @{Name="WSL2 Portainer HTTPS 9443"; Port=9443},
    @{Name="WSL2 Portainer HTTP 8000"; Port=8000},
    @{Name="WSL2 Webhook 9000"; Port=9000}
)

foreach ($rule in $firewallRules) {
    if (-not (Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Protocol TCP -LocalPort $rule.Port -Action Allow | Out-Null
        Write-Host ("Firewall rule created: {0}" -f $rule.Name) -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Port-proxy update completed ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Active Port Mappings:" -ForegroundColor Cyan
netsh interface portproxy show v4tov4
Write-Host ""
Write-Host "You can now access services at:" -ForegroundColor Green
Write-Host "  Gitea:           http://<this-pc-ip>:3000" -ForegroundColor White
Write-Host "  Portainer:       https://<this-pc-ip>:9443" -ForegroundColor White
Write-Host "  Gitea SSH:       ssh://git@<this-pc-ip>:2222" -ForegroundColor White
Write-Host "  Docker:          tcp://<this-pc-ip>:2376" -ForegroundColor White
Write-Host "  Webhook:         http://<this-pc-ip>:9000" -ForegroundColor White
