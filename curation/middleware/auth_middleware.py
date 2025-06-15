# auth_middleware.py
from functools import wraps
from flask import request, jsonify, g
from ..services.auth_service import AuthService

def auth_required(f):
    """Decorator per richiedere autenticazione"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Cerca il token nell'header Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Se non c'è nell'header, cerca nei cookie
        if not token:
            token = request.cookies.get('session_token')
        
        if not token:
            return jsonify({'error': 'Authentication token required'}), 401
        
        # Verifica il token
        user_account = AuthService.verify_session_token(token)
        if not user_account:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Aggiungi l'utente al contesto della richiesta
        g.current_user = user_account
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """Ottieni l'utente corrente dal contesto"""
    return getattr(g, 'current_user', None)

def check_user_limits(max_watched=None, max_daily_votes=None):
    """Decorator per verificare i limiti dell'utente"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Verifica limite utenti monitorati
            if max_watched:
                from ..models.auth import UserWatchedAccount
                watched_count = UserWatchedAccount.query.filter_by(
                    user_account_id=user.id
                ).count()
                
                if watched_count >= user.max_watched_users:
                    return jsonify({
                        'error': f'Maximum watched users limit reached ({user.max_watched_users})',
                        'upgrade_required': True
                    }), 403
            
            # Verifica limite voti giornalieri
            if max_daily_votes:
                stats = AuthService.get_user_stats(user)
                if stats['daily_votes'] >= user.max_daily_votes:
                    return jsonify({
                        'error': f'Daily vote limit reached ({user.max_daily_votes})',
                        'upgrade_required': True
                    }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
