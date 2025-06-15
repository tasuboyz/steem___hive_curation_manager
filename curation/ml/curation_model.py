"""
Machine Learning module for curation optimization
Integrates with the existing VoteManager system
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import pickle
import os
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb
from typing import Dict, List, Tuple, Optional
import logging

from ..components.logger_config import logger
from ..components.config import steem_curator as CURATOR
from ..components.beem import Blockchain
from ..utils.vote import VoteManager


class CurationMLModel:
    """
    Machine Learning model for optimizing curation decisions
    Predicts optimal vote timing and expected rewards
    """
    
    def __init__(self, model_type='random_forest', model_path='instance/ml_models/'):
        self.model_type = model_type
        self.model_path = model_path
        self.vote_timing_model = None
        self.reward_prediction_model = None
        self.feature_importance = {}
        
        # Ensure model directory exists
        os.makedirs(model_path, exist_ok=True)
        
        # Initialize models based on type
        self._initialize_models()
        
        # Try to load existing models
        self._load_models()
    
    def _initialize_models(self):
        """Initialize ML models based on specified type"""
        if self.model_type == 'random_forest':
            self.vote_timing_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            self.reward_prediction_model = RandomForestRegressor(
                n_estimators=150,
                max_depth=12,
                min_samples_split=3,
                random_state=42
            )
        elif self.model_type == 'gradient_boosting':
            self.vote_timing_model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=8,
                random_state=42
            )
            self.reward_prediction_model = GradientBoostingRegressor(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=10,
                random_state=42
            )
        elif self.model_type == 'xgboost':
            self.vote_timing_model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
            self.reward_prediction_model = xgb.XGBRegressor(
                n_estimators=250,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def extract_features(self, post_data: Dict, voter_history: List[Dict], 
                        post_stats: Dict = None) -> Dict:
        """
        Extract features from post data and voter history
        
        Args:
            post_data: Post information from blockchain
            voter_history: Historical voting data
            post_stats: Additional post statistics
            
        Returns:
            Dictionary of features for ML model
        """
        features = {}
        
        # Post-based features
        features['post_age_minutes'] = post_data.get('age_minutes', 0)
        features['author_reputation'] = post_data.get('author_rep', 0)
        features['post_length'] = len(post_data.get('body', ''))
        features['title_length'] = len(post_data.get('title', ''))
        features['tags_count'] = len(post_data.get('tags', []))
        features['has_images'] = 1 if 'image' in post_data.get('body', '').lower() else 0
        features['has_links'] = 1 if 'http' in post_data.get('body', '') else 0
        
        # Time-based features
        post_time = post_data.get('created', datetime.now())
        if isinstance(post_time, str):
            post_time = datetime.fromisoformat(post_time.replace('Z', '+00:00'))
        
        features['hour_of_day'] = post_time.hour
        features['day_of_week'] = post_time.weekday()
        features['is_weekend'] = 1 if post_time.weekday() >= 5 else 0
        
        # Voter-based features
        if voter_history:
            # Nuova implementazione: categorizziamo i votanti in base all'rshares
            rshares_values = [v.get('rshares', 0) for v in voter_history]
            vote_delays = [v.get('vote_delay_minutes', 30) for v in voter_history]
            
            features['total_voters'] = len(voter_history)
            
            # Categorizzazione votanti per importanza rshares
            if rshares_values:
                # Definizione soglie per le categorie basate su rshares
                high_rshares_threshold = 1000000    # Votanti di alto valore
                medium_rshares_threshold = 100000   # Votanti di medio valore
                
                # Categorizzazione votanti
                high_value_voters = [v for i, v in enumerate(voter_history) if rshares_values[i] >= high_rshares_threshold]
                medium_value_voters = [v for i, v in enumerate(voter_history) if medium_rshares_threshold <= rshares_values[i] < high_rshares_threshold]
                low_value_voters = [v for i, v in enumerate(voter_history) if rshares_values[i] < medium_rshares_threshold]
                
                # Conteggio per categoria
                features['high_value_voters_count'] = len(high_value_voters)
                features['medium_value_voters_count'] = len(medium_value_voters)
                features['low_value_voters_count'] = len(low_value_voters)
                
                # Rapporti per categoria
                features['high_value_ratio'] = len(high_value_voters) / len(voter_history) if voter_history else 0
                features['medium_value_ratio'] = len(medium_value_voters) / len(voter_history) if voter_history else 0
                
                # Statistiche rshares
                features['max_rshares'] = max(rshares_values) if rshares_values else 0
                features['avg_rshares'] = np.mean(rshares_values) if rshares_values else 0
                features['median_rshares'] = np.median(rshares_values) if rshares_values else 0
                features['total_rshares'] = sum(rshares_values) if rshares_values else 0
                
                # Timing per votanti di alto valore
                if high_value_voters:
                    hv_indices = [i for i, v in enumerate(voter_history) if rshares_values[i] >= high_rshares_threshold]
                    hv_delays = [vote_delays[i] for i in hv_indices]
                    features['high_value_avg_delay'] = np.mean(hv_delays) if hv_delays else 30
                    features['high_value_min_delay'] = np.min(hv_delays) if hv_delays else 30
                else:
                    features['high_value_avg_delay'] = 30
                    features['high_value_min_delay'] = 30
                
                # Timing per votanti di medio valore
                if medium_value_voters:
                    mv_indices = [i for i, v in enumerate(voter_history) if medium_rshares_threshold <= rshares_values[i] < high_rshares_threshold]
                    mv_delays = [vote_delays[i] for i in mv_indices]
                    features['medium_value_avg_delay'] = np.mean(mv_delays) if mv_delays else 30
                else:
                    features['medium_value_avg_delay'] = 30
            else:
                # Default per nessun rshares disponibile
                for feature in ['high_value_voters_count', 'medium_value_voters_count', 'low_value_voters_count',
                               'high_value_ratio', 'medium_value_ratio', 'max_rshares', 'avg_rshares',
                               'median_rshares', 'total_rshares', 'high_value_avg_delay', 'high_value_min_delay',
                               'medium_value_avg_delay']:
                    features[feature] = 0
            
            # Statistiche generali sul timing dei voti (manteniamo queste)
            features['avg_vote_delay'] = np.mean(vote_delays) if vote_delays else 30
            features['min_vote_delay'] = np.min(vote_delays) if vote_delays else 30
            features['vote_delay_std'] = np.std(vote_delays) if len(vote_delays) > 1 else 0
        else:
            # Default values when no voter history
            voter_features = [
                'total_voters', 'high_value_voters_count', 'medium_value_voters_count', 'low_value_voters_count',
                'high_value_ratio', 'medium_value_ratio', 'max_rshares', 'avg_rshares',
                'median_rshares', 'total_rshares', 'avg_vote_delay', 'min_vote_delay', 'vote_delay_std',
                'high_value_avg_delay', 'high_value_min_delay', 'medium_value_avg_delay'
            ]
            for feature in voter_features:
                features[feature] = 0
        
        # Author-based features (if available)
        if post_stats:
            features['author_followers'] = post_stats.get('followers', 0)
            features['author_post_count'] = post_stats.get('post_count', 0)
            features['author_avg_rewards'] = post_stats.get('avg_rewards', 0)
        
        return features
    
    def predict_optimal_timing(self, post_data: Dict, voter_history: List[Dict],
                              post_stats: Dict = None) -> Tuple[float, Dict]:
        """
        Predict optimal voting timing using ML model
        
        Returns:
            Tuple of (optimal_time_minutes, prediction_details)
        """
        if self.vote_timing_model is None:
            logger.warning("Vote timing model not trained. Using fallback logic.")
            return self._fallback_timing_prediction(voter_history)
        
        try:
            features = self.extract_features(post_data, voter_history, post_stats)
            feature_vector = np.array([list(features.values())]).reshape(1, -1)
            
            predicted_time = self.vote_timing_model.predict(feature_vector)[0]
            
            # Ensure prediction is within reasonable bounds
            predicted_time = max(0.5, min(30.0, predicted_time))
            
            # Get feature importance for explanation
            if hasattr(self.vote_timing_model, 'feature_importances_'):
                feature_names = list(features.keys())
                importance_dict = dict(zip(feature_names, self.vote_timing_model.feature_importances_))
                top_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:5]
            else:
                top_features = []
            
            prediction_details = {
                'ml_prediction': True,
                'confidence': self._calculate_prediction_confidence(features),
                'top_influencing_features': top_features,
                'feature_values': features
            }
            
            logger.info(f"ML predicted optimal timing: {predicted_time:.2f} minutes")
            return predicted_time, prediction_details
            
        except Exception as e:
            logger.error(f"Error in ML timing prediction: {str(e)}")
            return self._fallback_timing_prediction(voter_history)
    
    def predict_expected_rewards(self, post_data: Dict, voter_history: List[Dict],
                                vote_timing: float, post_stats: Dict = None) -> Dict:
        """
        Predict expected curation rewards for given timing
        
        Returns:
            Dictionary with reward predictions
        """
        if self.reward_prediction_model is None:
            logger.warning("Reward prediction model not trained.")
            return {'expected_reward': 0, 'ml_prediction': False}
        
        try:
            features = self.extract_features(post_data, voter_history, post_stats)
            features['vote_timing'] = vote_timing  # Add timing as feature
            
            feature_vector = np.array([list(features.values())]).reshape(1, -1)
            predicted_reward = self.reward_prediction_model.predict(feature_vector)[0]
            
            # Ensure non-negative reward prediction
            predicted_reward = max(0, predicted_reward)
            
            return {
                'expected_reward': predicted_reward,
                'ml_prediction': True,
                'confidence': self._calculate_prediction_confidence(features)
            }
            
        except Exception as e:
            logger.error(f"Error in reward prediction: {str(e)}")
            return {'expected_reward': 0, 'ml_prediction': False, 'error': str(e)}
    
    def train_models(self, training_data: List[Dict]) -> Dict:
        """
        Train ML models with historical curation data
        
        Args:
            training_data: List of dictionaries containing:
                - post_data: Post information
                - voter_history: Historical voting data
                - actual_optimal_timing: Known optimal timing (target)
                - actual_reward: Actual curation reward received
                
        Returns:
            Training results and metrics
        """
        if not training_data:
            raise ValueError("No training data provided")
        
        logger.info(f"Training models with {len(training_data)} samples")
        
        # Prepare features and targets
        X_timing, y_timing = [], []
        X_reward, y_reward = [], []
        
        for sample in training_data:
            try:
                features = self.extract_features(
                    sample['post_data'], 
                    sample['voter_history'],
                    sample.get('post_stats')
                )
                
                X_timing.append(list(features.values()))
                y_timing.append(sample['actual_optimal_timing'])
                
                # For reward prediction, add timing as feature
                reward_features = features.copy()
                reward_features['vote_timing'] = sample.get('vote_timing', sample['actual_optimal_timing'])
                X_reward.append(list(reward_features.values()))
                y_reward.append(sample.get('actual_reward', 0))
                
            except KeyError as e:
                logger.warning(f"Skipping training sample due to missing key: {e}")
                continue
        
        if not X_timing:
            raise ValueError("No valid training samples found")
        
        X_timing = np.array(X_timing)
        y_timing = np.array(y_timing)
        X_reward = np.array(X_reward)
        y_reward = np.array(y_reward)
        
        # Train timing model
        timing_scores = cross_val_score(self.vote_timing_model, X_timing, y_timing, cv=5, scoring='neg_mean_squared_error')
        self.vote_timing_model.fit(X_timing, y_timing)
        
        # Train reward model
        reward_scores = cross_val_score(self.reward_prediction_model, X_reward, y_reward, cv=5, scoring='neg_mean_squared_error')
        self.reward_prediction_model.fit(X_reward, y_reward)
        
        # Store feature importance
        if hasattr(self.vote_timing_model, 'feature_importances_'):
            feature_names = list(self.extract_features({}, []).keys())
            self.feature_importance['timing'] = dict(zip(feature_names, self.vote_timing_model.feature_importances_))
        
        # Save trained models
        self._save_models()
        
        results = {
            'timing_cv_score': -np.mean(timing_scores),
            'timing_cv_std': np.std(timing_scores),
            'reward_cv_score': -np.mean(reward_scores),
            'reward_cv_std': np.std(reward_scores),
            'training_samples': len(training_data),
            'model_type': self.model_type
        }
        
        logger.info(f"Model training completed. Timing RMSE: {results['timing_cv_score']:.3f}")
        return results
    
    def _fallback_timing_prediction(self, voter_history: List[Dict]) -> Tuple[float, Dict]:
        """Fallback timing prediction when ML model is not available"""
        if not voter_history:
            return 5.0, {'ml_prediction': False, 'fallback': 'no_voter_history'}
        
        # Simple heuristic based on high-value voters (ora con rshares)
        high_rshares_threshold = 1000000  # Soglia per votanti di alto valore
        high_value_voters = [v for v in voter_history if float(v.get('rshares', 0)) >= high_rshares_threshold]
        if high_value_voters:
            delays = [v.get('vote_delay_minutes', 30) for v in high_value_voters]
            optimal_time = max(1.0, min(delays) - 1.0)  # Vote 1 minute before earliest high-value voter
        else:
            optimal_time = 5.0  # Default
        
        return optimal_time, {'ml_prediction': False, 'fallback': 'heuristic'}
    
    def _calculate_prediction_confidence(self, features: Dict) -> float:
        """Calculate confidence score for predictions"""
        # Simple confidence based on feature completeness and reasonableness
        confidence = 0.5  # Base confidence
        
        # Increase confidence if we have good voter data
        if features.get('total_voters', 0) > 3:
            confidence += 0.1
        
        # Usa le nuove metriche basate su rshares
        if features.get('high_value_voters_count', 0) > 0:
            confidence += 0.2
        if features.get('max_rshares', 0) > 1000000:
            confidence += 0.1
        if features.get('total_rshares', 0) > 5000000:
            confidence += 0.1
            
        return min(1.0, confidence)
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            timing_path = os.path.join(self.model_path, 'vote_timing_model.pkl')
            reward_path = os.path.join(self.model_path, 'reward_prediction_model.pkl')
            
            with open(timing_path, 'wb') as f:
                pickle.dump(self.vote_timing_model, f)
            with open(reward_path, 'wb') as f:
                pickle.dump(self.reward_prediction_model, f)
                
            # Save feature importance
            importance_path = os.path.join(self.model_path, 'feature_importance.pkl')
            with open(importance_path, 'wb') as f:
                pickle.dump(self.feature_importance, f)
                
            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
    
    def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            timing_path = os.path.join(self.model_path, 'vote_timing_model.pkl')
            reward_path = os.path.join(self.model_path, 'reward_prediction_model.pkl')
            
            if os.path.exists(timing_path):
                with open(timing_path, 'rb') as f:
                    self.vote_timing_model = pickle.load(f)
                logger.info("Vote timing model loaded")
            
            if os.path.exists(reward_path):
                with open(reward_path, 'rb') as f:
                    self.reward_prediction_model = pickle.load(f)
                logger.info("Reward prediction model loaded")
                
            # Load feature importance
            importance_path = os.path.join(self.model_path, 'feature_importance.pkl')
            if os.path.exists(importance_path):
                with open(importance_path, 'rb') as f:
                    self.feature_importance = pickle.load(f)
                    
        except Exception as e:
            logger.warning(f"Could not load pre-trained models: {str(e)}")


class TrainingDataCollector:
    """Collects and prepares training data from historical curation activities"""
    
    def __init__(self):
        self.blockchain = Blockchain()
        self.vote_manager = VoteManager()
    
    def collect_historical_data(self, usernames: List[str], days_back: int = 30) -> List[Dict]:
        """
        Collect historical voting data for training
        
        Args:
            usernames: List of usernames to analyze
            days_back: Number of days to look back for data
            
        Returns:
            List of training samples
        """
        logger.info(f"Collecting training data for {len(usernames)} users, {days_back} days back")
        
        training_samples = []
        
        for username in usernames:
            try:
                # Get user's voting history
                votes = self.blockchain.get_user_votes_by_days_back(username, days_back)
                
                for vote in votes:
                    # Get post data at time of vote
                    post_data = self.blockchain.get_comment(vote['comment_author'], vote['comment_permlink'], "steem")

                    # Calcola la data di creazione del post
                    post_created = post_data.get('created')
                    if isinstance(post_created, str):
                        try:
                            post_created = datetime.strptime(post_created, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                        except ValueError:
                            post_created = datetime.fromisoformat(post_created.replace('Z', '+00:00'))

                    # Calcola la differenza in minuti tra voto e creazione post
                    vote_time = vote['timestamp']
                    if isinstance(vote_time, str):
                        try:
                            vote_time = datetime.strptime(vote_time, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                        except ValueError:
                            vote_time = datetime.fromisoformat(vote_time.replace('Z', '+00:00'))

                    minutes_after_post = (vote_time - post_created).total_seconds() / 60 if post_created and vote_time else None

                    # Get voter history for the post
                    post_url = f"@{vote['comment_author']}/{vote['comment_permlink']}"
                    voter_history = self.vote_manager.get_post_voters(post_url)

                    # Calculate actual optimal timing (retrospective analysis)
                    actual_timing = self._calculate_retrospective_optimal_timing(voter_history, vote_time)

                    amount = votes[0]['reward']['amount']
                    precision = votes[0]['reward']['precision']
                    vests_amount = float(amount) / (10 ** precision)
                    curation_reward = self.blockchain.vesting_shares_to_steem(vests_amount)

                    training_sample = {
                        'post_data': post_data,
                        'voter_history': voter_history,
                        'actual_optimal_timing': actual_timing,
                        'vote_timing': minutes_after_post,
                        'actual_reward': curation_reward
                    }

                    training_samples.append(training_sample)
                    
            except Exception as e:
                logger.error(f"Error collecting data for {username}: {str(e)}")
                continue
        
        logger.info(f"Collected {len(training_samples)} training samples")
        return training_samples
    
    def _calculate_retrospective_optimal_timing(self, voter_history: List[Dict], vote_time: datetime) -> float:
        """Calculate what would have been optimal timing based on actual voting patterns"""
        if not voter_history:
            return 5.0
        
        # Utilizziamo rshares invece di steem_vote_value
        # Definiamo la soglia per votanti di alto valore in base a rshares
        high_rshares_threshold = 1000000
        
        # Troviamo votanti ad alto valore di rshares
        high_value_voters = [v for v in voter_history if v.get('rshares', 0) >= high_rshares_threshold]
        
        if high_value_voters:
            # Optimal timing would be just before the earliest high-value voter
            earliest_hv_time = min(v.get('vote_delay_minutes', 30) for v in high_value_voters)
            return max(1.0, earliest_hv_time - 0.5)
        else:
            return 5.0  # Default timing
