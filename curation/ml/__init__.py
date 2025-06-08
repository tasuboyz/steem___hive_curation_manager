"""
Machine Learning module for Steem/Hive Curation Manager

This module provides advanced machine learning capabilities for optimizing
curation decisions, including:

- Optimal vote timing prediction
- Expected reward estimation  
- Historical pattern analysis
- Feature extraction from blockchain data

Models supported:
- Random Forest (recommended for most use cases)
- Gradient Boosting (good balance of performance and interpretability)  
- XGBoost (high performance for large datasets)

Usage:
    from curation.ml import CurationMLModel, MLEnhancedVoteManager
    
    # Create ML-enhanced vote manager
    ml_vote_manager = MLEnhancedVoteManager(vote_manager, blockchain_connector)
    
    # Train model with historical data
    training_results = ml_vote_manager.train_model_from_user_history(
        usernames=['user1', 'user2'], 
        days_back=30
    )
    
    # Get ML-enhanced predictions
    result = ml_vote_manager.get_optimal_vote_time_enhanced(post_url)
"""

from .curation_model import CurationMLModel, TrainingDataCollector
from .ml_integration import MLEnhancedVoteManager, integrate_ml_with_vote_manager

__all__ = [
    'CurationMLModel',
    'TrainingDataCollector', 
    'MLEnhancedVoteManager',
    'integrate_ml_with_vote_manager'
]

__version__ = '1.0.0'
