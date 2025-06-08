"""
Flask routes for ML functionality
Adds ML management endpoints to the existing application
"""

from flask import Blueprint, jsonify, request, render_template, current_app
from curation.components.logger_config import logger
from curation.ml.ml_integration import MLEnhancedVoteManager
from curation.components.beem import Blockchain
from curation.utils.vote import VoteManager
from curation.services.settings_service import SettingsService
import json

# Create blueprint for ML routes
ml_bp = Blueprint('ml', __name__, url_prefix='/api/ml')


def get_enhanced_vote_manager():
    """Get or create enhanced vote manager instance"""
    if not hasattr(current_app, '_enhanced_vote_manager'):
        blockchain_connector = Blockchain(app=current_app)
        current_app._enhanced_vote_manager = MLEnhancedVoteManager()
    return current_app._enhanced_vote_manager


@ml_bp.route('/status', methods=['GET'])
def ml_status():
    """Get ML model status and information"""
    try:
        enhanced_vm = get_enhanced_vote_manager()
        ml_info = enhanced_vm.get_ml_info()
        
        return jsonify({
            'success': True,
            'data': ml_info
        })
    except Exception as e:
        logger.error(f"Error getting ML status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/train', methods=['POST'])
def train_model():
    """Train ML model with specified parameters"""
    try:
        data = request.get_json()
        
        # Get training parameters
        usernames = data.get('usernames', [])
        days_back = data.get('days_back', 30)
        
        if not usernames:
            return jsonify({
                'success': False,
                'error': 'No usernames provided for training'
            }), 400
        
        # Start training
        enhanced_vm = get_enhanced_vote_manager()
        results = enhanced_vm.train_ml_model(usernames, days_back)
        
        if 'error' in results:
            return jsonify({
                'success': False,
                'error': results['error']
            }), 500
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        logger.error(f"Error training ML model: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/predict/compare', methods=['POST'])
def compare_predictions():
    """Compare traditional vs ML predictions for a post"""
    try:
        data = request.get_json()
        post_url = data.get('post_url')
        
        if not post_url:
            return jsonify({
                'success': False,
                'error': 'Post URL is required'
            }), 400
        
        enhanced_vm = get_enhanced_vote_manager()
        comparison = enhanced_vm.compare_predictions(post_url)
        
        return jsonify({
            'success': True,
            'data': comparison
        })
        
    except Exception as e:
        logger.error(f"Error comparing predictions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/settings', methods=['GET', 'POST'])
def ml_settings():
    """Get or update ML settings"""
    try:
        enhanced_vm = get_enhanced_vote_manager()
        if request.method == 'GET':
            # Get current settings
            settings = {
                'ml_enabled': SettingsService.get_setting('ml_enabled', default=True),
                'ml_weight': SettingsService.get_setting('ml_weight', default=0.7),
                'ml_min_confidence': SettingsService.get_setting('ml_min_confidence', default=0.6),
                'model_type': SettingsService.get_setting('ml_model_type', default='random_forest')
            }
            
            return jsonify({
                'success': True,
                'data': settings
            })
            
        else:  # POST
            data = request.get_json()
              # Update settings
            if 'ml_enabled' in data:
                SettingsService.set_setting('ml_enabled', data['ml_enabled'], app=current_app)
                enhanced_vm.update_ml_settings(use_ml=data['ml_enabled'])
            
            if 'ml_weight' in data:
                SettingsService.set_setting('ml_weight', data['ml_weight'], app=current_app)
                enhanced_vm.update_ml_settings(ml_weight=data['ml_weight'])
            
            if 'ml_min_confidence' in data:
                SettingsService.set_setting('ml_min_confidence', data['ml_min_confidence'], app=current_app)
                enhanced_vm.update_ml_settings(min_confidence=data['ml_min_confidence'])
            
            if 'model_type' in data:
                SettingsService.set_setting('ml_model_type', data['model_type'], app=current_app)
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error with ML settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/features/importance', methods=['GET'])
def feature_importance():
    """Get feature importance from trained model"""
    try:
        enhanced_vm = get_enhanced_vote_manager()
        ml_info = enhanced_vm.get_ml_info()
        
        importance_data = ml_info.get('feature_importance', {})
        
        return jsonify({
            'success': True,
            'data': importance_data
        })
        
    except Exception as e:
        logger.error(f"Error getting feature importance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Template route for ML management interface
@ml_bp.route('/dashboard')
def ml_dashboard():
    """Render ML management dashboard"""
    return render_template('ml_dashboard.html')


def register_ml_routes(app):
    """Register ML routes with Flask app"""
    app.register_blueprint(ml_bp)
    logger.info("ML routes registered successfully")
