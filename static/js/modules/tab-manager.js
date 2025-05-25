/**
 * Tab Management Module
 * Handles tab switching functionality for the application interface
 */

class TabManager {
  constructor() {
    this.currentTab = 'curation-tab';
    this.tabButtons = [];
    this.tabContents = [];
  }

  /**
   * Initialize the tab management system
   */
  initialize() {
    this.setupTabElements();
    this.setupEventListeners();
    this.setActiveTab(this.currentTab);
  }

  /**
   * Setup tab elements references
   */
  setupTabElements() {
    this.tabButtons = Array.from(document.querySelectorAll('.tab-button'));
    this.tabContents = Array.from(document.querySelectorAll('.tab-content'));
  }

  /**
   * Setup event listeners for tab buttons
   */
  setupEventListeners() {
    this.tabButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        const tabId = e.currentTarget.dataset.tab;
        this.setActiveTab(tabId);
      });
    });

    // Keyboard navigation support
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const tabIndex = parseInt(e.key) - 1;
        if (tabIndex < this.tabButtons.length) {
          const tabId = this.tabButtons[tabIndex].dataset.tab;
          this.setActiveTab(tabId);
        }
      }
    });
  }

  /**
   * Set the active tab
   * @param {string} tabId - The ID of the tab to activate
   */
  setActiveTab(tabId) {
    // Update current tab
    this.currentTab = tabId;

    // Update tab buttons
    this.tabButtons.forEach(button => {
      const isActive = button.dataset.tab === tabId;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-selected', isActive.toString());
    });

    // Update tab contents
    this.tabContents.forEach(content => {
      const isActive = content.id === tabId;
      content.classList.toggle('active', isActive);
      content.setAttribute('aria-hidden', (!isActive).toString());
    });

    // Store current tab in localStorage for persistence
    localStorage.setItem('activeTab', tabId);

    // Emit custom event for other modules
    this.emitTabChangeEvent(tabId);
  }

  /**
   * Get the currently active tab
   * @returns {string} Current tab ID
   */
  getCurrentTab() {
    return this.currentTab;
  }

  /**
   * Load the last active tab from localStorage
   */
  loadLastActiveTab() {
    const savedTab = localStorage.getItem('activeTab');
    if (savedTab && this.tabContents.some(content => content.id === savedTab)) {
      this.setActiveTab(savedTab);
    }
  }

  /**
   * Emit a custom event when tab changes
   * @param {string} tabId - The new active tab ID
   */
  emitTabChangeEvent(tabId) {
    const event = new CustomEvent('tabChange', {
      detail: {
        newTab: tabId,
        previousTab: this.currentTab
      }
    });
    document.dispatchEvent(event);
  }

  /**
   * Add a new tab programmatically
   * @param {string} tabId - Tab content ID
   * @param {string} buttonText - Button text
   * @param {string} iconClass - Icon class for the button
   */
  addTab(tabId, buttonText, iconClass = 'fas fa-file') {
    // Create tab button
    const button = document.createElement('button');
    button.className = 'tab-button';
    button.dataset.tab = tabId;
    button.innerHTML = `<i class="${iconClass}"></i> ${buttonText}`;
    
    // Add event listener
    button.addEventListener('click', (e) => {
      const tabId = e.currentTarget.dataset.tab;
      this.setActiveTab(tabId);
    });

    // Add to navigation
    const navigation = document.querySelector('.tab-navigation');
    if (navigation) {
      navigation.appendChild(button);
      this.tabButtons.push(button);
    }
  }

  /**
   * Remove a tab programmatically
   * @param {string} tabId - Tab ID to remove
   */
  removeTab(tabId) {
    // Remove button
    const button = this.tabButtons.find(btn => btn.dataset.tab === tabId);
    if (button) {
      button.remove();
      this.tabButtons = this.tabButtons.filter(btn => btn !== button);
    }

    // Remove content
    const content = document.getElementById(tabId);
    if (content) {
      content.remove();
      this.tabContents = this.tabContents.filter(cnt => cnt !== content);
    }

    // If removed tab was active, activate the first available tab
    if (this.currentTab === tabId && this.tabButtons.length > 0) {
      this.setActiveTab(this.tabButtons[0].dataset.tab);
    }
  }
}

// Create and export singleton instance
const tabManager = new TabManager();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    tabManager.initialize();
    tabManager.loadLastActiveTab();
  });
} else {
  tabManager.initialize();
  tabManager.loadLastActiveTab();
}

export default tabManager;
