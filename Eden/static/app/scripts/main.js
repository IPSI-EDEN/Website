// main.js (ES6 module)

// Imports existants
import { showModal, saveModalState, hideForm } from './modals.js';
import { initCharts, loadChartsData } from './charts.js';

// Exécution au DOMContentLoaded pour le thème initial
document.addEventListener('DOMContentLoaded', () => {
    const theme = getCookie('theme') || 'light';
    document.body.classList.toggle('dark-mode', theme === 'dark');
    document.body.classList.toggle('light-mode', theme === 'light');
    applyTheme(theme);
});

// Rendez certaines fonctions globales si besoin
window.showModal = showModal;
window.hideForm = hideForm;
window.saveModalState = saveModalState;
window.initCharts = initCharts;
window.loadChartsData = loadChartsData;

// Exécution au load pour initialiser les formulaires, etc.
window.addEventListener('load', () => {
  bootstrapForms();
  initPageState();
});

document.addEventListener('DOMContentLoaded', () => {

    // === 1) Récupération des variables globales définies dans le template ===
    const toggleThemeUrl = window.toggleThemeUrl || "/toggle_theme/"; 
    const logoLight = window.logoCTCLight || "/static/images/logo_ctc.png";
    const logoDark  = window.logoCTCDark  || "/static/images/logo_ctc_blanc.png";
    const csrfToken = window.csrfToken    || "";
  
    // === 2) Récupération des éléments du DOM ===
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon   = document.getElementById('theme-icon');
    const logo        = document.getElementById('img_logo');
  
    // === 3) Thème initial (basé sur un cookie ou défaut 'light') ===
    const currentTheme = getCookie('theme') || 'light';
    document.body.classList.toggle('dark-mode', currentTheme === 'dark');
    document.body.classList.toggle('light-mode', currentTheme === 'light');
    applyTheme(currentTheme);
  
    // Met à jour le logo en fonction du thème
    if (logo) {
      logo.src = (currentTheme === 'dark') ? logoDark : logoLight;
    }
  
    // Icône du bouton thème
    if (themeIcon) {
      if (currentTheme === 'dark') {
        themeIcon.classList.add('bi-sun-fill');
      } else {
        themeIcon.classList.add('bi-moon-fill');
      }
    }
  
    // === 4) Gérer le clic sur le bouton de bascule de thème ===
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const oldTheme = getCookie('theme') || 'light';
        const newTheme = (oldTheme === 'light') ? 'dark' : 'light';
  
        // Basculer classes
        document.body.classList.toggle('dark-mode', newTheme === 'dark');
        document.body.classList.toggle('light-mode', newTheme === 'light');
        applyTheme(newTheme);
  
        // Actualiser le logo
        if (logo) {
          logo.src = (newTheme === 'dark') ? logoDark : logoLight;
        }
  
        // Actualiser l’icône
        if (themeIcon) {
          if (newTheme === 'dark') {
            themeIcon.classList.remove('bi-moon-fill');
            themeIcon.classList.add('bi-sun-fill');
          } else {
            themeIcon.classList.remove('bi-sun-fill');
            themeIcon.classList.add('bi-moon-fill');
          }
        }
  
        // Faire une requête POST pour mettre à jour le cookie côté serveur
        fetch(toggleThemeUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ theme: newTheme })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Échec de la mise à jour du thème sur le serveur.');
            }
        })
        .catch(err => {
            console.error('Erreur de requête toggle_theme:', err);
        });
      });
    }

});