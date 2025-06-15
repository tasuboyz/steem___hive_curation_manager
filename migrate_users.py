#!/usr/bin/env python3
"""
Script di migrazione per trasferire i dati esistenti al nuovo sistema multi-utente
"""

import sys
import os

# Aggiungi il percorso del progetto al Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curation.components.factory import create_app
from curation.components.db import db, User
from curation.models.auth import UserAccount, UserWatchedAccount
from datetime import datetime

def migrate_existing_users():
    """Migra gli utenti esistenti al nuovo sistema"""
    app = create_app()
    
    with app.app_context():
        try:
            # Ottieni tutti gli utenti esistenti
            existing_users = User.query.all()
            
            if not existing_users:
                print("📝 No existing users found to migrate.")
                return True
                
            print(f"🔄 Found {len(existing_users)} users to migrate...")
            
            # Crea un account utente "legacy" per gli utenti esistenti
            # Questi utenti dovranno effettuare il login per associare la loro posting key
            
            migrated_count = 0
            skipped_count = 0
            
            for user in existing_users:
                try:
                    user_data = user.data
                    username = user.username
                    platform = user_data.get('platform', 'steem')
                    
                    # Controlla se esiste già un UserAccount per questo utente
                    existing_account = UserAccount.query.filter_by(
                        username=f"legacy_{username}_{platform}"
                    ).first()
                    
                    if existing_account:
                        print(f"⏭️  Skipping {username} - already migrated")
                        skipped_count += 1
                        continue
                    
                    # Crea un account legacy temporaneo
                    # Nota: questi utenti dovranno rifare il login per fornire la posting key
                    legacy_account = UserAccount(
                        username=f"legacy_{username}_{platform}",
                        platform=platform,
                        posting_key_hash="legacy_account_needs_reauth",  # Segnaposto
                        subscription_plan='free',
                        max_watched_users=5,
                        max_daily_votes=10,
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(legacy_account)
                    db.session.flush()  # Per ottenere l'ID
                    
                    # Migra i dati dell'utente monitorato
                    watched_account = UserWatchedAccount(
                        user_account_id=legacy_account.id,
                        watched_username=username,
                        platform=platform,
                        vote_delay=str(user_data.get('voteDelay', 5)),
                        vote_weight=user_data.get('voteWeight', 100),
                        votes_per_day=user_data.get('votesPerDay', 1),
                        use_optimal_time=user_data.get('useOptimalTime', False),
                        daily_votes_count=user_data.get('dailyVotesCount', 0),
                        last_vote_date=datetime.fromisoformat(user_data['lastVoteDate']) if user_data.get('lastVoteDate') else None,
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(watched_account)
                    migrated_count += 1
                    
                    print(f"✅ Migrated user: {username} ({platform})")
                    
                except Exception as e:
                    print(f"❌ Error migrating user {username}: {e}")
                    db.session.rollback()
                    continue
            
            # Commit tutte le modifiche
            db.session.commit()
            
            print(f"\n📊 Migration Summary:")
            print(f"   ✅ Migrated: {migrated_count} users")
            print(f"   ⏭️  Skipped: {skipped_count} users")
            print(f"   📝 Note: Legacy users need to login again to provide posting keys")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

def cleanup_legacy_accounts():
    """Pulisce gli account legacy dopo che gli utenti hanno fatto il login"""
    app = create_app()
    
    with app.app_context():
        try:
            legacy_accounts = UserAccount.query.filter(
                UserAccount.username.like('legacy_%')
            ).filter_by(posting_key_hash="legacy_account_needs_reauth").all()
            
            if not legacy_accounts:
                print("📝 No legacy accounts found to cleanup.")
                return True
            
            print(f"🧹 Found {len(legacy_accounts)} legacy accounts to cleanup...")
            
            for account in legacy_accounts:
                # Rimuovi gli account watched associati
                UserWatchedAccount.query.filter_by(user_account_id=account.id).delete()
                # Rimuovi l'account legacy
                db.session.delete(account)
            
            db.session.commit()
            print(f"✅ Cleaned up {len(legacy_accounts)} legacy accounts")
            
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate existing users to new auth system')
    parser.add_argument('--migrate', action='store_true', help='Migrate existing users')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup legacy accounts')
    
    args = parser.parse_args()
    
    if args.migrate:
        print("🚀 Starting user migration...")
        success = migrate_existing_users()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            print("\n📝 Important notes:")
            print("1. Existing users are migrated as 'legacy' accounts")
            print("2. They need to login again with their posting key")
            print("3. After login, the system will create proper authenticated accounts")
            print("4. Run with --cleanup flag to remove legacy accounts after migration")
        else:
            print("\n❌ Migration failed!")
            sys.exit(1)
    
    elif args.cleanup:
        print("🧹 Starting legacy account cleanup...")
        success = cleanup_legacy_accounts()
        
        if success:
            print("\n🎉 Cleanup completed successfully!")
        else:
            print("\n❌ Cleanup failed!")
            sys.exit(1)
    
    else:
        print("Please specify --migrate or --cleanup")
        parser.print_help()
