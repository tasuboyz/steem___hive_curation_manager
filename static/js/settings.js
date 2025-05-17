/**
 * Modulo per la gestione delle impostazioni
 */
import apiService from './modules/api.js';

class SettingsManager {
  constructor() {
    this.themeDark = localStorage.getItem('theme') === 'dark';
    
    // Elementi UI
    this.steemForm = document.getElementById('steemCuratorForm');
    this.hiveForm = document.getElementById('hiveCuratorForm');
    this.testModeToggle = document.getElementById('testModeToggle');
    this.themeToggle = document.getElementById('themeToggle');
    this.notification = document.getElementById('notification');
    
    // Imposta il tema iniziale
    this.updateTheme();
    
    // Configura gli eventi
    this.setupEventListeners();
    
    // Carica i dati iniziali
    this.loadSettings();
  }
  
  setupEventListeners() {
    // Event listener per il tema
    this.themeToggle.addEventListener('click', () => this.toggleTheme());
    
    // Event listener per la modalità test
    this.testModeToggle.addEventListener('change', e => this.updateTestMode(e.target.checked));
    
    // Event listeners per i form
    this.steemForm.addEventListener('submit', e => this.handleSteemFormSubmit(e));
    this.hiveForm.addEventListener('submit', e => this.handleHiveFormSubmit(e));
    
    // Event listeners per i campi password
    document.querySelectorAll('.toggle-visibility').forEach(btn => {
      btn.addEventListener('click', e => this.togglePasswordVisibility(e.currentTarget));
    });
  }
  
  async loadSettings() {
    try {
      // Carica la modalità test
      const testModeResponse = await apiService.sendRequest('/api/test_mode', 'GET');
      if (testModeResponse.success) {
        this.testModeToggle.checked = testModeResponse.data.test_mode;
      }
      
      // Carica le impostazioni del curatore Steem
      const steemCuratorResponse = await apiService.sendRequest('/api/curator/info?platform=steem', 'GET');
      if (steemCuratorResponse.success) {        document.getElementById('steemUsername').value = steemCuratorResponse.data.username || '';
        
        // Aggiorna lo stato della chiave posting
        const steemPostingKeyStatus = document.querySelector('#steemPostingKey').closest('.form-field').querySelector('.key-status');
        if (steemCuratorResponse.data.posting_key_set) {
          steemPostingKeyStatus.classList.add('is-set');
          steemPostingKeyStatus.classList.remove('not-set');
        } else {
          steemPostingKeyStatus.classList.add('not-set');
          steemPostingKeyStatus.classList.remove('is-set');
        }
        
        // Aggiorna lo stato della chiave active
        const steemActiveKeyStatus = document.querySelector('#steemActiveKey').closest('.form-field').querySelector('.key-status');
        if (steemCuratorResponse.data.active_key_set) {
          steemActiveKeyStatus.classList.add('is-set');
          steemActiveKeyStatus.classList.remove('not-set');
        } else {
          steemActiveKeyStatus.classList.add('not-set');
          steemActiveKeyStatus.classList.remove('is-set');
        }
      }
      
      // Carica le impostazioni del curatore Hive
      const hiveCuratorResponse = await apiService.sendRequest('/api/curator/info?platform=hive', 'GET');
      if (hiveCuratorResponse.success) {        document.getElementById('hiveUsername').value = hiveCuratorResponse.data.username || '';
        
        // Aggiorna lo stato della chiave posting
        const hivePostingKeyStatus = document.querySelector('#hivePostingKey').closest('.form-field').querySelector('.key-status');
        if (hiveCuratorResponse.data.posting_key_set) {
          hivePostingKeyStatus.classList.add('is-set');
          hivePostingKeyStatus.classList.remove('not-set');
        } else {
          hivePostingKeyStatus.classList.add('not-set');
          hivePostingKeyStatus.classList.remove('is-set');
        }
      }
    } catch (error) {
      this.showNotification('Errore nel caricamento delle impostazioni', 'error');
      console.error('Error loading settings:', error);
    }
  }
  
  async updateTestMode(enabled) {
    try {
      const response = await apiService.sendRequest('/api/test_mode', 'POST', { enabled });
      if (response.success) {
        this.showNotification(`Modalità test ${enabled ? 'attivata' : 'disattivata'}`, 'success');
      } else {
        this.showNotification('Errore nell\'aggiornamento della modalità test', 'error');
        this.testModeToggle.checked = !enabled; // Ripristina lo stato precedente
      }
    } catch (error) {
      this.showNotification('Errore nella comunicazione con il server', 'error');
      console.error('Error updating test mode:', error);
      this.testModeToggle.checked = !enabled; // Ripristina lo stato precedente
    }
  }
  
  async handleSteemFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(this.steemForm);
    const data = {
      platform: 'steem',
      username: formData.get('username'),
      posting_key: formData.get('posting_key'),
      active_key: formData.get('active_key')
    };
    
    try {
      const response = await apiService.sendRequest('/api/curator/update', 'POST', data);      if (response.success) {
        this.showNotification('Impostazioni Steem salvate con successo', 'success');
        
        // Aggiorna lo stato delle chiavi
        if (data.posting_key) {
          const keyStatus = document.querySelector('#steemPostingKey').closest('.form-field').querySelector('.key-status');
          keyStatus.classList.add('is-set');
          keyStatus.classList.remove('not-set');
        }
        
        if (data.active_key) {
          const keyStatus = document.querySelector('#steemActiveKey').closest('.form-field').querySelector('.key-status');
          keyStatus.classList.add('is-set');
          keyStatus.classList.remove('not-set');
        }
        
        // Pulisci i campi password
        document.getElementById('steemPostingKey').value = '';
        document.getElementById('steemActiveKey').value = '';
      } else {
        this.showNotification('Errore nel salvataggio delle impostazioni Steem', 'error');
      }
    } catch (error) {
      this.showNotification('Errore nella comunicazione con il server', 'error');
      console.error('Error updating Steem settings:', error);
    }
  }
  
  async handleHiveFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(this.hiveForm);
    const data = {
      platform: 'hive',
      username: formData.get('username'),
      posting_key: formData.get('posting_key')
    };
    
    try {
      const response = await apiService.sendRequest('/api/curator/update', 'POST', data);      if (response.success) {
        this.showNotification('Impostazioni Hive salvate con successo', 'success');
        
        // Aggiorna lo stato della chiave
        if (data.posting_key) {
          const keyStatus = document.querySelector('#hivePostingKey').closest('.form-field').querySelector('.key-status');
          keyStatus.classList.add('is-set');
          keyStatus.classList.remove('not-set');
        }
        
        // Pulisci il campo password
        document.getElementById('hivePostingKey').value = '';
      } else {
        this.showNotification('Errore nel salvataggio delle impostazioni Hive', 'error');
      }
    } catch (error) {
      this.showNotification('Errore nella comunicazione con il server', 'error');
      console.error('Error updating Hive settings:', error);
    }
  }
  
  togglePasswordVisibility(button) {
    const passwordField = button.parentElement;
    const input = passwordField.querySelector('input');
    
    if (input.type === 'password') {
      input.type = 'text';
      passwordField.classList.add('visible');
    } else {
      input.type = 'password';
      passwordField.classList.remove('visible');
    }
  }
  
  toggleTheme() {
    this.themeDark = !this.themeDark;
    localStorage.setItem('theme', this.themeDark ? 'dark' : 'light');
    this.updateTheme();
  }
  
  updateTheme() {
    if (this.themeDark) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }
  
  showNotification(message, type = 'info') {
    this.notification.className = 'notification';
    this.notification.classList.add(type);
    this.notification.querySelector('.notification-message').textContent = message;
    this.notification.classList.add('show');
    
    setTimeout(() => {
      this.notification.classList.remove('show');
    }, 5000);
  }
}

// Inizializza il gestore delle impostazioni quando il DOM è caricato
document.addEventListener('DOMContentLoaded', () => {
  new SettingsManager();
});
