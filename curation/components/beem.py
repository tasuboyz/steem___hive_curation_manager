from beem import Steem, Hive
from beem.account import Account
from beem.comment import Comment
from beem.community import Communities, Community
import requests
import json
from .config import node_list
from .logger_config import logger
from datetime import datetime, timezone
from .instance import published_posts, last_check_time

class Blockchain:
    def __init__(self, mode='irreversible'):
        self.mode = mode
        # self.tester = SteemNodeTester()
        self.update_interval = 60
        self.hive_node = ''
        self.node_urls = node_list
        self.last_check_time = last_check_time

    def ping_server(self, node_url):
        """Verifica se il nodo è raggiungibile."""
        try:
            response = requests.get(node_url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Error pinging server {node_url}: {e}")
            return False

    def get_steem_profile_info(self, username):  
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo

        data = {
        "jsonrpc": "2.0",
        "method": "condenser_api.get_accounts",
        "params": [[username]],
        "id": 1
        }
        response = requests.post(node_url, data=json.dumps(data))
        if response.status_code == 200:
            data = response.json()
            if len(data['result']) > 0:
                return data
            else:
                raise Exception("user not exist")
        else:
            raise Exception(response.reason)
            
    def get_hive_profile_info(self, username):  
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo

        data = {
        "jsonrpc": "2.0",
        "method": "condenser_api.get_accounts",
        "params": [[username]],
        "id": 1
        }
        response = requests.post(node_url, data=json.dumps(data))
        if response.status_code == 200:
            data = response.json()
            if len(data['result']) > 0:
                return data
            else:
                raise Exception("user not exist")
        else:
            raise Exception(response.reason)

    def get_posts(self, usernames, platform, max_age_minutes=5):
        post_links = []
        current_time = datetime.now(timezone.utc)
        logger.info(f"Recuperando post per {len(usernames)} utenti su {platform}")

        for node_url in self.node_urls:
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo

        headers = {'Content-Type': 'application/json'}

        for username in usernames:
            logger.info(f"Recuperando post per {username} su {platform}")
            data = {
                "jsonrpc": "2.0",
                "method": "condenser_api.get_discussions_by_blog",
                "params": [{"tag": username, "limit": 1}],
                "id": 1
            }
            try:
                response = requests.post(node_url, headers=headers, data=json.dumps(data), timeout=5)
                response.raise_for_status()
                result = response.json().get('result', [])
                for post in result:
                    link = post.get('url')
                    created_time = post.get('created')
                    if link and created_time:
                        post_time = datetime.strptime(created_time, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                        post_age = current_time - post_time
                        age_minutes = post_age.total_seconds() / 60
                        last_check_time = self.last_check_time[username]
                        # logger.info(f"Post trovato: {link} - {post_time} - età: {post_age}")
                        # logger.info(f"Ultimo controllo per {username}: {self.last_check_time[username]}")
                        # logger.info(f"Età del post: {post_age.total_seconds() / 60} minuti")
                        # logger.info(f"Massimo tempo di pubblicazione: {max_age_minutes} minuti")

                        if link in published_posts:
                            logger.info(f"Il post è già stato pubblicato: {link}")
                            continue

                        if age_minutes <= max_age_minutes:
                            logger.info(f"Post pubblicato di recente: {link}")
                            post_links.append(link)
                            published_posts.add(link)
                            self.last_check_time[username] = post_time
                        else:
                            logger.info(f"Post non pubblicato di recente: {link} - età: {post_age}")
            except Exception as e:
                logger.error(f"Errore durante la recuperazione dei post per {username} su {platform}: {e}")

        logger.info(f"Recuperati {len(post_links)} post per {len(usernames)} utenti su {platform}")
        return post_links
    
    def get_steem_dynamic_global_properties(self):
        headers = {'Content-Type': 'application/json'}
        data = {
            "jsonrpc": "2.0",
            "method": "condenser_api.get_dynamic_global_properties",
            "params": [],
            "id": 1
        }
        response = requests.post(steem_node, headers=headers, data=json.dumps(data))
        if response.ok:
            return True
        else:
            raise Exception(response.reason)
        
    def get_hive_dynamic_global_properties(self):
        headers = {'Content-Type': 'application/json'}
        data = {
            "jsonrpc": "2.0",
            "method": "condenser_api.get_dynamic_global_properties",
            "params": [],
            "id": 1
        }
        response = requests.post(self.hive_node, headers=headers, data=json.dumps(data))
        if response.ok:
            return True
        else:
            raise Exception(response.reason)    

    def get_steem_cur8_info(self):
        steem_url = 'https://imridd.eu.pythonanywhere.com/api/steem'
        response = requests.get(steem_url)
        if response.status_code == 200:
            data = response.json()
            return data[0]
        else:
            raise Exception(response.reason)
        
    def get_hive_cur8_info(self):
        hive_url = 'https://imridd.eu.pythonanywhere.com/api/hive'
        response = requests.get(hive_url)
        if response.status_code == 200:
            data = response.json()
            return data[0]
        else:
            raise Exception(response.reason)
        
    def get_steem_hive_price(self):
        url = 'https://imridd.eu.pythonanywhere.com/api/prices'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            raise Exception(response.reason)
        
    def get_cur8_history(self):        
        url = 'https://imridd.eu.pythonanywhere.com/api/steem/history/cur8'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            raise Exception(response.reason)
        
    def get_steem_transaction_cur8(self):
        stm = Steem(node=steem_node)
        account = Account("cur8", steem_instance=stm)
        history = account.get_account_history(-1, limit=1000)
        transactions = []
        for operation in history:
            op_type = operation['type']
            if op_type == 'transfer':
                account_to = operation['to']
                amount = operation['amount']['amount']
                transactions.append((account_to, amount.strip()))
        return transactions
    
    def get_top_20_steem_transactions(self):
        transactions = self.get_steem_transaction_cur8()
        account_transactions = {}

        for account_to, amount in transactions:
            if account_to not in account_transactions:
                account_transactions[account_to] = 0
            account_transactions[account_to] += float(amount)

        sorted_transactions = sorted(account_transactions.items(), key=lambda item: item[1], reverse=True)

        top_transactions = sorted_transactions[:20]
        return top_transactions
    
    def get_hive_transaction_cur8(self):
        hive = Hive(node=self.hive_node)
        account = Account("cur8", steem_instance=hive)
        history = account.get_account_history(-1, limit=1000)
        transactions = []
        for operation in history:
            op_type = operation['type']
            if op_type == 'transfer':
                account_to = operation['to']
                amount = operation['amount']['amount']
                transactions.append((account_to, amount.strip()))
        return transactions
    
    def get_top_20_hive_transactions(self):
        transactions = self.get_hive_transaction_cur8()
        account_transactions = {}

        for account_to, amount in transactions:
            if account_to not in account_transactions:
                account_transactions[account_to] = 0
            account_transactions[account_to] += float(amount)

        sorted_transactions = sorted(account_transactions.items(), key=lambda item: item[1], reverse=True)

        top_transactions = sorted_transactions[:20]
        return top_transactions
    
    async def get_steem_top_delegators(self):
        url = 'https://imridd.eu.pythonanywhere.com/api/steem/delegators/cur8'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise Exception(response.reason)

    async def get_hive_top_delegators(self):
        url = 'https://imridd.eu.pythonanywhere.com/api/hive/delegators/cur8'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise Exception(response.reason)
        
##################################################################################### Community command
        
    def get_steem_community(self, community_name):
        steem = Steem(node=steem_node)
        community = Communities(blockchain_instance=steem)
        result = community.search_title(community_name)
        return result
    
    def get_steem_community_post(self, community):
        steem = Steem(node=steem_node)
        community = Community(community, blockchain_instance=steem)
        result = community.get_ranked_posts(limit=100)
        return result
    
    def subscribe_community(self, community, username, wif):   
        stm = Steem(keys=[wif], node=steem_node)  
        community = Community(community, blockchain_instance=stm)
        result = community.subscribe(username)
        return True

    def unsubscribe_community(self, community, username, wif):        
        stm = Steem(keys=[wif], node=steem_node)  
        community = Community(community, blockchain_instance=stm)
        result = community.unsubscribe(username)
        return True

    def get_account_sub(self, username):
        community = []
        steem = Steem(node=steem_node)
        account = Account(username, steem_instance=steem)
        results = account.list_all_subscriptions()
        for result in results:
            community.append(result[0])
        return community
    
    def create_account(self, new_account_name: str):
        new_account_name = new_account_name.lower()
        url = "http://imridd.eu.pythonanywhere.com/api/steem/create_account"
        headers = {
            "Content-Type": "application/json",
            "API-Key": "your_secret_api_key"
        }
        data = {
            "new_account_name": new_account_name
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to create account. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception("failed to create account")

    ##########################################################################################
    ##########################################################################################
    
    def like_steem_post(self, voter, voted, private_posting_key, permlink, weight=20):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        steem = Steem(keys=[private_posting_key], node=node_url, rpcuser=voter) 
        account = Account(voter, blockchain_instance=steem)
        comment = Comment(authorperm=f"@{voted}/{permlink}", blockchain_instance=steem)
        comment.vote(weight, account=account)

    def like_hive_post(self, voter, voted, private_posting_key, permlink, weight=20):   
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        hive = Hive(keys=[private_posting_key], node=node_url, rpcuser=voter)
        account = Account(voter, blockchain_instance=hive)
        comment = Comment(authorperm=f"@{voted}/{permlink}", blockchain_instance=hive)
        comment.vote(weight, account=account)

    def get_steem_permlink(self, post_url):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        steem = Steem(node=node_url) 
        comment = Comment(post_url, blockchain_instance=steem)
        permlink = comment.permlink
        return permlink
    
    def get_steem_author(self, post_url):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        steem = Steem(node=node_url) 
        comment = Comment(post_url, blockchain_instance=steem)
        author = comment.author
        return author
    
    def get_hive_permlink(self, post_url):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        hive = Hive(node=node_url)
        comment = Comment(post_url, blockchain_instance=hive)
        permlink = comment.permlink
        return permlink
    
    def get_hive_author(self, post_url):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        hive = Hive(node=node_url)
        comment = Comment(post_url, blockchain_instance=hive)
        author = comment.author
        return author
    
    def get_user_last_post(self, username):
        steem = Steem(node=steem_node) 
        account = Account(username, blockchain_instance=steem)
        result = account.get_blog(start_entry_id=0, limit=1, raw_data=False, short_entries=False, account=None)
        return result
    
    def get_user_last_hive_post(self, username):
        hive = Hive(node=hive_node) 
        account = Account(username, blockchain_instance=hive)
        result = account.get_blog(start_entry_id=0, limit=1, raw_data=False, short_entries=False, account=None)
        return result
    
    def get_steem_comment(self, author, permalink):
        steem = Steem(node=steem_node) 
        comment = Comment(f"@{author}/{permalink}", blockchain_instance=steem)
        return comment
    
    def calculate_voting_power(self, timestamp_last_vote, voting_power):
        last_vote_time = datetime.strptime(timestamp_last_vote, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff_seconds = (now - last_vote_time).total_seconds()
        regenerated_vp = (diff_seconds / 432000) * 100  # 432000 secondi = 5 giorni
        current_vp = min(voting_power + regenerated_vp, 100)
        return current_vp