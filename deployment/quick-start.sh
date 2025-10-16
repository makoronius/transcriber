#!/bin/bash

# Quick Start Script for Gitea + Deployment Setup
# This script helps you quickly set up your self-hosted Git + CI/CD

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    log "✓ Prerequisites check passed"
}

# Setup Gitea
setup_gitea() {
    log "Setting up Gitea..."

    # Generate secure database password
    DB_PASSWORD=$(openssl rand -hex 16)

    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    info "Detected server IP: $SERVER_IP"

    read -p "Enter your server domain or IP (default: $SERVER_IP): " USER_DOMAIN
    USER_DOMAIN=${USER_DOMAIN:-$SERVER_IP}

    # Update docker-compose file
    sed -i "s/GITEA__database__PASSWD=.*/GITEA__database__PASSWD=$DB_PASSWORD/" docker-compose.gitea.yml
    sed -i "s/GITEA__server__DOMAIN=.*/GITEA__server__DOMAIN=$USER_DOMAIN/" docker-compose.gitea.yml
    sed -i "s|GITEA__server__ROOT_URL=.*|GITEA__server__ROOT_URL=http://$USER_DOMAIN:3000/|" docker-compose.gitea.yml

    # Start Gitea
    log "Starting Gitea containers..."
    docker compose -f docker-compose.gitea.yml up -d

    log "✓ Gitea is starting up..."
    info "Access Gitea at: http://$USER_DOMAIN:3000"
    info "Please complete the web setup wizard to create an admin account"
    info ""
    info "After setup, you'll need to:"
    info "1. Login to Gitea"
    info "2. Go to Site Administration → Actions → Runners"
    info "3. Create a new runner and copy the registration token"
    info ""
    read -p "Press Enter after you have the registration token..."

    read -p "Enter the Gitea Actions registration token: " RUNNER_TOKEN

    # Update runner token
    sed -i "s/GITEA_RUNNER_REGISTRATION_TOKEN=.*/GITEA_RUNNER_REGISTRATION_TOKEN=$RUNNER_TOKEN/" docker-compose.gitea.yml

    # Restart runner
    docker compose -f docker-compose.gitea.yml restart gitea-runner

    log "✓ Gitea setup complete!"
}

# Setup webhook
setup_webhook() {
    log "Setting up webhook server..."

    # Generate webhook secret
    WEBHOOK_SECRET=$(openssl rand -hex 32)

    # Create .env file
    cat > .env << EOF
WEBHOOK_SECRET=$WEBHOOK_SECRET
EOF

    log "✓ Webhook secret generated"

    read -p "Enter your Gitea username: " GITEA_USERNAME
    read -p "Enter your repository name (default: whisper): " REPO_NAME
    REPO_NAME=${REPO_NAME:-whisper}

    # Update webhook docker-compose
    sed -i "s|REPO_URL=.*|REPO_URL=http://gitea:3000/$GITEA_USERNAME/$REPO_NAME.git|" docker-compose.webhook.yml

    # Start webhook server
    log "Starting webhook server..."
    docker compose -f docker-compose.webhook.yml up -d

    log "✓ Webhook server started"
    info ""
    info "Webhook Configuration:"
    info "  URL: http://<server-ip>:9000/webhook"
    info "  Secret: $WEBHOOK_SECRET"
    info ""
    info "Add this webhook in Gitea:"
    info "1. Go to your repository → Settings → Webhooks"
    info "2. Add Webhook → Gitea"
    info "3. Payload URL: http://webhook-server:9000/webhook"
    info "4. Secret: $WEBHOOK_SECRET"
    info "5. Events: Push"
    info ""
    read -p "Press Enter after configuring the webhook..."
}

# Setup git remote
setup_git_remote() {
    log "Configuring Git remote..."

    cd ..

    read -p "Do you want to replace the GitHub remote with Gitea? (y/n): " REPLACE_REMOTE

    if [[ "$REPLACE_REMOTE" =~ ^[Yy]$ ]]; then
        # Remove existing remote
        git remote remove origin 2>/dev/null || true

        read -p "Enter Gitea repository URL (e.g., http://gitea:3000/username/whisper.git): " REPO_URL

        # Add new remote
        git remote add origin "$REPO_URL"

        log "✓ Git remote configured"
        info "You can now push with: git push -u origin main"
    else
        info "Skipping Git remote configuration"
    fi
}

# Show summary
show_summary() {
    log "Setup Complete! 🎉"
    echo ""
    info "═══════════════════════════════════════════════════════════"
    info "                    SETUP SUMMARY"
    info "═══════════════════════════════════════════════════════════"
    echo ""
    info "📦 Gitea Web UI:     http://$USER_DOMAIN:3000"
    info "🔗 Gitea SSH:        ssh://git@$USER_DOMAIN:2222"
    info "🪝 Webhook Server:   http://$USER_DOMAIN:9000"
    echo ""
    info "Next Steps:"
    info "1. Create a repository in Gitea"
    info "2. Push your code: git push -u origin main"
    info "3. Configure webhook in Gitea (see DEPLOYMENT.md)"
    echo ""
    info "📚 Full documentation: deployment/DEPLOYMENT.md"
    info "═══════════════════════════════════════════════════════════"
}

# Main menu
main_menu() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║     Self-Hosted Git + CI/CD Setup for Whisper App            ║
║                                                               ║
║  This wizard will help you set up:                           ║
║  • Gitea (Self-hosted Git server)                            ║
║  • Webhook-based automatic deployment                        ║
║  • CI/CD pipeline                                            ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo ""
    echo "Select setup option:"
    echo "  1) Full setup (Gitea + Webhook + Git remote)"
    echo "  2) Setup Gitea only"
    echo "  3) Setup Webhook only"
    echo "  4) Configure Git remote only"
    echo "  5) Show status"
    echo "  6) Exit"
    echo ""
    read -p "Enter choice [1-6]: " choice

    case $choice in
        1)
            check_prerequisites
            setup_gitea
            setup_webhook
            setup_git_remote
            show_summary
            ;;
        2)
            check_prerequisites
            setup_gitea
            ;;
        3)
            check_prerequisites
            setup_webhook
            ;;
        4)
            setup_git_remote
            ;;
        5)
            log "Checking service status..."
            docker compose -f docker-compose.gitea.yml ps
            echo ""
            docker compose -f docker-compose.webhook.yml ps
            ;;
        6)
            log "Exiting..."
            exit 0
            ;;
        *)
            error "Invalid choice"
            exit 1
            ;;
    esac
}

# Run
cd "$(dirname "$0")"
main_menu
