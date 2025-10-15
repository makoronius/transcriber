# Helper script to run whisper transcriber with Docker on Windows
# Usage: .\docker-run.ps1 [cpu|gpu] "PLAYLIST_URL" [additional args]

param(
    [Parameter(Position=0)]
    [ValidateSet('cpu', 'gpu')]
    [string]$Mode = 'cpu',

    [Parameter(Position=1)]
    [string]$PlaylistUrl = '',

    [Parameter(Position=2, ValueFromRemainingArguments=$true)]
    [string[]]$ExtraArgs
)

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-ColorOutput Red "Error: Docker is not installed"
    Write-Host "Install Docker Desktop from: https://docs.docker.com/desktop/install/windows-install/"
    exit 1
}

# Check if docker-compose is installed
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-ColorOutput Red "Error: docker-compose is not installed"
    Write-Host "docker-compose is usually included with Docker Desktop"
    exit 1
}

# GPU-specific checks for Windows
if ($Mode -eq 'gpu') {
    Write-ColorOutput Yellow "Note: GPU support on Windows requires WSL 2 with NVIDIA GPU driver"
    Write-Host "See: https://docs.nvidia.com/cuda/wsl-user-guide/index.html"
    Write-Host ""

    # Check if WSL 2 is available
    $wslVersion = wsl --status 2>&1 | Select-String "WSL 2"
    if (-not $wslVersion) {
        Write-ColorOutput Red "Warning: WSL 2 not detected. GPU mode may not work."
        Write-Host "Install WSL 2 with: wsl --install"
        Write-Host "Consider using CPU mode instead: .\docker-run.ps1 cpu `"URL`""
        Write-Host ""
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne 'y') {
            exit 1
        }
    }
}

# Build command
if ([string]::IsNullOrEmpty($PlaylistUrl)) {
    Write-ColorOutput Yellow "No playlist URL provided. Starting interactive shell..."
    $Command = "bash"
} else {
    $ExtraArgsStr = if ($ExtraArgs) { $ExtraArgs -join ' ' } else { '' }
    $Command = "python transcribe_playlist.py `"$PlaylistUrl`" $ExtraArgsStr"
}

# Create necessary directories
New-Item -ItemType Directory -Force -Path "yt_downloads" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Build the image
$ServiceName = "whisper-$Mode"
Write-ColorOutput Green "Building $ServiceName image..."
docker-compose build $ServiceName

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "Build failed!"
    exit 1
}

# Run the container
Write-ColorOutput Green "`nRunning transcription..."
Write-ColorOutput Yellow "Mode: $Mode"
Write-ColorOutput Yellow "Command: $Command"
Write-Host ""

# For GPU mode on Windows, recommend running from WSL
if ($Mode -eq 'gpu') {
    Write-ColorOutput Yellow "For best GPU performance, consider running from WSL 2:"
    Write-Host "  wsl"
    Write-Host "  cd /mnt/d/Code/whisper  # Adjust path"
    Write-Host "  ./docker-run.sh gpu `"URL`""
    Write-Host ""
}

# Execute
docker-compose run --rm $ServiceName $Command

Write-Host ""
Write-ColorOutput Green "Done! Check the yt_downloads\ directory for results."
