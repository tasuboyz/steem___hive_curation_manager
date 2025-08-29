#!/usr/bin/env python3
"""Test web interface backend for Steem/Hive curation system.

This Flask app provides a web interface to test the curation system
by analyzing post voters and sending them to n8n webhook.
"""
import logging
import sys
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os

# Add the parent directory to Python path to import curation modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from curation.components.beem import Blockchain
from curation.utils.vote import VoteManager
from curation.utils.webhook import send_post_voters_to_n8n

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_web")

# Custom log handler to capture logs for web display
class WebLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def emit(self, record):
        self.logs.append(self.format(record))
    
    def get_logs(self):
        return self.logs.copy()
    
    def clear_logs(self):
        self.logs.clear()

web_log_handler = WebLogHandler()
web_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files (CSS, JS)"""
    return send_from_directory('.', filename)

@app.route('/api/test-curation', methods=['POST'])
def test_curation():
    """API endpoint to test the curation system"""
    try:
        # Clear previous logs
        web_log_handler.clear_logs()
        
        # Add our handler to capture logs
        root_logger = logging.getLogger()
        root_logger.addHandler(web_log_handler)
        
        # Get request data
        data = request.get_json()
        sample = data.get('sample', '')
        platform = data.get('platform', 'steem')
        min_importance = data.get('min_importance', 0.1)
        
        logger.info(f"Starting test with sample: {sample}")
        logger.info(f"Platform: {platform}, Min importance: {min_importance}")
        
        # Parse the sample string
        try:
            if sample.startswith('@'):
                _, rest = sample.split('@', 1)
            else:
                rest = sample
            author, permlink = rest.split('/', 1)
        except Exception as e:
            error_msg = f"Unable to parse sample string: {e}"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'logs': web_log_handler.get_logs()
            }), 400
        
        # Initialize blockchain and vote manager
        blockchain = Blockchain()
        vote_manager = VoteManager(blockchain_connector_instance=blockchain)
        
        # Get previous post
        previous_permlink = permlink
        try:
            previous_posts = blockchain.get_previous_author_posts(author, platform, limit=1)
            if previous_posts and len(previous_posts) > 0:
                previous_permlink = previous_posts[0].get('permlink', permlink)
                logger.info(f"Found previous post: @{author}/{previous_permlink}")
            else:
                logger.info("No previous post found, using current permlink")
        except Exception as e:
            logger.warning(f"Error getting previous post: {e}. Using current permlink")
        
        # Get post voters
        post_voters = []
        try:
            post_identifier = f"@{author}/{previous_permlink}"
            logger.info(f"Getting voters for {post_identifier} (min_importance={min_importance})")
            post_voters = vote_manager.get_post_voters(post_identifier, min_importance=min_importance)
            logger.info(f"Found {len(post_voters)} voters")
        except Exception as e:
            logger.error(f"Error getting post voters: {e}")
            post_voters = []
        
        # Send to webhook
        webhook_response = None
        try:
            resp = send_post_voters_to_n8n(author, previous_permlink, post_voters)
            webhook_response = {
                'status_code': getattr(resp, 'status_code', None),
                'text': getattr(resp, 'text', '')[:500] if hasattr(resp, 'text') else ''
            }
            logger.info(f"Webhook response: {webhook_response['status_code']}")
        except Exception as e:
            logger.warning(f"Webhook failed: {e}")
            webhook_response = {
                'error': str(e),
                'status_code': None
            }
        
        # Prepare response
        response_data = {
            'author': author,
            'permlink': permlink,
            'previous_permlink': previous_permlink,
            'platform': platform,
            'min_importance': min_importance,
            'post_voters': post_voters,
            'webhook_response': webhook_response,
            'logs': web_log_handler.get_logs()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            'error': f"Unexpected error: {str(e)}",
            'logs': web_log_handler.get_logs()
        }), 500
    
    finally:
        # Remove our handler
        root_logger = logging.getLogger()
        if web_log_handler in root_logger.handlers:
            root_logger.removeHandler(web_log_handler)

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Test web interface is running'})

if __name__ == '__main__':
    print("Starting Steem/Hive Curation Test Web Interface...")
    print("Access the interface at: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
