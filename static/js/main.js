// main.js - Funciones JavaScript principales

// Función para mostrar notificaciones
function showNotification(message, type = 'info', duration = 4000) {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
    `;
    
    // Estilos inline para la notificación
    notification.style.cssText = `
        position: fixed;
        top: 70px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${getNotificationColor(type)};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 3000;
        display: flex;
        align-items: center;
        gap: 10px;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
    `;
    
    document.body.appendChild(notification);
    
    // Remover después de la duración especificada
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function getNotificationColor(type) {
    const colors = {
        'success': '#27AE60',
        'error': '#E74C3C',
        'warning': '#F39C12',
        'info': '#3498DB'
    };
    return colors[type] || '#3498DB';
}

// Agregar animaciones CSS al documento
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Función para formatear fechas
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Función para formatear tamaño de archivo
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Exportar funciones globales
window.showNotification = showNotification;
window.formatDate = formatDate;
window.formatFileSize = formatFileSize;

// ===== SISTEMA DE SESIONES EFÍMERAS =====

// Función para finalizar sesión (eliminar todos los archivos y datos)
async function endSession() {
    // Confirmar acción
    const confirmed = confirm(
        '⚠️ ¿Estás seguro de que quieres finalizar la sesión?\n\n' +
        'Esto eliminará:\n' +
        '• Todos los videos subidos\n' +
        '• Todos los clips generados\n' +
        '• Toda la base de datos\n\n' +
        'Asegúrate de haber descargado los informes y clips que necesites antes de continuar.'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        showNotification('🧹 Limpiando sesión...', 'info');
        
        const response = await fetch(buildApiUrl('/api/session/cleanup'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('✅ Sesión finalizada. Todos los archivos fueron eliminados.', 'success', 5000);
            
            // Recargar página después de 2 segundos
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showNotification(`❌ Error al finalizar sesión: ${data.error}`, 'error', 6000);
        }
    } catch (error) {
        console.error('Error al finalizar sesión:', error);
        showNotification('❌ Error de conexión al finalizar sesión', 'error');
    }
}

// Limpieza automática al cerrar/recargar la página (opcional - comentado por defecto)
// Descomenta si quieres que SIEMPRE limpie al cerrar el navegador
/*
window.addEventListener('beforeunload', async (event) => {
    // Intentar limpiar sesión (navigator.sendBeacon para envío asíncrono garantizado)
    navigator.sendBeacon('/api/session/cleanup', JSON.stringify({}));
});
*/

// Limpieza al ocultar la pestaña por mucho tiempo (inactividad de 1 hora)
let inactivityTimeout;
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Usuario cambió de pestaña - iniciar timeout de 1 hora
        inactivityTimeout = setTimeout(async () => {
            console.log('⏰ Sesión inactiva por 1 hora, limpiando...');
            // Limpiar sesión automáticamente
            await fetch(buildApiUrl('/api/session/cleanup'), {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
        }, 60 * 60 * 1000); // 1 hora
    } else {
        // Usuario volvió a la pestaña - cancelar timeout
        if (inactivityTimeout) {
            clearTimeout(inactivityTimeout);
            inactivityTimeout = null;
        }
    }
});

// Exportar función de finalizar sesión
window.endSession = endSession;


