#!/bin/bash
# Helper script to run port proxy on remote Windows server

REMOTE_HOST="mark@100.79.70.15"

echo "Attempting to run port proxy script on remote server..."
echo "Note: This requires the remote user to have Administrator privileges"
echo ""

# Try to execute via Windows PowerShell
ssh $REMOTE_HOST "cmd.exe /c 'powershell -Command \"Start-Process powershell -ArgumentList \\\"-NoProfile -ExecutionPolicy Bypass -Command \\\\\\\"wsl cat ~/Update-DockerPortProxy.ps1 | powershell -\\\\\\\"\\\" -Verb RunAs\"'"

echo ""
echo "If that didn't work, please run this manually on the remote server:"
echo "  1. Open PowerShell as Administrator"
echo "  2. Run: wsl cat ~/Update-DockerPortProxy.ps1 | powershell -"
