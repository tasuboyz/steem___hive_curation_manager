import json
import requests
import logging
import time
import threading
import signal
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from functools import wraps
from .components.logger_config import logger
from .components.config import (
    steem_domain, hive_domain, admin_id, TOKEN, 
    steem_curator, steem_curator_posting_key, 
    hive_curator, hive_curator_posting_key,
    TEST
)
from .components.beem import Blockchain
from .components.instance import local_data_list
from curation.components.factory import create_app
from curation.components.db import User


class WatchdogTimer:
    """Un timer watchdog che monitora se un processo è bloccato."""
    def __init__(self, timeout, callback, *args, **kwargs):
        self.timeout = timeout
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.timer = None
        self.last_reset_time = None
        self.start()
        
    def reset(self):
        """Resetta il timer."""
        if self.timer:
            self.timer.cancel()
        self.last_reset_time = datetime.now()
        self.timer = threading.Timer(self.timeout, self.callback, self.args, self.kwargs)
        self.timer.daemon = True
        self.timer.start()
        
    def start(self):
        """Avvia il timer."""
        self.last_reset_time = datetime.now()
        self.reset()
        
    def stop(self):
        """Ferma il timer."""
        if self.timer:
            self.timer.cancel()
            self.timer = None
            
    def get_elapsed_time(self):
        """Restituisce il tempo trascorso dall'ultimo reset.""" 
        if self.last_reset_time:
            return (datetime.now() - self.last_reset_time).total_seconds()
        return 0


def timeout_handler(timeout=30):
    """Decorator per aggiungere timeout alle funzioni."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                error_msg = f"La funzione {func.__name__} è scaduta dopo {timeout} secondi"
                logger.error(error_msg)
                raise TimeoutError(error_msg)
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        return wrapper
    return decorator


class SocialMediaPublisher:
    def __init__(self):
        self.beem = Blockchain()
        self.published_links = {"steem": set(), "hive": set()}
        self.published_posts = set()
        self.watchdog = None
        self.status_check_interval = 600  # 10 minuti per controllo di stato
        self.operation_timeout = 30  # 30 secondi di timeout per operazioni
        self.last_process_time = datetime.now()
        self.app = create_app()

    def start_watchdog(self):
        """Avvia il sistema di watchdog."""
        self.watchdog = WatchdogTimer(900, self.handle_watchdog_timeout)  # 15 minuti di timeout

    def handle_watchdog_timeout(self):
        """Gestisce il timeout del watchdog."""
        elapsed = (datetime.now() - self.last_process_time).total_seconds() / 60
        message = f"⚠️ ALLARME: Il sistema di curation è bloccato da {elapsed:.1f} minuti! Controllare immediatamente."
        self.log_and_notify(message, critical=True)
        self.log_and_notify("Tentativo di auto-riavvio del sistema di curation...")

    def log_and_notify(self, message, critical=False):
        """Logga un messaggio e lo invia tramite Telegram."""
        if critical:
            logger.critical(message)
        else:
            logger.info(message)
        self.send_telegram_message(TOKEN, admin_id, message)

    def update_user_data(self):
        """Raccoglie gli utenti per piattaforma dal database."""
        platform_users = {"steem": [], "hive": []}
        with self.app.app_context():
            try:
                users = User.query.all()
                for user in users:
                    if 'platform' in user.data:
                        platform_users[user.data['platform']].append(user.username)
            except Exception as e:
                self.log_and_notify(f"Errore nell'aggiornamento dei dati utente: {str(e)}", critical=True)
                # Fallback sui dati locali in caso di errore
                for data in local_data_list:
                    platform_users[data['platform']].append(data['username'])
        return platform_users

    def process_posts(self, platform, usernames):
        """Elabora i post per una specifica piattaforma."""
        new_links = []
        domain = steem_domain if platform == "steem" else hive_domain

        try:
            posts = self.beem.get_posts(usernames, platform)
            new_links = [link for link in posts if link not in self.published_links[platform] and f"{domain}{link}" not in self.published_posts]
            
            if new_links:
                # Aggiorna entrambi i set di tracking dei post
                self.published_links[platform].update(new_links)
                # Aggiungi anche i link completi con dominio al set globale
                # for link in new_links:
                #     published_posts.add(f"{domain}{link}")
                
                # Processa solo i nuovi link
                for link in new_links:
                    self.handle_voting(platform, f"{domain}{link}")

            self.last_process_time = datetime.now()
            if self.watchdog:
                self.watchdog.reset()

        except Exception as e:
            self.log_and_notify(f"Errore nell'elaborazione dei post per {platform}: {str(e)}", critical=True)

    def handle_voting(self, platform, post_link):
        """Gestisce il processo di voto per un post."""
        try:
            user_data = next((user for user in local_data_list if user['username'] in post_link), None)
            if not user_data:
                return
            
            vote_delay = user_data['voteDelay']
            vote_weight = user_data['voteWeight']
            curator = steem_curator if platform == "steem" else hive_curator
            curator_key = steem_curator_posting_key if platform == "steem" else hive_curator_posting_key
            
            # Tentiamo di ottenere le informazioni del profilo con timeout
            try:
                if platform == "steem":
                    curator_info = self.beem.get_steem_profile_info(curator)
                else:
                    curator_info = self.beem.get_hive_profile_info(curator)
            except Exception as e:
                error_msg = f"Impossibile ottenere informazioni del profilo per {curator}: {str(e)}"
                logger.error(error_msg)
                self.send_telegram_message(TOKEN, admin_id, f"⚠️ {error_msg}")
                return
            
            last_vote_time = curator_info['result'][0]['last_vote_time']
            old_voting_power = curator_info['result'][0]['voting_power'] / 100
            voting_power = self.beem.calculate_voting_power(last_vote_time, old_voting_power)
            
            telegram_message = f"[{platform.upper()}] (VP: {voting_power:.1f} MIN: {vote_delay})\n{post_link}"
            self.send_telegram_message(TOKEN, admin_id, telegram_message)
            
            # Ottieni author e permlink con gestione degli errori
            try:
                if platform == "steem":
                    author = self.beem.get_steem_author(post_link)
                    permlink = self.beem.get_steem_permlink(post_link)
                else:
                    author = self.beem.get_hive_author(post_link)
                    permlink = self.beem.get_hive_permlink(post_link)
            except Exception as e:
                error_msg = f"Impossibile ottenere author/permlink per {post_link}: {str(e)}"
                logger.error(error_msg)
                self.send_telegram_message(TOKEN, admin_id, f"⚠️ {error_msg}")
                return
            
            if voting_power > 89:
                try:
                    post = self.beem.get_comment(author=author, permalink=permlink, blockchain=platform)
                    created_time = post['created']
                    target_vote_time = created_time + timedelta(minutes=vote_delay)
                    time_until_vote = target_vote_time - datetime.now(timezone.utc)
                    minutes_until_vote = time_until_vote.total_seconds() / 60
                    
                    if minutes_until_vote > 0:
                        # Se l'attesa è lunga, inviamo un messaggio
                        if minutes_until_vote > 10:
                            self.send_telegram_message(TOKEN, admin_id, f"Attesa di {minutes_until_vote:.1f} minuti prima del voto...")
                        
                        logger.info(f"Attesa di {minutes_until_vote:.1f} minuti prima del voto...")
                        # Dividiamo il tempo di attesa in intervalli più brevi per resettare il watchdog
                        remaining_minutes = minutes_until_vote
                        while remaining_minutes > 0:
                            sleep_time = min(1, remaining_minutes)  # Dormi massimo 1 minuto alla volta
                            time.sleep(sleep_time * 60)
                            remaining_minutes -= sleep_time
                            # Reset del watchdog durante l'attesa
                            if self.watchdog:
                                self.watchdog.reset()
                                
                    if TEST:
                        logger.info(f"Voting: {author} {permlink} {vote_weight}")
                    else:
                        # Esegui il voto con gestione degli errori
                        try:
                            if platform == "steem":
                                self.beem.like_steem_post(voter=steem_curator, voted=author, permlink=permlink, private_posting_key=steem_curator_posting_key, weight=vote_weight)
                            else:
                                self.beem.like_hive_post(voter=hive_curator, voted=author, permlink=permlink, private_posting_key=hive_curator_posting_key, weight=vote_weight)
                            self.send_telegram_message(TOKEN, admin_id, "✅ Votato con successo!")
                        except Exception as e:
                            error_msg = f"Errore durante il voto per {post_link}: {str(e)}"
                            logger.error(error_msg)
                            self.send_telegram_message(TOKEN, admin_id, f"⚠️ {error_msg}")
                except Exception as e:
                    error_msg = f"Errore durante la preparazione al voto per {post_link}: {str(e)}"
                    logger.error(error_msg)
                    self.send_telegram_message(TOKEN, admin_id, f"⚠️ {error_msg}")
            else:
                self.send_telegram_message(TOKEN, admin_id, f"⚠️ Non votato! Voting power troppo basso: {voting_power:.1f}%")
            
            # Aggiorna il timestamp dell'ultima operazione completata
            self.last_process_time = datetime.now()
            
        except TimeoutError:
            error_msg = f"Timeout durante il processo di voto per {post_link}"
            logger.error(error_msg)
            self.send_telegram_message(TOKEN, admin_id, f"⚠️ {error_msg}")
        except Exception as e:
            error_msg = f"Errore imprevisto durante il voto per {post_link}: {str(e)}"
            logger.error(error_msg)
            self.send_telegram_message(TOKEN, admin_id, f"⚠️ {error_msg}")

    def publish_posts(self):
        """Controlla e pubblica nuovi post periodicamente."""
        self.start_watchdog()
        last_status_check = datetime.now()

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                while True:
                    current_time = datetime.now()
                    if (current_time - last_status_check).total_seconds() > self.status_check_interval:
                        uptime_minutes = (current_time - self.last_process_time).total_seconds() / 60
                        self.log_and_notify(f"✅ Sistema di curation attivo. Ultima attività: {uptime_minutes:.1f} minuti fa.")
                        last_status_check = current_time

                    platform_users = self.update_user_data()
                    futures = {executor.submit(self.process_posts, platform, users): platform for platform, users in platform_users.items() if users}

                    for future in as_completed(futures):
                        platform = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            self.log_and_notify(f"Errore durante l'elaborazione dei post per {platform}: {str(e)}", critical=True)

                    if self.watchdog:
                        self.watchdog.reset()

                    time.sleep(5)

        except KeyboardInterrupt:
            if self.watchdog:
                self.watchdog.stop()
            logger.info("Sistema di curation fermato manualmente")
        except Exception as e:
            if self.watchdog:
                self.watchdog.stop()
            self.log_and_notify(f"Errore critico nel sistema di curation: {str(e)}", critical=True)

    def send_telegram_message(self, bot_token, chat_id, message):
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"
            response = requests.get(url, timeout=10)  # Aggiungi un timeout di 10 secondi
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore invio messaggio Telegram: {e}")
            return False
