#!/usr/bin/env python3
"""
Simple webhook server for Gitea
Listens for push events and triggers deployment
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
DEPLOY_SCRIPT = os.environ.get('DEPLOY_SCRIPT', '/opt/deployment/deploy.sh')
ALLOWED_BRANCHES = os.environ.get('ALLOWED_BRANCHES', 'main,master').split(',')
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

    # Get commit info
    commits = payload.get('commits', [])
    if commits:
        latest_commit = commits[-1]
        commit_msg = latest_commit.get('message', 'No message')
        commit_author = latest_commit.get('author', {}).get('name', 'Unknown')
        logger.info(f"Deploying: {commit_msg} by {commit_author}")

    # Trigger deployment
    try:
        logger.info(f"Starting deployment for branch {branch}")

        result = subprocess.run(
            [DEPLOY_SCRIPT, 'deploy'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        if result.returncode == 0:
            logger.info("Deployment successful!")
            return jsonify({
                'status': 'success',
                'message': 'Deployment completed',
                'branch': branch,
                'output': result.stdout
            }), 200
        else:
            logger.error(f"Deployment failed: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Deployment failed',
                'error': result.stderr
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

    try:
        logger.info("Manual deployment triggered")
        result = subprocess.run(
            [DEPLOY_SCRIPT, 'deploy'],
            capture_output=True,
            text=True,
            timeout=300
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
