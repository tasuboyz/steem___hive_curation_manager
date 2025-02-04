import json
import requests
import logging
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .components.logger_config import logger
from .components.config import (
    steem_domain, hive_domain, admin_id, TOKEN, 
    steem_curator, steem_curator_posting_key, 
    hive_curator, hive_curator_posting_key,
    TEST
)
from .components.beem import Blockchain
from .components.instance import local_data_list


class SocialMediaPublisher:
    def __init__(self):
        self.beem = Blockchain()
        self.published_links = {"steem": set(), "hive": set()}
    
    def update_user_data(self):
        """Raccoglie gli utenti per piattaforma."""
        platform_users = {"steem": [], "hive": []}
        for data in local_data_list:
            platform_users[data['platform']].append(data['username'])
        return platform_users

    def process_posts(self, platform, usernames):
        """Elabora i post per una specifica piattaforma."""
        new_links = []
        domain = steem_domain if platform == "steem" else hive_domain
        posts = self.beem.get_posts(usernames, platform)
        
        for link in posts:
            if link not in self.published_links[platform]:
                new_links.append(link)
                self.published_links[platform].add(link)
        
        for link in new_links:
            post_link = f"{domain}{link}"
            self.handle_voting(platform, post_link)
    
    def handle_voting(self, platform, post_link):
        """Gestisce il processo di voto per un post."""
        user_data = next((user for user in local_data_list if user['username'] in post_link), None)
        if not user_data:
            return
        
        vote_delay = user_data['voteDelay']
        vote_weight = user_data['voteWeight']
        curator = steem_curator if platform == "steem" else hive_curator
        curator_key = steem_curator_posting_key if platform == "steem" else hive_curator_posting_key
        
        curator_info = self.beem.get_steem_profile_info(curator) if platform == "steem" else self.beem.get_hive_profile_info(curator)
        last_vote_time = curator_info['result'][0]['last_vote_time']
        old_voting_power = curator_info['result'][0]['voting_power'] / 100
        voting_power = self.beem.calculate_voting_power(last_vote_time, old_voting_power)
        
        telegram_message = f"[{platform.upper()}] (VP: {voting_power} MIN: {vote_delay})\n{post_link}"
        self.send_telegram_message(TOKEN, admin_id, telegram_message)
        
        author = self.beem.get_steem_author(post_link) if platform == "steem" else self.beem.get_hive_author(post_link)
        permlink = self.beem.get_steem_permlink(post_link) if platform == "steem" else self.beem.get_hive_permlink(post_link)
        
        if voting_power > 89:
            time.sleep(vote_delay * 60)
            if TEST:
                logger.info(f"Voting: {author} {permlink} {vote_weight}")
            else:
                if platform == "steem":
                    self.beem.like_steem_post(voter=steem_curator, voted=author, permlink=permlink, private_posting_key=steem_curator_posting_key, weight=vote_weight)
                else:
                    self.beem.like_hive_post(voter=hive_curator, voted=author, permlink=permlink, private_posting_key=hive_curator_posting_key, weight=vote_weight)
            self.send_telegram_message(TOKEN, admin_id, "Voted!")
        else:
            self.send_telegram_message(TOKEN, admin_id, "Not Voted!")

    def publish_posts(self):
        """Controlla e pubblica nuovi post periodicamente."""
        with ThreadPoolExecutor(max_workers=2) as executor:
            while True:
                platform_users = self.update_user_data()
                futures = {executor.submit(self.process_posts, platform, users): platform 
                           for platform, users in platform_users.items() if users}
                
                for future in as_completed(futures):
                    future.result()
                
                time.sleep(5)  # Attendere tra le iterazioni

    def send_telegram_message(self, bot_token, chat_id, message):
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"
            response = requests.get(url)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error telegram server {e}")
            return False
