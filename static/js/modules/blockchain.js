/**
 * Blockchain Module - Gestisce l'interazione con le blockchain Steem e Hive
 */

class BlockchainService {  constructor() {
    this.nodes = {
      steem: [
        'https://api.steemit.com',
        'https://api.justyy.com',
        'https://api.moecki.online'
      ],
      hive: [
        'https://api.deathwing.me',
        'https://api.hive.blog',
        'https://api.openhive.network'
      ]
    };
    
    this.currentNodes = { steem: 0, hive: 0 };
    this.steemClient = null;
    this.hiveClient = null;
    this.currentPlatform = 'steem'; // Default platform
    
    // Inizializzazione quando il browser carica steem e dhive
    this.initializeClientsWhenReady();
  }

  /**
   * Controlla se i client blockchain sono disponibili e li inizializza
   */
  initializeClientsWhenReady() {
    // Controlla se steem e dhive sono già caricati
    if (typeof steem !== 'undefined' && typeof dhive !== 'undefined') {
      this.initializeClients();
    } else {
      // Riprova dopo un breve timeout
      setTimeout(() => this.initializeClientsWhenReady(), 200);
    }
  }
  /**
   * Inizializza i client blockchain
   */
  initializeClients() {
    this.steemClient = steem;
    this.steemClient.api.setOptions({ url: this.nodes.steem[0] });
    this.hiveClient = new dhive.Client(this.nodes.hive);
    console.log("Blockchain clients initialized");
  }

  /**
   * Passa al nodo successivo per la blockchain specificata
   * @param {string} platform - 'steem' o 'hive'
   * @returns {Promise<void>}
   */
  async switchNode(platform) {
    this.currentNodes[platform] = (this.currentNodes[platform] + 1) % this.nodes[platform].length;
    const newNode = this.nodes[platform][this.currentNodes[platform]];
    
    if (platform === 'steem') {
      this.steemClient.api.setOptions({ url: newNode });
    } else {
      this.hiveClient = new dhive.Client([newNode]);
    }
    
    console.log(`Switched ${platform} node to: ${newNode}`);
  }
  /**
   * Verifica la connessione al nodo corrente
   * @param {string} platform - 'steem' o 'hive'
   * @returns {Promise<boolean>} - true se la connessione è ok
   */
  async verifyNodeConnection(platform) {
    try {
      await this.executeWithFallback(platform, async (client) => {
        if (platform === 'steem') {
          return new Promise((resolve, reject) => {
            client.api.getDynamicGlobalProperties((err, result) => {
              if (err) reject(err);
              else resolve(result);
            });
          });
        } else {
          return await client.database.getDynamicGlobalProperties();
        }
      });
      return true;
    } catch (error) {
      console.error(`Impossibile stabilire una connessione con alcun nodo ${platform}:`, error);
      return false;
    }
  }
  /**
   * Ottiene le informazioni di un account
   * @param {string} username - Nome utente
   * @param {string} platform - 'steem' o 'hive'
   * @returns {Promise<Object>} - Informazioni dell'account
   */
  async getAccountInfo(username, platform) {
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getAccounts([username], (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.database.getAccounts([username]);
      }
    });
  }
  /**
   * Ottiene i post più recenti di un utente
   * @param {string} username - Nome utente
   * @param {string} platform - 'steem' o 'hive'
   * @returns {Promise<Array>} - Lista di post
   */
  async getLatestPosts(username, platform) {
    const query = {
      tag: username,
      limit: 1
    };
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getDiscussionsByBlog(query, (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.database.getDiscussions('blog', query);
      }
    });
  }

  /**
   * Ottiene le proprietà dinamiche globali della blockchain
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Proprietà dinamiche globali
   */
  async getDynamicGlobalProperties(platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getDynamicGlobalProperties((err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.database.getDynamicGlobalProperties();
      }
    });
  }
  
  /**
   * Ottiene il contenuto di un post o commento
   * @param {string} author - Autore del post
   * @param {string} permlink - Permlink del post
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Contenuto del post
   */
  async getContent(author, permlink, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getContent(author, permlink, (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.call('condenser_api', 'get_content', [author, permlink]);
      }
    });
  }
  
  /**
   * Ottiene la cronologia delle operazioni di un account
   * @param {string} username - Nome utente
   * @param {number} start - Punto di partenza (default: -1 per iniziare dall'operazione più recente)
   * @param {number} limit - Limite di operazioni da restituire (default: 1000)
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Array>} - Cronologia delle operazioni
   */
  async getAccountHistory(username, start = -1, limit = 1000, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getAccountHistory(username, start, limit, (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.call('condenser_api', 'get_account_history', [username, start, limit]);
      }
    });
  }

  /**
   * Invia un commento o post alla blockchain
   * @param {Object} commentData - Dati del commento/post
   * @param {string} commentData.parentAuthor - Autore del post padre (vuoto se è un post principale)
   * @param {string} commentData.parentPermlink - Permlink del post padre
   * @param {string} commentData.author - Autore del commento/post
   * @param {string} commentData.permlink - Permlink del commento/post
   * @param {string} commentData.title - Titolo (vuoto per i commenti)
   * @param {string} commentData.body - Corpo del testo
   * @param {Object} commentData.jsonMetadata - Metadati JSON
   * @param {string} privateKey - Chiave privata per firmare la transazione
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Risultato dell'operazione
   */
  async createComment(commentData, privateKey, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.broadcast.comment(
            commentData.parentAuthor,
            commentData.parentPermlink,
            commentData.author,
            commentData.permlink,
            commentData.title,
            commentData.body,
            commentData.jsonMetadata,
            privateKey,
            (err, result) => {
              if (err) reject(err);
              else resolve(result);
            }
          );
        });
      } else {
        // Per Hive usiamo il client dhive
        const operations = [
          ['comment', {
            parent_author: commentData.parentAuthor,
            parent_permlink: commentData.parentPermlink,
            author: commentData.author,
            permlink: commentData.permlink,
            title: commentData.title,
            body: commentData.body,
            json_metadata: JSON.stringify(commentData.jsonMetadata)
          }]
        ];
        
        const key = dhive.PrivateKey.fromString(privateKey);
        return await client.broadcast.sendOperations(operations, key);
      }
    });
  }

  /**
   * Vota un post o un commento
   * @param {string} voter - Nome utente del votante
   * @param {string} author - Autore del post/commento
   * @param {string} permlink - Permlink del post/commento
   * @param {number} weight - Peso del voto (tra -10000 e 10000)
   * @param {string} privateKey - Chiave privata per firmare la transazione
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Risultato dell'operazione
   */
  async vote(voter, author, permlink, weight, privateKey, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.broadcast.vote(
            voter,
            author,
            permlink,
            weight,
            privateKey,
            (err, result) => {
              if (err) reject(err);
              else resolve(result);
            }
          );
        });
      } else {
        // Per Hive usiamo il client dhive
        const operations = [
          ['vote', {
            voter,
            author,
            permlink,
            weight
          }]
        ];
        
        const key = dhive.PrivateKey.fromString(privateKey);
        return await client.broadcast.sendOperations(operations, key);
      }
    });
  }
  
  /**
   * Ottiene il dominio corretto per una piattaforma
   * @param {string} platform - 'steem' o 'hive'
   * @returns {string} - URL del dominio
   */
  getDomainForPlatform(platform) {
    return platform === 'steem' ? 'https://steemit.com' : 'https://peakd.com';
  }  /**
   * Esegue una richiesta API con fallback automatico tra nodi in caso di errore
   * @param {string} platform - 'steem' o 'hive'
   * @param {Function} requestFunction - Funzione che esegue la richiesta API
   * @returns {Promise<any>} - Risultato della richiesta
   */
  async executeWithFallback(platform, requestFunction) {
    // In caso di piattaforma non specificata, usa quella corrente
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    // Verifica che la piattaforma sia valida
    if (platform !== 'steem' && platform !== 'hive') {
      throw new Error(`Piattaforma non valida: ${platform}`);
    }
    
    // Numero totale di nodi disponibili per la piattaforma
    const totalNodes = this.nodes[platform].length;
    
    // Copia dell'indice del nodo corrente
    let nodeIndex = this.currentNodes[platform];
    let attempts = 0;
    const maxAttempts = totalNodes * 2; // Tenta ogni nodo due volte prima di fallire definitivamente
    
    // Tenta l'operazione con ogni nodo fino a quando ha successo o superato il numero massimo di tentativi
    while (attempts < maxAttempts) {
      const currentNode = this.nodes[platform][nodeIndex];
      
      try {
        // Assicurati che il client sia configurato per usare il nodo corrente
        if (platform === 'steem') {
          this.steemClient.api.setOptions({ url: currentNode });
        } else {
          this.hiveClient = new dhive.Client([currentNode]);
        }
        
        console.log(`Esecuzione richiesta su ${platform} usando il nodo: ${currentNode}`);
        
        // Esegui la funzione di richiesta
        const result = await requestFunction(platform === 'steem' ? this.steemClient : this.hiveClient);
        
        // Se la richiesta ha successo, aggiorna l'indice del nodo corrente e restituisci il risultato
        this.currentNodes[platform] = nodeIndex;
        return result;
        
      } catch (error) {
        attempts++;
        console.warn(`Errore sul nodo ${currentNode}: ${error.message} (Tentativo ${attempts}/${maxAttempts})`);
        
        // Passa al nodo successivo
        nodeIndex = (nodeIndex + 1) % totalNodes;
        
        // Se abbiamo provato tutti i nodi, aspetta un po' prima di riprovare
        if (attempts % totalNodes === 0) {
          console.log(`Provati tutti i nodi disponibili per ${platform}. Attesa prima di riprovare...`);
          await new Promise(resolve => setTimeout(resolve, 2000)); // Attendi 2 secondi
        }
      }
    }
    
    // Se tutti i tentativi falliscono, lancia un errore
    throw new Error(`Impossibile completare la richiesta su ${platform} dopo ${maxAttempts} tentativi`);
  }

  /**
   * Get current active blockchain platform
   * @returns {string} Current platform ('steem' or 'hive')
   */
  getCurrentPlatform() {
    return this.currentPlatform;
  }
  
  /**
   * Set current active blockchain platform
   * @param {string} platform - Platform to use ('steem' or 'hive')
   */
  setCurrentPlatform(platform) {
    if (platform === 'steem' || platform === 'hive') {
      this.currentPlatform = platform;
    }
  }
  
  /**
   * Get active client for current platform
   * @returns {Object} Client object for current platform
   */
  getActiveClient() {
    return this.currentPlatform === 'steem' ? this.steemClient : this.hiveClient;
  }
  
  /**
   * Ottiene le discussioni per tag
   * @param {string} tag - Tag da cercare
   * @param {Object} query - Parametri di query (limit, start_author, start_permlink)
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Array>} - Lista di discussioni
   */
  async getDiscussionsByTag(tag, query = { limit: 20 }, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getDiscussionsByTrending({ ...query, tag }, (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.database.getDiscussions('trending', { ...query, tag });
      }
    });
  }
  
  /**
   * Ottiene la ricompensa stimata per un post
   * @param {string} author - Autore del post
   * @param {string} permlink - Permlink del post
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Ricompensa stimata
   */
  async getEstimatedReward(author, permlink, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    try {
      const content = await this.getContent(author, permlink, platform);
      
      if (!content) {
        throw new Error('Post non trovato');
      }
      
      return {
        pendingPayout: parseFloat(content.pending_payout_value.split(' ')[0]),
        totalPayout: parseFloat(content.total_payout_value.split(' ')[0]),
        curatorPayout: parseFloat(content.curator_payout_value.split(' ')[0]),
        payoutTime: new Date(content.cashout_time + 'Z')
      };
    } catch (error) {
      console.error(`Errore nel recupero della ricompensa stimata per ${author}/${permlink}:`, error);
      throw error;
    }
  }

  /**
   * Ottiene i dettagli del voto di un utente specifico su un post
   * @param {string} author - Autore del post
   * @param {string} permlink - Permlink del post
   * @param {string} voter - Nome utente del votante
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Dettagli del voto o null se non trovato
   */
  async getUserVoteOnPost(author, permlink, voter, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    try {
      const content = await this.getContent(author, permlink, platform);
      
      if (!content || !content.active_votes || !Array.isArray(content.active_votes)) {
        return null;
      }
      
      // Cerca il voto dell'utente specifico
      const userVote = content.active_votes.find(vote => 
        vote.voter && vote.voter.toLowerCase() === voter.toLowerCase()
      );
      
      if (userVote) {
        return {
          voter: userVote.voter,
          percent: parseFloat(userVote.percent),
          weight: parseFloat(userVote.weight),
          rshares: parseFloat(userVote.rshares),
          reputation: userVote.reputation || 0,
          time: userVote.time || null
        };
      }
      
      return null;
    } catch (error) {
      console.error(`Errore nel recupero del voto di ${voter} per ${author}/${permlink}:`, error);
      return null;
    }
  }

  /**
   * Ottiene tutti i voti su un post
   * @param {string} author - Autore del post
   * @param {string} permlink - Permlink del post
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Array>} - Array di voti
   */
  async getPostVotes(author, permlink, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    try {
      const content = await this.getContent(author, permlink, platform);
      
      if (!content || !content.active_votes || !Array.isArray(content.active_votes)) {
        return [];
      }
      
      return content.active_votes.map(vote => ({
        voter: vote.voter,
        percent: parseFloat(vote.percent),
        weight: parseFloat(vote.weight),
        rshares: parseFloat(vote.rshares),
        reputation: vote.reputation || 0,
        time: vote.time || null
      }));
    } catch (error) {
      console.error(`Errore nel recupero dei voti per ${author}/${permlink}:`, error);
      return [];
    }
  }
    
  /**
   * Invia una notifica all'utente riguardo allo stato dei nodi
   * @param {string} message - Messaggio da mostrare all'utente
   * @param {string} type - Tipo di notifica ('info', 'warning', 'error')
   */
  notifyUser(message, type = 'info') {
    if (typeof eventEmitter !== 'undefined') {
      eventEmitter.emit('notification', {
        type,
        message,
        timeout: type === 'error' ? 8000 : 5000 // Mantieni l'errore visibile più a lungo
      });
    } else {
      console[type === 'error' ? 'error' : type === 'warning' ? 'warn' : 'log'](message);
    }
  }

  /**
   * Ottiene le informazioni del reward fund dalla blockchain
   * @param {string} fundName - Nome del fund (default: 'post')
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Informazioni del reward fund
   */
  async getRewardFund(fundName = 'post', platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getRewardFund(fundName, (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.call('condenser_api', 'get_reward_fund', [fundName]);
      }
    });
  }

  /**
   * Ottiene il prezzo mediano corrente dalla blockchain
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Informazioni sul prezzo mediano
   */
  async getCurrentMedianHistoryPrice(platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }
    
    return await this.executeWithFallback(platform, async (client) => {
      if (platform === 'steem') {
        return new Promise((resolve, reject) => {
          client.api.getCurrentMedianHistoryPrice((err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        return await client.call('condenser_api', 'get_current_median_history_price', []);
      }
    });
  }

  /**
   * Calcola il valore del voto basato sui parametri della blockchain
   * @param {number} votePercent - Percentuale del voto (0-100)
   * @param {number} effectiveVests - Vests effettivi dell'account (opzionale)
   * @param {number} votingPower - Voting power dell'account (default: 10000 = 100%)
   * @param {string} username - Username per recuperare i vests se non forniti
   * @param {string} platform - 'steem' o 'hive' (opzionale, default: piattaforma corrente)
   * @returns {Promise<Object>} - Risultato del calcolo con valori in STEEM e SBD/HBD
   */
  async calculateVoteValue(votePercent, effectiveVests = null, votingPower = 10000, username = null, platform = null) {
    if (!platform) {
      platform = this.currentPlatform;
    }

    try {
      console.log(`Calcolo valore voto: ${votePercent}% su ${platform}`);

      // Step 1: Ottieni le proprietà dinamiche globali
      const props = await this.getDynamicGlobalProperties(platform);
      
      // Step 2: Calcola il rapporto SP/VESTS
      const totalVestingFundSteem = parseFloat(props.total_vesting_fund_steem.split(' ')[0]);
      const totalVestingShares = parseFloat(props.total_vesting_shares.split(' ')[0]);
      const steemPerVests = totalVestingFundSteem / totalVestingShares;

      // Step 3: Se non forniti vesting shares, usa quelli dell'account corrente
      let vestingShares = effectiveVests;
      if (!vestingShares && username) {
        const accounts = await this.getAccountInfo(username, platform);
        if (!accounts || accounts.length === 0) {
          throw new Error('Impossibile ottenere informazioni account');
        }
        
        const account = accounts[0];
        const accountVests = parseFloat(account.vesting_shares.split(' ')[0]);
        const delegatedOut = parseFloat(account.delegated_vesting_shares.split(' ')[0]);
        const receivedVests = parseFloat(account.received_vesting_shares.split(' ')[0]);
        vestingShares = accountVests - delegatedOut + receivedVests;
      }

      if (!vestingShares) {
        throw new Error('Vesting shares non disponibili');
      }

      // Step 4: Converti vests in Steem Power
      const sp = vestingShares * steemPerVests;

      // Step 5: Calcola 'r' (rapporto SP/spv)
      const r = sp / steemPerVests;

      // Step 6: Calcola 'p' (voting power)
      const weight = votePercent * 100; // Converti percentuale in weight (100% = 10000)
      const p = (votingPower * weight / 10000 + 49) / 50;

      // Step 7: Ottieni il reward fund
      const rewardFund = await this.getRewardFund('post', platform);

      // Step 8: Calcola rbPrc
      const recentClaims = parseFloat(rewardFund.recent_claims);
      let rewardBalance;
      
      if (typeof rewardFund.reward_balance === 'string') {
        rewardBalance = parseFloat(rewardFund.reward_balance.split(' ')[0]);
      } else {
        rewardBalance = parseFloat(rewardFund.reward_balance.amount);
      }
      
      const rbPrc = rewardBalance / recentClaims;

      // Step 9: Ottieni il prezzo mediano
      const priceInfo = await this.getCurrentMedianHistoryPrice(platform);
      
      const baseAmount = parseFloat(priceInfo.base.split(' ')[0]);
      const quoteAmount = parseFloat(priceInfo.quote.split(' ')[0]);
      const steemToSbdRate = baseAmount / quoteAmount;

      // Step 10: Applica la formula ufficiale Steem
      const steemValue = r * p * 100 * rbPrc;

      // Converti STEEM in USD/SBD usando il prezzo mediano
      const usdValue = steemValue * steemToSbdRate;

      console.log(`Calcolo completato:
        - SP: ${sp.toFixed(3)}
        - Vote Weight: ${weight}
        - Voting Power: ${votingPower}
        - Price ratio: ${steemToSbdRate.toFixed(4)}
        - Result: ${steemValue.toFixed(4)} STEEM (${usdValue.toFixed(4)} USD)`);

      return {
        steemValue: parseFloat(steemValue.toFixed(4)),
        sbdValue: parseFloat(usdValue.toFixed(4)),
        formula: {
          r: r,
          p: p,
          rbPrc: rbPrc,
          median: steemToSbdRate,
          sp: sp,
          vestingShares: vestingShares
        }
      };

    } catch (error) {
      console.error('Errore nel calcolo del valore del voto:', error);
      return {
        steemValue: 0,
        sbdValue: 0,
        error: error.message
      };
    }
  }
}

// Esporta un'istanza singleton
const blockchainService = new BlockchainService();
export default blockchainService;