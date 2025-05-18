import requests
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from .components.logger_config import logger
from .components.config import steem_domain, hive_domain
from .components.beem import Blockchain
from .services.user_service import UserService
from .services.settings_service import SettingsService


class SocialMediaPublisher:
    def __init__(self, app=None):
        self.app = app
        # Inizializza le impostazioni per i test
        self.is_test_mode = True
        # Carica la modalità test dal database se possibile
        try:
            self.is_test_mode = SettingsService.is_test_mode(app)
        except:
            # In caso di errore, usa il valore predefinito
            self.is_test_mode = True
            
        # Inizializza l'istanza di blockchain
        self.beem = Blockchain(app=self.app)
        self.published_links = {"steem": set(), "hive": set()}
        self.running = True
    
    def update_user_data(self):
        """Raccoglie gli utenti per piattaforma usando direttamente il database."""
        platform_users = {"steem": [], "hive": []}
        
        # Recupera gli utenti per steem
        steem_usernames = UserService.get_usernames_by_platform("steem", self.app)
        platform_users["steem"] = steem_usernames
        
        # Recupera gli utenti per hive
        hive_usernames = UserService.get_usernames_by_platform("hive", self.app)
        platform_users["hive"] = hive_usernames
        
        logger.debug(f"Utenti caricati: {len(steem_usernames)} su Steem, {len(hive_usernames)} su Hive")
        return platform_users

    def process_posts(self, platform, usernames):
        """Elabora i post per una specifica piattaforma."""
        if not usernames:
            logger.debug(f"Nessun utente trovato per la piattaforma {platform}")
            return
            
        try:
            new_links = []
            domain = steem_domain if platform == "steem" else hive_domain
            posts = self.beem.get_posts(usernames, platform)
            
            for link in posts:
                if link not in self.published_links[platform]:
                    new_links.append(link)
                    self.published_links[platform].add(link)
            
            for link in new_links:
                post_link = f"{domain}{link}"
                try:
                    self.handle_voting(platform, post_link)
                except Exception as e:
                    logger.error(f"Errore durante il voto su {post_link}: {str(e)}")
        except Exception as e:
            logger.error(f"Errore durante l'elaborazione dei post per {platform}: {str(e)}")
    
    def handle_voting(self, platform, post_link):
        """Gestisce il processo di voto per un post."""
        # Usa UserService per trovare l'utente associato al post
        user_data = UserService.get_user_for_post(post_link, self.app)
        
        if not user_data:
            logger.debug(f"Nessun utente trovato per il post {post_link}")
            return
        
        try:
            use_optimal_time = user_data.get('useOptimalTime', False) or user_data.get('voteDelay') == 'auto'
            vote_weight = user_data['voteWeight']
            curator_info_db = self.beem.get_curator_info(platform)
            curator = curator_info_db['username']
            curator_key = curator_info_db['posting_key']
            curator_active_key = curator_info_db.get('active_key')
            curator_profile = self.beem.get_steem_profile_info(curator) if platform == "steem" else self.beem.get_hive_profile_info(curator)
            last_vote_time = curator_profile['result'][0]['last_vote_time']
            old_voting_power = curator_profile['result'][0]['voting_power'] / 100
            voting_power = self.beem.calculate_voting_power(last_vote_time, old_voting_power)
            author = self.beem.get_steem_author(post_link) if platform == "steem" else self.beem.get_hive_author(post_link)
            permlink = self.beem.get_steem_permlink(post_link) if platform == "steem" else self.beem.get_hive_permlink(post_link)
            
            # Controlla se stiamo utilizzando il tempo ottimale
            if use_optimal_time:
                # Ottieni i post precedenti dell'autore
                previous_posts = self.beem.get_previous_author_posts(author, platform, limit=5)
                
                if previous_posts and len(previous_posts) > 0:
                    # Raccoglie i dati dei votanti dai post precedenti
                    all_voters_data = []
                    for post in previous_posts:
                        # Ottieni i votanti del post precedente
                        post_permlink = post.get('permlink', '')
                        if post_permlink:
                            post_voters = self.beem.get_post_voters(f"@{author}/{post_permlink}", min_importance=0.1)
                            all_voters_data.extend(post_voters)
                    
                    # Calcola il tempo ottimale basato sui post precedenti
                    optimal_vote_info = self.beem.calculate_optimal_vote_time(all_voters_data)
                    
                    # Usa il tempo di voto ottimale
                    vote_delay = optimal_vote_info['optimal_time']
                    vote_window = optimal_vote_info['vote_window']
                    vote_explanation = optimal_vote_info['explanation'] + " (basato su post precedenti)"
                    
                    telegram_message = f"[{platform.upper()}] (VP: {voting_power:.2f}, OPTIMAL: {vote_delay} min)\n{vote_explanation}\n{post_link}"
                else:
                    # Se non ci sono post precedenti, usa un valore di default
                    vote_delay = 5
                    vote_window = (4.5, 5.5)
                    telegram_message = f"[{platform.upper()}] (VP: {voting_power:.2f}, DEFAULT: {vote_delay} min)\nNessun post precedente trovato\n{post_link}"
            else:
                # Usa il tempo di ritardo specificato dall'utente
                vote_delay = user_data['voteDelay']
                telegram_message = f"[{platform.upper()}] (VP: {voting_power:.2f}, DELAY: {vote_delay} min)\n{post_link}"

                # Recupera dinamicamente admin_ids e bot_token
                admin_ids = SettingsService.get_setting('admin_ids', default='', app=self.app)
                bot_token = SettingsService.get_setting('bot_token', default='', app=self.app)
                self.send_telegram_message(bot_token, admin_ids, telegram_message)

            if voting_power > 89:
                post = self.beem.get_comment(author=author, permalink=permlink, blockchain=platform)
                # Controlla se il curatore ha già votato il post
                already_voted = any(v['voter'] == curator for v in post['votes'])
                if already_voted:
                    logger.info(f"{curator} ha già votato il post {author}/{permlink} su {platform}")
                    self.send_telegram_message(bot_token, admin_ids, "Already voted!")
                    return
                created_time = post['created']
                target_vote_time = created_time + timedelta(minutes=vote_delay)
                time_until_vote = target_vote_time - datetime.now(timezone.utc)
                minutes_until_vote = time_until_vote.total_seconds() / 60
                
                if not self.running:
                    logger.info("Publisher fermato durante l'attesa del voto")
                    return
                
                if minutes_until_vote > 0:
                    logger.info(f"Waiting {minutes_until_vote:.1f} minutes before voting...")
                    self._safe_sleep(minutes_until_vote * 60)
                
                if self.is_test_mode:
                    logger.info(f"Voting: {author} {permlink} {vote_weight}")
                else:
                    if platform == "steem":
                        self.beem.like_steem_post(voter=curator, voted=author, permlink=permlink, private_posting_key=curator_key, weight=vote_weight)
                    else:
                        self.beem.like_hive_post(voter=curator, voted=author, permlink=permlink, private_posting_key=curator_key, weight=vote_weight)
                # Notifica dopo il voto
                self.send_telegram_message(bot_token, admin_ids, "Voted!")
            else:
                self.send_telegram_message(bot_token, admin_ids, "Not Voted! Voting power too low.")
        except Exception as e:
            logger.error(f"Errore durante la gestione del voto per {post_link}: {str(e)}")
            # Notifica errore
            admin_ids = SettingsService.get_setting('admin_ids', default='', app=self.app)
            bot_token = SettingsService.get_setting('bot_token', default='', app=self.app)
            self.send_telegram_message(bot_token, admin_ids, f"Error during vote: {str(e)}")

    def publish_posts(self):
        """Controlla e pubblica nuovi post periodicamente."""
        logger.info("Avvio del publisher dei post")
        with self.app.app_context():
            with ThreadPoolExecutor(max_workers=2) as executor:
                while self.running:
                    try:
                        platform_users = self.update_user_data()
                        futures = {
                            executor.submit(self.process_posts, platform, users): platform 
                            for platform, users in platform_users.items() if users
                        }
                        
                        for future in as_completed(futures):
                            try:
                                future.result()
                            except Exception as e:
                                platform = futures[future]
                                logger.error(f"Errore nell'elaborazione dei post per {platform}: {str(e)}")
                        
                        self._safe_sleep(5)  # Attendi tra le iterazioni
                    except Exception as e:
                        logger.error(f"Errore nel ciclo principale del publisher: {str(e)}")
                        self._safe_sleep(10)  # Attendi un po' più a lungo in caso di errore
        
        logger.info("Publisher dei post fermato")    
        
    def _safe_sleep(self, seconds):
        """Sleep che può essere interrotto quando self.running diventa False."""
        start_time = time.time()
        while self.running and time.time() - start_time < seconds:
            time.sleep(min(1, seconds - (time.time() - start_time)))

    def stop(self):
        """Ferma il publisher in modo pulito."""
        logger.info("Arresto del publisher...")
        self.running = False

    def send_telegram_message(self, bot_token, chat_id, message):
        """
        Invia un messaggio Telegram a uno o più utenti.
        
        Args:
            bot_token (str): Token del bot Telegram
            chat_id (str): ID chat o lista di ID separati da virgola
            message (str): Messaggio da inviare
        """
        if not bot_token or not chat_id:
            logger.warning("Token del bot o chat_id mancanti, impossibile inviare messaggio Telegram")
            return False
            
        # Supporto per più admin ID
        chat_ids = [id.strip() for id in chat_id.split(',') if id.strip()]
        
        results = []
        for id in chat_ids:
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id}&text={message}"
                response = requests.get(url)
                results.append(response.json())
            except requests.exceptions.RequestException as e:
                logger.error(f"Errore comunicazione con server Telegram per chat_id {id}: {e}")
        
        return results
