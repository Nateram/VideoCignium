// i18n.js - Sistema de internacionalización

const supportedLangs = ['en', 'es'];

let currentLang = 'en';
let translations = {};
let translationsLoaded = false;

// Función para obtener el idioma por defecto
function getDefaultLang() {
    // Primero, verificar si hay idioma guardado en localStorage
    const saved = localStorage.getItem('app_lang');
    if (saved && supportedLangs.includes(saved)) {
        return saved;
    }

    // Si no, detectar idioma del navegador/sistema
    const browserLang = navigator.language || navigator.userLanguage;
    const langCode = browserLang.slice(0, 2); // Obtener solo 'en' o 'es'

    if (supportedLangs.includes(langCode)) {
        return langCode;
    }

    // Fallback a inglés
    return 'en';
}

// Función para cargar traducciones
async function loadTranslations(lang) {
    try {
        const response = await fetch(`/static/js/${lang}.json?v=${Date.now()}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        translations[lang] = await response.json();
        currentLang = lang;
        localStorage.setItem('app_lang', lang);
        translationsLoaded = true;
        console.log(`🌐 Idioma cargado: ${lang}`);
    } catch (error) {
        console.error(`❌ Error cargando traducciones para ${lang}:`, error);
        // Fallback a inglés si falla
        if (lang !== 'en') {
            await loadTranslations('en');
        }
    }
}

// Función para traducir texto
function t(key, fallback = '') {
    if (translations[currentLang] && translations[currentLang][key]) {
        return translations[currentLang][key];
    }
    return fallback || key;
}

// Función para actualizar todos los elementos con data-i18n
function updateTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translated = t(key);
        if (translated !== key) { // Solo actualizar si hay traducción
            element.textContent = translated;
        }
    });

    // Actualizar placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        const translated = t(key);
        if (translated !== key) {
            element.placeholder = translated;
        }
    });

    // Actualizar títulos
    document.querySelectorAll('[data-i18n-title]').forEach(element => {
        const key = element.getAttribute('data-i18n-title');
        const translated = t(key);
        if (translated !== key) {
            element.title = translated;
        }
    });
}

// Función para cambiar idioma
async function changeLanguage(lang) {
    if (!supportedLangs.includes(lang)) {
        console.warn(`Idioma no soportado: ${lang}`);
        return;
    }

    await loadTranslations(lang);
    updateTranslations();
    updateLangButton();

    // Mostrar notificación
    showNotification(`🌐 Idioma cambiado a ${t(lang === 'es' ? 'espanol' : 'ingles')}`, 'info', 2000);
}

// Función para actualizar el botón de idioma
function updateLangButton() {
    const langSelect = document.getElementById('lang-select');
    if (langSelect) {
        langSelect.value = currentLang;
    }
}

// Configurar event listeners para el selector de idioma
function setupLangSelector() {
    const langSelect = document.getElementById('lang-select');
    if (langSelect) {
        // Establecer valor inicial
        langSelect.value = currentLang;
        
        // Escuchar cambios
        langSelect.addEventListener('change', (e) => {
            changeLanguage(e.target.value);
        });
    }
}

// Función para inicializar i18n
async function initI18n() {
    const defaultLang = getDefaultLang();
    console.log('🌐 Iniciando i18n con idioma detectado:', defaultLang);
    await loadTranslations(defaultLang);
    updateTranslations();
    updateLangButton();
    setupLangSelector();
    console.log(`🌐 i18n inicializado con idioma: ${currentLang}`);
}

// Función para actualizar traducciones (útil cuando se carga contenido dinámico)
function refreshTranslations() {
    updateTranslations();
    updateLangButton();
}

// Exportar funciones globales
window.t = t;
window.changeLanguage = changeLanguage;
window.initI18n = initI18n;
window.refreshTranslations = refreshTranslations;

// Inicializar automáticamente cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initI18n);

// También observar cambios en el DOM para contenido dinámico
const observer = new MutationObserver((mutations) => {
    if (!translationsLoaded) return;
    
    let hasNewContent = false;
    mutations.forEach((mutation) => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            hasNewContent = true;
        }
    });
    
    if (hasNewContent) {
        // Traducir inmediatamente sin delay
        updateTranslations();
    }
});

// Observar cambios en el panel principal
document.addEventListener('DOMContentLoaded', () => {
    const mainPanel = document.getElementById('main-panel');
    if (mainPanel) {
        observer.observe(mainPanel, { childList: true, subtree: true });
    }
});