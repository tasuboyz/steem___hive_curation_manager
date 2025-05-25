/**
 * Wallet Service Module
 * Handles blockchain wallet operations, balances, and curation efficiency calculations
 */

import blockchainService from './blockchain.js';

class WalletService {
  constructor() {
    this.currentUser = null;
    this.balances = {
      steem: '0.000',
      sbd: '0.000',
      steemPower: '0.000'
    };
    
    // Listen for auth changes from an event system if available
    if (typeof eventEmitter !== 'undefined') {
      eventEmitter.on('auth:changed', ({ user }) => {
        this.currentUser = user ? user.username : null;
        if (this.currentUser) {
          this.updateBalances();
        }
      });
    }
    
    // Set initial user if authService is available
    if (typeof authService !== 'undefined') {
      const user = authService.getCurrentUser();
      if (user) {
        this.currentUser = user.username;
      }
    }
  }
    /**
   * Convert vests to STEEM POWER (SP)
   * @param {number|string} vests - Amount of vests to convert
   * @returns {Promise<number>} Converted SP amount
   */
  async vestsToSteem(vests) {
    try {
      const platform = blockchainService.getCurrentPlatform();
      const props = await blockchainService.getDynamicGlobalProperties(platform);
      
      if (platform === 'steem') {
        const vestSteem = parseFloat(props.total_vesting_fund_steem) / 
                          parseFloat(props.total_vesting_shares);
        return parseFloat(vests) * vestSteem;
      } else {
        // Hive implementation
        const vestHive = parseFloat(props.total_vesting_fund_hive) / 
                        parseFloat(props.total_vesting_shares);
        return parseFloat(vests) * vestHive;
      }
    } catch (error) {
      console.error('Error converting vests:', error);
      throw error;
    }
  }
    /**
   * Convert STEEM POWER (SP) to vests
   * @param {number|string} steemPower - Amount of SP to convert
   * @returns {Promise<number>} Converted vests amount
   */
  async steemToVests(steemPower) {
    try {
      const platform = blockchainService.getCurrentPlatform();
      const props = await blockchainService.getDynamicGlobalProperties(platform);
      
      if (platform === 'steem') {
        const steemVest = parseFloat(props.total_vesting_shares) / 
                          parseFloat(props.total_vesting_fund_steem);
        return parseFloat(steemPower) * steemVest;
      } else {
        // Hive implementation
        const hiveVest = parseFloat(props.total_vesting_shares) / 
                        parseFloat(props.total_vesting_fund_hive);
        return parseFloat(steemPower) * hiveVest;
      }
    } catch (error) {
      console.error('Error converting steem power to vests:', error);
      throw error;
    }
  }
  
  /**
   * Update user balances
   * @param {number} delayMs - Optional delay in milliseconds before updating
   */
  async updateBalances(delayMs = 0) {
    if (!this.currentUser) return;
    
    // Add delay if specified
    if (delayMs > 0) {
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
    
    try {
      const account = await this.getAccount(this.currentUser);
      
      if (account) {
        const platform = blockchainService.getCurrentPlatform();
        
        if (platform === 'steem') {
          this.balances.steem = account.balance;
          this.balances.sbd = account.sbd_balance;
        } else {
          this.balances.steem = account.balance; // Actually HIVE
          this.balances.sbd = account.hbd_balance; // HBD for Hive
        }
        
        // Convert vests to SP
        const vestingShares = parseFloat(account.vesting_shares);
        const delegatedVestingShares = parseFloat(account.delegated_vesting_shares || 0);
        const receivedVestingShares = parseFloat(account.received_vesting_shares || 0);
        
        const effectiveVestingShares = vestingShares - delegatedVestingShares + receivedVestingShares;
        
        this.balances.steemPower = await this.vestsToSteem(effectiveVestingShares);
        this.balances.steemPower = this.balances.steemPower.toFixed(3);
        
        // Emit event if event system available
        if (typeof eventEmitter !== 'undefined') {
          eventEmitter.emit('wallet:updated', { balances: this.balances });
        }
      }
    } catch (error) {
      console.error('Error updating balances:', error);
      if (typeof eventEmitter !== 'undefined') {
        eventEmitter.emit('notification', {
          type: 'error',
          message: 'Failed to update wallet balances'
        });
      }
    }
  }
    /**
   * Get account data from blockchain
   * @param {string} username - Username to fetch account for
   * @returns {Promise<Object>} Account data
   */
  async getAccount(username) {
    try {
      const accounts = await blockchainService.getAccountInfo(username, blockchainService.getCurrentPlatform());
      return accounts && accounts.length > 0 ? accounts[0] : null;
    } catch (error) {
      console.error(`Error fetching account ${username}:`, error);
      throw error;
    }
  }
  
  /**
   * Calculate voting power based on account data
   * @param {Object} account - The account data object
   * @returns {number} Current voting power as percentage (0-100)
   */
  calculateVotingPower(account) {
    // Voting Power calculation
    const lastVoteTime = new Date(account.last_vote_time + 'Z').getTime();
    const secondsPassedSinceLastVote = (new Date().getTime() - lastVoteTime) / 1000;
    const regeneratedVotingPower = secondsPassedSinceLastVote * (10000 / (5 * 24 * 60 * 60));
    const currentVotingPower = Math.min(10000, account.voting_power + regeneratedVotingPower) / 100;
      
    return Math.floor(currentVotingPower);
  }
  
  /**
   * Calculate curation efficiency metrics for a user over a specific time period
   * @param {string} username - Blockchain username to analyze
   * @param {number} daysBack - Number of days to look back (default: 7)
   * @returns {Promise<Object>} Curation statistics, efficiency data and APR
   */
  async calculateCurationEfficiency(username = null, daysBack = 7) {
    try {
      if (!username) {
        throw new Error('Username is required');
      }
      
      const account = await this.getAccount(username);
      if (!account) {
        throw new Error('Account not found');
      }
      
      // Calculate user's effective SP
      const vestingShares = parseFloat(account.vesting_shares);
      const delegatedVestingShares = parseFloat(account.delegated_vesting_shares || 0);
      const receivedVestingShares = parseFloat(account.received_vesting_shares || 0);
      
      const effectiveVestingShares = vestingShares - delegatedVestingShares + receivedVestingShares;
      const effectiveSP = await this.vestsToSteem(effectiveVestingShares);
      
      // Get account history - will be different based on platform
      const client = blockchainService.getActiveClient();
      const platform = blockchainService.getCurrentPlatform();
      
      // Set up tracking vars
      let totalCurationRewards = 0;
      let totalVotes = 0;
      let avgEfficiency = 0;
      const detailedResults = [];
      
      // Define the timeframe
      const currentTime = new Date();
      const startTime = new Date(currentTime.getTime() - (daysBack * 24 * 60 * 60 * 1000));
      
      // Processing function for curation rewards
      const processCurationRewards = async (operations) => {
        // Filter for curation reward operations
        const curationRewards = operations.filter(op => 
          op[1].op[0] === 'curation_reward'
        );
        
        for (const curation of curationRewards) {
          const operation = curation[1].op[1];
          const timestamp = new Date(curation[1].timestamp + 'Z');
          
          // Only include rewards within the specified timeframe
          if (timestamp >= startTime) {
            totalVotes++;
            
            // Convert reward to SP
            const rewardVests = parseFloat(operation.reward.split(' ')[0]);
            const rewardSP = await this.vestsToSteem(rewardVests);
            
            totalCurationRewards += rewardSP;
            
            // Get post details to calculate efficiency
            const author = operation.comment_author;
            const permlink = operation.comment_permlink;
            
            try {
              const postDetails = await this.getPostDetails(author, permlink);
              
              // Calculate potential reward and efficiency
              const potentialReward = this.calculatePotentialReward(postDetails, effectiveSP);
              const efficiency = rewardSP > 0 && potentialReward > 0 ? 
                (rewardSP / potentialReward) * 100 : 0;
              
              // Recupera i dettagli del voto dell'utente su questo post
              let votePercent = 100; // Default value
              let voteWeight = 0;
              
              try {
                const userVoteDetails = await blockchainService.getUserVoteOnPost(
                  author, 
                  permlink, 
                  username,
                  platform
                );
                
                if (userVoteDetails) {
                  votePercent = userVoteDetails.percent / 100; // La percent è in percentuale x100 (10000 = 100%)
                  voteWeight = userVoteDetails.weight;
                  console.log(`Vote details for ${username} on ${author}/${permlink}:`, userVoteDetails);
                }
              } catch (voteError) {
                console.warn(`Could not get vote details for ${username} on ${author}/${permlink}:`, voteError);
              }
              
              detailedResults.push({
                author,
                permlink,
                title: postDetails.title || `@${author}/${permlink}`,
                time: timestamp.toISOString(),
                voteAgeMins: this.calculateVoteAge(postDetails, timestamp),
                rewardSP,
                potentialReward,
                efficiency,
                percent: votePercent, // Aggiungiamo la percentuale di voto
                voteWeight, // Aggiungiamo il peso del voto
                postUrl: `https://${platform === 'steem' ? 'steemit.com' : 'hive.blog'}/@${author}/${permlink}`
              });
              
              avgEfficiency += efficiency;
            } catch (error) {
              console.warn(`Could not get full details for post ${author}/${permlink}`, error);
            }
          }
        }
      };
        // Get account history from blockchain utilizzando il sistema di fallback
      let start = -1;
      let isWithinTimeframe = true;
      
      while (isWithinTimeframe) {
        try {
          // Utilizza il sistema di fallback per ottenere la cronologia dell'account
          const history = await blockchainService.getAccountHistory(username, start, 1000, platform);
          
          if (!history || history.length === 0) break;
          
          // Process this batch
          await processCurationRewards(history);
          
          // Check if we should continue
          const oldestOpTime = new Date(history[0][1].timestamp + 'Z');
          if (oldestOpTime < startTime || history.length < 1000) {
            isWithinTimeframe = false;
          } else {
            start = history[0][0] - 1;
          }
        } catch (error) {
          console.error(`Errore nel recupero della cronologia per l'account ${username}:`, error);
          throw new Error(`Impossibile recuperare i dati della cronologia per l'account ${username}. Si prega di riprovare più tardi.`);
        }
      }
      
      // Calculate APR
      const weeklyRewards = (totalCurationRewards / daysBack) * 7;
      const apr = (weeklyRewards / effectiveSP) * 52 * 100;
        // Finalize average efficiency
      avgEfficiency = detailedResults.length > 0 ? avgEfficiency / detailedResults.length : 0;
      
      // Check if we found any rewards
      if (detailedResults.length === 0) {
        throw new Error(`No curation rewards found for @${username} in the last ${daysBack} days`);
      }
      
      // Prepare and return results
      return {
        username,
        daysAnalyzed: daysBack,
        effectiveSP,
        summary: {
          totalVotes,
          totalRewards: totalCurationRewards,
          avgEfficiency,
          apr
        },
        detailedResults: detailedResults.sort((a, b) => b.efficiency - a.efficiency)
      };
    } catch (error) {
      console.error('Error calculating curation efficiency:', error);
      throw error;
    }
  }
    /**
   * Get post details from blockchain
   * @param {string} author - Author of the post
   * @param {string} permlink - Permlink of the post
   * @returns {Promise<Object>} Post details
   */
  async getPostDetails(author, permlink) {
    try {
      return await blockchainService.getContent(author, permlink);
    } catch (error) {
      console.error(`Error fetching post details for ${author}/${permlink}:`, error);
      throw error;
    }
  }

   /**
 * Calculate vote value using the official Steem formula
 * @param {number} votePercent - Vote percentage (-100 to 100)
 * @param {number} effectiveVests - User's effective vesting shares (including delegations)
 * @param {number} votingPower - Voting power (default: 10000 = 100%)
 * @returns {Promise<Object>} Estimated vote value in SBD and STEEM
 */
async calculateVoteValue(votePercent, effectiveVests = null, votingPower = 10000) {
  try {
    const steem = await steemService.ensureLibraryLoaded();
    
    // Step 1: Get dynamic global properties
    const props = await new Promise((resolve, reject) => {
      steem.api.getDynamicGlobalProperties((error, result) => {
        if (error) reject(error);
        else resolve(result);
      });
    });
    
    // Step 2: Calculate SP/VESTS ratio
    const totalVestingFundSteem = parseFloat(props.total_vesting_fund_steem.split(' ')[0]);
    const totalVestingShares = parseFloat(props.total_vesting_shares.split(' ')[0]);
    const steemPerVests = totalVestingFundSteem / totalVestingShares;
    
    // Step 3: If no vesting shares provided, use current user's
    let vestingShares = effectiveVests;
    if (!vestingShares) {
      const account = await steemService.getUser(this.currentUser);
      if (!account) throw new Error('Unable to get account info');
      
      const accountVests = parseFloat(account.vesting_shares.split(' ')[0]);
      const delegatedOut = parseFloat(account.delegated_vesting_shares.split(' ')[0]);
      const receivedVests = parseFloat(account.received_vesting_shares.split(' ')[0]);
      vestingShares = accountVests - delegatedOut + receivedVests;
    }
    
    // Step 4: Convert vests to Steem Power
    const sp = vestingShares * steemPerVests;
    
    // Step 5: Calculate 'r' (SP/spv ratio)
    const r = sp / steemPerVests;
    
    // Step 6: Calculate 'p' (voting power)
    const weight = Math.abs(votePercent) * 100; // Convert percentage to weight (100% = 10000)
    const p = (votingPower * weight / 10000 + 49) / 50;
    
    // Step 7: Get reward fund
    const rewardFund = await new Promise((resolve, reject) => {
      steem.api.getRewardFund('post', (error, result) => {
        if (error) reject(error);
        else resolve(result);
      });
    });
    
    // Step 8: Calculate rbPrc
    const recentClaims = parseFloat(rewardFund.recent_claims);
    const rewardBalance = parseFloat(rewardFund.reward_balance.split(' ')[0]);
    const rbPrc = rewardBalance / recentClaims;
    
    // Step 9: Get median price from Steem API
    const priceInfo = await new Promise((resolve, reject) => {
      steem.api.getCurrentMedianHistoryPrice((error, result) => {
        if (error) reject(error);
        else resolve(result);
      });
    });
    
    const baseAmount = parseFloat(priceInfo.base.split(' ')[0]);
    const quoteAmount = parseFloat(priceInfo.quote.split(' ')[0]);
    const steemToSbdRate = baseAmount / quoteAmount;
    
    // Step 10: Apply the official Steem formula
    // result = r * p * 100 * rbPrc
    const steemValue = r * p * 100 * rbPrc;
    
    // Convert STEEM to USD/SBD using the median price
    const usdValue = steemValue * steemToSbdRate;
    
    // Log calculated values for debugging
    console.log(`Vote Value Calculation:
      - SP: ${sp.toFixed(3)}
      - Vote Weight: ${weight}
      - Voting Power: ${votingPower}
      - Price ratio: ${steemToSbdRate.toFixed(4)}
      - Result: ${steemValue.toFixed(4)} STEEM ($${usdValue.toFixed(4)})`);
    
    return {
      steemValue: parseFloat(steemValue.toFixed(4)),
      sbdValue: parseFloat(usdValue.toFixed(4)),
      formula: {
        r: r,
        p: p,
        rbPrc: rbPrc,
        media: steemToSbdRate
      }
    };
  } catch (error) {
    console.error('Error calculating vote value:', error);
    return {
      steemValue: 0,
      sbdValue: 0,
      error: error.message
    };
  }
}
  
  /**
   * Calculate the age of a vote based on post creation time
   * @param {Object} post - Post details
   * @param {Date} voteTime - Time of the vote
   * @returns {number} Vote age in minutes
   */
  calculateVoteAge(post, voteTime) {
    const postCreationTime = new Date(post.created + 'Z');
    const diffMs = voteTime.getTime() - postCreationTime.getTime();
    return Math.round(diffMs / (60 * 1000)); // Convert to minutes
  }
  
  /**
   * Calculate potential reward based on voting power
   * This is a simplified calculation
   * @param {Object} post - Post details
   * @param {number} effectiveSP - User's effective SP
   * @returns {number} Potential reward
   */
  calculatePotentialReward(post, effectiveSP) {
    // This is a highly simplified calculation and should be refined
    // based on the actual reward algorithm of the blockchain
    const postRshares = parseFloat(post.net_rshares);
    const postReward = parseFloat(post.pending_payout_value.split(' ')[0]);
    
    if (postRshares <= 0 || postReward <= 0) return 0;
    
    // Approximate reward per rshare
    const rewardPerRshare = postReward / postRshares;
    
    // Approximate rshares from SP (very simplified)
    const approximateRshares = effectiveSP * 1000;
    
    // Potential reward
    return approximateRshares * rewardPerRshare;
  }
}

// Create and export singleton instance
const walletService = new WalletService();
export default walletService;
