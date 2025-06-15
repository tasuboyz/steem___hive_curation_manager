/**
 * Theme Service - Gestisce il tema dell'applicazione in modo centralizzato
 */

class ThemeService {
  constructor() {
    this.STORAGE_KEY = 'theme';
    this.DEFAULT_THEME = 'light';
    this.initialized = false;
  }

  /**
   * Inizializza il servizio tema
   */
  init() {
    if (this.initialized) {
      console.log('ThemeService: Already initialized, skipping');
      return;
    }

    console.log('ThemeService: Initializing...');
    
    // Carica il tema salvato o usa quello di default
    const savedTheme = this.getTheme();
    this.applyTheme(savedTheme);
    
    // Setup del pulsante toggle se presente
    this.setupToggleButton();
    
    this.initialized = true;
    console.log(`ThemeService: Initialized with theme: ${savedTheme}`);
  }

  /**
   * Ottiene il tema corrente dal localStorage
   * @returns {string} Il tema corrente ('light' o 'dark')
   */
  getTheme() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    const theme = saved === 'dark' ? 'dark' : this.DEFAULT_THEME;
    console.log(`ThemeService: Retrieved theme: ${theme}`);
    return theme;
  }

  /**
   * Salva il tema nel localStorage
   * @param {string} theme - Il tema da salvare ('light' o 'dark')
   */
  saveTheme(theme) {
    console.log(`ThemeService: Saving theme: ${theme}`);
    localStorage.setItem(this.STORAGE_KEY, theme);
  }

  /**
   * Applica il tema al documento
   * @param {string} theme - Il tema da applicare ('light' o 'dark')
   */
  applyTheme(theme) {
    console.log(`ThemeService: Applying theme: ${theme}`);
    document.documentElement.setAttribute('data-theme', theme);
    this.updateToggleButton(theme);
  }

  /**
   * Alterna tra tema chiaro e scuro
   */
  toggleTheme() {
    const currentTheme = this.getTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    console.log(`ThemeService: Toggling theme from ${currentTheme} to ${newTheme}`);
    
    this.saveTheme(newTheme);
    this.applyTheme(newTheme);
    
    return newTheme;
  }

  /**
   * Setup del pulsante toggle
   */
  setupToggleButton() {
    const toggleButton = document.getElementById('themeToggle');
    if (!toggleButton) {
      console.log('ThemeService: Toggle button not found, will retry when DOM is ready');
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.setupToggleButton());
      }
      return;
    }

    console.log('ThemeService: Setting up toggle button');
    
    // Rimuovi eventuali listener precedenti
    const newButton = toggleButton.cloneNode(true);
    toggleButton.parentNode.replaceChild(newButton, toggleButton);
    
    // Aggiungi il nuovo listener
    newButton.addEventListener('click', (e) => {
      e.preventDefault();
      this.toggleTheme();
    });

    // Aggiorna l'icona iniziale
    this.updateToggleButton(this.getTheme());
  }

  /**
   * Aggiorna l'icona del pulsante toggle
   * @param {string} theme - Il tema corrente
   */
  updateToggleButton(theme) {
    const toggleButton = document.getElementById('themeToggle');
    if (!toggleButton) return;

    const moonIcon = toggleButton.querySelector('.fa-moon');
    const sunIcon = toggleButton.querySelector('.fa-sun');
    
    if (moonIcon && sunIcon) {
      if (theme === 'dark') {
        moonIcon.style.display = 'none';
        sunIcon.style.display = 'block';
        toggleButton.setAttribute('aria-label', 'Switch to light theme');
      } else {
        moonIcon.style.display = 'block';
        sunIcon.style.display = 'none';
        toggleButton.setAttribute('aria-label', 'Switch to dark theme');
      }
      console.log(`ThemeService: Updated toggle button for ${theme} theme`);
    }
  }

  /**
   * Forza il reset del tema (utile per debug)
   */
  reset() {
    console.log('ThemeService: Resetting to default theme');
    this.saveTheme(this.DEFAULT_THEME);
    this.applyTheme(this.DEFAULT_THEME);
  }
}

// Crea l'istanza globale
const themeService = new ThemeService();

// Esporta per l'uso come modulo
export default themeService;

// Rendi disponibile globalmente per compatibilità
window.themeService = themeService;
