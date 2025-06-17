from .services.user_service import UserService
from .components.beem import Blockchain
from .models.auth import UserAccount, UserWatchedAccount
from .components.logger_config import logger
from .components.db import db
from flask import Flask
from datetime import datetime, timedelta
import time
import threading
from beem.account import Account
from beem.vote import Vote
from beem import Steem, Hive

class Sniper:
    def __init__(self, platform="steem", app=None):
        self.platform = platform
        self.app = app or Flask(__name__)
        self.blockchain = Blockchain()
        self.posts = []
        self.processed_posts = set()  # Per evitare di processare lo stesso post più volte
        self.vote_queue = []  # Coda per i voti schedulati

    def run(self):
        """Esegue il ciclo principale di sniping"""
        with self.app.app_context():
            # 1. Recupera tutti gli autori monitorati per la piattaforma
            watched_authors = set(UserService.get_all_watched_authors(self.platform))
            logger.info(f"Autori monitorati per {self.platform}: {len(watched_authors)} autori")

            if not watched_authors:
                logger.info("Nessun autore monitorato, sniping saltato")
                return

            # 2. Recupera i nuovi post dalla blockchain
            new_posts = self.blockchain.get_new_posts()
            logger.info(f"Trovati {len(new_posts)} nuovi post")

            # 3. Per ogni nuovo post, verifica se l'autore è monitorato
            posts_to_vote = 0
            for post in new_posts:
                author = post['author']
                if author in watched_authors:
                    logger.info(f"Nuovo post da autore monitorato: {author} - {post['permlink']}")
                    # 4. Trova tutti i curator che seguono questo autore
                    curators_data = self.get_curators_for_author(author)
                    for curator_data in curators_data:
                        curator = curator_data['curator']
                        watch_settings = curator_data['settings']
                        self.schedule_vote(curator, post, watch_settings)
                        posts_to_vote += 1
            
            logger.info(f"Pianificati {posts_to_vote} voti")
            
            # 5. Processa i voti in coda
            self.process_vote_queue()

    def get_curators_for_author(self, author):
        """Restituisce tutti i curatori che monitorano l'autore con le loro impostazioni"""
        accounts = UserWatchedAccount.query.filter_by(
            watched_username=author, 
            platform=self.platform
        ).all()
        
        result = []
        for watch_account in accounts:
            curator = UserAccount.query.get(watch_account.user_account_id)
            if curator and curator.is_active:
                result.append({
                    'curator': curator,
                    'settings': watch_account
                })
        
        return result

    def schedule_vote(self, curator, post, watch_settings):
        """Pianifica un voto considerando delay e impostazioni"""
        post_time = datetime.strptime(post['created'], '%Y-%m-%dT%H:%M:%S')
        
        # Calcola quando votare
        if watch_settings.use_optimal_time or watch_settings.vote_delay == 'auto':
            # TODO: Implementare logica tempo ottimale
            vote_delay_minutes = 15  # Default per ora
        else:
            vote_delay_minutes = int(watch_settings.vote_delay)
        
        vote_time = post_time + timedelta(minutes=vote_delay_minutes)
        
        # Controlla limiti giornalieri
        if self.check_daily_limits(curator, watch_settings):
            vote_data = {
                'curator': curator,
                'post': post,
                'settings': watch_settings,
                'vote_time': vote_time,
                'weight': watch_settings.vote_weight
            }
            self.vote_queue.append(vote_data)
            logger.info(f"Voto pianificato per {curator.username} su {post['author']}/{post['permlink']} alle {vote_time}")
        else:
            logger.info(f"Limite giornaliero raggiunto per {curator.username}")

    def check_daily_limits(self, curator, watch_settings):
        """Verifica se il curatore può ancora votare oggi"""
        today = datetime.utcnow().date()
        
        # Controlla se l'account ha già votato oggi per questo autore
        if watch_settings.last_vote_date and watch_settings.last_vote_date.date() == today:
            if watch_settings.daily_votes_count >= watch_settings.votes_per_day:
                return False
        
        # Controlla limite globale giornaliero del curatore
        total_votes_today = db.session.query(UserWatchedAccount).filter_by(
            user_account_id=curator.id
        ).filter(
            db.func.date(UserWatchedAccount.last_vote_date) == today
        ).count()
        
        return total_votes_today < curator.max_daily_votes

    def process_vote_queue(self):
        """Processa la coda dei voti, votando quelli pronti"""
        now = datetime.utcnow()
        votes_cast = 0
        
        for vote_data in self.vote_queue[:]:
            if vote_data['vote_time'] <= now:
                success = self.cast_vote(vote_data)
                if success:
                    votes_cast += 1
                self.vote_queue.remove(vote_data)
        
        if votes_cast > 0:
            logger.info(f"Eseguiti {votes_cast} voti")

    def cast_vote(self, vote_data):
        """Esegue il voto effettivo sulla blockchain"""
        try:
            curator = vote_data['curator']
            post = vote_data['post']
            settings = vote_data['settings']
            weight = vote_data['weight']
            
            # Simula il voto (sostituire con logica reale)
            logger.info(f"[VOTO] {curator.username} vota {post['author']}/{post['permlink']} al {weight}%")
            
            # Aggiorna contatori nel database
            settings.daily_votes_count = (settings.daily_votes_count or 0) + 1
            settings.last_vote_date = datetime.utcnow()
            db.session.commit()
            
            # TODO: Implementare voto reale con beem
            # vote = Vote(post['author'] + '/' + post['permlink'], weight, account=curator.username)
            # vote.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Errore nel voto: {e}")
            return False

if __name__ == "__main__":
    from curation.components.factory import create_app
    
    app = create_app()
    
    # Esegui sniper per entrambe le piattaforme
    steem_sniper = Sniper(platform="steem", app=app)
    hive_sniper = Sniper(platform="hive", app=app)
    
    logger.info("Avvio sniper per Steem e Hive...")
    
    # Esegui in loop continuo
    while True:
        try:
            steem_sniper.run()
            hive_sniper.run()
            time.sleep(60)  # Aspetta 1 minuto prima del prossimo ciclo
        except KeyboardInterrupt:
            logger.info("Sniper fermato manualmente")
            break
        except Exception as e:
            logger.error(f"Errore nello sniper: {e}")
            time.sleep(10)  # Aspetta 10 secondi in caso di errore
