# db.py
from flask_sqlalchemy import SQLAlchemy

# Configure the SQLite database
DATABASE_URI = 'sqlite:///site.db'  # Path to the SQLite database file
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    data = db.Column(db.JSON, nullable=False)  # Ensure the correct data type

    def __repr__(self):
        return f'<User  {self.username}>'

class Delegator(db.Model):  # Nuovo modello per i delegatori
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f'<Delegator {self.username}>'