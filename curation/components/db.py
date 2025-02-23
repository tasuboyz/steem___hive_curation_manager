# db.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Configure the SQLite database
DATABASE_URI = 'sqlite:///site.db'  # Path to the SQLite database file
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    data = db.Column(db.JSON, nullable=False)  # Ensure the correct data type

    def __repr__(self):
        return f'<User  {self.username}>'

class Delegator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    vesting_shares = db.Column(db.String(20), nullable=False)  # Memorizza l'ultimo importo
    last_operation_id = db.Column(db.String(50), unique=True)  # Previene duplicati
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Delegator  {self.username}>'

class AuthorStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(10), nullable=False)  # 'steem' or 'hive'
    author = db.Column(db.String(80), nullable=False)
    avg_efficiency = db.Column(db.Float, default=0.0)
    avg_payout = db.Column(db.Float, default=0.0)
    reputation = db.Column(db.Float, default=0.0)
    post_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)  # Percentuale di post con efficiency > 50
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('platform', 'author', name='unique_author_platform'),)

    def __repr__(self):
        return f'<AuthorStats {self.platform}:{self.author}>'