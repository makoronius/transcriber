# Windows Port Proxy Setup for WSL2

This folder contains scripts to expose WSL2 Docker services to the Windows network.

## Files

- **`Update-DockerPortProxy.ps1`** - PowerShell script that configures port forwarding
- **`port-mappings.csv`** - Configuration file with port mappings

## Quick Start

### On Remote Server (100.79.70.15)

The files are already copied to `C:\Scripts\` on the remote server.

**Run as Administrator** in PowerShell:

```powershell
cd C:\Scripts
.\Update-DockerPortProxy.ps1
```

This will:
1. Detect WSL IP address
2. Read port mappings from `port-mappings.csv`
3. Create port proxy rules for each port
4. Create Windows Firewall rules
5. Display all service URLs

## Adding a New Port

Edit `C:\Scripts\port-mappings.csv`:

```csv
Port,Service,Description
5001,Whisper App,Whisper transcription web application
3000,Gitea Web,Gitea web interface
9443,Portainer HTTPS,Portainer web UI (HTTPS)
8080,My New App,My new application  <-- Add this line
```

Then run the script again:

```powershell
.\Update-DockerPortProxy.ps1
```

## Current Port Mappings

| Port | Service | Description |
|------|---------|-------------|
| 2376 | Docker TLS | Docker daemon TLS port |
| 22 | SSH | SSH access to WSL |
| 3000 | Gitea Web | Gitea web interface |
| 2222 | Gitea SSH | Gitea SSH for git operations |
| 9443 | Portainer HTTPS | Portainer web UI (HTTPS) |
| 8000 | Portainer HTTP | Portainer web UI (HTTP) |
| 9000 | Webhook Server | CI/CD webhook receiver |
| 5001 | Whisper App | Whisper transcription web application |

## Accessing Services

After running the script, services are accessible at:

- **Whisper App**: `http://100.79.70.15:5001`
- **Gitea**: `http://100.79.70.15:3000`
- **Portainer**: `https://100.79.70.15:9443`
- **Webhook**: `http://100.79.70.15:9000`

## Troubleshooting

### Script won't run

Make sure you're running as Administrator:
```powershell
# Right-click PowerShell and select "Run as Administrator"
```

### Ports not accessible

1. Check if WSL is running:
   ```powershell
   wsl --list --running
   ```

2. Check port proxies:
   ```powershell
   netsh interface portproxy show v4tov4
   ```

3. Check firewall rules:
   ```powershell
   Get-NetFirewallRule -DisplayName "WSL2*"
   ```

### WSL IP changed after reboot

WSL IP addresses change on reboot. Just run the script again:

```powershell
.\Update-DockerPortProxy.ps1
```

### Remove all port proxies

```powershell
netsh interface portproxy reset
```

## When to Run

Run this script whenever:
- WSL is restarted
- Windows is rebooted
- You add a new service that needs external access
- You modify `port-mappings.csv`

## Automation (Optional)

To run automatically on Windows startup:

1. Create a scheduled task in Task Scheduler
2. Trigger: At startup
3. Action: Run PowerShell script with Administrator privileges
4. Program: `powershell.exe`
5. Arguments: `-NoProfile -ExecutionPolicy Bypass -File "C:\Scripts\Update-DockerPortProxy.ps1"`

---

**Note**: This script must be run as Administrator because it modifies Windows network settings and firewall rules.
