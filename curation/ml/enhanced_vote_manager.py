"""
Example integration of ML capabilities with existing VoteManager
This demonstrates how to enhance the current system with machine learning
"""

from flask import current_app
from curation.utils.vote import VoteManager
from curation.components.beem import Blockchain
from curation.ml.ml_integration import MLEnhancedVoteManager as MLCore
from curation.components.logger_config import logger


class EnhancedVoteManager(VoteManager):
    """
    Extended VoteManager that includes ML capabilities
    Maintains full backward compatibility while adding ML features
    """
    
    def __init__(self, blockchain_connector_instance=None):
        # Initialize parent class
        super().__init__(blockchain_connector_instance)
        
        # Initialize ML enhancement
        self.ml_enhanced = None
        self._initialize_ml()
      
    def _initialize_ml(self):
        """Initialize ML capabilities if available"""
        try:
            self.ml_enhanced = MLCore(
                vote_manager=self,
                blockchain_connector=self.blockchain_connector,
                model_type='random_forest'  # Can be configured
            )
            logger.info("ML enhancement initialized successfully")
        except Exception as e:
            logger.warning(f"ML enhancement not available: {str(e)}")
            self.ml_enhanced = None
    
    def get_optimal_vote_time(self, post_url, max_top_voters=5, curator_username=None):
        """
        Enhanced version that uses ML when available, falls back to traditional method
        """
        if self.ml_enhanced and self._should_use_ml():
            try:
                return self.ml_enhanced.get_optimal_vote_time_enhanced(
                    post_url, max_top_voters, curator_username
                )
            except Exception as e:
                logger.warning(f"ML prediction failed, using traditional method: {str(e)}")
        
        # Fall back to traditional method
        return super().get_optimal_vote_time(post_url, max_top_voters, curator_username)
    
    def _should_use_ml(self):
        """Determine whether to use ML prediction based on settings"""
        try:
            # Check if ML is enabled in settings (you could store this in database)
            # For now, default to True if ML is available
            return self.ml_enhanced is not None
        except:
            return False
    
    def train_ml_model(self, usernames, days_back=30):
        """
        Train the ML model with historical data
        
        Args:
            usernames: List of usernames to collect training data from
            days_back: Number of days to look back
            
        Returns:
            Training results
        """
        if not self.ml_enhanced:
            return {'error': 'ML enhancement not available'}
        
        return self.ml_enhanced.train_model_from_user_history(usernames, days_back)
    
    def get_ml_info(self):
        """Get information about ML model status"""
        if not self.ml_enhanced:
            return {'ml_available': False}
        
        info = self.ml_enhanced.get_ml_model_info()
        info['ml_available'] = True
        return info
    
    def compare_predictions(self, post_url):
        """Compare traditional vs ML predictions"""
        if not self.ml_enhanced:
            return {'error': 'ML enhancement not available'}
        
        return self.ml_enhanced.analyze_prediction_comparison(post_url)


# Example usage and integration patterns
def create_enhanced_vote_manager(blockchain_connector=None):
    """Factory function to create enhanced vote manager"""
    return EnhancedVoteManager(blockchain_connector)


def integrate_ml_with_existing_system():
    """
    Example of how to integrate ML with existing Flask app
    """
    
    # This would typically be called during app initialization
    def setup_ml_vote_manager(app):
        """Setup ML-enhanced vote manager for Flask app"""
        with app.app_context():
            # Get existing blockchain connector
            blockchain_connector = Blockchain(app=app)
            
            # Create enhanced vote manager
            enhanced_vm = create_enhanced_vote_manager(blockchain_connector)
            
            # Store in app context for use in routes
            app.config['ENHANCED_VOTE_MANAGER'] = enhanced_vm
            
            return enhanced_vm
    
    return setup_ml_vote_manager


# Training script example
def train_model_script():
    """
    Example script for training the ML model
    Can be run as a separate process or scheduled job
    """
    from curation.components.factory import create_app
    
    app = create_app()
    
    with app.app_context():
        # Initialize enhanced vote manager
        blockchain_connector = Blockchain(app=app)
        enhanced_vm = EnhancedVoteManager(blockchain_connector)
        
        # Define users to collect training data from
        training_users = [
            'curie', 'ocd', 'cervantes', 'blocktrades', 
            'steemitblog', 'good-karma', 'acidyo'
        ]
        
        print("Starting ML model training...")
        print(f"Collecting data from {len(training_users)} users...")
        
        # Train the model
        results = enhanced_vm.train_ml_model(training_users, days_back=30)
        
        if 'error' in results:
            print(f"Training failed: {results['error']}")
        else:
            print("Training completed successfully!")
            print(f"Timing model RMSE: {results.get('timing_cv_score', 'N/A'):.3f}")
            print(f"Reward model RMSE: {results.get('reward_cv_score', 'N/A'):.3f}")
            print(f"Training samples: {results.get('training_samples', 'N/A')}")
        
        # Show model info
        ml_info = enhanced_vm.get_ml_info()
        print("\nML Model Status:")
        for key, value in ml_info.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    # Run training script
    train_model_script()
