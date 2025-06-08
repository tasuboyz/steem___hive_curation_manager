"""
ML Integration module for VoteManager
Enhances existing vote timing logic with machine learning predictions
"""

from .curation_model import CurationMLModel, TrainingDataCollector
from ..components.logger_config import logger
from typing import Dict, List, Tuple, Optional
from curation.utils.vote import VoteManager
from curation.components.beem import Blockchain

class MLEnhancedVoteManager:
    """
    Extends VoteManager with ML capabilities while maintaining compatibility
    """
    
    def __init__(self, model_type='random_forest'):
        self.vote_manager = VoteManager()
        self.blockchain_connector = Blockchain()
        self.ml_model = CurationMLModel(model_type=model_type)
        self.training_collector = TrainingDataCollector()
        
        # Settings
        self.use_ml_prediction = True
        self.ml_weight = 0.7  # Weight for ML prediction vs traditional algorithm
        self.minimum_confidence = 0.6  # Minimum confidence to use ML prediction
      
    def get_optimal_vote_time_enhanced(self, post_url: str, max_top_voters: int = 5, 
                                     curator_username: str = None) -> Dict:
        """
        Enhanced optimal timing calculation using both traditional and ML approaches
        
        Returns enhanced timing analysis with ML insights
        """
        # Get traditional analysis first - need to get voters data then calculate timing
        voters_data = self.vote_manager.get_post_voters(post_url, min_importance=0.0)
        traditional_result = self.vote_manager.calculate_optimal_vote_time(
            voters_data, max_top_voters=max_top_voters, curator_username=curator_username
        )
        
        if not self.use_ml_prediction:
            traditional_result['ml_enhanced'] = False
            return traditional_result
        
        try:
            # Get post data and voter history for ML
            post_data = self._extract_post_data_from_url(post_url)
            voters_data = self.vote_manager.get_post_voters(post_url, use_cache=True)
            
            if not post_data or not voters_data:
                logger.warning("Insufficient data for ML prediction, using traditional approach")
                traditional_result['ml_enhanced'] = False
                return traditional_result
            
            # Get ML prediction
            ml_timing, ml_details = self.ml_model.predict_optimal_timing(
                post_data, voters_data
            )
            
            # Get reward prediction
            reward_prediction = self.ml_model.predict_expected_rewards(
                post_data, voters_data, ml_timing
            )
            
            # Combine predictions if ML confidence is sufficient
            if ml_details.get('confidence', 0) >= self.minimum_confidence:
                # Weighted combination of traditional and ML predictions
                traditional_timing = traditional_result['optimal_time']
                combined_timing = (
                    self.ml_weight * ml_timing + 
                    (1 - self.ml_weight) * traditional_timing
                )
                
                # Update result with ML enhancements
                enhanced_result = traditional_result.copy()
                enhanced_result.update({
                    'optimal_time': round(combined_timing, 1),
                    'ml_enhanced': True,
                    'ml_prediction': ml_timing,
                    'traditional_prediction': traditional_timing,
                    'ml_confidence': ml_details.get('confidence', 0),
                    'combination_weight': self.ml_weight,
                    'expected_reward': reward_prediction.get('expected_reward', 0),
                    'ml_explanation': self._generate_ml_explanation(ml_details),
                    'top_ml_features': ml_details.get('top_influencing_features', [])
                })
                
                # Update explanation
                ml_explanation = f"\n🤖 ML Enhanced: {ml_timing:.1f}min (confidence: {ml_details.get('confidence', 0):.2f})"
                enhanced_result['explanation'] += ml_explanation
                
                logger.info(f"ML-enhanced timing: Traditional={traditional_timing:.1f}, ML={ml_timing:.1f}, Combined={combined_timing:.1f}")
                return enhanced_result
            else:
                # Low confidence, use traditional approach but add ML info
                traditional_result.update({
                    'ml_enhanced': False,
                    'ml_prediction': ml_timing,
                    'ml_confidence': ml_details.get('confidence', 0),
                    'ml_low_confidence_reason': 'Confidence below threshold'
                })
                return traditional_result
                
        except Exception as e:
            logger.error(f"Error in ML-enhanced prediction: {str(e)}")
            traditional_result['ml_enhanced'] = False
            traditional_result['ml_error'] = str(e)
            return traditional_result
    
    def train_model_from_user_history(self, usernames: List[str], days_back: int = 30) -> Dict:
        """
        Train the ML model using historical data from specified users
        
        Args:
            usernames: List of usernames to collect training data from
            days_back: Number of days to look back for training data
            
        Returns:
            Training results and metrics
        """
        logger.info(f"Starting ML model training for users: {usernames}")
        
        try:
            # Collect training data
            training_data = self.training_collector.collect_historical_data(usernames, days_back)
            
            if len(training_data) < 10:
                raise ValueError(f"Insufficient training data: {len(training_data)} samples (minimum 10 required)")
            
            # Train the model
            training_results = self.ml_model.train_models(training_data)
            
            # Enable ML predictions after successful training
            self.use_ml_prediction = True
            
            logger.info(f"ML model training completed successfully: {training_results}")
            return training_results
            
        except Exception as e:
            logger.error(f"Error in ML model training: {str(e)}")
            self.use_ml_prediction = False
            return {'error': str(e), 'training_completed': False}
    
    def update_ml_settings(self, use_ml: bool = None, ml_weight: float = None, 
                          min_confidence: float = None):
        """Update ML-related settings"""
        if use_ml is not None:
            self.use_ml_prediction = use_ml
            logger.info(f"ML prediction {'enabled' if use_ml else 'disabled'}")
        
        if ml_weight is not None:
            self.ml_weight = max(0.0, min(1.0, ml_weight))
            logger.info(f"ML weight set to {self.ml_weight}")
        
        if min_confidence is not None:
            self.minimum_confidence = max(0.0, min(1.0, min_confidence))
            logger.info(f"Minimum ML confidence set to {self.minimum_confidence}")
    
    def get_ml_model_info(self) -> Dict:
        """Get information about the current ML model state"""
        return {
            'ml_enabled': self.use_ml_prediction,
            'model_type': self.ml_model.model_type,
            'ml_weight': self.ml_weight,
            'minimum_confidence': self.minimum_confidence,
            'timing_model_trained': self.ml_model.vote_timing_model is not None,
            'reward_model_trained': self.ml_model.reward_prediction_model is not None,
            'feature_importance': self.ml_model.feature_importance
        }
    
    def get_ml_info(self) -> Dict:
        """
        Get comprehensive ML information for the dashboard
        Alias for get_ml_model_info with additional statistics
        """
        base_info = self.get_ml_model_info()
        
        # Add additional dashboard-specific information
        additional_info = {
            'last_training_time': getattr(self.ml_model, 'last_training_time', None),
            'training_data_size': getattr(self.ml_model, 'training_data_size', 0),
            'model_performance': getattr(self.ml_model, 'model_performance', {}),
            'prediction_count': getattr(self.ml_model, 'prediction_count', 0)
        }
        
        base_info.update(additional_info)
        return base_info
    
    def train_ml_model(self, usernames: List[str], days_back: int = 30) -> Dict:
        """
        Train ML model - alias for train_model_from_user_history
        Expected by the routes
        """
        return self.train_model_from_user_history(usernames, days_back)
    
    def analyze_prediction_comparison(self, post_url: str) -> Dict:
        """
        Compare traditional vs ML predictions for analysis
        Useful for model evaluation and debugging
        """
        try:
            # Get both predictions separately
            voters_data = self.vote_manager.get_post_voters(post_url)
        
            traditional_result = self.vote_manager.calculate_optimal_vote_time(voters_data)
            
            post_data = self._extract_post_data_from_url(post_url)
            voters_data = self.vote_manager.get_post_voters(post_url)
            
            if post_data and voters_data:
                ml_timing, ml_details = self.ml_model.predict_optimal_timing(post_data, voters_data)
                reward_prediction = self.ml_model.predict_expected_rewards(post_data, voters_data, ml_timing)
                
                return {
                    'traditional_timing': traditional_result['optimal_time'],
                    'ml_timing': ml_timing,
                    'difference': abs(traditional_result['optimal_time'] - ml_timing),
                    'ml_confidence': ml_details.get('confidence', 0),
                    'expected_reward': reward_prediction.get('expected_reward', 0),
                    'traditional_explanation': traditional_result['explanation'],
                    'ml_features': ml_details.get('top_influencing_features', []),
                    'comparison_valid': True
                }
            else:
                return {
                    'comparison_valid': False,
                    'error': 'Insufficient data for ML prediction'
                }
                
        except Exception as e:
            return {
                'comparison_valid': False,
                'error': str(e)
            }
    
    def compare_predictions(self, post_url: str) -> Dict:
        """
        Compare predictions - alias for analyze_prediction_comparison
        Expected by the routes
        """
        return self.analyze_prediction_comparison(post_url)
    
    def _extract_post_data_from_url(self, post_url: str) -> Optional[Dict]:
        """Extract post data from URL for ML processing"""
        try:
            # Parse URL to get author and permlink
            if '@' in post_url and '/' in post_url:
                parts = post_url.split('/')
                author_part = [p for p in parts if p.startswith('@')]
                if author_part:
                    author = author_part[0][1:]  # Remove @
                    permlink = parts[-1] if parts[-1] != author_part[0] else parts[-2]
                    
                    # Get post data from blockchain
                    return self.blockchain_connector.get_comment(author, permlink, "steem")
            
            return None
        except Exception as e:
            logger.error(f"Error extracting post data from URL {post_url}: {str(e)}")
            return None
    
    def _generate_ml_explanation(self, ml_details: Dict) -> str:
        """Generate human-readable explanation of ML prediction"""
        explanation = "ML Analysis: "
        
        top_features = ml_details.get('top_influencing_features', [])
        if top_features:
            feature_explanations = []
            for feature, importance in top_features[:3]:  # Top 3 features
                if 'voter' in feature.lower():
                    feature_explanations.append(f"voter patterns ({importance:.2f})")
                elif 'time' in feature.lower():
                    feature_explanations.append(f"timing factors ({importance:.2f})")
                elif 'value' in feature.lower():
                    feature_explanations.append(f"value metrics ({importance:.2f})")
                else:
                    feature_explanations.append(f"{feature} ({importance:.2f})")
            
            explanation += f"Key factors: {', '.join(feature_explanations)}"
        else:
            explanation += "Based on comprehensive post and voter analysis"
        
        return explanation
      
    def get_post_voters(self, post_url: str, min_importance: float = 0.0, use_cache: bool = True) -> List[Dict]:
        """
        Delegate to underlying VoteManager for post voters data
        """
        return self.vote_manager.get_post_voters(post_url, min_importance, use_cache=use_cache)
    
    def calculate_optimal_vote_time(self, voters_data: List[Dict]) -> Dict:
        """
        Delegate to underlying VoteManager for basic optimal vote time calculation
        For ML-enhanced calculations, use get_optimal_vote_time_enhanced instead
        """
        return self.vote_manager.calculate_optimal_vote_time(voters_data)
    
    def get_optimal_vote_time(self, post_url: str, max_top_voters: int = 5, 
                             curator_username: str = None) -> Dict:
        """
        Get optimal vote time - will use ML enhancement if available and configured
        This method provides the enhanced interface that doesn't exist in base VoteManager
        """
        if self.use_ml_prediction:
            return self.get_optimal_vote_time_enhanced(post_url, max_top_voters, curator_username)
        else:
            # For traditional approach, we need to get voters first, then calculate timing
            voters_data = self.vote_manager.get_post_voters(post_url, min_importance=0.0)
            return self.vote_manager.calculate_optimal_vote_time(
                voters_data, 
                max_top_voters=max_top_voters, 
                curator_username=curator_username
            )


def integrate_ml_with_vote_manager(vote_manager, blockchain_connector, 
                                 model_type='random_forest') -> MLEnhancedVoteManager:
    """
    Factory function to create ML-enhanced vote manager
    
    Args:
        vote_manager: Existing VoteManager instance
        blockchain_connector: Blockchain connector instance
        model_type: Type of ML model to use ('random_forest', 'gradient_boosting', 'xgboost')
        
    Returns:
        MLEnhancedVoteManager instance
    """
    return MLEnhancedVoteManager(vote_manager, blockchain_connector, model_type)
