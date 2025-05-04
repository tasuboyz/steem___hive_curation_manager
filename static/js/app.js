class ApiHandler {
  constructor() {
    this.apiUrl = 'https://api.example.com/curation'; // Replace with your actual API endpoint
    this.retryAttempts = 3;
    this.retryDelay = 1000; // 1 second
  }

  async sendRequest(endpoint, method, data) {
    let attempts = 0;
    while (attempts < this.retryAttempts) {
      try {
        const response = await fetch(`${endpoint}`, {
          method: method,
          headers: {
            'Content-Type': 'application/json',
            // Add any authentication headers here if needed
            // 'Authorization': 'Bearer your-token'
          },
          body: JSON.stringify(data)
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return { success: true, data: result };

      } catch (error) {
        attempts++;
        console.error(`API request failed (attempt ${attempts}/${this.retryAttempts}):`, error);
        
        if (attempts === this.retryAttempts) {
          return { success: false, error: error.message };
        }
        
        await new Promise(resolve => setTimeout(resolve, this.retryDelay));
      }
    }
  }

  async getUser() {
    return await this.sendRequest('/users', 'GET');
  }

  async addUser(userData) {
    return await this.sendRequest('/users', 'POST', userData);
  }

  async updateUser(username, userData) {
    return await this.sendRequest(`/users/${username}`, 'PUT', userData);
  }

  async deleteUser(username) {
    return await this.sendRequest(`/users/${username}`, 'DELETE');
  }

  async getPostVoters(postUrl) {
    return await this.sendRequest(`/api/post_voters?post_url=${encodeURIComponent(postUrl)}&min_importance=0.1`, 'GET');
  }
}

class CurationInterface {
  constructor() {
    this.currentPlatform = 'steem';
    this.users = new Map();
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
    this.currentNodes = {
      steem: 0,
      hive: 0
    };
    this.api = new ApiHandler();
    this.initializeClients();
    this.setupEventListeners();
    this.loadSavedUsers();
    this.initializeTheme();
    // Add status message container
    this.statusMessage = document.createElement('div');
    this.statusMessage.className = 'status-message';
    document.querySelector('.container').appendChild(this.statusMessage);
  }

  initializeClients() {
    this.steemClient = steem;
    this.steemClient.api.setOptions({ url: this.nodes.steem[0] });
    this.hiveClient = new dhive.Client(this.nodes.hive);
  }

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

  setupEventListeners() {
    document.getElementById('steemBtn').addEventListener('click', () => this.switchPlatform('steem'));
    document.getElementById('hiveBtn').addEventListener('click', () => this.switchPlatform('hive'));
    document.getElementById('addUserForm').addEventListener('submit', (e) => this.handleAddUser(e));
    document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());
    document.getElementById('exportDataBtn').addEventListener('click', () => this.exportData());
    document.getElementById('importDataBtn').addEventListener('click', () => document.getElementById('importInput').click());
    document.getElementById('importInput').addEventListener('change', (e) => this.importData(e));
    document.getElementById('logDataBtn').addEventListener('click', () => this.logData());
  }

  switchPlatform(platform) {
    this.currentPlatform = platform;
    document.getElementById('steemBtn').classList.toggle('active', platform === 'steem');
    document.getElementById('hiveBtn').classList.toggle('active', platform === 'hive');
    this.renderUsersList();
  }

  async handleAddUser(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const voteDelay = parseInt(document.getElementById('voteDelay').value);
    const voteWeight = parseInt(document.getElementById('voteWeight').value);

    try {
      await this.verifyNodeConnection(this.currentPlatform);
      const accounts = await this.getAccountInfo(username, this.currentPlatform);
      
      if (!accounts || accounts.length === 0) {
        throw new Error('User not found');
      }

      const userData = {
        username,
        platform: this.currentPlatform,
        voteDelay,
        voteWeight,
        timestamp: Date.now()
      };

      // Try API first, but continue even if it fails
      let apiSuccess = false;
      try {
        const apiResponse = await this.api.addUser(userData);
        apiSuccess = apiResponse.success;
      } catch (error) {
        console.warn('API call failed, continuing with local storage:', error);
      }

      // Save to local storage regardless of API response
      this.users.set(username, userData);
      this.saveUsers();
      this.renderUsersList();
      e.target.reset();
      
      if (apiSuccess) {
        this.showStatus('User added successfully and synced with API!', 'success');
      } else {
        this.showStatus('User added locally. API sync failed.', 'info');
      }

    } catch (error) {
      this.showStatus(`Error: ${error.message}`, 'error');
    }
  }

  showStatus(message, type = 'info') {
    this.statusMessage.textContent = message;
    this.statusMessage.className = `status-message ${type}`;
    this.statusMessage.style.display = 'block';
    setTimeout(() => {
      this.statusMessage.style.display = 'none';
    }, 3000);
  }

  updateUserSettings(username) {
    const userData = this.users.get(username);
    if (!userData) return;

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content">
        <h3><i class="fas fa-user-edit"></i> Edit Settings for @${username}</h3>
        <form id="editUserForm">
          <div class="setting">
            <label for="editVoteDelay">
              <i class="fas fa-clock"></i> Vote Delay (minutes)
            </label>
            <input 
              type="number" 
              id="editVoteDelay" 
              min="0" 
              max="1440"
              value="${userData.voteDelay}" 
              required
              oninput="this.form.querySelector('.delay-feedback').classList.add('show')"
            >
            <div class="input-feedback delay-feedback">
              Posts will be voted ${userData.voteDelay} minutes after publication
            </div>
          </div>
          
          <div class="setting">
            <label for="editVoteWeight">
              <i class="fas fa-percentage"></i> Vote Weight
            </label>
            <input 
              type="number" 
              id="editVoteWeight" 
              min="1" 
              max="100" 
              value="${userData.voteWeight}" 
              required
              oninput="this.form.querySelector('.weight-feedback').classList.add('show')"
            >
            <div class="input-feedback weight-feedback">
              Votes will be cast at ${userData.voteWeight}% strength
            </div>
          </div>
          
          <div class="modal-buttons">
            <button type="submit" class="save-btn">
              <i class="fas fa-save"></i> Save Changes
            </button>
            <button type="button" class="cancel-btn">
              <i class="fas fa-times"></i> Cancel
            </button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(modal);

    // Update feedback text dynamically
    const delayInput = modal.querySelector('#editVoteDelay');
    const weightInput = modal.querySelector('#editVoteWeight');
    const delayFeedback = modal.querySelector('.delay-feedback');
    const weightFeedback = modal.querySelector('.weight-feedback');

    delayInput.addEventListener('input', (e) => {
      const value = e.target.value;
      if (value >= 0 && value <= 1440) {
        delayFeedback.textContent = `Posts will be voted ${value} minutes after publication`;
        delayFeedback.classList.remove('invalid');
        delayFeedback.classList.add('valid');
      } else {
        delayFeedback.textContent = 'Please enter a value between 0 and 1440 minutes';
        delayFeedback.classList.remove('valid');
        delayFeedback.classList.add('invalid');
      }
    });

    weightInput.addEventListener('input', (e) => {
      const value = e.target.value;
      if (value >= 1 && value <= 100) {
        weightFeedback.textContent = `Votes will be cast at ${value}% strength`;
        weightFeedback.classList.remove('invalid');
        weightFeedback.classList.add('valid');
      } else {
        weightFeedback.textContent = 'Please enter a value between 1 and 100';
        weightFeedback.classList.remove('valid');
        weightFeedback.classList.add('invalid');
      }
    });

    const editForm = modal.querySelector('#editUserForm');
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const newVoteDelay = parseInt(delayInput.value);
      const newVoteWeight = parseInt(weightInput.value);

      if (newVoteDelay < 0 || newVoteDelay > 1440 || newVoteWeight < 1 || newVoteWeight > 100) {
        return;
      }

      const updatedData = {
        ...this.users.get(username),
        voteDelay: newVoteDelay,
        voteWeight: newVoteWeight,
        lastUpdated: Date.now()
      };

      let apiSuccess = false;
      try {
        const apiResponse = await this.api.updateUser(username, updatedData);
        apiSuccess = apiResponse.success;
      } catch (error) {
        console.warn('API update failed, continuing with local storage:', error);
      }

      // Update local storage regardless of API status
      this.users.set(username, updatedData);
      this.saveUsers();
      this.renderUsersList();
      
      const successMsg = document.createElement('div');
      successMsg.style.color = 'var(--success-color)';
      successMsg.innerHTML = apiSuccess ? 
        '<i class="fas fa-check-circle"></i> Settings updated successfully and synced with API!' :
        '<i class="fas fa-check-circle"></i> Settings updated locally. API sync failed.';
      modal.querySelector('.modal-content').appendChild(successMsg);
      
      setTimeout(() => modal.remove(), 1000);
      this.showStatus(
        apiSuccess ? 'User settings updated and synced!' : 'Settings updated locally. API sync failed.',
        apiSuccess ? 'success' : 'info'
      );
    });

    // Handle cancel button
    modal.querySelector('.cancel-btn').addEventListener('click', () => {
      modal.classList.add('fade-out');
      setTimeout(() => modal.remove(), 300);
    });

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.add('fade-out');
        setTimeout(() => modal.remove(), 300);
      }
    });

    // Add escape key listener
    const escapeHandler = (e) => {
      if (e.key === 'Escape') {
        modal.classList.add('fade-out');
        setTimeout(() => modal.remove(), 300);
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);
  }

  async deleteUser(username) {
    let apiSuccess = false;
    try {
      const apiResponse = await this.api.deleteUser(username);
      apiSuccess = apiResponse.success;
    } catch (error) {
      console.warn('API delete failed, continuing with local storage:', error);
    }

    // Delete from local storage regardless of API status
    this.users.delete(username);
    this.saveUsers();
    this.renderUsersList();
    
    if (apiSuccess) {
      this.showStatus('User deleted successfully and synced with API!', 'success');
    } else {
      this.showStatus('User deleted locally. API sync failed.', 'info');
    }
  }

  saveUsers() {
    localStorage.setItem('curatedUsers', JSON.stringify(Array.from(this.users.entries())));
  }

  async loadSavedUsers() {
    try {
      // Prova a caricare gli utenti dall'API
      const response = await this.api.getUser();
  
      if (response.success) {
        // Se la risposta è positiva, aggiorna la mappa degli utenti
        this.users = new Map(response.data.map(user => [user.username, user.data]));
        this.renderUsersList();
      } else {
        // Se c'è un errore, prova a caricare i dati dal localStorage
        console.warn('Failed to load users from API, loading from localStorage instead.');
        this.loadUsersFromLocalStorage();
      }
    } catch (error) {
      console.error('Error loading users from API:', error);
      // Se c'è un errore, prova a caricare i dati dal localStorage
      this.loadUsersFromLocalStorage();
    }
  }
  
  loadUsersFromLocalStorage() {
    const saved = localStorage.getItem('curatedUsers');
    if (saved) {
      this.users = new Map(JSON.parse(saved));
      this.renderUsersList();
    }
  }

  renderUsersList() {
    const usersList = document.getElementById('usersList');
    usersList.innerHTML = '';

    for (const [username, data] of this.users) {
      if (data.platform !== this.currentPlatform) continue;

      const userCard = document.createElement('div');
      userCard.className = 'user-card';
      userCard.innerHTML = `
        <div class="user-info">
          <strong><i class="fas fa-user"></i> @${username}</strong>
          <span><i class="fas fa-clock"></i> Vote Delay: ${data.voteDelay} minutes</span>
          <span><i class="fas fa-percentage"></i> Vote Weight: ${data.voteWeight}%</span>
          <div class="latest-post" id="latest-post-${username}">
            <div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading latest post...</div>
          </div>
        </div>
        <div class="user-settings">
          <button class="edit-btn" onclick="curationInterface.updateUserSettings('${username}')">
            <i class="fas fa-edit"></i>
          </button>
          <button class="delete-btn" onclick="curationInterface.deleteUser('${username}')">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `;
      usersList.appendChild(userCard);
      
      this.displayLatestPost(username, data.platform);
    }
  }

  async displayLatestPost(username, platform) {
    try {
      await this.verifyNodeConnection(platform);
      const posts = await this.getLatestPosts(username, platform);
      const postContainer = document.getElementById(`latest-post-${username}`);
      
      if (posts && posts.length > 0) {
        const latestPost = posts[0];
        const postDate = new Date(latestPost.created + 'Z');
        const formattedDate = postDate.toLocaleString();
        
        // Use the correct domain based on platform
        const domain = platform === 'steem' ? 'https://steemit.com' : 'https://peakd.com';
        const postUrl = `${domain}/@${username}/${latestPost.permlink}`;
        const viewUrl = `https://cur8.fun/#/@${username}/${latestPost.permlink}`;
        
        // Rendering del post base
        postContainer.innerHTML = `
          <div class="post-info">
            <h4><i class="fas fa-file-alt"></i> ${latestPost.title}</h4>
            <div class="post-meta">
              <span><i class="far fa-clock"></i> ${formattedDate}</span>
              <a href="${viewUrl}" 
                 target="_blank" 
                 rel="noopener noreferrer">
                <i class="fas fa-external-link-alt"></i> View Post
              </a>
              <button class="show-voters-btn" id="show-voters-${username}">
                <i class="fas fa-users"></i> Show Voters
              </button>
            </div>
            <div class="voters-container" id="voters-container-${username}" style="display:none">
              <div class="loading-voters"><i class="fas fa-spinner fa-spin"></i> Loading voters data...</div>
            </div>
          </div>
        `;

        // Aggiungi gestore eventi per mostrare i votanti
        document.getElementById(`show-voters-${username}`).addEventListener('click', async () => {
          const votersContainer = document.getElementById(`voters-container-${username}`);
          
          // Toggle visibility
          if (votersContainer.style.display === 'none') {
            votersContainer.style.display = 'block';
            
            try {
              // Richiedi i dati dei votanti
              const votersResponse = await this.api.getPostVoters(postUrl);
              
              if (votersResponse.success && votersResponse.data.voters) {
                const voters = votersResponse.data.voters;
                const totalVoters = votersResponse.data.total_voters;
                const optimalVoteTime = votersResponse.data.optimal_vote_time;
                
                // Mostra informazioni sul tempo ottimale di voto
                let votersHtml = `
                  <div class="optimal-vote-time">
                    <h5><i class="fas fa-stopwatch"></i> Tempo ottimale di voto</h5>
                    <div class="vote-timing-recommendation">
                      <span class="optimal-time">${optimalVoteTime.optimal_time} minuti</span>
                      <div class="vote-window">
                        (finestra ottimale: ${optimalVoteTime.vote_window[0]}-${optimalVoteTime.vote_window[1]} min)
                      </div>
                      <div class="vote-explanation">${optimalVoteTime.explanation}</div>
                    </div>
                  </div>
                  <h5><i class="fas fa-chart-bar"></i> Top Voters (${totalVoters} total)</h5>
                `;
                
                if (voters.length > 0) {
                  votersHtml += '<div class="voters-list">';
                  voters.forEach(voter => {
                    // Calcola il peso del voto come percentuale
                    const voteWeight = (voter.weight / 100).toFixed(0);
                    // Visualizza il ritardo del voto
                    const voteDelay = voter.vote_delay_minutes;
                    // Formatta l'importanza
                    const importance = voter.importance.toFixed(2);
                    
                    // Evidenzia i votanti principali menzionati nella strategia di voto
                    const isKeyVoter = optimalVoteTime.top_voters && 
                                      optimalVoteTime.top_voters.includes(voter.voter);
                    const keyVoterClass = isKeyVoter ? 'key-voter' : '';
                    
                    votersHtml += `
                      <div class="voter-item ${keyVoterClass}">
                        <strong>@${voter.voter}</strong> 
                        <span class="vote-stats">
                          <span class="vote-weight">${voteWeight}%</span>
                          <span class="vote-timing" title="Vote timing">after ${voteDelay} min</span>
                          <span class="vote-power" title="Voter influence score">power: ${importance}</span>
                        </span>
                      </div>
                    `;
                  });
                  votersHtml += '</div>';
                } else {
                  votersHtml += '<div class="no-voters">No significant voters yet</div>';
                }
                
                votersContainer.innerHTML = votersHtml;
                
              } else {
                votersContainer.innerHTML = '<div class="error"><i class="fas fa-exclamation-triangle"></i> Could not load voters data</div>';
              }
            } catch (error) {
              console.error('Error loading voters:', error);
              votersContainer.innerHTML = `<div class="error"><i class="fas fa-exclamation-circle"></i> Error: ${error.message}</div>`;
            }
          } else {
            votersContainer.style.display = 'none';
          }
        });
        
      } else {
        postContainer.innerHTML = '<div class="no-posts"><i class="fas fa-info-circle"></i> No posts found</div>';
      }
    } catch (error) {
      const postContainer = document.getElementById(`latest-post-${username}`);
      postContainer.innerHTML = `<div class="error"><i class="fas fa-exclamation-circle"></i> Error loading latest post: ${error.message}</div>`;
    }
  }

  async monitorUsers() {
    for (const [username, data] of this.users) {
      try {
        await this.verifyNodeConnection(data.platform);
        const posts = await this.getLatestPosts(username, data.platform);

        if (posts && posts.length > 0) {
          const latestPost = posts[0];
          const postDate = new Date(latestPost.created + 'Z');
          const now = new Date();
          const minutesSincePost = (now - postDate) / 1000 / 60;

          if (minutesSincePost >= data.voteDelay && minutesSincePost < data.voteDelay + 1) {
            // Here you would implement the actual voting logic
            console.log(`Voting on post by ${username} with weight ${data.voteWeight}%`);
            // Example post data available:
            console.log({
              author: latestPost.author,
              permlink: latestPost.permlink,
              title: latestPost.title,
              created: latestPost.created
            });
          }
        }
      } catch (error) {
        console.error(`Error monitoring ${username}: ${error}`);
      }
    }
  }

  initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    this.updateThemeIcon();
  }

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    this.updateThemeIcon();
  }

  updateThemeIcon() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const themeButton = document.getElementById('themeToggle');
    if (themeButton) {
      const moonIcon = themeButton.querySelector('.fa-moon');
      const sunIcon = themeButton.querySelector('.fa-sun');
      
      if (currentTheme === 'dark') {
        moonIcon.style.display = 'none';
        sunIcon.style.display = 'block';
      } else {
        moonIcon.style.display = 'block';
        sunIcon.style.display = 'none';
      }
    }
  }

  exportData() {
    const data = {
      users: Array.from(this.users.entries()),
      currentPlatform: this.currentPlatform,
      exportDate: new Date().toISOString(),
      version: '1.0'
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `curation-data-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    this.showStatus('Data exported successfully!', 'success');
  }

  async importData(e) {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);

      if (!data.users || !Array.isArray(data.users)) {
        throw new Error('Invalid data format');
      }

      // Attempt to sync with API
      let apiSuccess = false;
      try {
        for (const [username, userData] of data.users) {
          const apiResponse = await this.api.addUser(userData);
          if (!apiResponse.success) {
            console.warn(`Failed to sync user ${username} with API`);
          }
        }
        apiSuccess = true;
      } catch (error) {
        console.warn('API sync failed during import:', error);
      }

      // Update local storage regardless of API status
      this.users = new Map(data.users);
      this.currentPlatform = data.currentPlatform || 'steem';
      this.saveUsers();
      this.renderUsersList();

      // Reset file input
      e.target.value = '';

      if (apiSuccess) {
        this.showStatus('Data imported and synced with API successfully!', 'success');
      } else {
        this.showStatus('Data imported locally. API sync failed.', 'info');
      }

    } catch (error) {
      console.error('Import error:', error);
      this.showStatus('Error importing data: ' + error.message, 'error');
      e.target.value = '';
    }
  }

  logData() {
    const data = {
      users: Array.from(this.users.entries()),
      currentPlatform: this.currentPlatform,
      exportDate: new Date().toISOString(),
      version: '1.0',
      stats: {
        totalUsers: this.users.size,
        steemUsers: Array.from(this.users.values()).filter(u => u.platform === 'steem').length,
        hiveUsers: Array.from(this.users.values()).filter(u => u.platform === 'hive').length
      }
    };

    console.log('Current Curation Data:');
    console.log(JSON.stringify(data, null, 2));
    
    this.showStatus('Data logged to console!', 'info');
  }
}

// Initialize the interface
window.curationInterface = new CurationInterface();

// Start monitoring loop
setInterval(() => curationInterface.monitorUsers(), 60000); // Check every minute