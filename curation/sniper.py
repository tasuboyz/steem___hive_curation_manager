import json
import requests
import logging
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from .components.logger_config import logger
from .components.config import steem_domain, hive_domain, admin_id, TOKEN, steem_curator, steem_curator_posting_key, hive_curator, hive_curator_posting_key
from .components.beem import Blockchain
from .components.instance import local_data_list

class SocialMediaPublisher:
    def __init__(self):
        self.beem = Blockchain()  # Initialize the Blockchain class

    def update_user_data(self):
        steem_users = [data for data in local_data_list if data['platform'] == 'steem']
        hive_users = [data for data in local_data_list if data['platform'] == 'hive']
        steem_usernames = [local_data_list["username"] for local_data_list in steem_users]
        hive_usernames = [local_data_list["username"] for local_data_list in hive_users]
        return steem_usernames, hive_usernames

    def publish_posts(self):
        published_links = {"steem": set(), "hive": set()}

        steem_usernames, hive_usernames = self.update_user_data()

        with ThreadPoolExecutor(max_workers=2) as executor:
            while True:
                steem_usernames, hive_usernames = self.update_user_data()

                futures = []
                if steem_usernames:
                    futures.append(
                        executor.submit(self.beem.get_posts, steem_usernames, 'Steem')
                    )
                if hive_usernames:
                    futures.append(
                        executor.submit(self.beem.get_posts, hive_usernames, 'Hive')
                    )

                for future, platform in zip(futures, ["steem", "hive"]):
                    links = future.result()
                    new_links = [link for link in links if link not in published_links[platform]]
                    if new_links:
                        domain = steem_domain if platform == "steem" else hive_domain
                        logger.info(f"[{platform.upper()}] New post links: {domain}{new_links}")
                        published_links[platform].update(new_links)
                        for link in new_links:
                            post_link = f"{domain}{link}"
                            user_data = next((user for user in local_data_list if user['username'] in post_link), None)

                            if user_data:
                                vote_delay = user_data['voteDelay']
                                vote_weight = user_data['voteWeight']

                                if platform.upper() == "STEEM":
                                    steem_curator_info = self.beem.get_steem_profile_info(steem_curator)
                                    last_vote_time = steem_curator_info['result'][0]['last_vote_time']
                                    old_hive_voting_power = steem_curator_info['result'][0]['voting_power'] / 100
                                    steem_voting_power = self.beem.calculate_voting_power(last_vote_time, old_hive_voting_power)
                                    telegram_message = f"[{platform.upper()}] (VP: {steem_voting_power})\n{post_link}"
                                    self.send_telegram_message(TOKEN, admin_id, telegram_message)
                                    author = self.beem.get_steem_author(post_link)
                                    permlink = self.beem.get_steem_permlink(post_link)
                                    if steem_voting_power > 89:
                                        time.sleep(vote_delay)
                                        self.beem.like_steem_post(voter=steem_curator, voted=author, permlink=permlink, private_posting_key=steem_curator_posting_key, weight=vote_weight)
                                        self.send_telegram_message(TOKEN, admin_id, "Voted!")
                                    else:
                                        self.send_telegram_message(TOKEN, admin_id, "Not Voted!")
                                elif platform.upper() == "HIVE":
                                    hive_curator_info = self.beem.get_hive_profile_info(hive_curator)
                                    last_vote_time = hive_curator_info['result'][0]['last_vote_time']
                                    old_hive_voting_power = hive_curator_info['result'][0]['voting_power'] / 100
                                    hive_voting_power = self.beem.calculate_voting_power(last_vote_time, old_hive_voting_power)
                                    telegram_message = f"[{platform.upper()}] (VP: {hive_voting_power})\n{post_link}"
                                    self.send_telegram_message(TOKEN, admin_id, telegram_message)
                                    author = self.beem.get_hive_author(post_link)
                                    permlink = self.beem.get_hive_permlink(post_link)
                                    if hive_voting_power > 89:
                                        time.sleep(vote_delay) 
                                        self.beem.like_hive_post(voter=hive_curator, voted=author, permlink=permlink, private_posting_key=hive_curator_posting_key, weight=vote_weight)
                                        self.send_telegram_message(TOKEN, admin_id, "Voted!")                                   
                                    else:
                                        self.send_telegram_message(TOKEN, admin_id, "Not Voted!")
                                    # ...
                time.sleep(5)  # Controlla ogni 15 secondi

    def send_telegram_message(self, bot_token, chat_id, message):
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"
            response = requests.get(url)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error telegram server {e}")
            return False

