from ..components.db import User, db
from ..models.auth import UserWatchedAccount
from flask import current_app, Flask
import logging
from ..components.logger_config import logger

class UserService:
    """Servizio centralizzato per la gestione degli utenti"""
    
    @staticmethod
    def _ensure_app_context(app=None):
        """Assicura che ci sia un contesto dell'applicazione Flask"""
        if app:
            return app.app_context()
        elif current_app:
            return None  # Siamo già in un contesto
        else:
            logger.error("Nessun contesto app disponibile")
            return None

    @staticmethod
    def get_all_users(user_account_id, app=None):
        """Recupera tutti gli utenti monitorati per l'account specificato"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._get_watched_accounts(user_account_id)
            else:
                return UserService._get_watched_accounts(user_account_id)
        except Exception as e:
            logger.error(f"Errore nel recupero degli utenti: {e}")
            return []

    @staticmethod
    def _get_watched_accounts(user_account_id):
        """Recupera tutti gli account monitorati per l'utente"""
        watched_accounts = UserWatchedAccount.query.filter_by(
            user_account_id=user_account_id
        ).all()
        
        result = {}
        for account in watched_accounts:
            result[account.watched_username] = account.to_dict()
        
        return result

    @staticmethod
    def get_user_by_username(username, user_account_id, app=None):
        """Recupera un utente specifico per l'account"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._get_watched_account(username, user_account_id)
            else:
                return UserService._get_watched_account(username, user_account_id)
        except Exception as e:
            logger.error(f"Errore nel recupero dell'utente {username}: {e}")
            return None

    @staticmethod
    def _get_watched_account(username, user_account_id):
        """Recupera un account monitorato specifico"""
        watched_account = UserWatchedAccount.query.filter_by(
            user_account_id=user_account_id,
            watched_username=username
        ).first()
        
        if watched_account:
            return watched_account.to_dict()
        return None

    @staticmethod
    def get_user_by_post_link(post_link, app=None):
        """Trova un utente basato sul link del post (per compatibilità legacy)"""
        try:
            # Estrai username dal link del post
            if '@' in post_link:
                parts = post_link.split('@')
                if len(parts) > 1:
                    username_part = parts[1].split('/')[0]
                    
                    ctx = UserService._ensure_app_context(app)
                    if ctx:
                        with ctx:
                            # Cerca nel vecchio sistema per compatibilità
                            user = User.query.filter_by(username=username_part).first()
                            if user:
                                return user.data
                    else:
                        user = User.query.filter_by(username=username_part).first()
                        if user:
                            return user.data
                return None
        except Exception as e:
            logger.error(f"Errore nella ricerca dell'utente per il post {post_link}: {e}")
            return None

    @staticmethod
    def add_user(user_data, app=None):
        """Aggiunge un nuovo utente monitorato al database per l'utente autenticato."""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._add_watched_account(user_data)
            else:
                # Siamo già in un contesto
                return UserService._add_watched_account(user_data)
        except Exception as e:
            logger.error(f"Errore nell'aggiunta dell'utente al database: {e}")
            return False
    
    @staticmethod
    def _add_watched_account(user_data):
        """Aggiunge un account monitorato per l'utente autenticato"""
        user_account_id = user_data.get('user_account_id')
        username = user_data.get('username')
        platform = user_data.get('platform', 'hive')
        
        if not user_account_id or not username:
            logger.error("user_account_id e username sono richiesti")
            return False
        
        # Controlla se l'account è già monitorato da questo utente
        existing = UserWatchedAccount.query.filter_by(
            user_account_id=user_account_id,
            watched_username=username,
            platform=platform
        ).first()
        
        if existing:
            logger.info(f"Utente già monitorato: {username} su {platform}. Nessuna aggiunta.")
            return False
        
        # Crea nuovo account monitorato
        new_watched = UserWatchedAccount(
            user_account_id=user_account_id,
            watched_username=username,
            platform=platform,
            vote_delay=user_data.get('voteDelay', '15'),
            vote_weight=user_data.get('voteWeight', 100),
            votes_per_day=user_data.get('votesPerDay', 1),
            use_optimal_time=user_data.get('useOptimalTime', False)
        )
        
        db.session.add(new_watched)
        db.session.commit()
        logger.info(f"Nuovo account monitorato aggiunto: {username} su {platform}")
        return True

    @staticmethod
    def update_user(username, user_data, user_account_id, app=None):
        """Aggiorna i dati di un utente monitorato"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._update_watched_account(username, user_data, user_account_id)
            else:
                # Siamo già in un contesto
                return UserService._update_watched_account(username, user_data, user_account_id)
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento dell'utente {username}: {e}")
            return False
    
    @staticmethod
    def _update_watched_account(username, user_data, user_account_id):
        """Aggiorna un account monitorato"""
        platform = user_data.get('platform', 'hive')
        
        watched_account = UserWatchedAccount.query.filter_by(
            user_account_id=user_account_id,
            watched_username=username,
            platform=platform
        ).first()
        
        if not watched_account:
            logger.warning(f"Account monitorato non trovato: {username} su {platform}")
            return False
        
        # Aggiorna i campi
        watched_account.vote_delay = user_data.get('voteDelay', watched_account.vote_delay)
        watched_account.vote_weight = user_data.get('voteWeight', watched_account.vote_weight)
        watched_account.votes_per_day = user_data.get('votesPerDay', watched_account.votes_per_day)
        watched_account.use_optimal_time = user_data.get('useOptimalTime', watched_account.use_optimal_time)
        
        db.session.commit()
        logger.info(f"Account monitorato aggiornato: {username} su {platform}")
        return True

    @staticmethod
    def delete_user(username, user_account_id, app=None):
        """Elimina un utente monitorato dal database"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._delete_watched_account(username, user_account_id)
            else:
                return UserService._delete_watched_account(username, user_account_id)
        except Exception as e:
            logger.error(f"Errore nell'eliminazione dell'utente {username}: {e}")
            return False

    @staticmethod
    def _delete_watched_account(username, user_account_id):
        """Elimina un account monitorato"""
        watched_account = UserWatchedAccount.query.filter_by(
            user_account_id=user_account_id,
            watched_username=username
        ).first()
        
        if not watched_account:
            logger.warning(f"Account monitorato non trovato: {username}")
            return False
        
        db.session.delete(watched_account)
        db.session.commit()
        logger.info(f"Account monitorato eliminato: {username}")
        return True

    @staticmethod
    def clear_all_users(app=None):
        """Elimina tutti gli utenti dal database (legacy - mantenuto per compatibilità)"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    User.query.delete()
                    db.session.commit()
                    return True
            else:
                User.query.delete()
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Errore nella cancellazione di tutti gli utenti: {e}")
            return False
