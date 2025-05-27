import asyncio
from flask import current_app
from ..components.logger_config import logger
from ..components.beem import Blockchain
from ..components.config import steem_curator as CURATOR
from beem.comment import Comment
from beem.account import Account
import time
from datetime import datetime, timezone, timedelta
from beem.vote import Vote

# Istanza globale del BlockchainConnector
blockchain_connector = Blockchain(app=current_app)

class VoteManager:
    def __init__(self, blockchain_connector_instance=None):
        self.blockchain_connector = blockchain_connector_instance or blockchain_connector
    
    def calculate_vote_value(self, vote_percent, effective_vests=None, voting_power=9200):
        """Calculate vote value based on blockchain parameters, similar to the JS implementation."""
        try:
            # Step 1: Get dynamic global properties
            props = blockchain_connector.get_dynamic_global_properties()
            
            # Step 2: Calculate SP/VESTS ratio
            total_vesting_fund_steem = float(props['total_vesting_fund_steem'].split(' ')[0])
            total_vesting_shares = float(props['total_vesting_shares'].split(' ')[0])
            steem_per_vests = total_vesting_fund_steem / total_vesting_shares
            
            # Step 3: If no vesting shares provided, use current user's
            vesting_shares = effective_vests
            if not vesting_shares:
                # Usiamo blockchain_connector invece di blockchain
                account = blockchain_connector.get_account_info(CURATOR)
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
            reward_fund = blockchain_connector.get_reward_fund("post")
            
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
            price_info = blockchain_connector.get_current_median_history_price()
            
            base_amount = float(price_info['base']['amount'])
            quote_amount = float(price_info['quote']['amount'])
            steem_to_sbd_rate = base_amount / quote_amount
            
            # Step 10: Apply the official Steem formula
            steem_value = r * p * 100 * rb_prc
            
            # Convert STEEM to USD/SBD using the median price
            usd_value = steem_value * steem_to_sbd_rate
            
            logger.info(f"""Vote Value Calculation:
            - SP: {sp:.3f}
            - Vote Weight: {weight}
            - Voting Power: {voting_power}
            - Price ratio: {steem_to_sbd_rate:.4f}
            - Result: {steem_value:.4f} STEEM (${usd_value:.4f})""")
            
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

    def get_post_voters(self, post_url, min_importance=0.0):
        """Get the voters of a post sorted by importance (vesting shares or rshares)
        
        Args:
            post_url (str): The URL or identifier of the post
            min_importance (float): Minimum importance threshold to filter voters
            use_cache (bool): Whether to use cached voters data if available
            
        Returns:
            list: List of dictionaries with voter information
        """
    
        try:
            start_time = time.time()
            
            max_detailed_voters = 10  # Limite per analisi dettagliate
            max_total_voters = 30  # Limite totale di votanti da considerare
            
            platform, blockchain_instance = self.blockchain_connector.get_platform_and_instance(post_url)
            curator_info = blockchain_connector.get_curator_info(platform)
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
                logger.info(f"Limitati a {max_total_voters} voti senza pre-ordinamento per {post_url}")
            
            # Get voters data
            voters_data = []
            processed_voters = 0
            
            # Processa i voti più significativi (in batch per maggiore efficienza)
            for vote_data in active_votes:
                try:
                    voter_name = vote_data['voter']
                    # Escludi il curatore stesso
                    if voter_name.lower() == curator_username:
                        continue
                    processed_voters += 1
                    
                    # Prima prova a ottenere rshares direttamente dal voto (più veloce)
                    vote_rshares = float(vote_data.get('rshares', 0))
                    
                    # Salta rapidamente i voti non significativi se abbiamo superato il limite per analisi dettagliate
                    if processed_voters > max_detailed_voters and vote_rshares < 1e7:  # 10M rshares come soglia
                        continue
                    
                    # # Estrai informazioni dirette dal voto quando disponibili
                    # vote_percent = float(vote_data.get('percent', 0))
                    
                    # # Determina quando è avvenuto il voto
                    # vote_time = vote_data.get('time')
                    # if isinstance(vote_time, str):
                    #     vote_time = datetime.strptime(vote_time, '%Y-%m-%dT%H:%M:%S')
                    #     if vote_time.tzinfo is None:
                    #         vote_time = vote_time.replace(tzinfo=timezone.utc)
                    
                    # Se non abbiamo il timestamp nel voto base, usa il timestamp del post o il timestamp corrente
                    # if not vote_time:
                    #     if 'last_update' in vote_data:
                    #         vote_time = datetime.strptime(vote_data['last_update'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                    #     else:
                            # Per votanti top (importanti), vale la pena cercare il tempo preciso
                    if processed_voters <= max_detailed_voters:
                        try:
                            vote = Vote(voter_name, post_url, blockchain_instance=blockchain_instance)
                            vote_time = vote.time
                            vote_percent = vote.percent
                            if vote_time.tzinfo is None:
                                vote_time = vote_time.replace(tzinfo=timezone.utc)
                            
                            if not vote_rshares or vote_rshares == 0:
                                vote_rshares = float(vote.rshares)
                            
                        except Exception as vote_error:
                            logger.debug(f"Errore nel recupero dati voto per {voter_name}: {vote_error}")
                            vote_time = post_created + timedelta(hours=1)  # stima
                    else:
                        # Per votanti meno importanti, usa una stima
                        vote_time = post_created + timedelta(hours=1)
                    
                    # Calcola il ritardo del voto in minuti
                    vote_delay_minutes = int((vote_time - post_created).total_seconds() / 60)
                    
                    # Calcola l'importanza usando rshares direttamente se disponibili
                    importance = vote_rshares / 1e12  # Normalizza per leggibilità
                    
                    # Solo per i top votanti, ottieni ulteriori informazioni sull'account
                    vests = 0
                    reputation = 0
                    
                    # Per i primi N votanti o quelli con rshares significativi, ottieni dettagli aggiuntivi
                    if processed_voters <= max_detailed_voters or vote_rshares >= 1e9:  # 1B rshares come soglia
                        try:
                            # Cache locale temporanea per account (durante questa esecuzione)
                            voter_account = Account(voter_name, blockchain_instance=blockchain_instance)
                            vests = float(voter_account['vesting_shares'].amount) + float(voter_account['received_vesting_shares'].amount) - float(voter_account['delegated_vesting_shares'].amount)
                            calculate_vote_value = self.calculate_vote_value(vote_percent, effective_vests=vests)
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
                            'reputation': reputation,
                            'steem_vote_value': calculate_vote_value.get('steem_value', 0) if 'calculate_vote_value' in locals() else 0,
                            'sbd_vote_value': calculate_vote_value.get('sbd_value', 0) if 'calculate_vote_value' in locals() else 0
                        })
                except Exception as e:
                    logger.warning(f"Error processing voter {vote_data.get('voter', 'unknown')}: {str(e)}")
                    continue
            
            # Sort by importance (vesting shares o rshares)
            voters_data.sort(key=lambda x: x['importance'], reverse=True)
            
            # Limita il risultato finale ai votanti più importanti
            final_voters_limit = max(20, max_detailed_voters)  # Mantieni almeno questo numero di votanti importanti
            if len(voters_data) > final_voters_limit:
                voters_data = voters_data[:final_voters_limit]
            
            # Logga il tempo totale di esecuzione e i primi votanti importanti
            execution_time = time.time() - start_time
            logger.info(f"Analisi votanti completata in {execution_time:.2f} secondi")
            
            if voters_data:
                top_voters = [f"{v['voter']} (dopo {v['vote_delay_minutes']} min., importanza: {v['importance']:.2f})" 
                            for v in voters_data[:3]]
                logger.info(f"Top votanti per {post_url}: {', '.join(top_voters)}")
            
            return voters_data
            
        except Exception as e:
            logger.error(f"Error getting post voters: {str(e)}")
            return []

    def calculate_optimal_vote_time(self, voters_data, buffer_minutes=0.2):
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