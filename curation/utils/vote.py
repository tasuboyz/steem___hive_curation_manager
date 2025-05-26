import asyncio
from flask import current_app
from ..components.logger_config import logger
from ..components.beem import Blockchain
from beem.comment import Comment
from beem.vote import Vote
from ..components.config import steem_curator as CURATOR
import time
import os
import json
from datetime import datetime, timedelta, timezone


class VoteManager:
    """Class to manage blockchain voting operations and calculations"""
    
    def __init__(self, app=None):
        """Initialize the VoteManager with blockchain connector and cache
        
        Args:
            app (Flask): Flask application instance
        """
        self.blockchain_connector = Blockchain(app=app or current_app)
        self._voters_cache = {}
        self._cache_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'voters_cache.json')
        
        # Create cache directory if it doesn't exist
        cache_dir = os.path.dirname(self._cache_file)
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
            except Exception as e:
                logger.warning(f"Could not create cache directory: {e}")
        
        # Load cache if it exists
        self._load_cache()
    
    def _load_cache(self):
        """Load voters cache from file"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    self._voters_cache = json.load(f)
                logger.info(f"Loaded {len(self._voters_cache)} cached voter entries")
        except Exception as e:
            logger.warning(f"Could not load voters cache: {e}")
            self._voters_cache = {}

    def _save_cache(self):
        """Save voters cache to file with optimizations"""
        try:
            # Utilizziamo un file temporaneo per evitare corruzioni in caso di crash
            temp_file = f"{self._cache_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(self._voters_cache, f)
            
            # Sostituzione atomica del file (più sicura)
            import os
            if os.path.exists(temp_file):
                if os.path.exists(self._cache_file):
                    os.replace(temp_file, self._cache_file)
                else:
                    os.rename(temp_file, self._cache_file)
            
            logger.debug(f"Salvate {len(self._voters_cache)} entrate votanti in cache")
        except Exception as e:
            logger.warning(f"Impossibile salvare la cache dei votanti: {e}")
            
    def get_post_voters(self, post_url, min_importance=0.0, use_cache=False):
        """Get the voters of a post sorted by importance (basata sul valore del voto in STEEM)
        
        Args:
            post_url (str): The URL or identifier of the post
            min_importance (float): Minimum importance threshold to filter voters
                                   (ora basata sul valore del voto, 0.1 = circa $0.01)
            use_cache (bool): Whether to use cached voters data if available
            
        Returns:
            list: List of dictionaries with voter information including vote value
        """        # Check cache first if enabled (default to True per migliorare le prestazioni)
        cache_key = f"{post_url}_{min_importance}"
        if use_cache and cache_key in self._voters_cache:
            # Verifica che la cache non sia più vecchia di 30 minuti
            cache_entry = self._voters_cache[cache_key]
            cache_timestamp = cache_entry.get('timestamp', 0)
            if time.time() - cache_timestamp < 1800:  # 30 minuti in secondi
                logger.info(f"Utilizzando dati in cache per {post_url} (cache di {(time.time() - cache_timestamp) // 60} minuti)")
                return cache_entry.get('data', [])
        
        try:
            # Ottimizzazione: implementa analisi parallela
            start_time = time.time()
            
            # Imposta limiti più aggressivi per migliorare le prestazioni
            max_detailed_voters = 5  # Ridotto a 5 per analisi dettagliate (i più importanti)
            max_total_voters = 20   # Ridotto a 20 per il totale (sufficiente per la maggior parte dei casi)
            
            # Usa un timeout più breve per evitare blocchi lunghi
            platform, blockchain_instance = self.blockchain_connector.get_platform_and_instance(post_url)
            curator_info = self.blockchain_connector.get_curator_info(platform)
            curator_username = (curator_info.get('username') or '').lower()
            comment = Comment(post_url, blockchain_instance=blockchain_instance)
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
            
            # Pre-filtraggio: prima ordina i voti per rshares se disponibili
            if active_votes and 'rshares' in active_votes[0]:
                active_votes.sort(key=lambda v: float(v.get('rshares', 0)), reverse=True)
                active_votes = active_votes[:max_total_voters]  # Prendi solo i top N voti per rshares
                logger.info(f"Pre-filtrati i top {max_total_voters} voti per {post_url} basati su rshares")
            else:
                # Se non possiamo ordinare per rshares, limita comunque il numero totale
                active_votes = active_votes[:max_total_voters]
                logger.info(f"Limitati a {max_total_voters} voti senza pre-ordinamento per {post_url}")            # Pre-filtra i votanti per rshares e prepara per l'elaborazione asincrona
            filtered_votes = []
            for vote_data in active_votes:
                voter_name = vote_data.get('voter', '')
                if voter_name.lower() == curator_username:
                    continue
                    
                # Aggiungi solo votanti con rshares significativi (o i primi N)
                vote_rshares = float(vote_data.get('rshares', 0))
                if len(filtered_votes) < max_detailed_voters or vote_rshares >= 1e7:
                    filtered_votes.append(vote_data)
            
            # Processa i votanti in parallelo utilizzando asyncio
            logger.info(f"Processando {len(filtered_votes)} votanti in parallelo per {post_url}")
            
            # Crea ed esegui task asincroni
            # Nel Python 3.7+ possiamo usare asyncio.run(), ma per compatibilità utilizziamo un approccio più portabile
            loop = asyncio.new_event_loop()
            try:
                # Numero di operazioni concorrenti: 3 è un buon compromesso tra prestazioni e limiti API
                voters_data = loop.run_until_complete(
                    self._process_voters_parallel(
                        filtered_votes, 
                        post_url, 
                        post_created, 
                        blockchain_instance, 
                        curator_username,
                        max_concurrent=3  # Limitiamo la concorrenza per evitare errori API
                    )
                )
            finally:
                loop.close()
                
            # Filtra per importanza minima
            voters_data = [v for v in voters_data if v.get('importance', 0) >= min_importance]
              # Sort by importance (ora basata sul valore del voto in STEEM)
            voters_data.sort(key=lambda x: x['importance'], reverse=True)
            
            # Limita il risultato finale ai votanti più importanti
            final_voters_limit = max(20, max_detailed_voters)  # Mantieni almeno questo numero di votanti importanti
            if len(voters_data) > final_voters_limit:
                voters_data = voters_data[:final_voters_limit]
            
            # Logga il tempo totale di esecuzione e i primi votanti importanti
            execution_time = time.time() - start_time
            logger.info(f"Analisi votanti completata in {execution_time:.2f} secondi")
            if voters_data:
                top_voters = [f"{v['voter']} (dopo {v['vote_delay_minutes']} min., valore voto: {v.get('steem_vote_value', 0):.3f} STEEM, importanza: {v['importance']:.2f})" 
                            for v in voters_data[:3]]
                logger.info(f"Top votanti per {post_url}: {', '.join(top_voters)}")
              # Salva nella cache con timestamp se l'operazione ha avuto successo
            if voters_data:
                # Includi timestamp nella cache per controllare la validità
                cache_entry = {
                    'data': voters_data,
                    'timestamp': time.time(),  # Aggiungi timestamp per TTL
                    'post_url': post_url
                }
                self._voters_cache[cache_key] = cache_entry
                
                # Salva cache dopo ogni operazione riuscita
                self._save_cache()
                
                # Pulisci la cache se sta diventando troppo grande (mantieni solo gli ultimi 50 elementi)
                if len(self._voters_cache) > 50:
                    # Rimuovi le entry più vecchie
                    cache_items = list(self._voters_cache.items())
                    cache_items.sort(key=lambda x: x[1].get('timestamp', 0))
                    for old_key, _ in cache_items[:-50]:  # mantieni gli ultimi 50
                        del self._voters_cache[old_key]
                    logger.info(f"Cache pulita, mantenute {len(self._voters_cache)} entrate recenti")
                    
            logger.info(f"Analisi completata: trovati {len(voters_data)} votanti rilevanti per {post_url}")
            return voters_data
            
        except Exception as e:
            logger.error(f"Error getting post voters: {str(e)}")
            return []
            
    def cleanup(self):
        """Pulisce e salva la cache a fine esecuzione."""
        if self._voters_cache:
            self._save_cache()
            
    def calculate_optimal_vote_time(self, voters_data, buffer_minutes=0.2):
        """Calcola il tempo ottimale per votare in base ai votanti importanti
        
        L'importanza dei votanti è ora basata sul valore del voto in STEEM,
        rendendo più facile comprendere il loro impatto reale.
        
        Args:
            voters_data (list): Lista di dati sui votanti con 'importance', 'steem_vote_value' 
                               e 'vote_delay_minutes'
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
                'explanation': 'Valore di voto dei votanti troppo basso, usando il tempo predefinito di 5 minuti',
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
        
        # Trova il votante importante che vota più presto
        earliest_important_voter = min(top_voters, key=lambda x: x.get('vote_delay_minutes', 30))
        earliest_vote_time = earliest_important_voter.get('vote_delay_minutes', 30)
        
        # Calcola il tempo di voto ottimale - leggermente prima del votante importante più veloce
        optimal_time = max(0.5, earliest_vote_time - buffer_minutes)
        
        # Genera la spiegazione appropriata
        if earliest_important_voter['voter'] == most_important_voter['voter']:
            explanation = f"Votare {buffer_minutes} minuti prima del votante più importante (@{most_important_voter.get('voter', 'sconosciuto')}) che vota dopo {most_important_time:.1f} minuti"
        else:
            explanation = f"Votare {buffer_minutes} minuti prima del primo votante importante (@{earliest_important_voter.get('voter', 'sconosciuto')}) che vota dopo {earliest_vote_time:.1f} minuti"
        
        # Finestra stretta per massimizzare la precisione
        vote_window = (optimal_time - 0.2, optimal_time + 0.2)
        
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

    def calculate_vote_value(self, vote_percent, effective_vests=None, voting_power=9200):
        """Calculate vote value based on blockchain parameters, similar to the JS implementation."""
        try:
            # Step 1: Get dynamic global properties
            props = self.blockchain_connector.get_steem_dynamic_global_properties()
            
            # Step 2: Calculate SP/VESTS ratio
            total_vesting_fund_steem = float(props['total_vesting_fund_steem'].split(' ')[0])
            total_vesting_shares = float(props['total_vesting_shares'].split(' ')[0])
            steem_per_vests = total_vesting_fund_steem / total_vesting_shares
            
            # Step 3: If no vesting shares provided, use current user's
            vesting_shares = effective_vests
            if not vesting_shares:
                # Usiamo blockchain_connector invece di blockchain
                account = self.blockchain_connector.get_account_info(CURATOR)
                if not account:
                    raise Exception('Unable to get account info')
                
                # Ottieni i vesting shares dall'account
                account_vests = float(account['vesting_shares'].amount)
                delegated_out = float(account['delegated_vesting_shares'].amount)
                received_vests = float(account['received_vesting_shares'].amount)
                vesting_shares = account_vests - delegated_out + received_vests
            
            # Step 4: Convert vests to Steem Power
            sp = vesting_shares * steem_per_vests
            
            # Step 5: Calculate 'r' (SP/spv ratio)
            r = sp / steem_per_vests
            
            # Step 6: Calculate 'p' (voting power)
            weight = vote_percent  # Convert percentage to weight (100% = 10000)
            p = (voting_power * weight / 10000 + 49) / 50
            
            # Step 7: Get reward fund con il nuovo metodo - utilizziamo blockchain_connector
            reward_fund = self.blockchain_connector.get_reward_fund("post")
            
            # Step 8: Calculate rbPrc
            recent_claims = float(reward_fund['recent_claims'])
            # Controlla il formato e adatta di conseguenza
            if 'reward_balance' in reward_fund:
                if isinstance(reward_fund['reward_balance'], str):
                    reward_balance = float(reward_fund['reward_balance'].split(' ')[0])
                else:
                    reward_balance = float(reward_fund['reward_balance'].amount)
            else:
                raise Exception("Format of reward_fund not recognized")
                
            rb_prc = reward_balance / recent_claims
            
            # Step 9: Get median price con il nuovo metodo - utilizziamo blockchain_connector
            price_info = self.blockchain_connector.get_current_median_history_price()
            
            base_amount = float(price_info['base']['amount'])
            quote_amount = float(price_info['quote']['amount'])
            steem_to_sbd_rate = base_amount / quote_amount
            
            # Step 10: Apply the official Steem formula
            steem_value = r * p * 100 * rb_prc
            
            # Convert STEEM to USD/SBD using the median price
            usd_value = steem_value * steem_to_sbd_rate
            
            # logger.info(f"""Vote Value Calculation:
            #   - SP: {sp:.3f}
            #   - Vote Weight: {weight}
            #   - Voting Power: {voting_power}
            #   - Price ratio: {steem_to_sbd_rate:.4f}
            #   - Result: {steem_value:.4f} STEEM (${usd_value:.4f})""")
            
            return {
                "steem_value": float(f"{steem_value:.4f}"),
                "sbd_value": float(f"{usd_value:.4f}"),
                "formula": {
                    "r": r,
                    "p": p,
                    "rb_prc": rb_prc,
                    "median": steem_to_sbd_rate
                }
            }
        except Exception as e:
            logger.error(f'Error calculating vote value: {str(e)}')
            return {
                "steem_value": 0,
                "sbd_value": 0,
                "error": str(e)
            }
    
    async def _fetch_voter_details_async(self, voter_name, post_url, blockchain_instance):
        """Recupera in modo asincrono i dettagli di un votante"""
        try:
            voter_account = await asyncio.to_thread(
                self.blockchain_connector.get_account_info, voter_name
            )
            
            # Calcola vesting shares
            vests = float(voter_account['vesting_shares'].amount) + \
                   float(voter_account['received_vesting_shares'].amount) - \
                   float(voter_account['delegated_vesting_shares'].amount)
            
            # Calcola reputazione
            reputation = voter_account.get_reputation()
            
            # Ottieni il voto
            vote = await asyncio.to_thread(
                Vote, voter_name, post_url, blockchain_instance=blockchain_instance
            )
            
            # Informazioni sul voto
            vote_percent = vote.percent
            vote_time = vote.time
            vote_rshares = float(vote.rshares)
            
            # Calcola il valore del voto
            vote_value = await asyncio.to_thread(
                self.calculate_vote_value, vote_percent, effective_vests=vests
            )
            
            return {
                'voter_name': voter_name,
                'vests': vests,
                'reputation': reputation,
                'vote_percent': vote_percent,
                'vote_time': vote_time,
                'vote_rshares': vote_rshares,
                'vote_value': vote_value
            }
        except Exception as e:
            logger.debug(f"Errore nel recupero dettagli per {voter_name}: {e}")
            return {
                'voter_name': voter_name,
                'error': str(e)
            }
    
    async def _process_voters_parallel(self, voters_to_process, post_url, post_created, blockchain_instance, curator_username, max_concurrent=3):
        """Processa più votanti in parallelo con limite di concorrenza"""
        processed_voters = []
        # Usa un semaforo per limitare la concorrenza
        sem = asyncio.Semaphore(max_concurrent)
        
        async def process_one_voter(voter_data):
            async with sem:
                try:
                    voter_name = voter_data['voter']
                    # Escludi il curatore stesso
                    if voter_name.lower() == curator_username:
                        return None
                    
                    # Prima prova a ottenere rshares direttamente dal voto (più veloce)
                    vote_rshares = float(voter_data.get('rshares', 0))
                    
                    # Per i votanti importanti, recupera dettagli completi in modo asincrono
                    importance = vote_rshares / 1e12  # Stima preliminare
                    
                    # Inizializza con valori di base
                    result = {
                        'voter': voter_name,
                        'weight': voter_data.get('percent', 0),
                        'rshares': vote_rshares,
                        'vesting_shares': 0,
                        'importance': importance,
                        'vote_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'vote_delay_minutes': 5,
                        'reputation': 0,
                        'steem_vote_value': 0,
                        'vote_value_usd': 0
                    }
                    
                    # Recupera dettagli per votanti importanti
                    if importance >= 0.5 or vote_rshares >= 5e11:
                        details = await self._fetch_voter_details_async(
                            voter_name, post_url, blockchain_instance
                        )
                        
                        if 'error' not in details:
                            # Aggiorna con informazioni dettagliate
                            result.update({
                                'vote_time': details['vote_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(details['vote_time'], 'strftime') else details['vote_time'],
                                'vesting_shares': details['vests'],
                                'reputation': details['reputation'],
                                'steem_vote_value': details['vote_value'].get('steem_value', 0),
                                'vote_value_usd': details['vote_value'].get('sbd_value', 0),
                                'importance': details['vote_value'].get('steem_value', 0) * 10  # Scala per compatibilità
                            })
                    
                    return result
                except Exception as e:
                    logger.debug(f"Errore nell'elaborazione parallela per {voter_data.get('voter', 'unknown')}: {e}")
                    return None
        
        # Crea task per ogni votante
        tasks = [process_one_voter(voter) for voter in voters_to_process]
        results = await asyncio.gather(*tasks)
        
        # Filtra risultati nulli
        return [r for r in results if r is not None]