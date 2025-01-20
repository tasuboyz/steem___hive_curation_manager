# db.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    data = db.Column(db.JSON, nullable=False)  # Assicurati di avere il tipo di dato corretto

    def __repr__(self):
        return f'<User  {self.username}>'