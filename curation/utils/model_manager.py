import os
from pathlib import Path
from xgboost import XGBClassifier, XGBRegressor
from ..components.logger_config import logger

class ModelManager:
    def __init__(self, model_dir='models'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.clf_path = self.model_dir / 'classifier_model.json'
        self.reg_path = self.model_dir / 'regressor_model.json'
        self.clf_model = None
        self.reg_model = None
        
    def load_models(self):
        """Load existing classification and regression models."""
        try:
            self.clf_model = XGBClassifier()
            self.reg_model = XGBRegressor()
            
            if self.clf_path.exists() and self.reg_path.exists():
                self.clf_model.load_model(str(self.clf_path))
                self.reg_model.load_model(str(self.reg_path))
                logger.info("Successfully loaded existing models")
                return self.clf_model, self.reg_model
            else:
                logger.error("Model files not found")
                return None, None
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return None, None

    def train_models(self, X_train, y_clf_train, X_reg_train, y_reg_train):
        """Train both classifier and regressor models."""
        try:
            # Train classifier
            self.clf_model = self._train_classifier(X_train, y_clf_train)
            
            # Train regressor
            self.reg_model = self._train_regressor(X_reg_train, y_reg_train)
            
            return self.clf_model, self.reg_model
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return None, None

    def _train_classifier(self, X_train, y_train):
        """Train and save classifier model."""
        try:
            if self.clf_path.exists():
                model = XGBClassifier()
                model.load_model(str(self.clf_path))
                model.fit(X_train, y_train, xgb_model=str(self.clf_path))
            else:
                model = XGBClassifier()
                model.fit(X_train, y_train)
            
            model.save_model(str(self.clf_path))
            return model
        except Exception as e:
            logger.error(f"Error training classifier: {e}")
            return None

    def _train_regressor(self, X_train, y_train):
        """Train and save regressor model."""
        try:
            if self.reg_path.exists():
                model = XGBRegressor()
                model.load_model(str(self.reg_path))
                model.fit(X_train, y_train, xgb_model=str(self.reg_path))
            else:
                model = XGBRegressor()
                model.fit(X_train, y_train)
            
            model.save_model(str(self.reg_path))
            return model
        except Exception as e:
            logger.error(f"Error training regressor: {e}")
            return None

    def predict(self, features, author=None, historical_delays=None):
        """Make predictions using both models."""
        try:
            if self.clf_model is None or self.reg_model is None:
                raise ValueError("Models not loaded")
            
            # Make vote decision
            vote_decision = self.clf_model.predict(features)[0]
            
            if vote_decision == 0:
                return {
                    "vote_decision": 0,
                    "optimal_vote_delay_minutes": None,
                    "predicted_efficiency": None
                }
            
            # Get optimal delay
            optimal_delay = 1440  # default 24h
            if historical_delays and author in historical_delays:
                optimal_delay = int(historical_delays[author])
            
            # Predict efficiency with optimal delay
            features_with_delay = features.copy()
            features_with_delay["vote_delay"] = optimal_delay
            predicted_eff = self.reg_model.predict(features_with_delay)[0]
            
            return {
                "vote_decision": 1,
                "optimal_vote_delay_minutes": optimal_delay,
                "predicted_efficiency": predicted_eff
            }
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return None