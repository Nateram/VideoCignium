// config.js - Configuración global compartida por todos los módulos

// 🔥 CONFIGURACIÓN DE PREFIJO DE URL PARA PROXY
// Detectar el prefijo desde la URL actual del navegador
// Si estamos en /proyect1/, usar ese prefijo
const currentPath = window.location.pathname;
const prefixMatch = currentPath.match(/^(\/[^\/]+)\//);
window.URL_PREFIX = prefixMatch ? prefixMatch[1] : '';

console.log('🔧 URL Prefix detectado:', window.URL_PREFIX || '(ninguno)');
console.log('🔧 Ruta actual:', currentPath);

// Helper global para construir URLs con prefijo
window.buildApiUrl = function(path) {
    // Si hay prefijo y el path no empieza con él, agregarlo
    if (window.URL_PREFIX && !path.startsWith(window.URL_PREFIX)) {
        return `${window.URL_PREFIX}${path}`;
    }
    return path;
};
