# auth.py - Modelli per autenticazione semplificata
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from ..components.db import db
import secrets
import hashlib

class UserAccount(db.Model):
    """Account utente basato su username blockchain e posting key"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # Username blockchain
    platform = db.Column(db.String(10), nullable=False)  # 'steem' o 'hive'
    posting_key_hash = db.Column(db.String(128), nullable=False)  # Hash della posting key
    session_token = db.Column(db.String(255), unique=True, nullable=True)
    session_expires = db.Column(db.DateTime, nullable=True)
    subscription_plan = db.Column(db.String(20), default='free')
    max_watched_users = db.Column(db.Integer, default=5)
    max_daily_votes = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_posting_key(self, posting_key):
        """Salva l'hash della posting key"""
        self.posting_key_hash = hashlib.sha256(posting_key.encode()).hexdigest()
    
    def verify_posting_key(self, posting_key):
        """Verifica la posting key"""
        return hashlib.sha256(posting_key.encode()).hexdigest() == self.posting_key_hash
    
    def generate_session_token(self):
        """Genera un nuovo token di sessione"""
        self.session_token = secrets.token_urlsafe(32)
        self.session_expires = datetime.utcnow() + timedelta(days=30)
        return self.session_token
    
    def is_session_valid(self):
        """Controlla se la sessione è ancora valida"""
        return (self.session_token and 
                self.session_expires and 
                self.session_expires > datetime.utcnow())
    
    def __repr__(self):
        return f'<UserAccount {self.username}@{self.platform}>'

# Modifichiamo il modello User esistente per includere l'account_id
class UserWatchedAccount(db.Model):
    """Account monitorati da un utente"""
    __tablename__ = 'user_watched_account'
    
    id = db.Column(db.Integer, primary_key=True)
    user_account_id = db.Column(db.Integer, db.ForeignKey('user_account.id'), nullable=False)
    watched_username = db.Column(db.String(80), nullable=False)
    platform = db.Column(db.String(10), nullable=False)
    vote_delay = db.Column(db.String(10), nullable=False)  # minuti o 'auto'
    vote_weight = db.Column(db.Integer, nullable=False)
    votes_per_day = db.Column(db.Integer, default=1)
    use_optimal_time = db.Column(db.Boolean, default=False)
    daily_votes_count = db.Column(db.Integer, default=0)
    last_vote_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazione con l'account utente
    user_account = db.relationship('UserAccount', backref='watched_accounts')
    
    # Indice composto per evitare duplicati
    __table_args__ = (db.UniqueConstraint('user_account_id', 'watched_username', 'platform'),)
    
    def to_dict(self):
        return {
            'username': self.watched_username,
            'platform': self.platform,
            'voteDelay': self.vote_delay,
            'voteWeight': self.vote_weight,
            'votesPerDay': self.votes_per_day,
            'useOptimalTime': self.use_optimal_time,
            'dailyVotesCount': self.daily_votes_count,
            'lastVoteDate': self.last_vote_date.isoformat() if self.last_vote_date else None
        }
