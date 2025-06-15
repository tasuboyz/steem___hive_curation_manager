#!/usr/bin/env python3
"""
Script per inizializzare il database con le nuove tabelle per l'autenticazione multi-utente
"""

import sys
import os

# Aggiungi il percorso del progetto al Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curation.components.factory import create_app
from curation.components.db import db
from curation.models.auth import UserAccount, UserWatchedAccount

def init_database():
    """Inizializza il database con le nuove tabelle"""
    app = create_app()
    
    with app.app_context():
        try:
            # Crea tutte le tabelle
            db.create_all()
            print("✅ Database initialized successfully!")
            print("📊 Created tables:")
            print("   - user_account (for authentication)")
            print("   - user_watched_account (for user's watched accounts)")
            print("   - user (existing, for backward compatibility)")
            print("   - settings (existing)")
            print("   - delegator (existing)")
            
            # Verifica che le tabelle siano state create
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['user_account', 'user_watched_account']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"⚠️  Warning: Some tables were not created: {missing_tables}")
            else:
                print("✅ All required tables created successfully!")
                
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Initializing database for multi-user authentication...")
    success = init_database()
    
    if success:
        print("\n🎉 Database initialization completed!")
        print("\n📝 Next steps:")
        print("1. Run the application: python app.py")
        print("2. Navigate to http://localhost:8089/login.html")
        print("3. Login with your Steem/Hive username and posting key")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)
