# auth_service.py
from ..models.auth import UserAccount, UserWatchedAccount
from ..components.db import db
from ..components.beem import Blockchain
from flask import current_app
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AuthService:
    """Servizio per autenticazione basata su blockchain"""
    
    @staticmethod
    def authenticate_user(username, posting_key, platform):
        """
        Autentica un utente verificando username e posting key sulla blockchain
        
        Args:
            username: Username blockchain
            posting_key: Posting key dell'utente
            platform: 'steem' o 'hive'
            
        Returns:
            dict: {'success': bool, 'user': UserAccount, 'token': str, 'message': str}
        """
        try:            # 1. Verifica che l'account esista sulla blockchain e la posting key sia corretta
            blockchain = Blockchain()
            verification_result = blockchain.verify_account_exists(username, posting_key, platform)
            
            if not verification_result['exists']:
                return {
                    'success': False,
                    'message': verification_result['message']
                }
            
            if not verification_result['key_valid']:
                return {
                    'success': False,
                    'message': verification_result['message']
                }              # 2. Cerca l'utente esistente nel database
            user_account = UserAccount.query.filter_by(
                username=username, 
                platform=platform
            ).first()
            
            if user_account:
                # Utente esistente - verifica posting key
                if not user_account.verify_posting_key(posting_key):
                    return {
                        'success': False,
                        'message': 'Invalid posting key'
                    }
                
                # Aggiorna ultimo login e genera nuovo token
                user_account.last_login = datetime.utcnow()
                token = user_account.generate_session_token()
                
            else:
                # Nuovo utente - crea account
                user_account = UserAccount(
                    username=username,
                    platform=platform,
                    subscription_plan='free',
                    max_watched_users=20,
                    max_daily_votes=10
                )
                user_account.set_posting_key(posting_key)
                user_account.last_login = datetime.utcnow()
                token = user_account.generate_session_token()
                
                db.session.add(user_account)
            
            db.session.commit()
            
            return {
                'success': True,
                'user': user_account,
                'token': token,
                'message': 'Authentication successful'
            }
            
        except Exception as e:
            logger.error(f"Authentication error for {username}: {e}")
            return {
                'success': False,
                'message': f'Authentication failed: {str(e)}'
            }
    
    @staticmethod
    def verify_session_token(token):
        """
        Verifica se un token di sessione è valido
        
        Returns:
            UserAccount or None
        """
        if not token:
            return None
            
        user_account = UserAccount.query.filter_by(session_token=token).first()
        
        if user_account and user_account.is_session_valid() and user_account.is_active:
            return user_account
            
        return None
    
    @staticmethod
    def logout_user(token):
        """Invalida il token di sessione"""
        user_account = UserAccount.query.filter_by(session_token=token).first()
        if user_account:
            user_account.session_token = None
            user_account.session_expires = None
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_user_stats(user_account):
        """Ottieni statistiche dell'utente"""
        watched_count = UserWatchedAccount.query.filter_by(
            user_account_id=user_account.id
        ).count()
        
        # Calcola voti di oggi
        today = datetime.utcnow().date()
        daily_votes = sum(
            account.daily_votes_count for account in 
            UserWatchedAccount.query.filter_by(user_account_id=user_account.id).all()
            if account.last_vote_date and account.last_vote_date.date() == today
        )
        
        return {
            'username': user_account.username,
            'platform': user_account.platform,
            'subscription_plan': user_account.subscription_plan,
            'watched_users': watched_count,
            'max_watched_users': user_account.max_watched_users,
            'daily_votes': daily_votes,
            'max_daily_votes': user_account.max_daily_votes,
            'created_at': user_account.created_at.isoformat(),
            'last_login': user_account.last_login.isoformat() if user_account.last_login else None
        }
