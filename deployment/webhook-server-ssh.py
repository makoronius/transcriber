#!/usr/bin/env python3
"""
Simple webhook server for Gitea
Listens for push events and triggers deployment via SSH
"""

from flask import Flask, request, jsonify
import subprocess
import hmac
import hashlib
import os
import logging
from datetime import datetime

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'change-me-to-a-secure-secret')
SSH_HOST = os.environ.get('SSH_HOST', 'localhost')  # localhost from container = WSL host
SSH_USER = os.environ.get('SSH_USER', 'mark')
DEPLOY_SCRIPT = os.environ.get('DEPLOY_SCRIPT', '/opt/deployment/deploy.sh')
ALLOWED_BRANCHES = os.environ.get('ALLOWED_BRANCHES', 'main').split(',')
LOG_FILE = os.environ.get('LOG_FILE', '/var/log/webhook-deploy.log')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def verify_signature(payload, signature):
    """Verify webhook signature from Gitea"""
    if not signature:
        return False

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


def get_deploy_script_for_repo(repo_name):
    """Get deployment script path for a specific repository"""
    deploy_scripts = {
        'transcriber': '/opt/deployment/deploy.sh',
        'whisper': '/opt/deployment/deploy.sh',
    }

    # Default pattern: /opt/deployment/deploy-{repo_name}.sh
    return deploy_scripts.get(repo_name, f'/opt/deployment/deploy-{repo_name}.sh')


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook from Gitea"""

    # Verify signature
    signature = request.headers.get('X-Gitea-Signature')
    if not verify_signature(request.data, signature):
        logger.warning(f"Invalid signature from {request.remote_addr}")
        return jsonify({'error': 'Invalid signature'}), 403

    # Parse payload
    payload = request.json
    event = request.headers.get('X-Gitea-Event')

    logger.info(f"Received {event} event")

    if event != 'push':
        return jsonify({'message': 'Event ignored'}), 200

    # Check branch
    ref = payload.get('ref', '')
    branch = ref.split('/')[-1]

    if branch not in ALLOWED_BRANCHES:
        logger.info(f"Branch {branch} not in allowed list, ignoring")
        return jsonify({'message': f'Branch {branch} not deployed'}), 200

    # Get repository name
    repo_name = payload.get('repository', {}).get('name', '')
    if not repo_name:
        logger.error("No repository name in payload")
        return jsonify({'error': 'No repository name'}), 400

    # Get commit info
    commits = payload.get('commits', [])
    if commits:
        latest_commit = commits[-1]
        commit_msg = latest_commit.get('message', 'No message')
        commit_author = latest_commit.get('author', {}).get('name', 'Unknown')
        logger.info(f"Repository: {repo_name}")
        logger.info(f"Deploying: {commit_msg} by {commit_author}")

    # Get deployment script for this repo
    deploy_script = get_deploy_script_for_repo(repo_name)
    logger.info(f"Using deployment script: {deploy_script}")

    # Trigger deployment via SSH
    try:
        logger.info(f"Starting deployment for {repo_name} on branch {branch}")

        # Execute deployment on host via SSH
        # Using 'bash -l -c' to ensure proper environment
        ssh_command = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'ConnectTimeout=10',
            f'{SSH_USER}@{SSH_HOST}',
            f'{deploy_script} deploy'
        ]

        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        if result.returncode == 0:
            logger.info("Deployment successful!")
            return jsonify({
                'status': 'success',
                'message': 'Deployment completed',
                'repository': repo_name,
                'branch': branch,
                'output': result.stdout[-1000:]  # Last 1000 chars
            }), 200
        else:
            logger.error(f"Deployment failed: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Deployment failed',
                'repository': repo_name,
                'error': result.stderr[-1000:]  # Last 1000 chars
            }), 500

    except subprocess.TimeoutExpired:
        logger.error("Deployment timed out")
        return jsonify({'error': 'Deployment timeout'}), 500
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/deploy', methods=['POST'])
def manual_deploy():
    """Manual deployment endpoint (requires authentication)"""
    auth_token = request.headers.get('Authorization')
    expected_token = f"Bearer {WEBHOOK_SECRET}"

    if auth_token != expected_token:
        return jsonify({'error': 'Unauthorized'}), 401

    repo_name = request.json.get('repository', 'transcriber')
    deploy_script = get_deploy_script_for_repo(repo_name)

    try:
        logger.info(f"Manual deployment triggered for {repo_name}")

        ssh_command = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            f'{SSH_USER}@{SSH_HOST}',
            f'{deploy_script} deploy'
        ]

        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'output': result.stdout
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': result.stderr
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=False)
