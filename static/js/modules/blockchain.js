/**
 * Blockchain Module - Gestisce l'interazione con le blockchain Steem e Hive
 */

class BlockchainService {
  constructor() {
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
      if (platform === 'steem') {
        await new Promise((resolve, reject) => {
          this.steemClient.api.getDynamicGlobalProperties((err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        await this.hiveClient.database.getDynamicGlobalProperties();
      }
      return true;
    } catch (error) {
      console.error(`Node connection failed for ${platform}, switching...`, error);
      await this.switchNode(platform);
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
    let attempts = 0;
    const maxAttempts = 3;

    while (attempts < maxAttempts) {
      try {
        if (platform === 'steem') {
          const result = await new Promise((resolve, reject) => {
            this.steemClient.api.getAccounts([username], (err, result) => {
              if (err) reject(err);
              else resolve(result);
            });
          });
          return result;
        } else {
          return await this.hiveClient.database.getAccounts([username]);
        }
      } catch (error) {
        attempts++;
        console.error(`Attempt ${attempts} failed for ${username}:`, error);
        if (attempts === maxAttempts) throw error;
        await this.switchNode(platform);
      }
    }
  }

  /**
   * Ottiene i post più recenti di un utente
   * @param {string} username - Nome utente
   * @param {string} platform - 'steem' o 'hive'
   * @returns {Promise<Array>} - Lista di post
   */
  async getLatestPosts(username, platform) {
    let attempts = 0;
    const maxAttempts = 3;

    while (attempts < maxAttempts) {
      try {
        const query = {
          tag: username,
          limit: 1
        };

        if (platform === 'steem') {
          return await new Promise((resolve, reject) => {
            this.steemClient.api.getDiscussionsByBlog(query, (err, result) => {
              if (err) reject(err);
              else resolve(result);
            });
          });
        } else {
          return await this.hiveClient.database.getDiscussions('blog', query);
        }
      } catch (error) {
        attempts++;
        console.error(`Attempt ${attempts} failed for getting posts:`, error);
        if (attempts === maxAttempts) throw error;
        await this.switchNode(platform);
      }
    }
  }

  /**
   * Ottiene il dominio corretto per una piattaforma
   * @param {string} platform - 'steem' o 'hive'
   * @returns {string} - URL del dominio
   */
  getDomainForPlatform(platform) {
    return platform === 'steem' ? 'https://steemit.com' : 'https://peakd.com';
  }

  /**
   * Calcola il valore del voto di un utente
   * @param {string} username - Nome dell'utente
   * @param {number} voteWeight - Peso del voto (0-100)
   * @param {string} platform - 'steem' o 'hive'
   * @returns {Promise<Object>} - Valore del voto in STEEM/HIVE e SBD
   */
  async calculateVoteValue(username, voteWeight = 100, platform = 'steem') {
    try {
      // Verifica connessione al nodo
      await this.verifyNodeConnection(platform);
      
      // Ottieni l'account dell'utente
      const accounts = await this.getAccountInfo(username, platform);
      if (!accounts || accounts.length === 0) {
        throw new Error(`Account ${username} non trovato`);
      }
      
      const account = accounts[0];
      
      // Ottieni proprietà globali
      let props;
      if (platform === 'steem') {
        props = await new Promise((resolve, reject) => {
          this.steemClient.api.getDynamicGlobalProperties((err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        props = await this.hiveClient.database.getDynamicGlobalProperties();
      }
      
      // Ottieni rewardFund
      let rewardFund;
      if (platform === 'steem') {
        rewardFund = await new Promise((resolve, reject) => {
          this.steemClient.api.getRewardFund('post', (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        rewardFund = await this.hiveClient.database.call('get_reward_fund', ['post']);
      }
      
      // Ottieni prezzi correnti
      let price;
      if (platform === 'steem') {
        price = await new Promise((resolve, reject) => {
          this.steemClient.api.getCurrentMedianHistoryPrice((err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });
      } else {
        price = await this.hiveClient.database.getCurrentMedianHistoryPrice();
      }
      
      // Calcolo del valore del voto
      
      // 1. Calcola il rapporto SP/VESTS
      const totalVestingShares = parseFloat(props.total_vesting_shares.split(' ')[0]);
      const totalVestingFundSteem = parseFloat(props.total_vesting_fund_steem.split(' ')[0]);
      const steemPerVest = totalVestingFundSteem / totalVestingShares;
      
      // 2. Calcola vesting shares effettive
      const vestingShares = parseFloat(account.vesting_shares.split(' ')[0]);
      const receivedVesting = parseFloat(account.received_vesting_shares.split(' ')[0]);
      const delegatedVesting = parseFloat(account.delegated_vesting_shares.split(' ')[0]);
      const effectiveVestingShares = vestingShares + receivedVesting - delegatedVesting;
      
      // 3. Converti vesting shares in SP
      const sp = effectiveVestingShares * steemPerVest;
      
      // 4. Calcola power ratio (r) e peso voto (p)
      const r = sp / steemPerVest;
      const votingPower = account.voting_power;
      const weight = voteWeight * 100;  // peso in percentuale moltiplicato per 100
      const p = (votingPower * weight / 10000 + 49) / 50;
      
      // 5. Calcola rbPrc (reward balance per recent claim)
      const recentClaims = parseFloat(rewardFund.recent_claims);
      const rewardBalance = parseFloat(rewardFund.reward_balance.split(' ')[0]);
      const rbPrc = rewardBalance / recentClaims;
      
      // 6. Calcola il prezzo medio
      const baseAmount = parseFloat(price.base.split(' ')[0]);
      const quoteAmount = parseFloat(price.quote.split(' ')[0]);
      const steemToSbdRate = baseAmount / quoteAmount;
      
      // 7. Applica la formula ufficiale STEEM
      const steemValue = r * p * 100 * rbPrc;
      
      // 8. Converte STEEM in SBD usando il prezzo medio
      const sbdValue = steemValue * steemToSbdRate;
      debugger
      return {
        steemValue: parseFloat(steemValue.toFixed(4)),
        sbdValue: parseFloat(sbdValue.toFixed(4)),
        votingPower: votingPower / 100, // converte in percentuale
        sp: parseFloat(sp.toFixed(3))
      };
    } catch (error) {
      console.error(`Errore nel calcolo del valore del voto:`, error);
      return {
        steemValue: 0,
        sbdValue: 0,
        votingPower: 0,
        sp: 0,
        error: error.message
      };
    }
  }
}

// Esporta un'istanza singleton
const blockchainService = new BlockchainService();
export default blockchainService;