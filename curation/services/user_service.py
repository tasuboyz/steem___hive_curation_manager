from ..components.db import User, db
from ..models.auth import UserWatchedAccount
from flask import current_app, Flask
import logging
from ..components.logger_config import logger

class UserService:
    """Servizio centralizzato per la gestione degli utenti"""
    
    @staticmethod
    def _ensure_app_context(app=None):
        """Assicura che ci sia un contesto dell'applicazione attivo
        
        Se app è fornito, crea un nuovo contesto.
        Se current_app è disponibile, lo usa.
        Ritorna il contesto (per uso con 'with') o None se già in un contesto.
        """
        if app is not None:
            return app.app_context()
        
        try:
            # Verifica se siamo già in un contesto
            _ = current_app._get_current_object()
            return None
        except RuntimeError:
            logger.error("Nessun contesto applicazione disponibile e nessun app fornito")
            raise
    
    @staticmethod
    def get_users_by_platform(platform=None, app=None):
        """Recupera utenti filtrati per piattaforma (o tutti se platform=None)"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    users = User.query.all()
                    if platform:
                        return [u for u in users if u.data.get('platform') == platform]
                    return users
            else:
                # Siamo già in un contesto
                users = User.query.all()
                if platform:
                    return [u for u in users if u.data.get('platform') == platform]
                return users
        except Exception as e:
            logger.error(f"Errore nel recupero degli utenti dal database: {e}")
            return []
    
    @staticmethod
    def get_usernames_by_platform(platform, app=None):
        """Restituisce una lista di nomi utente per la piattaforma specificata"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    users = User.query.all()
                    return [u.username for u in users if u.data.get('platform') == platform]
            else:                # Siamo già in un contesto
                users = User.query.all()
                return [u.username for u in users if u.data.get('platform') == platform]
        except Exception as e:
            logger.error(f"Errore nel recupero dei nomi utente dal database: {e}")
            return []
    
    @staticmethod
    def get_user_by_username(username, user_account_id, app=None):
        """Recupera i dati di un account monitorato specifico per l'utente autenticato"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._get_watched_account_by_username(username, user_account_id)
            else:
                # Siamo già in un contesto
                return UserService._get_watched_account_by_username(username, user_account_id)
        except Exception as e:
            logger.error(f"Errore nel recupero dell'account monitorato {username} per user_account_id {user_account_id}: {e}")
            return None
    
    @staticmethod
    def _get_watched_account_by_username(username, user_account_id):
        """Ottiene un account monitorato specifico"""
        watched_account = UserWatchedAccount.query.filter_by(
            user_account_id=user_account_id,
            watched_username=username
        ).first()
        
        if not watched_account:
            return None
        
        return {
            'username': watched_account.watched_username,
            'platform': watched_account.platform,
            'voteDelay': watched_account.vote_delay,
            'voteWeight': watched_account.vote_weight,
            'votesPerDay': watched_account.votes_per_day,
            'useOptimalTime': watched_account.use_optimal_time,
            'dailyVotesCount': watched_account.daily_votes_count,
            'lastVoteDate': watched_account.last_vote_date.isoformat() if watched_account.last_vote_date else None,
            'timestamp': watched_account.created_at.isoformat() if watched_account.created_at else None
        }

    @staticmethod
    def get_user_for_post(post_link, app=None):
        """Trova l'utente associato a un post tramite il link"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    users = User.query.all()
                    for user in users:
                        if user.username in post_link:
                            return user.data
                    return None
            else:
                # Siamo già in un contesto
                users = User.query.all()
                for user in users:
                    if user.username in post_link:                        return user.data
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
        """Elimina un account monitorato (UserWatchedAccount) per l'utente autenticato"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    watched = UserWatchedAccount.query.filter_by(watched_username=username, user_account_id=user_account_id).first()
                    if watched:
                        db.session.delete(watched)
                        db.session.commit()
                        return True
                    return False
            else:
                watched = UserWatchedAccount.query.filter_by(watched_username=username, user_account_id=user_account_id).first()
                if watched:
                    db.session.delete(watched)
                    db.session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Errore nell'eliminazione dell'account monitorato {username} per user_account_id {user_account_id}: {e}")
            return False
    
    @staticmethod
    def get_all_users(curator_username, platform=None, app=None):
        """Recupera tutti gli account monitorati per il curatore loggato (username e piattaforma)"""
        try:
            ctx = UserService._ensure_app_context(app)
            if ctx:
                with ctx:
                    return UserService._get_all_watched_accounts_by_curator(curator_username, platform)
            else:
                return UserService._get_all_watched_accounts_by_curator(curator_username, platform)
        except Exception as e:
            logger.error(f"Errore nel recupero degli account monitorati per il curatore {curator_username} su {platform}: {e}")
            return {}

    @staticmethod
    def _get_all_watched_accounts_by_curator(curator_username, platform=None):
        from ..models.auth import UserAccount, UserWatchedAccount
        query = UserAccount.query.filter_by(username=curator_username)
        if platform:
            query = query.filter_by(platform=platform)
        user = query.first()
        if not user:
            return {}
        watched_accounts = UserWatchedAccount.query.filter_by(user_account_id=user.id)
        if platform:
            watched_accounts = watched_accounts.filter_by(platform=platform)
        watched_accounts = watched_accounts.all()
        result = {}
        for account in watched_accounts:
            result[account.watched_username] = {
                'platform': account.platform,
                'voteDelay': account.vote_delay,
                'voteWeight': account.vote_weight,
                'votesPerDay': account.votes_per_day,
                'useOptimalTime': account.use_optimal_time,
                'dailyVotesCount': account.daily_votes_count,
                'lastVoteDate': account.last_vote_date.isoformat() if account.last_vote_date else None,
                'timestamp': account.created_at.isoformat() if account.created_at else None
            }
        return result

    @staticmethod
    def get_all_watched_authors(platform=None, app=None):
        """Restituisce la lista di tutti gli autori monitorati (watched_username distinti) opzionalmente filtrati per piattaforma."""
        from ..models.auth import UserWatchedAccount
        ctx = UserService._ensure_app_context(app)
        if ctx:
            with ctx:
                query = UserWatchedAccount.query
                if platform:
                    query = query.filter_by(platform=platform)
                authors = query.with_entities(UserWatchedAccount.watched_username).distinct().all()
        else:
            query = UserWatchedAccount.query
            if platform:
                query = query.filter_by(platform=platform)
            authors = query.with_entities(UserWatchedAccount.watched_username).distinct().all()
        # Estrae solo il nome autore dalla tupla
        return [a[0] for a in authors]