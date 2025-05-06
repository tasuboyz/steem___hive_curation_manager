from beem import Steem, Hive
from beem.account import Account
from beem.comment import Comment
from beem.community import Communities, Community
import requests
import json
import os
import time
import pickle
import aiohttp
from .config import node_list, steem_curator, steem_active_key
from .logger_config import logger
from datetime import datetime, timezone
from .instance import published_posts, last_check_time
from beem.transactionbuilder import TransactionBuilder
from beembase.operations import Transfer
from .db import db, Delegator

class Blockchain:
    def __init__(self, mode='irreversible'):
        self.mode = mode
        # self.tester = SteemNodeTester()
        self.update_interval = 60
        self.hive_node = ''
        self.node_urls = node_list
        self.last_check_time = last_check_time
        
        # Inizializzazione della cache dei votanti
        self._voters_cache = {}
        self._cache_path = os.path.join(os.path.dirname(__file__), "../../instance/voters_cache.pkl")
        # Inizializza la blockchain di riferimento (usata in get_post_voters)
        self.blockchain = None
        
        # Carica la cache esistente se disponibile
        self._load_cache()

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

        for node_url in self.node_urls[platform.lower()]:
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
                logger.error(f"Errore durante la recupero dei post per {username} su {platform}: {e}")

        logger.info(f"Recuperati {len(post_links)} post per {len(usernames)} utenti su {platform}")
        return post_links
    
    def get_steem_dynamic_global_properties(self):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Server non raggiungibile: {node_url}")
                continue
        headers = {'Content-Type': 'application/json'}
        data = {
            "jsonrpc": "2.0",
            "method": "condenser_api.get_dynamic_global_properties",
            "params": [],
            "id": 1
        }
        response = requests.post(node_url, headers=headers, data=json.dumps(data))
        if response.ok:
            return True
        else:
            raise Exception(response.reason)
        
    def get_hive_dynamic_global_properties(self):
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Server non raggiungibile: {node_url}")
                continue
            
            headers = {'Content-Type': 'application/json'}
            data = {
                "jsonrpc": "2.0",
                "method": "condenser_api.get_dynamic_global_properties",
                "params": [],
                "id": 1
            }
            
            try:
                response = requests.post(node_url, headers=headers, data=json.dumps(data), timeout=5)
                if response.ok:
                    return response.json().get('result', {})
                else:
                    logger.error(f"Errore dal nodo {node_url}: {response.reason}")
            except Exception as e:
                logger.error(f"Errore di connessione al nodo {node_url}: {str(e)}")
        
        raise Exception("Nessun nodo Hive disponibile")

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
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
                
            try:
                stm = Steem(node=node_url)
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
            except Exception as e:
                logger.error(f"Errore nel recupero delle transazioni con il nodo {node_url}: {str(e)}")
                
        raise Exception("Nessun nodo Steem disponibile")
    
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
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
                
            try:
                hive = Hive(node=node_url)
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
            except Exception as e:
                logger.error(f"Errore nel recupero delle transazioni con il nodo {node_url}: {str(e)}")
        
        raise Exception("Nessun nodo Hive disponibile")
    
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
                
############################################################################################# Delegators
                
    def get_steem_delegators(self):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Server non raggiungibile: {node_url}")
                continue

        stm = Steem(node=node_url)
        acc = Account(steem_curator, blockchain_instance=stm)
        
        # Ottieni l'ultima operazione processata dal database
        last_processed = Delegator.query.order_by(Delegator.timestamp.desc()).first()
        virtual_op = acc.virtual_op_count() 
        start_from = virtual_op - 20
        
        delegate_ops = []
        for h in acc.history(start=start_from, stop=virtual_op, use_block_num=False):
            if h['type'] == 'delegate_vesting_shares' and h['_id'] != getattr(last_processed, 'last_operation_id', None):
                delegate_ops.append(h)

        logger.info(f"Operazioni rilevate: {len(delegate_ops)}")

        # Processa le modifiche
        changes = self.process_delegation_changes(delegate_ops)
        self.save_delegation_changes(changes)
        self.send_confirmation(changes, stm)

        return changes

    def process_delegation_changes(self, operations):
        changes = []
        for op in operations:
            delegator = op['delegator']
            amount = op['vesting_shares']
            entry = Delegator.query.filter_by(username=delegator).first()

            # Controlla se è una nuova delegazione o una modifica
            if not entry:
                changes.append({'type': 'new', 'data': op})
            elif entry.vesting_shares != amount:
                changes.append({'type': 'update', 'data': op})
        
        return changes

    def save_delegation_changes(self, changes):
        for change in changes:
            op = change['data']
            delegator = op['delegator']
            entry = Delegator.query.filter_by(username=delegator).first()

            if change['type'] == 'new':
                new_entry = Delegator(
                    username=delegator,
                    vesting_shares=op['vesting_shares']['amount'],
                    last_operation_id=op['_id'],
                    timestamp=datetime.strptime(op['timestamp'], '%Y-%m-%dT%H:%M:%S')
                )
                db.session.add(new_entry)
            else:
                entry.vesting_shares = op['vesting_shares']
                entry.last_operation_id = op['_id']

        db.session.commit()

    def send_confirmation(self, changes, stm):
        for change in changes:
            op = change['data']
            try:
                memo = "Grazie per la nuova delegazione!" if change['type'] == 'new' else "Grazie per aver aggiornato la tua delegazione!"
                
                tx = TransactionBuilder(blockchain_instance=stm)
                tx.appendOps(Transfer(
                    **{
                        'from': steem_curator,
                        'to': op['delegator'],
                        'amount': '0.001 STEEM',
                        'memo': memo
                    }
                ))
                tx.appendWif(steem_active_key)
                tx.sign()
                tx.broadcast()
                
                logger.info(f"Inviata conferma a {op['delegator']} per {change['type']}")
            except Exception as e:
                logger.error(f"Errore invio a {op['delegator']}: {str(e)}")

##################################################################################### Community command
    
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
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        hive = Hive(node=node_url)
        comment = Comment(post_url, blockchain_instance=hive)
        permlink = comment.permlink
        return permlink
    
    def get_hive_author(self, post_url):
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        hive = Hive(node=node_url)
        comment = Comment(post_url, blockchain_instance=hive)
        author = comment.author
        return author
    
    def get_user_last_post(self, username):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
            
            steem = Steem(node=node_url)
            try:
                account = Account(username, blockchain_instance=steem)
                result = account.get_blog(start_entry_id=0, limit=1, raw_data=False, short_entries=False, account=None)
                return result
            except Exception as e:
                logger.error(f"Errore con il nodo {node_url}: {str(e)}")
        
        raise Exception("Nessun nodo Steem disponibile")
    
    def get_user_last_hive_post(self, username):
        for node_url in self.node_urls.get('hive'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
            
            hive = Hive(node=node_url)
            try:
                account = Account(username, blockchain_instance=hive)
                result = account.get_blog(start_entry_id=0, limit=1, raw_data=False, short_entries=False, account=None)
                return result
            except Exception as e:
                logger.error(f"Errore con il nodo {node_url}: {str(e)}")
        
        raise Exception("Nessun nodo Hive disponibile")
    
    def get_comment(self, author, permalink, blockchain: str):
        for node_url in self.node_urls.get(blockchain):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue  # Prova il nodo successivo
        if blockchain == 'steem':
            instance = Steem(node=node_url)
        else:
            instance = Hive(node=node_url)
        comment = Comment(f"@{author}/{permalink}", blockchain_instance=instance)
        return comment
    
    def calculate_voting_power(self, timestamp_last_vote, voting_power):
        last_vote_time = datetime.strptime(timestamp_last_vote, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff_seconds = (now - last_vote_time).total_seconds()
        regenerated_vp = (diff_seconds / 432000) * 100  # 432000 secondi = 5 giorni
        current_vp = min(voting_power + regenerated_vp, 100)
        return current_vp
    
    def get_account_info(self, username):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue
        steem = Steem(node=node_url)
        account = Account(username, blockchain_instance=steem)
        return account
    
    def get_reward_fund(self, fund_name="post"):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue
        """Get reward fund information directly from the blockchain.
        
        Args:
            fund_name (str): Name of the reward fund, typically "post"
            
        Returns:
            dict: Reward fund data with relevant information
        """
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {
                "jsonrpc": "2.0",
                "method": "condenser_api.get_reward_fund",
                "params": [fund_name],
                "id": 1
            }
            
            response = requests.post(node_url, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    # Convert amounts to a more usable format
                    reward_data = result['result']
                    return reward_data
                    
            logger.warning(f"Failed to get reward fund data from {node_url}")
            # self.switch_to_backup_node()
            return self.get_reward_fund(fund_name)  # Try again with new node
            
        except Exception as e:
            logger.error(f"Error getting reward fund: {str(e)}")
            # self.switch_to_backup_node()
            return self.get_reward_fund(fund_name)  # Try again with new node
    
    def get_current_median_history_price(self):
        for node_url in self.node_urls.get('steem'):
            if not self.ping_server(node_url):
                logger.error(f"Impossibile raggiungere il server: {node_url}")
                continue
        """Get the current median price history from the blockchain.
        
        Returns:
            dict: Price data with base and quote values
        """
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {
                "jsonrpc": "2.0",
                "method": "condenser_api.get_current_median_history_price",
                "params": [],
                "id": 1
            }
            
            response = requests.post(node_url, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    # Parse price data into a usable format
                    price_data = result['result']
                    
                    # Convert price strings to structured data
                    base_parts = price_data['base'].split(' ')
                    quote_parts = price_data['quote'].split(' ')
                    
                    return {
                        'base': {
                            'amount': float(base_parts[0]),
                            'symbol': base_parts[1]
                        },
                        'quote': {
                            'amount': float(quote_parts[0]),
                            'symbol': quote_parts[1]
                        }
                    }
                    
            logger.warning(f"Failed to get price data from {node_url}")
            # self.switch_to_backup_node()
            return self.get_current_median_history_price()  # Try again with new node
            
        except Exception as e:
            logger.error(f"Error getting current median history price: {str(e)}")
            # self.switch_to_backup_node()
            return self.get_current_median_history_price()  # Try again with new node
        

    def _load_cache(self):
        """Carica la cache dei votanti dal file se esiste."""
        try:
            if os.path.exists(self._cache_path):
                with open(self._cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    # Verifica che la cache non sia vecchia (più di 7 giorni)
                    if 'timestamp' in cached_data and (datetime.now() - cached_data['timestamp']).days < 7:
                        self._voters_cache = cached_data.get('voters', {})
                        logger.info(f"Caricati {len(self._voters_cache)} record dalla cache dei votanti")
                    else:
                        logger.info("Cache dei votanti scaduta, verrà rigenerata")
        except Exception as e:
            logger.warning(f"Errore nel caricamento della cache dei votanti: {e}")
            self._voters_cache = {}
    
    def _save_cache(self):
        """Salva la cache dei votanti su file."""
        try:
            # Assicurati che la directory esista
            os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
            
            cache_data = {
                'timestamp': datetime.now(),
                'voters': self._voters_cache
            }
            
            with open(self._cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.info(f"Salvati {len(self._voters_cache)} record nella cache dei votanti")
        except Exception as e:
            logger.warning(f"Errore nel salvataggio della cache dei votanti: {e}")

    def get_post_voters(self, post_url, min_importance=0.0, use_cache=True):
        """Get the voters of a post sorted by importance (vesting shares or rshares)
        
        Args:
            post_url (str): The URL or identifier of the post
            min_importance (float): Minimum importance threshold to filter voters
            use_cache (bool): Whether to use cached voters data if available
            
        Returns:
            list: List of dictionaries with voter information
        """
        # Check cache first if enabled
        cache_key = f"{post_url}_{min_importance}"
        if use_cache and cache_key in self._voters_cache:
            logger.info(f"Utilizzando dati in cache per {post_url}")
            return self._voters_cache[cache_key]
        
        try:
            # Ottimizzazione: limita il numero di richieste parallele
            start_time = time.time()
            from beem.vote import Vote
            
            # Usa un timeout più breve per evitare blocchi lunghi
            comment = Comment(post_url, blockchain_instance=self.blockchain)
            # Ottiene i dati completi del post
            comment_data = comment.json()
            
            # Estrai la data di creazione del post e assicurati che abbia timezone UTC
            post_created = comment_data.get('created')
            if isinstance(post_created, str):
                post_created = datetime.strptime(post_created, '%Y-%m-%dT%H:%M:%S')
                # Assicurati che post_created sia timezone-aware (UTC)
                if post_created.tzinfo is None:
                    post_created = post_created.replace(tzinfo=timezone.utc)
            
            # Ottiene i voti con i dettagli completi
            active_votes = comment_data.get('active_votes', [])
            if not active_votes and hasattr(comment, 'get_active_votes'):
                active_votes = comment.get_active_votes()
            
            logger.info(f"Trovati {len(active_votes)} voti per il post {post_url}")
            
            # Ottimizzazione: limita il numero di voti da analizzare per post con molti voti
            max_votes_to_process = 50  # Imposta un limite ragionevole
            if len(active_votes) > max_votes_to_process:
                # Ordina preliminarmente per rshares se disponibili
                if 'rshares' in active_votes[0]:
                    active_votes.sort(key=lambda v: float(v.get('rshares', 0)), reverse=True)
                active_votes = active_votes[:max_votes_to_process]
                logger.info(f"Limitata analisi ai top {max_votes_to_process} voti per {post_url}")
            
            # Get voters data
            voters_data = []
            processed_voters = 0
            
            # Processa i voti più significativi (in batch per maggiore efficienza)
            for vote_data in active_votes:
                try:
                    voter_name = vote_data['voter']
                    processed_voters += 1
                    
                    # Prima prova a ottenere rshares direttamente dal voto (più veloce)
                    vote_rshares = float(vote_data.get('rshares', 0))
                    
                    # Se non ci sono rshares significativi, passa al votante successivo (ottimizzazione)
                    if vote_rshares < 1000000 and processed_voters > 10:
                        continue
                    
                    # Estrai informazioni dirette dal voto quando disponibili
                    vote_percent = float(vote_data.get('percent', 0))
                    
                    # Determina quando è avvenuto il voto
                    vote_time = vote_data.get('time')
                    if isinstance(vote_time, str):
                        vote_time = datetime.strptime(vote_time, '%Y-%m-%dT%H:%M:%S')
                        if vote_time.tzinfo is None:
                            vote_time = vote_time.replace(tzinfo=timezone.utc)
                    
                    # Se non abbiamo il timestamp nel voto base, prova con l'oggetto Vote (più lento)
                    if not vote_time:
                        try:
                            vote = Vote(voter_name, post_url, blockchain_instance=self.blockchain)
                            vote_time = vote.time
                            if vote_time.tzinfo is None:
                                vote_time = vote_time.replace(tzinfo=timezone.utc)
                            
                            if not vote_rshares or vote_rshares == 0:
                                vote_rshares = float(vote.rshares)
                            
                            if not vote_percent or vote_percent == 0:
                                vote_percent = vote.weight
                        except Exception as vote_error:
                            # Se fallisce anche questo, usa una stima
                            if 'last_update' in vote_data:
                                vote_time = vote_data.get('last_update')
                                if isinstance(vote_time, str):
                                    vote_time = datetime.strptime(vote_time, '%Y-%m-%dT%H:%M:%S')
                                    if vote_time.tzinfo is None:
                                        vote_time = vote_time.replace(tzinfo=timezone.utc)
                            else:
                                # Ultimo tentativo: usa il timestamp attuale
                                vote_time = datetime.now(timezone.utc)
                    
                    # Calcola il ritardo del voto in minuti
                    vote_delay_minutes = int((vote_time - post_created).total_seconds() / 60)
                    
                    # Calcola l'importanza usando rshares direttamente se disponibili
                    importance = vote_rshares / 1e12  # Normalizza per leggibilità
                    
                    # Solo se l'importanza è troppo bassa, ottieni ulteriori informazioni sull'account
                    vests = 0
                    reputation = 0
                    
                    if importance < min_importance and processed_voters <= 10:
                        try:
                            # Ottimizzazione: ottieni informazioni sull'account solo se necessario
                            voter_account = Account(voter_name, blockchain_instance=self.blockchain)
                            vests = float(voter_account['vesting_shares'].amount) + float(voter_account['received_vesting_shares'].amount) - float(voter_account['delegated_vesting_shares'].amount)
                            importance = max(importance, vests / 1e6)  # Usa il valore maggiore tra rshares e vests
                            reputation = voter_account.get_reputation()
                        except Exception as e:
                            logger.debug(f"Non è stato possibile ottenere dettagli completi per {voter_name}: {e}")
                    
                    if importance >= min_importance or vote_rshares >= min_importance * 1e12:
                        voters_data.append({
                            'voter': voter_name,
                            'weight': vote_percent,
                            'rshares': vote_rshares,
                            'vesting_shares': vests,
                            'importance': importance,
                            'vote_time': vote_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(vote_time, 'strftime') else vote_time,
                            'vote_delay_minutes': vote_delay_minutes,
                            'reputation': reputation
                        })
                except Exception as e:
                    logger.warning(f"Error processing voter {vote_data.get('voter', 'unknown')}: {str(e)}")
                    continue
            
            # Sort by importance (vesting shares o rshares)
            voters_data.sort(key=lambda x: x['importance'], reverse=True)
            
            # Logga il tempo totale di esecuzione e i primi votanti importanti
            execution_time = time.time() - start_time
            logger.info(f"Analisi votanti completata in {execution_time:.2f} secondi")
            
            if voters_data:
                top_voters = [f"{v['voter']} (dopo {v['vote_delay_minutes']} min., importanza: {v['importance']:.2f})" 
                            for v in voters_data[:3]]
                logger.info(f"Top votanti per {post_url}: {', '.join(top_voters)}")
            
            # Save to cache if the operation was successful
            if use_cache:
                self._voters_cache[cache_key] = voters_data
                # Save cache every 10 new entries
                if len(self._voters_cache) % 10 == 0:
                    self._save_cache()
            
            return voters_data
            
        except Exception as e:
            logger.error(f"Error getting post voters: {str(e)}")
            return []

    def cleanup(self):
        """Pulisce e salva la cache a fine esecuzione."""
        if self._voters_cache:
            self._save_cache()

    def calculate_optimal_vote_time(self, voters_data, buffer_minutes=0.5):
        """Calcola il tempo ottimale per votare in base ai votanti importanti
        
        Args:
            voters_data (list): Lista di dati sui votanti con 'importance' e 'vote_delay_minutes'
            buffer_minutes (float): Minuti di anticipo rispetto al primo votante importante
            
        Returns:
            dict: Dizionario con 'optimal_time' (in minuti) e 'explanation'
        """
        if not voters_data:
            return {
                'optimal_time': 5,  # Default se non ci sono dati
                'explanation': 'Nessun dato sui votanti disponibile, usando il tempo predefinito di 5 minuti',
                'vote_window': (4.5, 5.5)  # Finestra di voto predefinita
            }
        
        # Ordina i votanti per importanza (decrescente)
        important_voters = sorted(voters_data, key=lambda x: x.get('importance', 0), reverse=True)
        
        # Prendi i 3 votanti più importanti, se disponibili
        top_voters = important_voters[:min(3, len(important_voters))]
        
        # Calcola l'importanza totale di questi votanti
        total_importance = sum(v.get('importance', 0) for v in top_voters)
        
        if total_importance <= 0:
            return {
                'optimal_time': 5,  # Default in caso di importanza zero
                'explanation': 'Importanza dei votanti troppo bassa, usando il tempo predefinito di 5 minuti',
                'vote_window': (4.5, 5.5)
            }
        
        # Calcola il tempo medio ponderato di voto in base all'importanza
        weighted_vote_time = 0
        for voter in top_voters:
            importance = voter.get('importance', 0)
            delay_minutes = voter.get('vote_delay_minutes', 30)  # Default a 30 minuti se non specificato
            weight = importance / total_importance
            weighted_vote_time += delay_minutes * weight
        
        # Trova il votante più importante e il suo tempo di voto
        most_important_voter = top_voters[0]
        most_important_time = most_important_voter.get('vote_delay_minutes', 30)
        
        # Calcola il tempo di voto ottimale - leggermente prima del tempo medio ponderato
        optimal_time = max(1, weighted_vote_time - buffer_minutes)
        
        # Supporto per la strategia "vote before whales"
        if most_important_time < 10:  # Se il votante principale vota presto
            # Vota appena prima di lui
            optimal_time = max(0.5, most_important_time - buffer_minutes)
            explanation = f"Votare {buffer_minutes} minuti prima del votante più importante (@{most_important_voter.get('voter', 'sconosciuto')}) che vota dopo {most_important_time:.1f} minuti"
            vote_window = (optimal_time - 0.2, optimal_time + 0.2)  # Finestra stretta
        else:
            # Usa una strategia media
            explanation = f"Votare in base alla media ponderata dei top {len(top_voters)} votanti (tempo medio: {weighted_vote_time:.1f} minuti)"
            vote_window = (optimal_time - 1, optimal_time + 1)  # Finestra più ampia
        
        # Evita tempi di voto troppo precoci
        if optimal_time < 0.5:
            optimal_time = 0.5
            explanation += " (limitato a un minimo di 0.5 minuti per evitare vote spamming)"
            vote_window = (0.5, 1.0)
        
        return {
            'optimal_time': round(optimal_time, 1),
            'explanation': explanation,
            'top_voters': [v.get('voter', 'sconosciuto') for v in top_voters],
            'vote_window': (round(vote_window[0], 1), round(vote_window[1], 1))
        }

    def get_previous_author_posts(self, author, platform, limit=5):
        """
        Recupera i post precedenti di un autore per analizzare i pattern di voto.
        
        Args:
            author (str): Nome dell'autore
            platform (str): 'steem' o 'hive'
            limit (int): Numero massimo di post da recuperare
            
        Returns:
            list: Lista di post precedenti dell'autore
        """
        try:
            logger.info(f"Recupero dei {limit} post precedenti di @{author} su {platform}")
            
            # Trova il nodo disponibile
            node_urls = self.node_urls.get(platform.lower(), [])
            node_url = None
            
            for url in node_urls:
                if self.ping_server(url):
                    node_url = url
                    break
            
            if not node_url:
                logger.error(f"Nessun nodo {platform} disponibile")
                return []
            
            # Prepara la richiesta API
            headers = {'Content-Type': 'application/json'}
            data = {
                "jsonrpc": "2.0",
                "method": "condenser_api.get_discussions_by_blog",
                "params": [{"tag": author, "limit": limit+1}],  # +1 per escludere il post attuale
                "id": 1
            }
            
            response = requests.post(node_url, headers=headers, data=json.dumps(data), timeout=10)
            response.raise_for_status()
            
            posts = response.json().get('result', [])
            # Filtra solo i post dell'autore (esclude reblog) e salta il primo (post attuale)
            author_posts = [post for post in posts if post.get('author') == author][1:limit+1]
            
            logger.info(f"Recuperati {len(author_posts)} post precedenti di @{author}")
            return author_posts
            
        except Exception as e:
            logger.error(f"Errore nel recupero dei post precedenti di @{author}: {str(e)}")
            return []