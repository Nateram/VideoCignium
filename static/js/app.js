// app.js - Controlador principal de la aplicación (réplica de la app desktop)
// VERSIÓN: 20251107-chunks-50MB-fix-spaces
console.log('🔵 app.js CARGADO - Versión: 20251107-chunks-50MB-fix-spaces (Chunking 50MB + fix espacios en nombres)');

// Detectar si estamos en Electron
const isElectronApp = !!(window.electron && window.electron.isElectron);
console.log(`🔍 Entorno detectado: ${isElectronApp ? 'Electron Desktop App' : 'Navegador Web'}`);
if (isElectronApp) {
    console.log('✅ API de Electron disponible:', Object.keys(window.electron));
}

// Estado global de la aplicación
const appState = {
    currentView: 'welcome',
    selectedFolder: null,
    selectedVideo: null,
    currentROI: [0, 0, 640, 480],
    processing: false
};

// Variables globales para el estado de procesamiento
let completedNotificationShown = false;

// Cargar vista según el botón del sidebar
function loadView(viewName, evt) {
    // Limpiar flag de completado si estamos saliendo de la vista de proceso
    if (appState.currentView === 'process' && viewName !== 'process') {
        console.log('🔄 Saliendo de la vista de análisis - limpiando flag de completado...');
        clearCompletedFlagSilent();
    }
    
    // Actualizar botones activos
    document.querySelectorAll('.sidebar-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Marcar como activo el botón clickeado
    if (evt && evt.target) {
        const clickedBtn = evt.target.closest('.sidebar-btn');
        if (clickedBtn) {
            clickedBtn.classList.add('active');
        } else {
            // Si el evento existe pero no es de un botón del sidebar (ej: botones de vista de proceso),
            // usar el mapeo de nombres de vista
            const viewButtonMap = {
                'folders': 'Carpetas y Videos',
                'select-folder': 'Seleccionar Carpeta',
                'select-video': 'Seleccionar Video',
                'process': 'Estado de Análisis',
                'roi-config': 'Configurar Zona Hora',
                'advanced': 'Configuración Avanzada',
                'excel': 'Excel',
                'help': 'Ayuda',
                'logs': 'Ver Logs'
            };

            const buttonText = viewButtonMap[viewName];
            if (buttonText) {
                const buttons = Array.from(document.querySelectorAll('.sidebar-btn'));
                const targetBtn = buttons.find(btn => btn.textContent.includes(buttonText));
                if (targetBtn) {
                    targetBtn.classList.add('active');
                }
            }
        }
    } else {
        // Si no hay evento, buscar el botón por el nombre de la vista
        const viewButtonMap = {
            'folders': 'Carpetas y Videos',
            'select-folder': 'Seleccionar Carpeta',
            'select-video': 'Seleccionar Video',
            'process': 'Estado de Análisis',
            'roi-config': 'Configurar Zona Hora',
            'advanced': 'Configuración Avanzada',
            'excel': 'Excel',
            'help': 'Ayuda',
            'logs': 'Ver Logs'
        };

        const buttonText = viewButtonMap[viewName];
        if (buttonText) {
            const buttons = Array.from(document.querySelectorAll('.sidebar-btn'));
            const targetBtn = buttons.find(btn => btn.textContent.includes(buttonText));
            if (targetBtn) {
                targetBtn.classList.add('active');
            }
        }
    }
    
    // Cargar la vista correspondiente
    switch(viewName) {
        case 'folders':
            showFoldersAndVideosView();
            break;
        case 'select-folder':
            showSelectFolderView();
            break;
        case 'select-video':
            showSelectVideoView();
            break;
        case 'process':
            showProcessView();
            break;
        case 'roi-config':
            showROIConfigView();
            break;
        case 'advanced':
            showAdvancedConfigView();
            break;
        case 'excel':
            showExcelView();
            break;
        case 'logs':
            showLogsView();
            break;
        case 'help':
            showHelpView();
            break;
        case 'directo':
            showDirectoInitView();
            break;
    }
    
    appState.currentView = viewName;
}

// Vista: Pantalla de bienvenida (simple y moderna como la imagen)

// Cargar estado del sistema
async function loadSystemStatus() {
    const statusContainer = document.getElementById('systemStatus');
    if (!statusContainer) return;
    
    try {
        const response = await fetch(buildApiUrl('/api/system/status'));
        const data = await response.json();
        
        if (!data.success) {
            statusContainer.innerHTML = `
                <div class="status-error">
                    <i class="fas fa-exclamation-circle"></i>
                    Error al verificar sistema
                </div>
            `;
            return;
        }
        
        const deps = data.dependencies;
        let html = '<div class="system-status-content">';
        html += '<h4><i class="fas fa-cogs"></i> Estado del Sistema</h4>';
        html += '<div class="dependencies-grid">';
        
        // Python
        if (deps.python?.available) {
            html += `
                <div class="dep-item dep-ok">
                    <i class="fas fa-check-circle"></i>
                    <span>Python ${deps.python.version}</span>
                </div>
            `;
        }
        
        // OpenCV
        if (deps.opencv?.available) {
            html += `
                <div class="dep-item dep-ok">
                    <i class="fas fa-check-circle"></i>
                    <span>OpenCV ${deps.opencv.version}</span>
                </div>
            `;
        } else {
            html += `
                <div class="dep-item dep-error">
                    <i class="fas fa-times-circle"></i>
                    <span>OpenCV no disponible</span>
                </div>
            `;
        }
        
        // ffmpeg
        if (deps.ffmpeg?.available) {
            html += `
                <div class="dep-item dep-ok">
                    <i class="fas fa-check-circle"></i>
                    <span>ffmpeg ${deps.ffmpeg.version}</span>
                </div>
            `;
        } else {
            html += `
                <div class="dep-item dep-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>ffmpeg no instalado</span>
                </div>
            `;
        }
        
        // SQLite
        if (deps.sqlite?.available) {
            html += `
                <div class="dep-item dep-ok">
                    <i class="fas fa-check-circle"></i>
                    <span>SQLite ${deps.sqlite.version}</span>
                </div>
            `;
        }
        
        // Espacio en disco
        if (deps.disk_space?.available) {
            const freeGB = deps.disk_space.free_gb;
            const statusClass = freeGB < 1 ? 'dep-warning' : 'dep-ok';
            html += `
                <div class="dep-item ${statusClass}">
                    <i class="fas fa-hdd"></i>
                    <span>${freeGB} GB libres</span>
                </div>
            `;
        }
        
        html += '</div>';
        
        // Advertencias
        if (!deps.ffmpeg?.available) {
            html += `
                <div class="status-warning">
                    <i class="fas fa-info-circle"></i>
                    <small>ffmpeg no está instalado. La conversión de archivos DAV será limitada.</small>
                </div>
            `;
        }
        
        html += '</div>';
        statusContainer.innerHTML = html;
        
    } catch (error) {
        console.error('Error al cargar estado del sistema:', error);
        statusContainer.innerHTML = `
            <div class="status-error">
                <i class="fas fa-exclamation-circle"></i>
                Error de conexión
            </div>
        `;
    }
}

// Vista: Carpetas y Videos (TreeView como en desktop)
function showFoldersAndVideosView() {
    updateViewTitle('<i class="fas fa-folder-open"></i> Carpetas y Videos');
    
    const content = `
        <div class="folders-view">
            <div class="view-header">
                <h3>Explorar Carpetas y Videos Analizados</h3>
                <div class="header-controls">
                    <div class="search-box">
                        <i class="fas fa-search"></i>
                        <input type="text" id="searchInput" placeholder="Buscar carpetas o videos..." onkeyup="filterTree()">
                    </div>
                    <select id="sortSelect" class="sort-select" onchange="sortTree()">
                        <option value="name-asc">Nombre (A-Z)</option>
                        <option value="name-desc">Nombre (Z-A)</option>
                        <option value="date-desc">Más reciente</option>
                        <option value="date-asc">Más antiguo</option>
                        <option value="clips-desc">Más clips</option>
                    </select>
                    <button class="btn btn-primary" onclick="loadFolders()">
                        <i class="fas fa-sync"></i> Actualizar
                    </button>
                </div>
            </div>
            
            <!-- TreeView ocupa todo el espacio -->
            <div class="tree-panel-full">
                <div class="treeview-container" id="treeview">
                    <div class="loading-message">
                        <i class="fas fa-spinner fa-spin"></i> Cargando datos...
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    loadFolders();
}

// Actualizar título de la vista
function updateViewTitle(title) {
    document.getElementById('view-title').innerHTML = title;
}

// Cargar carpetas en el TreeView
async function loadFolders() {
    const treeview = document.getElementById('treeview');
    
    try {
        const response = await fetch(buildApiUrl('/api/folders'));
        const data = await response.json();
        
        if (!data.success || data.folders.length === 0) {
            treeview.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open" style="font-size: 3rem; color: var(--light-text);"></i>
                    <p>No hay carpetas analizadas aún</p>
                    <button class="btn btn-primary" onclick="loadView('select-folder')">
                        <i class="fas fa-folder-plus"></i> Analizar Carpeta
                    </button>
                </div>
            `;
            return;
        }
        
        let html = '<div class="tree-root">';
        
        data.folders.forEach(folder => {
            html += `
                <div class="tree-item-container">
                    <div class="tree-item" onclick="toggleFolder(${folder.id}, this)">
                        <span class="expand-icon">▶</span>
                        <i class="fas fa-folder item-icon"></i>
                        <span>${folder.name}</span>
                    </div>
                    <button class="btn-icon-compact btn-danger" onclick="event.stopPropagation(); deleteFolder(${folder.id}, '${folder.name.replace(/'/g, "\\'")}')" title="Eliminar carpeta completa">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="tree-children" id="folder-${folder.id}">
                    <div class="loading-message"><i class="fas fa-spinner fa-spin"></i> Cargando videos...</div>
                </div>
            `;
        });
        
        html += '</div>';
        treeview.innerHTML = html;
        
    } catch (error) {
        console.error('Error cargando carpetas:', error);
        treeview.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-circle" style="font-size: 3rem; color: var(--danger-color);"></i>
                <p>Error al cargar las carpetas</p>
            </div>
        `;
    }
}

// Toggle de carpetas en TreeView
async function toggleFolder(folderId, element) {
    const isExpanded = element.classList.contains('expanded');
    const childrenDiv = document.getElementById(`folder-${folderId}`);
    
    if (isExpanded) {
        element.classList.remove('expanded');
        childrenDiv.style.display = 'none';
    } else {
        element.classList.add('expanded');
        childrenDiv.style.display = 'block';
        
        // Cargar videos si aún no se han cargado
        if (childrenDiv.querySelector('.loading-message')) {
            await loadVideosForFolder(folderId, childrenDiv);
        }
    }
}

// Cargar videos de una carpeta
async function loadVideosForFolder(folderId, container) {
    try {
        const response = await fetch(buildApiUrl(`/api/folder/${folderId}`));
        const data = await response.json();
        
        if (!data.success || data.videos.length === 0) {
            container.innerHTML = `
                <div class="tree-item" style="padding-left: 30px; color: var(--light-text);">
                    <i class="fas fa-info-circle"></i>
                    <span>No hay videos</span>
                </div>
            `;
            return;
        }
        
        let html = '';
        data.videos.forEach(video => {
            html += `
                <div class="tree-item-container">
                    <div class="tree-item" onclick="toggleVideo(${video.id}, this)">
                        <span class="expand-icon">▶</span>
                        <i class="fas fa-file-video item-icon"></i>
                        <span>${video.name} (${video.clip_count} clips)</span>
                    </div>
                    <button class="btn-icon-compact btn-danger" onclick="event.stopPropagation(); deleteVideo(${video.id}, '${video.name}')" title="Eliminar video de BD (clips se borran del disco)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="tree-children" id="video-${video.id}"></div>
            `;
        });
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error cargando videos:', error);
        container.innerHTML = '<div class="error-state">Error al cargar videos</div>';
    }
}

// Toggle de videos en TreeView (mostrar clips)
async function toggleVideo(videoId, element) {
    const isExpanded = element.classList.contains('expanded');
    const childrenDiv = document.getElementById(`video-${videoId}`);
    
    if (isExpanded) {
        element.classList.remove('expanded');
        childrenDiv.style.display = 'none';
    } else {
        element.classList.add('expanded');
        childrenDiv.style.display = 'block';
        
        // Cargar clips si aún no se han cargado
        if (childrenDiv.querySelector('.loading-message') || childrenDiv.innerHTML === '') {
            await loadClipsForVideo(videoId, childrenDiv);
        }
    }
}

// Cargar clips de un video
async function loadClipsForVideo(videoId, container) {
    container.innerHTML = '<div class="loading-message"><i class="fas fa-spinner fa-spin"></i> Cargando clips...</div>';
    
    try {
        const response = await fetch(buildApiUrl(`/api/video/${videoId}/clips`));
        const data = await response.json();
        
        if (!data.success || data.clips.length === 0) {
            container.innerHTML = `
                <div class="tree-item" style="margin-left: 60px; color: var(--light-text);">
                    <i class="fas fa-info-circle"></i>
                    <span>No hay clips</span>
                </div>
            `;
            return;
        }
        
        let html = '';
        data.clips.forEach(clip => {
            const objectInfo = clip.object_type ? `${clip.object_type}` : 'Sin clasificar';
            const colorInfo = clip.object_color ? ` (${clip.object_color})` : '';
            
            html += `
                <div class="tree-item-container clip-container">
                    <div class="tree-item tree-item-clip" onclick="showClipDetails(${clip.id})">
                        <i class="fas fa-film item-icon" style="color: var(--success-color);"></i>
                        <span class="clip-text">${clip.event_date || clip.timestamp} - ${objectInfo}${colorInfo}</span>
                    </div>
                    <button class="btn-icon-compact btn-danger" onclick="event.stopPropagation(); deleteClip(${clip.id}, true)" title="Eliminar clip">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error cargando clips:', error);
        container.innerHTML = '<div class="error-state">Error al cargar clips</div>';
    }
}

// Mostrar detalles de un clip
async function showClipDetails(clipId) {
    try {
        const response = await fetch(buildApiUrl(`/api/clip/${clipId}`));
        const data = await response.json();
        
        if (!data.success) {
            showNotification('Error al cargar detalles del clip', 'error');
            return;
        }
        
        const clip = data.clip;
        console.log('Clip seleccionado:', clip);
        
        // Crear modal con detalles del clip
        showClipModal(clip);
        
    } catch (error) {
        console.error('Error cargando detalles del clip:', error);
        showNotification('Error al cargar detalles del clip', 'error');
    }
}

// Mostrar modal con detalles y reproductor del clip
function showClipModal(clip) {
    // Construir URL del clip (solo si existe) con prefijo correcto
    const clipUrl = clip.ruta_relativa ? buildApiUrl(`/clips/${clip.ruta_relativa}`) : null;
    const hasClip = clip.has_clip !== false && clipUrl !== null;  // Si has_clip existe, usarlo; sino, verificar URL
    
    // Título del modal según si tiene clip o no
    const modalTitle = hasClip ? 'Detalles del Clip' : 'Detalles del Evento';
    const modalIcon = hasClip ? 'fa-film' : 'fa-calendar-check';
    
    const modalHTML = `
        <div class="modal-overlay" id="clipModal" onclick="closeClipModal(event)">
            <div class="modal-content clip-modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2><i class="fas ${modalIcon}"></i> ${modalTitle}</h2>
                    <button class="modal-close" onclick="closeClipModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="modal-body">
                    <!-- Reproductor de video (solo si hay clip MP4) -->
                    ${hasClip ? `
                    <div class="clip-player-container">
                        <video id="clipVideoPlayer" controls autoplay class="clip-video">
                            <source src="${clipUrl}" type="video/mp4">
                            Tu navegador no soporta el reproductor de video.
                        </video>
                    </div>
                    ` : ''}
                    
                    <!-- Información del clip -->
                    <div class="clip-info-grid" id="clipInfoGrid">
                        <div class="clip-info-item">
                            <div class="clip-info-label">
                                <i class="fas fa-calendar"></i> Fecha del Evento
                            </div>
                            <div class="clip-info-value-container">
                                <div class="clip-info-value editable-field" id="clipTimestamp-${clip.id}" 
                                     ondblclick="makeFieldEditable('timestamp', ${clip.id}, 'clipTimestamp-${clip.id}')">
                                    ${clip.timestamp || 'No disponible'}
                                </div>
                                <button class="edit-field-btn" onclick="makeFieldEditable('timestamp', ${clip.id}, 'clipTimestamp-${clip.id}')" 
                                        title="Editar fecha">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="clip-info-item">
                            <div class="clip-info-label">
                                <i class="fas fa-clock"></i> Tiempo en Video
                            </div>
                            <div class="clip-info-value" id="clipVideoTime">
                                ${clip.tiempo_video || '00:00'}
                            </div>
                        </div>
                        
                        <div class="clip-info-item">
                            <div class="clip-info-label">
                                <i class="fas fa-cube"></i> Objeto Detectado
                            </div>
                            <div class="clip-info-value-container">
                                <div class="clip-info-value editable-field" id="clipObject-${clip.id}" 
                                     ondblclick="makeFieldEditable('object', ${clip.id}, 'clipObject-${clip.id}')">
                                    ${clip.detected_object || 'Sin clasificar'}
                                </div>
                                <button class="edit-field-btn" onclick="makeFieldEditable('object', ${clip.id}, 'clipObject-${clip.id}')" 
                                        title="Editar objeto">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="clip-info-item">
                            <div class="clip-info-label">
                                <i class="fas fa-palette"></i> Color
                            </div>
                            <div class="clip-info-value-container">
                                <div class="clip-info-value editable-field" id="clipColor-${clip.id}" 
                                     ondblclick="makeFieldEditable('color', ${clip.id}, 'clipColor-${clip.id}')">
                                    ${clip.color || 'No detectado'}
                                </div>
                                <button class="edit-field-btn" onclick="makeFieldEditable('color', ${clip.id}, 'clipColor-${clip.id}')" 
                                        title="Editar color">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="clip-info-item full-width">
                            <div class="clip-info-label">
                                <i class="fas fa-file"></i> Archivo
                            </div>
                            <div class="clip-info-value clip-filename">
                                ${clip.nombre}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Acciones -->
                    <div class="clip-actions">
                        ${hasClip ? `
                        <button class="btn-action btn-primary" onclick="downloadClip('${clipUrl}', '${clip.nombre}')">
                            <i class="fas fa-download"></i> Descargar Clip
                        </button>
                        ` : ''}
                        <button class="btn-action btn-danger" onclick="deleteClipFromModal(${clip.id})">
                            <i class="fas fa-trash"></i> ${hasClip ? 'Eliminar Clip' : 'Eliminar Evento'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Agregar modal al body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Prevenir scroll del body
    document.body.style.overflow = 'hidden';
}

// Cerrar modal de clip
function closeClipModal(event) {
    if (event && event.target.classList.contains('modal-overlay')) {
        // Solo cerrar si se hace clic en el overlay
    } else if (!event) {
        // Cerrar desde el botón X
    } else {
        return; // No cerrar si se hace clic dentro del modal
    }
    
    const modal = document.getElementById('clipModal');
    if (modal) {
        // Detener video antes de cerrar
        const video = document.getElementById('clipVideoPlayer');
        if (video) {
            video.pause();
        }
        
        modal.remove();
        document.body.style.overflow = '';
    }
}

// Formatear milisegundos a formato legible
function formatMilliseconds(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Descargar clip
function downloadClip(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showNotification('📥 Descargando clip...', 'info');
}

// Sistema de edición inline por campo
function makeFieldEditable(fieldType, clipId, elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error('Elemento no encontrado:', elementId);
        return;
    }
    
    const currentValue = element.textContent.trim();
    
    // Crear input
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'clip-edit-input-inline';
    input.value = currentValue;
    
    // Placeholder según tipo de campo
    if (fieldType === 'timestamp') {
        input.placeholder = 'DD-MM-YYYY HH:MM:SS';
    } else if (fieldType === 'object') {
        input.placeholder = 'Ej: car, person, bird';
    } else if (fieldType === 'color') {
        input.placeholder = 'Ej: blanco, negro, rojo';
    }
    
    // Reemplazar contenido con input
    element.innerHTML = '';
    element.appendChild(input);
    input.focus();
    input.select();
    
    // Guardar con Enter
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveFieldValue(fieldType, clipId, input.value, element, currentValue);
        } else if (e.key === 'Escape') {
            element.textContent = currentValue;
        }
    });
    
    // Guardar al perder foco
    input.addEventListener('blur', () => {
        if (input.value !== currentValue) {
            saveFieldValue(fieldType, clipId, input.value, element, currentValue);
        } else {
            element.textContent = currentValue;
        }
    });
}

async function saveFieldValue(fieldType, clipId, newValue, element, originalValue) {
    if (!newValue || newValue.trim() === '') {
        showNotification('⚠️ El campo no puede estar vacío', 'warning');
        element.textContent = originalValue || 'Sin datos';
        return;
    }
    
    try {
        showNotification('💾 Guardando...', 'info');
        
        // Mapear tipo de campo a nombre de parámetro API
        const fieldMap = {
            'object': 'detected_object',
            'color': 'color',
            'timestamp': 'timestamp'
        };
        
        const response = await fetch(buildApiUrl(`/api/clip/${clipId}`), {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                [fieldMap[fieldType]]: newValue.trim()
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('✓ Campo actualizado', 'success');
            element.textContent = newValue.trim();
            
            // Recargar lista de clips para reflejar cambios
            setTimeout(() => showFoldersAndVideosView(), 500);
        } else {
            showNotification('❌ Error: ' + data.error, 'error');
            element.textContent = originalValue || 'Sin datos';
        }
        
    } catch (error) {
        console.error('Error guardando campo:', error);
        showNotification('❌ Error al guardar', 'error');
        element.textContent = originalValue || 'Sin datos';
    }
}

// Eliminar clip desde el modal
async function deleteClipFromModal(clipId) {
    closeClipModal();
    await deleteClip(clipId, true);
    
    // Recargar la vista actual
    showFoldersAndVideosView();
}

// Eliminar clip
async function deleteClip(clipId, deleteFromDisk) {
    const message = `¿Eliminar este clip?\n\n` +
        `✅ Se eliminará:\n` +
        `  • Registro del clip en la BD\n` +
        `  • Archivo del clip del disco\n\n` +
        `⚠️ Esta acción NO se puede deshacer.`;
    
    if (!confirm(message)) {
        return;
    }
    
    try {
        showNotification('🗑️ Eliminando clip...', 'info');
        
        const response = await fetch(buildApiUrl(`/api/clip/${clipId}`), {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ delete_from_disk: deleteFromDisk })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('✓ Clip eliminado correctamente', 'success');
            
            // Eliminar solo el elemento del clip del DOM sin recargar todo
            const clipElements = document.querySelectorAll('.tree-item-container');
            clipElements.forEach(el => {
                if (el.innerHTML.includes(`deleteClip(${clipId}`)) {
                    el.remove();
                }
            });
            
            // Actualizar el Excel si está abierto
            if (appState.currentView === 'excel') {
                loadSessionExcel();
            }
        } else {
            showNotification('Error: ' + data.message, 'error');
        }
        
    } catch (error) {
        console.error('Error eliminando clip:', error);
        showNotification('Error al eliminar clip', 'error');
    }
}

// Eliminar video completo
async function deleteVideo(videoId, videoName) {
    const message = `¿Eliminar "${videoName}" de la base de datos?\n\n` +
        `✅ Se eliminará:\n` +
        `  • Registro del video en la BD\n` +
        `  • Todos los clips de la BD\n` +
        `  • Archivos de clips del disco\n\n` +
        `❌ NO se eliminará:\n` +
        `  • El video original del disco\n\n` +
        `⚠️ Esta acción NO se puede deshacer.`;
    
    if (!confirm(message)) {
        return;
    }
    
    try {
        showNotification('🗑️ Eliminando video...', 'info');
        
        const response = await fetch(buildApiUrl(`/api/video/${videoId}`), {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`✓ Video eliminado. Se eliminaron ${data.deleted_files} archivos del disco`, 'success');
            
            // Eliminar el contenedor del video y sus clips del DOM
            const videoContainers = document.querySelectorAll('.tree-item-container');
            videoContainers.forEach(container => {
                if (container.innerHTML.includes(`toggleVideo(${videoId}`)) {
                    // Eliminar también los clips asociados
                    const videoChildren = document.getElementById(`video-${videoId}`);
                    if (videoChildren) {
                        videoChildren.remove();
                    }
                    container.remove();
                }
            });
        } else {
            showNotification('Error: ' + data.message, 'error');
        }
        
    } catch (error) {
        console.error('Error eliminando video:', error);
        showNotification('Error al eliminar video', 'error');
    }
}

// Eliminar carpeta completa
async function deleteFolder(folderId, folderName) {
    const message = `¿Eliminar la carpeta "${folderName}" de la base de datos?\n\n` +
        `✅ Se eliminará:\n` +
        `  • Registro de la carpeta en la BD\n` +
        `  • Todos los videos de la BD\n` +
        `  • Todos los clips de la BD\n` +
        `  • Archivos de clips del disco\n\n` +
        `❌ NO se eliminará:\n` +
        `  • Los videos originales del disco\n\n` +
        `⚠️ Esta acción NO se puede deshacer.`;
    
    if (!confirm(message)) {
        return;
    }
    
    try {
        showNotification('🗑️ Eliminando carpeta...', 'info');
        
        const response = await fetch(buildApiUrl(`/api/folder/${folderId}`), {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`✓ Carpeta eliminada. Se eliminaron ${data.deleted_files} archivos del disco`, 'success');
            
            // Eliminar el contenedor de la carpeta completa del DOM
            const folderContainers = document.querySelectorAll('.tree-item-container');
            folderContainers.forEach(container => {
                if (container.innerHTML.includes(`toggleFolder(${folderId}`)) {
                    // Eliminar también los hijos de la carpeta
                    const folderChildren = document.getElementById(`folder-${folderId}`);
                    if (folderChildren) {
                        folderChildren.remove();
                    }
                    container.remove();
                }
            });
        } else {
            showNotification('Error: ' + data.message, 'error');
        }
        
    } catch (error) {
        console.error('Error eliminando carpeta:', error);
        showNotification('Error al eliminar carpeta', 'error');
    }
}

// Filtrar árbol de carpetas/videos
function filterTree() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const treeItems = document.querySelectorAll('.tree-item');
    
    treeItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

// Ordenar árbol
function sortTree() {
    const sortValue = document.getElementById('sortSelect').value;
    // Recargar carpetas con el orden seleccionado
    loadFolders(sortValue);
}

// Vista: Seleccionar Carpeta
function showSelectFolderView() {
    updateViewTitle('📁 Analizar Nueva Carpeta');
    
    const content = `
        <div class="upload-container-full">
            <div class="upload-card-wide">
                <!-- Opciones de Procesamiento ARRIBA -->
                <div class="processing-options-horizontal">
                    <h3><i class="fas fa-sliders-h"></i> Opciones de Análisis</h3>
                    <div class="options-row">
                        <div class="option-compact">
                            <i class="fas fa-tachometer-alt" style="color: var(--info-color);"></i>
                            <span>Movimiento</span>
                            <span class="badge-always">ON</span>
                        </div>
                        <label class="option-compact option-toggle-horizontal">
                            <input type="checkbox" id="folderGenerateClipsOption" checked>
                            <span class="toggle-slider-small"></span>
                            <i class="fas fa-cut" style="color: var(--warning-color);"></i>
                            <span>Clips</span>
                        </label>
                        <label class="option-compact option-toggle-horizontal">
                            <input type="checkbox" id="folderUseAiAnalysisOption" checked>
                            <span class="toggle-slider-small"></span>
                            <i class="fas fa-brain" style="color: var(--secondary-color);"></i>
                            <span>IA</span>
                        </label>
                    </div>
                </div>

                <h2 style="text-align: center; margin: 20px 0 15px 0; font-size: 1.2rem;">
                    <i class="fas fa-folder-open"></i> Selecciona una carpeta con videos
                </h2>
                
                <div class="upload-drop-zone" id="folderDropZone">
                    <i class="fas fa-cloud-upload-alt"></i>
                    <p><strong>Arrastra una carpeta aquí</strong></p>
                    <p class="upload-hint">o haz clic para seleccionar</p>
                    <input type="file" id="folderInput" webkitdirectory directory multiple style="display: none;">
                </div>
                
                <button class="btn-upload btn-green" onclick="document.getElementById('folderInput').click()">
                    <i class="fas fa-folder-plus"></i>
                    Seleccionar Carpeta
                </button>
                
                <div id="folderFileList" class="file-preview" style="display: none;"></div>
                
                <div id="uploadProgressSection" style="display: none;">
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" id="folderUploadProgress">0%</div>
                        </div>
                        <p class="progress-text" id="folderUploadText">Subiendo archivos...</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Event listeners
    const folderInput = document.getElementById('folderInput');
    const folderDropZone = document.getElementById('folderDropZone');
    
    folderInput.addEventListener('change', handleFolderSelect);
    
    folderDropZone.addEventListener('click', () => folderInput.click());
    folderDropZone.addEventListener('dragover', handleDragOver);
    folderDropZone.addEventListener('drop', handleFolderDrop);
    folderDropZone.addEventListener('dragleave', handleDragLeave);
    // Configurar listeners de sincronización para checkboxes de folder
    setTimeout(() => {
        const folderClipsCheckbox = document.getElementById('folderGenerateClipsOption');
        const folderAICheckbox = document.getElementById('folderUseAiAnalysisOption');
        
        if (folderClipsCheckbox) {
            // Cargar estado desde sessionStorage o usar valor del checkbox
            const savedClipsState = sessionStorage.getItem('processingOptions.generateClips');
            if (savedClipsState !== null) {
                folderClipsCheckbox.checked = savedClipsState === 'true';
                console.log('📂 Estado Clips restaurado desde sesión:', folderClipsCheckbox.checked);
            }
            
            // Guardar estado inicial en variable global y sessionStorage
            window.lastProcessingOptions = window.lastProcessingOptions || {};
            window.lastProcessingOptions.generateClips = folderClipsCheckbox.checked;
            sessionStorage.setItem('processingOptions.generateClips', folderClipsCheckbox.checked);
            console.log('💾 Estado inicial Clips guardado:', window.lastProcessingOptions.generateClips);
            
            folderClipsCheckbox.addEventListener('change', function() {
                console.log('🔄 [FOLDER] Checkbox Clips cambió a:', this.checked);
                
                // Guardar en variable global y sessionStorage
                window.lastProcessingOptions = window.lastProcessingOptions || {};
                window.lastProcessingOptions.generateClips = this.checked;
                sessionStorage.setItem('processingOptions.generateClips', this.checked);
                
                // Sincronizar con checkbox de ROI si existe
                const roiCheckbox = document.getElementById('processingGenerateClips');
                if (roiCheckbox) {
                    roiCheckbox.checked = this.checked;
                    console.log('  ↪️ Sincronizado processingGenerateClips a:', this.checked);
                }
                
                // CRÍTICO: Actualizar dependencia IA cuando cambie Clips
                if (typeof window.updateAiState === 'function') {
                    window.updateAiState('folderGenerateClipsOption', 'folderUseAiAnalysisOption');
                    console.log('  ↪️ Estado IA actualizado según Clips:', this.checked);
                }
            });
            console.log('✅ Listener agregado a folderGenerateClipsOption');
        }
        
        if (folderAICheckbox) {
            // Cargar estado desde sessionStorage o usar valor del checkbox
            const savedAIState = sessionStorage.getItem('processingOptions.useAI');
            if (savedAIState !== null) {
                folderAICheckbox.checked = savedAIState === 'true';
                console.log('📂 Estado IA restaurado desde sesión:', folderAICheckbox.checked);
            }
            
            // Guardar estado inicial en variable global y sessionStorage
            window.lastProcessingOptions = window.lastProcessingOptions || {};
            window.lastProcessingOptions.useAI = folderAICheckbox.checked;
            sessionStorage.setItem('processingOptions.useAI', folderAICheckbox.checked);
            console.log('💾 Estado inicial IA guardado:', window.lastProcessingOptions.useAI);
            
            // CRÍTICO: Capturar click en el LABEL padre para manejar cuando está disabled
            const folderAILabel = folderAICheckbox.closest('label');
            if (folderAILabel) {
                folderAILabel.addEventListener('click', function(e) {
                    const clipsCheckbox = document.getElementById('folderGenerateClipsOption');
                    
                    // Si IA está disabled, activar Clips primero
                    if (folderAICheckbox.disabled) {
                        e.preventDefault(); // Prevenir el toggle default del label
                        e.stopPropagation();
                        
                        console.log('🔓 Click en IA disabled detectado - activando Clips...');
                        
                        // Activar Clips primero
                        if (clipsCheckbox) {
                            clipsCheckbox.checked = true;
                            console.log('  ↪️ Auto-activado Clips por click en IA disabled');
                            
                            // Actualizar estado de sessionStorage para Clips
                            window.lastProcessingOptions = window.lastProcessingOptions || {};
                            window.lastProcessingOptions.generateClips = true;
                            sessionStorage.setItem('processingOptions.generateClips', true);
                        }
                        
                        // Habilitar y marcar IA
                        folderAICheckbox.disabled = false;
                        folderAICheckbox.checked = true;
                        
                        // Guardar estado de IA
                        window.lastProcessingOptions.useAI = true;
                        sessionStorage.setItem('processingOptions.useAI', true);
                        console.log('  ↪️ IA habilitado y marcado');
                        
                        // Sincronizar con ROI si existe
                        const roiCheckbox = document.getElementById('processingUseAI');
                        if (roiCheckbox) {
                            roiCheckbox.checked = true;
                        }
                    }
                }, true);
            }
            
            folderAICheckbox.addEventListener('change', function() {
                console.log('🔄 [FOLDER] Checkbox IA cambió a:', this.checked);
                
                // CRÍTICO: Si se intenta marcar IA sin Clips, activar Clips primero
                const clipsCheckbox = document.getElementById('folderGenerateClipsOption');
                if (this.checked && clipsCheckbox && !clipsCheckbox.checked) {
                    clipsCheckbox.checked = true;
                    console.log('  ↪️ Auto-activado Clips porque se marcó IA');
                }
                
                // Guardar en variable global y sessionStorage
                window.lastProcessingOptions = window.lastProcessingOptions || {};
                window.lastProcessingOptions.useAI = this.checked;
                sessionStorage.setItem('processingOptions.useAI', this.checked);
                
                // Sincronizar con checkbox de ROI si existe
                const roiCheckbox = document.getElementById('processingUseAI');
                if (roiCheckbox) {
                    roiCheckbox.checked = this.checked;
                    console.log('  ↪️ Sincronizado processingUseAI a:', this.checked);
                }
            });
            console.log('✅ Listener agregado a folderUseAiAnalysisOption');
        }
        
        // CRÍTICO: Actualizar estado de dependencias IA/Clips después de restaurar valores
        if (typeof window.initAiClipDependencies === 'function') {
            window.initAiClipDependencies();
            console.log('✅ Dependencias IA/Clips inicializadas para FOLDER');
        }
    }, 100);
}

// Vista: Seleccionar Video Individual
function showSelectVideoView() {
    updateViewTitle('🎥 Analizar Video Individual');
    
    const content = `
        <div class="upload-container-full">
            <div class="upload-card-wide">
                <!-- Opciones de Procesamiento ARRIBA -->
                <div class="processing-options-horizontal">
                    <h3><i class="fas fa-sliders-h"></i> Opciones de Análisis</h3>
                    <div class="options-row">
                        <div class="option-compact">
                            <i class="fas fa-tachometer-alt" style="color: var(--info-color);"></i>
                            <span>Movimiento</span>
                            <span class="badge-always">ON</span>
                        </div>
                        <label class="option-compact option-toggle-horizontal">
                            <input type="checkbox" id="videoGenerateClipsOption" checked>
                            <span class="toggle-slider-small"></span>
                            <i class="fas fa-cut" style="color: var(--warning-color);"></i>
                            <span>Clips</span>
                        </label>
                        <label class="option-compact option-toggle-horizontal">
                            <input type="checkbox" id="videoUseAiAnalysisOption" checked>
                            <span class="toggle-slider-small"></span>
                            <i class="fas fa-brain" style="color: var(--secondary-color);"></i>
                            <span>IA</span>
                        </label>
                    </div>
                </div>

                <h2 style="text-align: center; margin: 20px 0 15px 0; font-size: 1.2rem;">
                    <i class="fas fa-video"></i> Selecciona uno o más videos
                </h2>
                
                <div class="upload-drop-zone" id="videoDropZone">
                    <i class="fas fa-cloud-upload-alt"></i>
                    <p><strong>Arrastra videos aquí</strong></p>
                    <p class="upload-hint">o haz clic para seleccionar</p>
                    <input type="file" id="videoInput" multiple accept=".mp4,.avi,.mov,.dav,.mkv" style="display: none;">
                </div>
                
                <button class="btn-upload btn-orange" onclick="document.getElementById('videoInput').click()">
                    <i class="fas fa-file-video"></i>
                    Seleccionar Videos
                </button>
                
                <div id="videoFileList" class="file-preview" style="display: none;"></div>
                
                <div id="videoUploadProgressSection" style="display: none;">
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" id="videoUploadProgress">0%</div>
                        </div>
                        <p class="progress-text" id="videoUploadText">Subiendo videos...</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Event listeners
    const videoInput = document.getElementById('videoInput');
    const videoDropZone = document.getElementById('videoDropZone');
    
    videoInput.addEventListener('change', handleVideoSelect);
    
    videoDropZone.addEventListener('click', () => videoInput.click());
    videoDropZone.addEventListener('dragover', handleDragOver);
    videoDropZone.addEventListener('drop', handleVideoDrop);
    videoDropZone.addEventListener('dragleave', handleDragLeave);
    
    // Configurar listeners de sincronización para checkboxes de video
    setTimeout(() => {
        const videoClipsCheckbox = document.getElementById('videoGenerateClipsOption');
        const videoAICheckbox = document.getElementById('videoUseAiAnalysisOption');
        
        if (videoClipsCheckbox) {
            // Cargar estado desde sessionStorage o usar valor del checkbox
            const savedClipsState = sessionStorage.getItem('processingOptions.generateClips');
            if (savedClipsState !== null) {
                videoClipsCheckbox.checked = savedClipsState === 'true';
                console.log('📂 Estado Clips restaurado desde sesión:', videoClipsCheckbox.checked);
            }
            
            // Guardar estado inicial en variable global y sessionStorage
            window.lastProcessingOptions = window.lastProcessingOptions || {};
            window.lastProcessingOptions.generateClips = videoClipsCheckbox.checked;
            sessionStorage.setItem('processingOptions.generateClips', videoClipsCheckbox.checked);
            console.log('💾 Estado inicial Clips guardado:', window.lastProcessingOptions.generateClips);
            
            videoClipsCheckbox.addEventListener('change', function() {
                console.log('🔄 [VIDEO] Checkbox Clips cambió a:', this.checked);
                
                // Guardar en variable global y sessionStorage
                window.lastProcessingOptions = window.lastProcessingOptions || {};
                window.lastProcessingOptions.generateClips = this.checked;
                sessionStorage.setItem('processingOptions.generateClips', this.checked);
                
                // Sincronizar con checkbox de ROI si existe
                const roiCheckbox = document.getElementById('processingGenerateClips');
                if (roiCheckbox) {
                    roiCheckbox.checked = this.checked;
                    console.log('  ↪️ Sincronizado processingGenerateClips a:', this.checked);
                }
                
                // CRÍTICO: Actualizar dependencia IA cuando cambie Clips
                if (typeof window.updateAiState === 'function') {
                    window.updateAiState('videoGenerateClipsOption', 'videoUseAiAnalysisOption');
                    console.log('  ↪️ Estado IA actualizado según Clips:', this.checked);
                }
            });
            console.log('✅ Listener agregado a videoGenerateClipsOption');
        }
        
        if (videoAICheckbox) {
            // Cargar estado desde sessionStorage o usar valor del checkbox
            const savedAIState = sessionStorage.getItem('processingOptions.useAI');
            if (savedAIState !== null) {
                videoAICheckbox.checked = savedAIState === 'true';
                console.log('📂 Estado IA restaurado desde sesión:', videoAICheckbox.checked);
            }
            
            // Guardar estado inicial en variable global y sessionStorage
            window.lastProcessingOptions = window.lastProcessingOptions || {};
            window.lastProcessingOptions.useAI = videoAICheckbox.checked;
            sessionStorage.setItem('processingOptions.useAI', videoAICheckbox.checked);
            console.log('💾 Estado inicial IA guardado:', window.lastProcessingOptions.useAI);
            
            // CRÍTICO: Capturar click en el LABEL padre para manejar cuando está disabled
            const videoAILabel = videoAICheckbox.closest('label');
            if (videoAILabel) {
                videoAILabel.addEventListener('click', function(e) {
                    const clipsCheckbox = document.getElementById('videoGenerateClipsOption');
                    
                    // Si IA está disabled, activar Clips primero
                    if (videoAICheckbox.disabled) {
                        e.preventDefault(); // Prevenir el toggle default del label
                        e.stopPropagation();
                        
                        console.log('🔓 Click en IA disabled detectado - activando Clips...');
                        
                        // Activar Clips primero
                        if (clipsCheckbox) {
                            clipsCheckbox.checked = true;
                            console.log('  ↪️ Auto-activado Clips por click en IA disabled');
                            
                            // Actualizar estado de sessionStorage para Clips
                            window.lastProcessingOptions = window.lastProcessingOptions || {};
                            window.lastProcessingOptions.generateClips = true;
                            sessionStorage.setItem('processingOptions.generateClips', true);
                        }
                        
                        // Habilitar y marcar IA
                        videoAICheckbox.disabled = false;
                        videoAICheckbox.checked = true;
                        
                        // Guardar estado de IA
                        window.lastProcessingOptions.useAI = true;
                        sessionStorage.setItem('processingOptions.useAI', true);
                        console.log('  ↪️ IA habilitado y marcado');
                        
                        // Sincronizar con ROI si existe
                        const roiCheckbox = document.getElementById('processingUseAI');
                        if (roiCheckbox) {
                            roiCheckbox.checked = true;
                        }
                    }
                }, true);
            }
            
            videoAICheckbox.addEventListener('change', function() {
                console.log('🔄 [VIDEO] Checkbox IA cambió a:', this.checked);
                
                // CRÍTICO: Si se intenta marcar IA sin Clips, activar Clips primero
                const clipsCheckbox = document.getElementById('videoGenerateClipsOption');
                if (this.checked && clipsCheckbox && !clipsCheckbox.checked) {
                    clipsCheckbox.checked = true;
                    console.log('  ↪️ Auto-activado Clips porque se marcó IA');
                }
                
                // Guardar en variable global y sessionStorage
                window.lastProcessingOptions = window.lastProcessingOptions || {};
                window.lastProcessingOptions.useAI = this.checked;
                sessionStorage.setItem('processingOptions.useAI', this.checked);
                
                // Sincronizar con checkbox de ROI si existe
                const roiCheckbox = document.getElementById('processingUseAI');
                if (roiCheckbox) {
                    roiCheckbox.checked = this.checked;
                    console.log('  ↪️ Sincronizado processingUseAI a:', this.checked);
                }
            });
            console.log('✅ Listener agregado a videoUseAiAnalysisOption');
        }
        
        // CRÍTICO: Actualizar estado de dependencias IA/Clips después de restaurar valores
        if (typeof window.initAiClipDependencies === 'function') {
            window.initAiClipDependencies();
            console.log('✅ Dependencias IA/Clips inicializadas para VIDEO');
        }
    }, 100);
}

// Handlers para carpetas
function handleFolderSelect(event) {
    const allFiles = Array.from(event.target.files);
    
    // Filtrar solo archivos que estén directamente en la carpeta raíz (sin subcarpetas)
    const files = allFiles.filter(file => {
        if (!file.webkitRelativePath) {
            // Archivo seleccionado individualmente (sin webkitRelativePath)
            return true;
        }
        // Archivo de carpeta: incluir solo si está en la raíz (tiene exactamente 1 '/')
        // Ejemplo: "carpeta/archivo.mp4" tiene length === 2
        return file.webkitRelativePath.split('/').length === 2;
    });
    
    displaySelectedFiles(files, 'folderFileList', 'folder');
}

function handleFolderDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    
    const items = event.dataTransfer.items;
    const files = [];
    
    for (let i = 0; i < items.length; i++) {
        const item = items[i].webkitGetAsEntry();
        if (item && item.isFile) {
            const file = items[i].getAsFile();
            if (isVideoFile(file.name)) {
                files.push(file);
            }
        }
    }
    
    if (files.length > 0) {
        displaySelectedFiles(files, 'folderFileList', 'folder');
    }
}

// Handlers para videos
function handleVideoSelect(event) {
    const files = Array.from(event.target.files);
    displaySelectedFiles(files, 'videoFileList', 'video');
}

function handleVideoDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    
    const files = Array.from(event.dataTransfer.files).filter(file => 
        isVideoFile(file.name)
    );
    
    if (files.length > 0) {
        displaySelectedFiles(files, 'videoFileList', 'video');
    }
}

// Handlers comunes
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

function isVideoFile(filename) {
    const validExtensions = ['.mp4', '.avi', '.mov', '.dav', '.mkv'];
    return validExtensions.some(ext => filename.toLowerCase().endsWith(ext));
}

function displaySelectedFiles(files, containerId, type) {
    const container = document.getElementById(containerId);
    const videoFiles = files.filter(file => isVideoFile(file.name));
    
    if (videoFiles.length === 0) {
        showNotification('No se encontraron videos válidos', 'warning');
        return;
    }
    
    let html = `
        <div class="file-list-header">
            <h3><i class="fas fa-list"></i> ${videoFiles.length} archivo(s) seleccionado(s)</h3>
        </div>
        <div class="file-list-items">
    `;
    
    videoFiles.forEach(file => {
        const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
        html += `
            <div class="file-item">
                <i class="fas fa-file-video"></i>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${sizeInMB} MB</div>
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
        <button class="btn-upload btn-primary" onclick="uploadFiles('${type}')">
            <i class="fas fa-upload"></i>
            Subir y Analizar (${videoFiles.length} video${videoFiles.length > 1 ? 's' : ''})
        </button>
    `;
    
    container.innerHTML = html;
    container.style.display = 'block';
    
    // Guardar archivos en variable global temporal
    window.selectedFiles = videoFiles;
}

async function uploadFiles(type) {
    if (!window.selectedFiles || window.selectedFiles.length === 0) {
        showNotification('No hay archivos seleccionados', 'error');
        return;
    }
    
    console.log('🚀 [UPLOAD] Iniciando subida con chunking - Archivos:', window.selectedFiles.length);
    
    const progressSection = type === 'folder' ? 'uploadProgressSection' : 'videoUploadProgressSection';
    const progressBar = type === 'folder' ? 'folderUploadProgress' : 'videoUploadProgress';
    const progressText = type === 'folder' ? 'folderUploadText' : 'videoUploadText';
    
    document.getElementById(progressSection).style.display = 'block';
    
    try {
        // Subir archivos con chunking
        // Primer chunk: 5MB (prueba de conexión)
        // Resto de chunks: 20MB
        const FIRST_CHUNK_SIZE = 5 * 1024 * 1024;  // 5MB para prueba
        const CHUNK_SIZE = 20 * 1024 * 1024;       // 20MB para el resto
        console.log(`📦 [UPLOAD] Tamaño primer chunk (prueba): ${FIRST_CHUNK_SIZE / (1024*1024)} MB`);
        console.log(`📦 [UPLOAD] Tamaño resto chunks: ${CHUNK_SIZE / (1024*1024)} MB`);
        
        let totalSize = 0;
        let uploadedSize = 0;
        
        // Calcular tamaño total
        window.selectedFiles.forEach(file => {
            totalSize += file.size;
        });
        
        console.log(`📊 [UPLOAD] Tamaño total: ${(totalSize / (1024*1024)).toFixed(2)} MB`);
        
        // Crear sesión primero
        console.log(`📡 [UPLOAD] Creando sesión...`);
        const sessionResponse = await fetch(buildApiUrl('/api/session/create'), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!sessionResponse.ok) {
            throw new Error(`Error al crear sesión: ${sessionResponse.status}`);
        }
        
        const sessionData = await sessionResponse.json();
        console.log(`✅ [UPLOAD] Sesión creada: ${sessionData.session_id}`);
        
        if (!sessionData.success) {
            throw new Error('Error al crear sesión: ' + (sessionData.error || 'Desconocido'));
        }
        
        const folderId = sessionData.session_id;
        const uploadedFiles = [];
        
        // Subir cada archivo en chunks
        for (let fileIndex = 0; fileIndex < window.selectedFiles.length; fileIndex++) {
            const file = window.selectedFiles[fileIndex];
            
            // Calcular total de chunks: primer chunk de 5MB, el resto de 20MB
            let totalChunks;
            if (file.size <= FIRST_CHUNK_SIZE) {
                totalChunks = 1;
            } else {
                totalChunks = 1 + Math.ceil((file.size - FIRST_CHUNK_SIZE) / CHUNK_SIZE);
            }
            
            console.log(`📤 [UPLOAD] Archivo ${fileIndex + 1}/${window.selectedFiles.length}: ${file.name} - ${totalChunks} chunks`);
            
            const progressBarEl = document.getElementById(progressBar);
            const progressTextEl = document.getElementById(progressText);
            
            let currentPosition = 0;
            
            for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
                const currentChunkSize = (chunkIndex === 0) ? FIRST_CHUNK_SIZE : CHUNK_SIZE;
                const start = currentPosition;
                const end = Math.min(start + currentChunkSize, file.size);
                const chunk = file.slice(start, end);
                currentPosition = end;
                
                const formData = new FormData();
                formData.append('chunk', chunk);
                formData.append('filename', file.name);
                formData.append('chunkIndex', chunkIndex);
                formData.append('totalChunks', totalChunks);
                formData.append('folderId', folderId);
                
                if (chunkIndex === 0) {
                    console.log(`🔍 [UPLOAD] Enviando PRIMER CHUNK (prueba de conexión) - ${(chunk.size / (1024*1024)).toFixed(2)} MB`);
                } else {
                    console.log(`📦 [UPLOAD] Enviando chunk ${chunkIndex + 1}/${totalChunks} - ${(chunk.size / (1024*1024)).toFixed(2)} MB`);
                }
                
                // Subir chunk
                const chunkResponse = await fetch(buildApiUrl('/api/upload/chunk'), {
                    method: 'POST',
                    body: formData
                });
                
                if (!chunkResponse.ok) {
                    throw new Error(`Error al subir chunk ${chunkIndex + 1}/${totalChunks}: ${chunkResponse.status}`);
                }
                
                const chunkData = await chunkResponse.json();
                
                if (!chunkData.success) {
                    throw new Error(chunkData.error || 'Error al subir chunk');
                }
                
                // Si es el último chunk, guardar info del archivo
                if (chunkData.complete) {
                    console.log(`✅ [UPLOAD] Archivo completo: ${file.name}`);
                    console.log(`✅ [UPLOAD] Nombre sanitizado en servidor: ${chunkData.filename}`);
                    uploadedFiles.push({
                        name: chunkData.filename,  // Usar nombre sanitizado del servidor
                        originalName: file.name,    // Guardar nombre original también
                        path: chunkData.filepath,
                        is_duplicate: chunkData.is_duplicate || false
                    });
                }
                
                // Actualizar progreso
                uploadedSize += (end - start);
                const percentComplete = Math.round((uploadedSize / totalSize) * 100);
                
                if (progressBarEl) {
                    progressBarEl.style.width = percentComplete + '%';
                    progressBarEl.textContent = percentComplete + '%';
                }
                
                if (progressTextEl) {
                    progressTextEl.textContent = `Subiendo ${file.name}... ${percentComplete}%`;
                }
                
                console.log(`📊 [UPLOAD] Progreso: ${percentComplete}%`);
            }
        }
        
        // Finalizar subida
        console.log(`🎉 [UPLOAD] Subida completa - ${uploadedFiles.length} archivos`);
        showNotification('✓ Videos subidos correctamente. Configura el área de análisis...', 'success');
        
        // Guardar folder_id para usar después
        window.pendingFolderId = folderId;
        window.pendingFolderPath = sessionData.session_folder;
        
        // Mostrar vista de selección de ROI
        showROISelectionForProcessing(sessionData.session_folder, uploadedFiles);
        
    } catch (error) {
        console.error('❌ [UPLOAD] Error:', error);
        showNotification('Error al subir archivos: ' + error.message, 'error');
        document.getElementById(progressSection).style.display = 'none';
    }
}

async function startProcessing(videoIds, folderId) {
    console.log('🎬 startProcessing llamado con:', { videoIds, folderId });
    
    // Cambiar a vista de estado de análisis
    loadView('process', null);
    
    // Obtener configuración ROI
    const roi = window.currentROI || [0, 0, 640, 480];
    console.log('📍 ROI configurado:', roi);
    
    // Obtener opciones de procesamiento desde cualquier vista (index, folder, video, processing ROI)
    const generateClips = 
        document.getElementById('processingGenerateClips')?.checked ?? 
        document.getElementById('generateClipsOption')?.checked ?? 
        document.getElementById('folderGenerateClipsOption')?.checked ?? 
        document.getElementById('videoGenerateClipsOption')?.checked ?? 
        window.processingOptions?.generateClips ?? 
        true;
    
    const useAiAnalysis = 
        document.getElementById('processingUseAI')?.checked ?? 
        document.getElementById('useAiAnalysisOption')?.checked ?? 
        document.getElementById('folderUseAiAnalysisOption')?.checked ?? 
        document.getElementById('videoUseAiAnalysisOption')?.checked ?? 
        window.processingOptions?.useAI ?? 
        true;
    
    console.log('🔍 Valores de checkboxes:');
    console.log('  - processingGenerateClips:', document.getElementById('processingGenerateClips')?.checked);
    console.log('  - generateClipsOption:', document.getElementById('generateClipsOption')?.checked);
    console.log('  - window.processingOptions.generateClips:', window.processingOptions?.generateClips);
    console.log('  - FINAL generateClips:', generateClips);
    console.log('  - processingUseAI:', document.getElementById('processingUseAI')?.checked);
    console.log('  - useAiAnalysisOption:', document.getElementById('useAiAnalysisOption')?.checked);
    console.log('  - window.processingOptions.useAI:', window.processingOptions?.useAI);
    console.log('  - FINAL useAiAnalysis:', useAiAnalysis);
    
    // Mostrar modo seleccionado
    let mode = 'Solo movimiento';
    if (generateClips && useAiAnalysis) {
        mode = 'Completo (movimiento + clips + IA)';
    } else if (generateClips) {
        mode = 'Movimiento + clips (sin IA)';
    }
    
    console.log(`🎬 Modo de análisis: ${mode}`);
    
    console.log('📡 Enviando request a /api/process con:', {
        folder_id: folderId,
        roi: roi,
        generate_clips: generateClips,
        use_ai_analysis: useAiAnalysis
    });
    
    try {
        const response = await fetch(buildApiUrl('/api/process'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                folder_id: folderId,
                roi: roi,
                generate_clips: generateClips,
                use_ai_analysis: useAiAnalysis
            })
        });
        
        const data = await response.json();
        console.log('✅ Respuesta de /api/process:', data);
        
        if (data.success) {
            const queuePosition = data.queue_position || 1;
            if (queuePosition > 1) {
                showNotification(`✓ Tarea agregada a la cola (Posición #${queuePosition})`, 'success');
            } else {
                showNotification(`✓ Procesamiento iniciado en modo: ${mode}`, 'success');
            }

            // Reset hash para forzar actualización inmediata
            lastStatusHash = null;
            
            // Mostrar vista de procesamiento activo con datos iniciales
            const activeStatus = {
                is_processing: true,
                current_video: 'Iniciando...',
                progress: 0,
                total_videos: 0,
                status_message: 'Iniciando análisis...'
            };
            showActiveProcessingView(activeStatus);
            
            // Iniciar polling de estado
            startProcessingPolling();
            
            // Actualizar inmediatamente con datos reales del servidor
            setTimeout(async () => {
                try {
                    const response = await fetch(buildApiUrl('/api/processing-status'));
                    const realStatus = await response.json();
                    if (realStatus.is_processing) {
                        showActiveProcessingView(realStatus);
                    }
                } catch (error) {
                    console.error('Error obteniendo estado inicial:', error);
                }
            }, 500); // Esperar 500ms para que el servidor actualice el estado
        } else {
            throw new Error(data.error || 'Error al iniciar procesamiento');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al iniciar procesamiento: ' + error.message, 'error');
    }
}

// Polling de estado del procesamiento
let processingPollingInterval = null;
let lastStatusHash = null; // Para detectar cambios

function startProcessingPolling() {
    processingPollingInterval = setInterval(async () => {
        try {
            const response = await fetch(buildApiUrl('/api/processing-status'));
            const status = await response.json();
            
            // Calcular hash del estado para detectar cambios
            const currentHash = JSON.stringify({
                is_processing: status.is_processing,
                current_folder: status.current_folder,
                total_videos: status.total_videos,
                completed_tasks_count: status.completed_tasks ? status.completed_tasks.length : 0,
                queue_pending: status.queue ? status.queue.pending_jobs : 0
            });
            
            // Si el estado cambió, actualizar inmediatamente
            if (lastStatusHash !== currentHash) {
                console.log('🔄 Estado cambió, actualizando vista inmediatamente');
                lastStatusHash = currentHash;
                showActiveProcessingView(status);
            }
            
            updateProcessingStatus(status);
            
            // Mostrar información de cola si hay trabajos pendientes
            if (status.queue && status.queue.pending_jobs > 0) {
                const queueInfo = document.getElementById('queueInfo');
                if (queueInfo) {
                    queueInfo.textContent = `Cola: ${status.queue.pending_jobs} trabajo(s) pendiente(s)`;
                    queueInfo.style.display = 'block';
                }
            }
            
            if (!status.is_processing) {
                clearInterval(processingPollingInterval);
                processingPollingInterval = null;
                lastStatusHash = null; // Reset
                onProcessingCompleted(status);
            }
        } catch (error) {
            console.error('Error al obtener estado:', error);
        }
    }, 1000); // Reducir a 1 segundo para actualizaciones más rápidas
}

function updateProcessingStatus(status) {
    // Solo actualizar contadores, sin barras de progreso ni mensajes detallados
    const videosProcessed = document.getElementById('videosProcessed');
    const motionEventsDetected = document.getElementById('motionEventsDetected');
    const clipsGenerated = document.getElementById('clipsGenerated');
    const objectsDetected = document.getElementById('objectsDetected');
    
    // Actualizar contador de videos procesados (del trabajo ACTUAL, no acumulado)
    if (videosProcessed) {
        const processedInJob = status.videos_processed_in_job || 0;  // Videos completados en el trabajo actual
        const totalInJob = status.total_videos || 0;  // Total de videos en el trabajo actual
        
        if (totalInJob > 0) {
            videosProcessed.textContent = `${processedInJob}/${totalInJob}`;
        } else {
            videosProcessed.textContent = '0';
        }
    }
    
    if (motionEventsDetected) {
        motionEventsDetected.textContent = status.motion_events_detected || 0;
    }
    
    if (clipsGenerated) {
        clipsGenerated.textContent = status.clips_generated || 0;
    }
    
    if (objectsDetected) {
        objectsDetected.textContent = status.objects_detected || 0;
    }
    
    // El spinner sigue girando automáticamente por CSS, no necesita actualización
}

function onProcessingCompleted(status) {
    if (!completedNotificationShown) {
        showNotification('✓ ¡Procesamiento completado!', 'success');
        completedNotificationShown = true;
    }
    const isInProcessView = appState.currentView === 'process';
    if (isInProcessView) {
        showCompletedView(status);
    }

    // NO resetear processing_status aquí para evitar vistas fantasma
    // El estado se reseteará solo cuando el usuario navegue manualmente

    updateAnalysisBadge(status);

    // Reset hash para la próxima tarea
    lastStatusHash = null;
}

async function showProcessView() {
    updateViewTitle('📊 Estado de Análisis');

    // Limpiar el flag de completado al ENTRAR a la vista
    // Esto evita que se quede atascado en la vista de completado
    console.log('🔄 Entrando a la vista de análisis, limpiando flag de completado...');
    await clearCompletedFlagSilent();

    // Resetear hash de estado para forzar actualización cuando se vuelve a la vista
    lastStatusHash = null;

    // Ocultar tick verde del sidebar (el usuario ya está viendo la vista)
    const spinner = document.getElementById('analysisSpinner');
    if (spinner) {
        spinner.style.display = 'none';
    }

    // MOSTRAR VISTA INICIAL INMEDIATAMENTE para evitar pantalla vacía
    showNoProcessingView();

    // Verificar si venimos de iniciar un procesamiento (parámetro en URL)
    const urlParams = new URLSearchParams(window.location.search);
    const isStarting = urlParams.get('processing') === 'starting';

    if (isStarting) {
        console.log('🚀 Procesamiento recién iniciado, mostrando vista de inicio...');

        // Limpiar el parámetro de la URL
        window.history.replaceState({}, '', '/');

        // Mostrar vista de "iniciando procesamiento" inmediatamente
        showStartingProcessingView();

        // Esperar un momento y luego verificar el estado real
        setTimeout(() => {
            checkProcessingStatus();
        }, 2000); // Dar tiempo al servidor para actualizar el estado
    } else {
        // Verificar estado normal - NO mostrar completado automáticamente al entrar a la vista
        // Dar un pequeño delay para que el servidor actualice el estado después de limpiar el flag
        setTimeout(() => {
            checkProcessingStatus(false); // false = no mostrar completado automáticamente
        }, 500);
    }
}

function showStartingProcessingView() {
    const content = `
        <div class="processing-container">
            <div class="processing-card">
                <h2><i class="fas fa-play-circle"></i> Iniciando Análisis</h2>
                
                <div class="processing-info-card">
                    <div class="processing-spinner">
                        <i class="fas fa-circle-notch fa-spin" style="font-size: 3rem; color: var(--primary-color);"></i>
                    </div>
                    <p style="margin-top: 20px; font-size: 1.1rem;">
                        <i class="fas fa-rocket"></i> Preparando el procesamiento...
                    </p>
                    <p style="margin-top: 10px; color: var(--text-secondary);">
                        El análisis comenzará en unos momentos
                    </p>
                </div>
                
                <div class="processing-stats-grid" style="margin-top: 30px;">
                    <div class="processing-stat-box">
                        <div class="stat-icon"><i class="fas fa-video"></i></div>
                        <div class="stat-value" id="videosProcessed">0</div>
                        <div class="stat-label">Videos procesados</div>
                    </div>
                    <div class="processing-stat-box">
                        <div class="stat-icon"><i class="fas fa-running"></i></div>
                        <div class="stat-value" id="motionEventsDetected">0</div>
                        <div class="stat-label">Movimientos</div>
                    </div>
                    <div class="processing-stat-box">
                        <div class="stat-icon"><i class="fas fa-cut"></i></div>
                        <div class="stat-value" id="clipsGenerated">0</div>
                        <div class="stat-label">Clips generados</div>
                    </div>
                    <div class="processing-stat-box">
                        <div class="stat-icon"><i class="fas fa-brain"></i></div>
                        <div class="stat-value" id="objectsDetected">0</div>
                        <div class="stat-label">Objetos IA</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
}

async function checkProcessingStatus(autoShowCompleted = true) {
    try {
        const response = await fetch(buildApiUrl('/api/processing-status'));
        const status = await response.json();
        console.log('📊 Estado de procesamiento:', status);
        updateAnalysisBadge(status);
        const isInProcessView = appState.currentView === 'process';
        if (status.just_completed) {
            // Procesamiento acaba de completarse - mostrar vista de completado
            clearInterval(processingPollingInterval);
            processingPollingInterval = null;
            completedNotificationShown = false; // Reset para la próxima tarea
            console.log('✅ Procesamiento completado');
            if (autoShowCompleted && isInProcessView) {
                onProcessingCompleted(status);
            }
        } else if (!status.is_processing) {
            // No hay procesamiento activo (nunca empezó o ya terminó) - mostrar vista de "no hay análisis"
            clearInterval(processingPollingInterval);
            processingPollingInterval = null;
            completedNotificationShown = false; // Reset para la próxima tarea
            if (isInProcessView) {
                showNoProcessingView();
            }
        } else {
            // Procesamiento activo - mostrar vista correspondiente
            if (isInProcessView) {
                // Calcular hash del estado para detectar cambios
                const currentHash = JSON.stringify({
                    is_processing: status.is_processing,
                    current_folder: status.current_folder,
                    total_videos: status.total_videos,
                    completed_tasks_count: status.completed_tasks ? status.completed_tasks.length : 0,
                    queue_pending: status.queue ? status.queue.pending_jobs : 0
                });
                
                // Si el estado cambió o es la primera vez, actualizar vista
                if (lastStatusHash !== currentHash || !lastStatusHash) {
                    console.log('🔄 Estado cambió en checkProcessingStatus, actualizando vista');
                    lastStatusHash = currentHash;
                    showActiveProcessingView(status);
                }
                
                // IMPORTANTE: Iniciar polling si no está activo y hay procesamiento
                if (!processingPollingInterval) {
                    console.log('🔄 Iniciando polling de procesamiento desde checkProcessingStatus');
                    startProcessingPolling();
                }
            }
        }
    } catch (error) {
        console.error('Error al verificar estado:', error);
        if (appState.currentView === 'process') {
            showNoProcessingView();
        }
    }
}

/**
 * Actualiza el badge visual en la sección ANÁLISIS del sidebar
 */
function updateAnalysisBadge(status) {
    const spinner = document.getElementById('analysisSpinner');
    if (!spinner) return;
    
    const isInProcessView = appState.currentView === 'process';
    
    if (status.is_processing) {
        // Procesamiento activo: Mostrar spinner (girando)
        spinner.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        spinner.style.display = 'inline-block';
        spinner.style.color = 'var(--primary-color)';
    } else if (status.just_completed && !isInProcessView) {
        // Completado Y usuario NO está en la vista de análisis: Mostrar tick verde
        spinner.innerHTML = '<i class="fas fa-check-circle"></i>';
        spinner.style.display = 'inline-block';
        spinner.style.color = 'var(--success-color)';
    } else {
        // Sin procesamiento o usuario está en la vista (ya vio el resumen): Ocultar badge
        spinner.style.display = 'none';
    }
}

function showNoProcessingView() {
    const content = `
        <div class="no-processing-container">
            <div class="no-processing-card">
                <div class="no-processing-icon">
                    <i class="fas fa-inbox"></i>
                </div>
                
                <h2>No hay análisis en proceso</h2>
                <p class="no-processing-description">
                    Selecciona videos o una carpeta para iniciar un nuevo análisis
                </p>
                
                <div class="action-buttons-row">
                    <button class="btn-action btn-green" onclick="loadView('select-folder', event)">
                        <i class="fas fa-folder-open"></i>
                        Seleccionar Carpeta
                    </button>
                    <button class="btn-action btn-orange" onclick="loadView('select-video', event)">
                        <i class="fas fa-video"></i>
                        Seleccionar Video
                    </button>
                </div>
                
                <div class="quick-info">
                    <div class="info-box">
                        <i class="fas fa-info-circle"></i>
                        <p>Una vez que subas videos, el análisis comenzará automáticamente y podrás ver el progreso aquí.</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
}

function showCompletedView(status) {
    const content = `
        <div class="no-processing-container">
            <div class="no-processing-card completed-card">
                <div class="completed-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                
                <h2>¡Procesamiento Completado!</h2>
                <p class="no-processing-description">
                    El análisis ha finalizado exitosamente
                </p>
                
                <div class="completed-stats">
                    <div class="completed-stat-row">
                        <span class="stat-icon">📹</span>
                        <span class="stat-text">${status.total_videos_processed_all || status.total_videos_processed || 0} videos procesados</span>
                    </div>
                    <div class="completed-stat-row">
                        <span class="stat-icon">🔍</span>
                        <span class="stat-text">${status.motion_events_detected_all || status.motion_events_detected || 0} movimientos detectados</span>
                    </div>
                    <div class="completed-stat-row">
                        <span class="stat-icon">✂️</span>
                        <span class="stat-text">${status.clips_generated_all || status.clips_generated || 0} clips generados</span>
                    </div>
                    <div class="completed-stat-row">
                        <span class="stat-icon">🤖</span>
                        <span class="stat-text">${status.objects_detected_all || status.objects_detected || 0} objetos detectados</span>
                    </div>
                </div>
                
                <div class="action-buttons-row" style="margin-top: 30px;">
                    <button class="btn-action btn-primary" onclick="clearCompletedFlag(); loadView('folders', event);">
                        <i class="fas fa-folder"></i>
                        Ver Carpetas y Videos
                    </button>
                    <button class="btn-action btn-green" onclick="clearCompletedFlag(); loadView('select-video', event);">
                        <i class="fas fa-plus"></i>
                        Analizar Más Videos
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // NO limpiar el flag automáticamente, solo cuando el usuario haga clic
    console.log('✅ Vista de completado mostrada');
}

async function clearCompletedFlag() {
    // Limpiar el flag de completado SOLO cuando el usuario hace clic en un botón
    try {
        console.log('🧹 Limpiando flag de completado (acción manual del usuario)...');
        await fetch(buildApiUrl('/api/clear-completed-flag'), { method: 'POST' });
        updateSidebarCompletedBadge(false);

        // Resetear estado local de procesamiento cuando el usuario navega manualmente
        processing_status = {
            is_processing: false,
            current_video: '',
            progress: 0,
            total_videos: 0,
            status_message: '',
            motion_events_detected: 0,
            clips_generated: 0,
            objects_detected: 0,
            just_completed: false,
            completed_tasks: [],
            last_completed: null
        };

        // Resetear flag de notificación para la próxima tarea
        completedNotificationShown = false;

        // NO verificar estado automáticamente para evitar cambios de vista inesperados
        // Los botones de navegación manejarán el cambio de vista directamente
    } catch (error) {
        console.error('Error al limpiar flag:', error);
    }
}

async function clearCompletedFlagSilent() {
    // Limpiar el flag de completado SILENCIOSAMENTE (sin logs ni redirección)
    // Se usa cuando el usuario navega a otra vista
    try {
        await fetch(buildApiUrl('/api/clear-completed-flag'), { method: 'POST' });
        updateSidebarCompletedBadge(false);

        // NO resetear processing_status aquí para evitar problemas de estado
        // El estado se manejará apropiadamente en las funciones que lo necesiten
    } catch (error) {
        // Silenciar errores
    }
}

function updateSidebarCompletedBadge(show) {
    // Buscar el botón de Estado de Análisis en el sidebar
    const sidebarButtons = document.querySelectorAll('.sidebar-btn');
    
    sidebarButtons.forEach(btn => {
        const text = btn.textContent.toLowerCase();
        if (text.includes('estado') && text.includes('análisis')) {
            // Remover badge existente si hay
            const existingBadge = btn.querySelector('.completed-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
            
            // Agregar nuevo badge si es necesario
            if (show) {
                const badge = document.createElement('span');
                badge.className = 'completed-badge';
                badge.textContent = '✓';
                badge.title = 'Procesamiento completado';
                btn.appendChild(badge);
                
                // Hacer que el botón parpadee suavemente
                btn.classList.add('pulse-animation');
                setTimeout(() => {
                    btn.classList.remove('pulse-animation');
                }, 3000);
            }
        }
    });
}

function showActiveProcessingView(status) {
    console.log('🔄 showActiveProcessingView llamado con:', {
        current_folder: status.current_folder,
        total_videos: status.total_videos,
        total_videos_in_queue: status.total_videos_in_queue,
        completed_tasks: status.completed_tasks ? status.completed_tasks.length : 0,
        queue_pending: status.queue ? status.queue.pending_jobs : 0
    });
    
    // Generar lista de tareas en cola (INCLUYENDO la tarea actual Y completadas)
    let queueHTML = '';
    
    // Total de tareas: completadas + (actual si está procesando) + pendientes
    const currentTaskCount = status.is_processing ? 1 : 0;
    const totalTasks = (status.completed_tasks ? status.completed_tasks.length : 0) + currentTaskCount + (status.queue ? status.queue.pending_jobs : 0);
    
    if (totalTasks > 0) {
        // Crear array con todas las tareas: completadas + actual + pendientes
        let allTasks = [];
        
        // Tareas completadas PRIMERO
        if (status.completed_tasks && status.completed_tasks.length > 0) {
            status.completed_tasks.forEach((task, idx) => {
                allTasks.push({
                    position: idx + 1,
                    folder_name: task.folder_name,
                    video_count: task.video_count,
                    is_current: false,
                    is_completed: true,
                    generate_clips: task.generate_clips,
                    use_ai_analysis: task.use_ai_analysis,
                    completed_at: task.completed_at
                });
            });
        }
        
        // Tarea actual (en procesamiento) - SOLO si realmente está procesando
        if (status.is_processing) {
            const currentPosition = (status.completed_tasks ? status.completed_tasks.length : 0) + 1;
            allTasks.push({
                position: currentPosition,
                folder_name: status.current_folder || 'Procesando...',
                video_count: status.total_videos || 1,
                is_current: true,
                is_completed: false
            });
        }
        
        // Tareas pendientes en cola
        if (status.queue && status.queue.tasks && status.queue.tasks.length > 0) {
            const nextPosition = allTasks.length + 1;  // Posición después de las completadas y la actual (si existe)
            allTasks = allTasks.concat(status.queue.tasks.map((task, idx) => ({
                ...task,
                position: nextPosition + idx,
                is_current: false,
                is_completed: false
            })));
        }
        
        console.log('📋 Lista de tareas construida:', allTasks.map(t => `${t.position}: ${t.folder_name} (${t.video_count} videos) ${t.is_current ? '[CURRENT]' : t.is_completed ? '[DONE]' : '[PENDING]'}`));
        
        queueHTML = `
            <div class="queue-info-panel">
                <h3><i class="fas fa-list"></i> Tareas (${totalTasks})</h3>
                <div class="queue-tasks-list">
                    ${allTasks.map(task => `
                        <div class="queue-task-item ${task.is_current ? 'current-task' : ''} ${task.is_completed ? 'completed-task' : ''}">
                            <div class="task-position">${task.is_current ? '▶' : task.is_completed ? '✓' : '#'}${task.position}</div>
                            <div class="task-details">
                                <div class="task-name">${task.folder_name}</div>
                                <div class="task-meta">
                                    <span><i class="fas fa-video"></i> ${task.video_count} videos</span>
                                    ${task.is_current ? '<span class="current-badge">En proceso</span>' : ''}
                                    ${task.is_completed ? '<i class="fas fa-check-circle" style="color: var(--success-color); font-size: 1.2rem;"></i>' : ''}
                                    ${!task.is_current && !task.is_completed && task.generate_clips ? '<span><i class="fas fa-cut"></i> Clips</span>' : ''}
                                    ${!task.is_current && !task.is_completed && task.use_ai_analysis ? '<span><i class="fas fa-brain"></i> IA</span>' : ''}
                                    ${task.is_completed && task.generate_clips ? '<span><i class="fas fa-cut"></i> Clips</span>' : ''}
                                    ${task.is_completed && task.use_ai_analysis ? '<span><i class="fas fa-brain"></i> IA</span>' : ''}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    const content = `
        <div class="processing-container">
            <div class="processing-card">
                <div class="processing-icon">
                    <i class="fas fa-cog fa-spin"></i>
                </div>
                
                <h2>Analizando: ${status.current_folder || 'Videos'}</h2>
                <p class="processing-description">
                    ${status.current_video || 'Procesando videos...'}
                    ${status.total_videos > 0 ? `<br><small>Total: ${status.videos_processed_in_job || 0}/${status.total_videos} videos</small>` : ''}
                </p>
                
                <div class="processing-stats">
                    <div class="stat-item">
                        <div class="stat-value" id="videosProcessed">0</div>
                        <div class="stat-label">Videos Procesados</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="motionEventsDetected">0</div>
                        <div class="stat-label">Movimientos Detectados</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="clipsGenerated">0</div>
                        <div class="stat-label">Clips Generados</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="objectsDetected">0</div>
                        <div class="stat-label">Objetos Detectados</div>
                    </div>
                </div>
            </div>
            
            ${queueHTML}
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Actualizar con el estado actual
    updateProcessingStatus(status);
}

function showROIConfigView() {
    updateViewTitle('🕐 Configurar Zona de Hora');
    
    const content = `
        <div class="roi-config-container">
            <!-- Layout de una sola columna -->
            <div class="roi-single-column">
                <!-- Área de carga de video -->
                <div class="video-upload-button-area" id="videoUploadArea">
                    <i class="fas fa-video" style="font-size: 3rem; color: var(--secondary-color); margin-bottom: 15px;"></i>
                    <h3 style="color: var(--dark-text); margin-bottom: 10px;">Subir Video de Referencia</h3>
                    <p class="upload-hint">Sube un video para extraer un frame y definir la zona de hora</p>
                    <button class="btn btn-primary" onclick="document.getElementById('roiVideoInput').click()" style="margin-top: 20px;">
                        <i class="fas fa-upload"></i> Seleccionar Video
                    </button>
                    <input type="file" id="roiVideoInput" accept=".mp4,.avi,.mov,.dav,.mkv" style="display: none;" onchange="loadROIVideo(event)">
                </div>
                
                <!-- Coordenadas ARRIBA del video (oculto inicialmente) -->
                <div class="roi-coordinates-section" id="coordinatesSection" style="display: none;">
                    <h3><i class="fas fa-ruler-combined"></i> Coordenadas de la Zona</h3>
                    <div class="roi-controls">
                        <div class="form-group">
                            <label>Posición X:</label>
                            <input type="number" id="roiX" class="form-control" value="0" min="0" oninput="updateROIPreview()">
                        </div>
                        <div class="form-group">
                            <label>Posición Y:</label>
                            <input type="number" id="roiY" class="form-control" value="0" min="0" oninput="updateROIPreview()">
                        </div>
                        <div class="form-group">
                            <label>Ancho (W):</label>
                            <input type="number" id="roiW" class="form-control" value="200" min="1" oninput="updateROIPreview()">
                        </div>
                        <div class="form-group">
                            <label>Alto (H):</label>
                            <input type="number" id="roiH" class="form-control" value="80" min="1" oninput="updateROIPreview()">
                        </div>
                    </div>
                    
                    <!-- Botones de acción DEBAJO de las coordenadas -->
                    <div class="roi-actions-horizontal" style="margin-top: 20px;">
                        <button class="btn btn-success" onclick="saveROIConfig()" style="flex: 1;">
                            <i class="fas fa-save"></i> Guardar Configuración
                        </button>
                        <button class="btn btn-secondary" onclick="resetROIConfig()" style="flex: 1;">
                            <i class="fas fa-undo"></i> Restablecer Valores
                        </button>
                    </div>
                    
                    <div class="roi-saved-config" id="savedConfigCard" style="display: none; margin-top: 15px;">
                        <h4><i class="fas fa-check-circle" style="color: var(--success-color);"></i> Configuración Guardada</h4>
                        <p id="savedConfigText" style="font-size: 0.85rem; color: var(--light-text); margin: 10px 0 0 0;"></p>
                    </div>
                </div>
                
                <!-- Canvas para dibujar ROI (oculto inicialmente) -->
                <div id="canvasArea" style="display: none;">
                    <div class="canvas-wrapper">
                        <canvas id="roiCanvas" width="1000" height="600"></canvas>
                        <div class="canvas-instructions">
                            <i class="fas fa-mouse-pointer"></i>
                            <span>Arrastra con el mouse para dibujar la zona de hora</span>
                        </div>
                    </div>
                    
                    <div class="video-controls" style="margin-top: 15px;">
                        <button class="btn-icon" id="playPauseBtn" onclick="pauseROIVideo()" title="Reproducir/Pausar">
                            <i class="fas fa-play"></i>
                        </button>
                        <input type="range" id="videoSeekBar" min="0" max="100" value="0" style="flex: 1;">
                        <button class="btn-icon" onclick="captureFrame()" title="Capturar frame actual">
                            <i class="fas fa-camera"></i>
                        </button>
                        <button class="btn-icon btn-danger" onclick="clearROI()" title="Limpiar y reiniciar">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Inicializar canvas
    initROICanvas();
    
    // Cargar configuración guardada
    loadROIConfig();
}

function showAdvancedConfigView() {
    updateViewTitle('⚙️ Configuración Avanzada');
    
    const content = `
        <div class="config-container">
            <div class="config-card">
                <h2><i class="fas fa-cog"></i> Parámetros de Detección de Movimiento</h2>
                <p class="config-description">
                    Ajusta los parámetros para optimizar la detección según tus necesidades
                </p>
                
                <div class="advanced-settings">
                    <div class="setting-group">
                        <label>Umbral de Porcentaje de Cambio:</label>
                        <input type="number" id="thresholdPercentage" value="0.5" step="0.1" min="0.1" max="10" class="form-control">
                        <small>Porcentaje mínimo de cambio en la imagen para detectar movimiento</small>
                    </div>
                    
                    <div class="setting-group">
                        <label>Umbral de Varianza:</label>
                        <input type="number" id="varThreshold" value="16" step="1" min="1" max="100" class="form-control">
                        <small>Sensibilidad del algoritmo de sustracción de fondo</small>
                    </div>
                    
                    <div class="setting-group">
                        <label>Tiempo de Enfriamiento (ms):</label>
                        <input type="number" id="cooldownMs" value="8000" step="1000" min="1000" max="60000" class="form-control">
                        <small>Tiempo mínimo entre detecciones consecutivas</small>
                    </div>
                    
                    <div class="setting-group" id="localFolderSettingGroup" style="display:none">
                        <label>
                            <input type="checkbox" id="duplicateFiles" checked>
                            Duplicar archivos al seleccionar carpeta local
                        </label>
                        <small>Si está desactivado, los videos se analizarán desde su ubicación original sin copiarlos</small>
                    </div>
                </div>
                
                <div class="config-actions">
                    <button class="btn-config btn-primary" onclick="saveAdvancedConfig()">
                        <i class="fas fa-save"></i>
                        Guardar Configuración
                    </button>
                    <button class="btn-config btn-secondary" onclick="resetAdvancedConfig()">
                        <i class="fas fa-undo"></i>
                        Valores por Defecto
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Mostrar opción de carpeta local solo en Electron
    console.log('🔍 Verificando si mostrar opción de carpeta local...', { isElectronApp });
    if (isElectronApp) {
        const localFolderSetting = document.getElementById('localFolderSettingGroup');
        if (localFolderSetting) {
            console.log('✅ Mostrando opción de carpeta local en Configuración Avanzada');
            localFolderSetting.style.display = 'block';
        } else {
            console.error('❌ No se encontró el elemento localFolderSettingGroup');
        }
    } else {
        console.log('ℹ️ No es Electron, ocultando opción de carpeta local');
    }
    
    // Cargar configuración guardada
    loadAdvancedConfig();
}

function showExcelView() {
    updateViewTitle('<i class="fas fa-file-excel"></i> Excel de Sesión');
    
    const content = `
        <div class="excel-container">
            <!-- Header compacto con todos los controles en una línea -->
            <div class="excel-config-header">
                <div class="excel-config-row">
                    <div class="config-group">
                        <label><i class="fas fa-text-height"></i> Fuente:</label>
                        <select id="excelFontSize" onchange="updateExcelFontSize(this.value)">
                            <option value="10">10px</option>
                            <option value="11">11px</option>
                            <option value="12" selected>12px</option>
                            <option value="14">14px</option>
                            <option value="16">16px</option>
                            <option value="18">18px</option>
                        </select>
                    </div>
                    
                    <div class="config-group">
                        <label><i class="fas fa-border-all"></i> Bordes:</label>
                        <select id="excelBorders" onchange="updateExcelBorders(this.value)">
                            <option value="all" selected>Todos</option>
                            <option value="none">Ninguno</option>
                            <option value="minimal">Mínimo</option>
                        </select>
                    </div>
                    
                    <div class="config-group">
                        <label><i class="fas fa-layer-group"></i> Hoja:</label>
                        <select id="sheetDropdown" onchange="switchSheet(this.value)">
                            <option value="">Seleccionar hoja...</option>
                        </select>
                    </div>
                    
                    <div class="config-group">
                        <button class="btn btn-success" id="saveExcelBtn" onclick="saveExcelChanges()" disabled>
                            <i class="fas fa-save"></i> Guardar
                        </button>
                    </div>
                    
                    <div class="config-group">
                        <button class="btn btn-primary" id="downloadExcelBtn" onclick="downloadExcelFile()" disabled>
                            <i class="fas fa-download"></i> Descargar
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Contenedor del editor Handsontable -->
            <div id="excelEditor" class="excel-editor" style="display: none;"></div>
            
            <!-- Mensaje cuando no hay Excel cargado -->
            <div id="excelPlaceholder" class="excel-placeholder">
                <i class="fas fa-file-excel" style="font-size: 3rem; color: var(--light-text);"></i>
                <p>Excel se actualiza automáticamente con cada análisis</p>
                <small>Los datos se cargan al abrir esta vista</small>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Cargar Excel de sesión automáticamente
    loadSessionExcel();
    
    // Agregar atajo de teclado Ctrl+S para guardar
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.getElementById('saveExcelBtn');
            if (saveBtn && !saveBtn.disabled) {
                saveExcelChanges();
            }
        }
    });
}

// Cargar estadísticas para el dashboard
async function loadDashboardStats() {
    try {
        const response = await fetch(buildApiUrl('/api/stats'));
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            // Actualizar números
            document.getElementById('totalFolders').textContent = stats.total_folders;
            document.getElementById('totalVideos').textContent = stats.total_videos;
            document.getElementById('totalClips').textContent = stats.total_clips;
            document.getElementById('totalObjects').textContent = 
                stats.objects.reduce((sum, obj) => sum + obj.count, 0);
            
            // Crear gráfico
            createDashboardChart(stats.objects);
            
            // Cargar lista de carpetas
        }
    } catch (error) {
        console.error('Error al cargar estadísticas:', error);
        showNotification('Error al cargar estadísticas', 'error');
    }
}

// Crear gráfico para el dashboard
function createDashboardChart(objects) {
    const ctx = document.getElementById('objectsChart');
    if (!ctx) return;
    
    const labels = objects.map(obj => obj.type || 'Desconocido');
    const values = objects.map(obj => obj.count);
    
    const colors = [
        '#3498DB', '#E74C3C', '#27AE60', '#F39C12', 
        '#9B59B6', '#1ABC9C', '#E67E22', '#95A5A6'
    ];
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Objetos Detectados',
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: colors.slice(0, labels.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Variables globales para el editor Excel
let currentExcelData = null;
let currentFolderId = null;
let currentSheetName = null;
let hot = null; // Instancia de Handsontable

// Cargar lista de archivos Excel disponibles (ahora solo el consolidado de sesión)
async function loadExcelFilesList() {
    const selector = document.getElementById('excelSelector');
    
    try {
        const response = await fetch(buildApiUrl('/api/excel/list'));
        const data = await response.json();
        
        if (!data.success) {
            console.error('Error cargando lista de Excel:', data.error);
            return;
        }
        
        // Limpiar opciones existentes
        selector.innerHTML = '<option value="">Seleccionar archivo Excel...</option>';
        
        // Agregar el Excel consolidado si existe
        if (data.excel_files && data.excel_files.length > 0) {
            const excel = data.excel_files[0]; // Solo hay uno ahora
            const option = document.createElement('option');
            option.value = 'session'; // Usar 'session' en lugar de folder_id
            option.textContent = `${excel.filename} (${excel.size} bytes)`;
            option.dataset.filename = excel.filename;
            selector.appendChild(option);
        } else {
            selector.innerHTML = '<option value="">No hay Excel consolidado disponible</option>';
        }
        
    } catch (error) {
        console.error('Error cargando lista de Excel:', error);
        selector.innerHTML = '<option value="">Error al cargar archivos Excel</option>';
    }
}

// Cargar Excel seleccionado (ahora solo el consolidado de sesión)
async function loadSelectedExcel() {
    const selector = document.getElementById('excelSelector');
    const selectedValue = selector.value;
    
    if (!selectedValue || selectedValue !== 'session') {
        showNotification('Selecciona el Excel consolidado de sesión', 'warning');
        return;
    }
    
    const selectedOption = selector.options[selector.selectedIndex];
    const filename = selectedOption.dataset.filename;
    
    try {
        showNotification('Cargando Excel consolidado...', 'info');
        
        const response = await fetch(buildApiUrl('/api/excel/data'));
        const data = await response.json();
        
        if (!data.success) {
            showNotification('Error al cargar Excel: ' + data.error, 'error');
            return;
        }
        
        // Guardar datos actuales
        currentExcelData = data.data;
        currentFolderId = 'session'; // Usar 'session' como identificador
        
        // Mostrar selector de hojas
        const sheetSelector = document.getElementById('sheetSelector');
        const sheetDropdown = document.getElementById('sheetDropdown');
        sheetSelector.style.display = 'block';
        
        // Llenar dropdown de hojas
        sheetDropdown.innerHTML = '<option value="">Seleccionar hoja...</option>';
        Object.keys(data.data).forEach(sheetName => {
            const option = document.createElement('option');
            option.value = sheetName;
            option.textContent = sheetName;
            sheetDropdown.appendChild(option);
        });
        
        // Ocultar placeholder y mostrar editor
        document.getElementById('excelPlaceholder').style.display = 'none';
        document.getElementById('excelEditor').style.display = 'block';
        
        // Habilitar botones
        document.getElementById('saveExcelBtn').disabled = false;
        document.getElementById('downloadExcelBtn').disabled = false;
        
        showNotification(`Excel consolidado "${filename}" cargado correctamente`, 'success');
        
        // Auto-seleccionar primera hoja
        if (Object.keys(data.data).length > 0) {
            const firstSheet = Object.keys(data.data)[0];
            sheetDropdown.value = firstSheet;
            switchSheet(firstSheet);
        }
        
    } catch (error) {
        console.error('Error cargando Excel:', error);
        showNotification('Error al cargar Excel', 'error');
    }
}

// Cambiar entre hojas del Excel
function switchSheet(sheetName) {
    if (!sheetName || !currentExcelData || !currentExcelData[sheetName]) {
        return;
    }
    
    currentSheetName = sheetName;
    const sheetData = currentExcelData[sheetName];
    
    // Destruir instancia anterior si existe
    if (hot) {
        hot.destroy();
    }
    
    // Definir el contenedor del Excel
    const container = document.getElementById('excelEditor');
    
    // Calcular altura disponible para el Excel (ocupar todo el espacio vertical)
    const headerHeight = document.querySelector('.excel-config-header')?.offsetHeight || 60;
    const windowHeight = window.innerHeight;
    const availableHeight = windowHeight - headerHeight - 50; // 50px de margen (reducido de 100)
    
    hot = new Handsontable(container, {
        data: sheetData.rows,
        colHeaders: sheetData.headers,
        rowHeaders: true,
        height: Math.max(availableHeight, 400), // Mínimo 400px
        width: '100%',
        stretchH: 'all',
        contextMenu: true,
        manualColumnResize: true,
        manualRowResize: true,
        filters: true,
        dropdownMenu: true,
        licenseKey: 'non-commercial-and-evaluation',
        afterChange: function(changes, source) {
            if (source !== 'loadData' && changes) {
                // Marcar como modificado
                const saveBtn = document.getElementById('saveExcelBtn');
                saveBtn.innerHTML = '<i class="fas fa-save"></i> Guardar Cambios';
                saveBtn.classList.add('unsaved-changes');
            }
        }
    });
    
    // Agregar listener para recalcular altura al redimensionar ventana
    window.addEventListener('resize', () => {
        if (hot) {
            const headerHeight = document.querySelector('.excel-config-header')?.offsetHeight || 60;
            const windowHeight = window.innerHeight;
            const availableHeight = windowHeight - headerHeight - 50;
            hot.updateSettings({ height: Math.max(availableHeight, 400) });
        }
    });
    
    // showNotification(`Hoja "${sheetName}" cargada`, 'info');
}

// Cargar Excel de sesión automáticamente
async function loadSessionExcel() {
    try {
        
        const response = await fetch(buildApiUrl('/api/excel/data'));
        const data = await response.json();
        
        if (!data.success) {
            showNotification('Error al cargar Excel: ' + data.error, 'error');
            document.getElementById('excelPlaceholder').innerHTML = `
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: var(--danger-color);"></i>
                <p>Error al cargar Excel</p>
                <small>${data.error}</small>
            `;
            return;
        }
        
        // Guardar datos actuales
        currentExcelData = data.data;
        currentFolderId = 'session'; // Usar 'session' como identificador
        
        // Llenar dropdown de hojas directamente en el header
        const sheetDropdown = document.getElementById('sheetDropdown');
        sheetDropdown.innerHTML = '<option value="">Seleccionar hoja...</option>';
        Object.keys(data.data).forEach(sheetName => {
            const option = document.createElement('option');
            option.value = sheetName;
            option.textContent = sheetName;
            sheetDropdown.appendChild(option);
        });
        
        // Ocultar placeholder y mostrar editor
        document.getElementById('excelPlaceholder').style.display = 'none';
        document.getElementById('excelEditor').style.display = 'block';
        
        // Habilitar botones
        document.getElementById('saveExcelBtn').disabled = false;
        document.getElementById('downloadExcelBtn').disabled = false;
        
        // Auto-seleccionar primera hoja
        if (Object.keys(data.data).length > 0) {
            const firstSheet = Object.keys(data.data)[0];
            sheetDropdown.value = firstSheet;
            switchSheet(firstSheet);
        }
        
    } catch (error) {
        console.error('❌ ERROR CRÍTICO cargando Excel de sesión:', error);
        console.error('❌ Detalles del error:', {
            message: error.message,
            stack: error.stack,
            name: error.name
        });
        showNotification('Error al cargar Excel de sesión: ' + error.message, 'error');
        document.getElementById('excelPlaceholder').innerHTML = `
            <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: var(--danger-color);"></i>
            <p>Error de conexión</p>
            <small>Detalles: ${error.message}</small>
        `;
    }
}

// Funciones de configuración del Excel
function updateExcelFontSize(size) {
    if (!hot) return;
    
    // Aplicar configuración de fuente
    hot.updateSettings({
        fontSize: size + 'px'
    });
    
    showNotification(`Tamaño de fuente: ${size}px`, 'info');
}

function updateExcelTheme(theme) {
    // Tema removido - ya no se usa
    showNotification('Tema no disponible', 'info');
}

function updateExcelBorders(style) {
    if (!hot) return;
    
    // Configurar bordes según el estilo seleccionado
    let borderSettings = {};
    
    switch(style) {
        case 'all':
            borderSettings = {
                customBorders: true
            };
            break;
        case 'none':
            borderSettings = {
                customBorders: false
            };
            break;
        case 'minimal':
            borderSettings = {
                customBorders: [
                    // Bordes mínimos (solo externos)
                ]
            };
            break;
    }
    
    hot.updateSettings(borderSettings);
    showNotification(`Bordes: ${style}`, 'info');
}

// Guardar cambios en el Excel (consolidado de sesión)
async function saveExcelChanges() {
    if (!hot || !currentSheetName) {
        showNotification('No hay Excel cargado para guardar', 'warning');
        return;
    }
    
    try {
        showNotification('Guardando cambios...', 'info');
        
        // Obtener datos actuales del editor
        const currentData = hot.getData();
        const headers = hot.getColHeader();
        
        // Preparar datos para enviar
        const sheetData = {};
        sheetData[currentSheetName] = {
            headers: headers,
            rows: currentData
        };
        
        const response = await fetch(buildApiUrl('/api/excel/save'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sheet_data: sheetData
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Actualizar datos locales
            currentExcelData[currentSheetName].rows = currentData;
            
            // Resetear indicador de cambios
            const saveBtn = document.getElementById('saveExcelBtn');
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Guardar';
            saveBtn.classList.remove('unsaved-changes');
            
            showNotification('Cambios guardados correctamente', 'success');
            
            // Actualizar dashboard con los nuevos datos
            updateDashboardFromExcel();
            
        } else {
            showNotification('Error al guardar: ' + data.error, 'error');
        }
        
    } catch (error) {
        console.error('Error guardando Excel:', error);
        showNotification('Error al guardar cambios', 'error');
    }
}

// Descargar archivo Excel
async function downloadExcelFile() {
    if (!currentExcelData) {
        showNotification('No hay Excel cargado para descargar', 'warning');
        return;
    }
    
    try {
        // Crear enlace temporal para descarga
        const link = document.createElement('a');
        link.href = `/api/excel/download`;
        link.download = ''; // El servidor especifica el nombre
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('Descargando Excel...', 'info');
        
    } catch (error) {
        console.error('Error descargando Excel:', error);
        showNotification('Error al descargar Excel', 'error');
    }
}

// Actualizar dashboard con datos del Excel
function updateDashboardFromExcel() {
    if (!currentExcelData) {
        console.log('No hay datos de Excel para actualizar dashboard');
        return;
    }
    
    try {
        // Extraer estadísticas de las hojas del Excel
        const stats = extractStatsFromExcel(currentExcelData);
        
        // Actualizar estadísticas generales
        updateStatsCards(stats);
        
        // Actualizar gráfico de objetos detectados
        updateObjectsChart(stats.objects);
        
        console.log('Dashboard actualizado con datos del Excel');
        
    } catch (error) {
        console.error('Error actualizando dashboard desde Excel:', error);
    }
}

// Extraer estadísticas de los datos del Excel
function extractStatsFromExcel(excelData) {
    const stats = {
        total_folders: 0,
        total_videos: 0,
        total_clips: 0,
        objects: []
    };
    
    try {
        // Procesar hoja "Estadísticas por Carpeta" para contar carpetas
        if (excelData['Estadísticas por Carpeta']) {
            const folderStatsSheet = excelData['Estadísticas por Carpeta'];
            if (folderStatsSheet.rows && folderStatsSheet.rows.length > 0) {
                // Contar carpetas (excluyendo header)
                stats.total_folders = folderStatsSheet.rows.length;
            }
        }
        
        // Procesar hoja "Videos" si existe
        if (excelData['Videos']) {
            const videosSheet = excelData['Videos'];
            if (videosSheet.rows && videosSheet.rows.length > 0) {
                // Contar videos (excluyendo header)
                stats.total_videos = videosSheet.rows.length;
            }
        }
        
        // Procesar hoja "Clips Detectados" si existe
        if (excelData['Clips Detectados']) {
            const clipsSheet = excelData['Clips Detectados'];
            if (clipsSheet.rows && clipsSheet.rows.length > 0) {
                stats.total_clips = clipsSheet.rows.length;
                
                // Contar objetos detectados
                const objectCounts = {};
                clipsSheet.rows.forEach(row => {
                    // Asumiendo que la columna de objeto detectado está en la posición correcta
                    const detectedObject = row[5] || row[6]; // Intentar diferentes posiciones
                    if (detectedObject && detectedObject !== '' && detectedObject !== 'Sin clasificar') {
                        objectCounts[detectedObject] = (objectCounts[detectedObject] || 0) + 1;
                    }
                });
                
                // Convertir a formato para el gráfico
                stats.objects = Object.entries(objectCounts).map(([type, count]) => ({
                    type: type,
                    count: count
                }));
            }
        }
        
        // Si no hay estadísticas por carpeta, intentar obtener de "Estadísticas" generales
        if (stats.total_folders === 0 && excelData['Estadísticas']) {
            // Podríamos extraer estadísticas adicionales aquí si es necesario
            console.log('Usando estadísticas generales para dashboard');
        }
        
    } catch (error) {
        console.error('Error procesando estadísticas del Excel:', error);
        // Valores por defecto en caso de error
        stats.total_folders = 1;
        stats.total_videos = 0;
        stats.total_clips = 0;
        stats.objects = [];
    }
    
    return stats;
}

// Actualizar tarjetas de estadísticas
function updateStatsCards(stats) {
    const totalFoldersEl = document.getElementById('totalFolders');
    const totalVideosEl = document.getElementById('totalVideos');
    const totalClipsEl = document.getElementById('totalClips');
    const totalObjectsEl = document.getElementById('totalObjects');
    
    if (totalFoldersEl) totalFoldersEl.textContent = stats.total_folders;
    if (totalVideosEl) totalVideosEl.textContent = stats.total_videos;
    if (totalClipsEl) totalClipsEl.textContent = stats.total_clips;
    if (totalObjectsEl) {
        const totalObjects = stats.objects.reduce((sum, obj) => sum + obj.count, 0);
        totalObjectsEl.textContent = totalObjects;
    }
}

// Actualizar gráfico de objetos detectados
function updateObjectsChart(objects) {
    const ctx = document.getElementById('objectsChart');
    if (!ctx) return;
    
    const labels = objects.map(obj => obj.type || 'Desconocido');
    const values = objects.map(obj => obj.count);
    
    const colors = [
        '#3498DB', '#E74C3C', '#27AE60', '#F39C12', 
        '#9B59B6', '#1ABC9C', '#E67E22', '#95A5A6'
    ];
    
    // Destruir gráfico anterior si existe
    if (window.objectsChartInstance) {
        window.objectsChartInstance.destroy();
    }
    
    // Crear nuevo gráfico
    window.objectsChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Objetos Detectados',
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: colors.slice(0, labels.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Vista: Logs del sistema
function showLogsView() {
    updateViewTitle('📄 Logs del Sistema');
    
    const content = `
        <div class="logs-container">
            <div class="logs-header">
                <h2>
                    <i class="fas fa-file-alt"></i> Logs de Sesión
                    <span class="session-badge" id="sessionBadge"></span>
                </h2>
                <div class="logs-controls">
                    <button class="btn btn-success" onclick="downloadLogs()">
                        <i class="fas fa-download"></i> Descargar TXT
                    </button>
                    <button class="btn btn-secondary" onclick="refreshLogs()">
                        <i class="fas fa-sync-alt"></i> Actualizar
                    </button>
                    <button class="btn btn-secondary" onclick="clearLogsDisplay()">
                        <i class="fas fa-trash"></i> Limpiar Vista
                    </button>
                    <label class="auto-refresh-toggle">
                        <input type="checkbox" id="autoRefreshLogs" onchange="toggleAutoRefresh(this.checked)">
                        <span>Auto-actualizar (5s)</span>
                    </label>
                </div>
            </div>
            
            <div class="logs-filters">
                <button class="log-filter-btn active" data-level="all" onclick="filterLogs('all')">
                    <i class="fas fa-list"></i> Todos
                </button>
                <button class="log-filter-btn" data-level="INFO" onclick="filterLogs('INFO')">
                    <i class="fas fa-info-circle"></i> Info
                </button>
                <button class="log-filter-btn" data-level="WARNING" onclick="filterLogs('WARNING')">
                    <i class="fas fa-exclamation-triangle"></i> Advertencias
                </button>
                <button class="log-filter-btn" data-level="ERROR" onclick="filterLogs('ERROR')">
                    <i class="fas fa-times-circle"></i> Errores
                </button>
            </div>
            
            <div class="logs-content" id="logsContent">
                <div class="loading-logs">
                    <i class="fas fa-spinner fa-spin"></i> Cargando logs...
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    // Cargar logs inicialmente
    refreshLogs();
}

// Refrescar logs
async function refreshLogs() {
    const logsContent = document.getElementById('logsContent');
    if (!logsContent) return;
    
    try {
        const response = await fetch(buildApiUrl('/api/logs'));
        const data = await response.json();
        
        if (!data.success) {
            logsContent.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    Error al cargar logs: ${data.error}
                </div>
            `;
            return;
        }
        
        // Actualizar badge de sesión
        const sessionBadge = document.getElementById('sessionBadge');
        if (sessionBadge && data.session_id) {
            sessionBadge.textContent = data.session_id;
            sessionBadge.title = `Archivo: ${data.log_file}`;
        }
        
        if (data.logs.length === 0) {
            logsContent.innerHTML = `
                <div class="empty-logs">
                    <i class="fas fa-inbox"></i>
                    <p>No hay logs disponibles en esta sesión</p>
                    <small>ID Sesión: ${data.session_id}</small>
                </div>
            `;
            return;
        }
        
        // Renderizar logs con formato mejorado
        let html = '<div class="logs-list">';
        data.logs.forEach(log => {
            const levelClass = log.level.toLowerCase().trim();
            const icon = getLogIcon(log.level);
            
            // Formato mejorado: timestamp | nivel | función | mensaje
            html += `
                <div class="log-entry log-${levelClass}" data-level="${log.level}">
                    <span class="log-time">${log.timestamp}</span>
                    <span class="log-level">
                        <i class="${icon}"></i> ${log.level}
                    </span>
                    ${log.function ? `<span class="log-function">${escapeHtml(log.function)}</span>` : ''}
                    <span class="log-message">${escapeHtml(log.message)}</span>
                </div>
            `;
        });
        html += '</div>';
        
        logsContent.innerHTML = html;
        
        // Scroll al final
        logsContent.scrollTop = logsContent.scrollHeight;
        
    } catch (error) {
        console.error('Error al refrescar logs:', error);
        logsContent.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                Error de conexión: ${error.message}
            </div>
        `;
    }
}

// Obtener icono según nivel de log
function getLogIcon(level) {
    switch(level) {
        case 'INFO': return 'fas fa-info-circle';
        case 'WARNING': return 'fas fa-exclamation-triangle';
        case 'ERROR': return 'fas fa-times-circle';
        case 'DEBUG': return 'fas fa-bug';
        default: return 'fas fa-circle';
    }
}

// Filtrar logs por nivel
function filterLogs(level) {
    // Actualizar botones activos
    document.querySelectorAll('.log-filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.log-filter-btn').classList.add('active');
    
    // Filtrar entradas
    const entries = document.querySelectorAll('.log-entry');
    entries.forEach(entry => {
        if (level === 'all' || entry.dataset.level === level) {
            entry.style.display = 'flex';
        } else {
            entry.style.display = 'none';
        }
    });
}

// Limpiar logs (borrar archivo del servidor)
async function clearLogsDisplay() {
    if (!confirm('¿Estás seguro de que quieres borrar todos los logs de esta sesión? Esta acción no se puede deshacer.')) {
        return;
    }
    
    const logsContent = document.getElementById('logsContent');
    if (logsContent) {
        logsContent.innerHTML = `
            <div class="loading-logs">
                <i class="fas fa-spinner fa-spin"></i> Limpiando logs...
            </div>
        `;
    }
    
    try {
        const response = await fetch(buildApiUrl('/api/logs/clear'), {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✓ Logs eliminados correctamente', 'success');
            if (logsContent) {
                logsContent.innerHTML = `
                    <div class="empty-logs">
                        <i class="fas fa-check-circle"></i>
                        <p>Logs eliminados</p>
                        <small>Los nuevos logs se registrarán automáticamente</small>
                    </div>
                `;
            }
        } else {
            showNotification('❌ Error al limpiar logs: ' + result.error, 'danger');
            refreshLogs();
        }
    } catch (error) {
        showNotification('❌ Error al limpiar logs: ' + error.message, 'danger');
        console.error('Error:', error);
        refreshLogs();
    }
}

// Auto-actualizar logs
let autoRefreshInterval = null;

function toggleAutoRefresh(enabled) {
    if (enabled) {
        autoRefreshInterval = setInterval(refreshLogs, 5000);
        showNotification('✓ Auto-actualización activada (cada 5s)', 'success');
    } else {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        showNotification('Auto-actualización desactivada', 'info');
    }
}

// Escapar HTML para prevenir XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Descargar logs como archivo TXT
function downloadLogs() {
    window.location.href = buildApiUrl('/api/logs/download');
    showNotification('📥 Descargando logs de la sesión...', 'info');
}

function showHelpView() {
    updateViewTitle('❓ Ayuda');
    
    const content = `
        <div class="help-container">
            <div class="help-card">
                <h2><i class="fas fa-question-circle"></i> Ayuda y Documentación</h2>
                
                <div class="help-section">
                    <h3>¿Cómo usar el sistema?</h3>
                    <ol>
                        <li>Selecciona una carpeta con videos o videos individuales</li>
                        <li>Opcionalmente configura el ROI de timestamp</li>
                        <li>Espera a que el sistema analice los videos</li>
                        <li>Revisa los clips generados en el historial</li>
                    </ol>
                </div>
                
                <div class="help-section">
                    <h3>Formatos soportados</h3>
                    <p>MP4, AVI, MOV, DAV, MKV</p>
                </div>
                
                <div class="help-section">
                    <h3>Contacto</h3>
                    <p>Grupo de Ingeniería de Medios<br>Escuela Politécnica</p>
                    <p><strong>Email:</strong> <a href="mailto:natera@unex.es">natera@unex.es</a></p>
                    <p><strong>Teléfono:</strong> +34 674 844 082</p>
                    <div class="help-section" style="margin-top: 15px;">
                        <h4>Reportar Errores</h4>
                        <p>Si encuentras algún problema, por favor incluye los logs del sistema en tu reporte:</p>
                        <ol style="font-size: 0.9em;">
                            <li>Ve a la sección "Logs del Sistema"</li>
                            <li>Haz clic en "Descargar Logs"</li>
                            <li>Adjunta el archivo descargado a tu email</li>
                        </ol>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
}

// Variables globales para ROI
let roiVideo = null;
let roiCanvas = null;
let roiCtx = null;
    // let isDrawing = false; // Eliminada para evitar duplicidad
let startX = 0;
let startY = 0;
let currentROI = { x: 0, y: 0, w: 0, h: 0 };
let videoScale = 1; // Escala entre video original y canvas

// Inicializar canvas de ROI
function initROICanvas() {
    roiCanvas = document.getElementById('roiCanvas');
    
    if (roiCanvas) {
        roiCtx = roiCanvas.getContext('2d');
        
        // Event listeners para dibujar
        roiCanvas.addEventListener('mousedown', startDrawing);
        roiCanvas.addEventListener('mousemove', draw);
        roiCanvas.addEventListener('mouseup', stopDrawing);
        roiCanvas.addEventListener('mouseleave', stopDrawing);
    }
}

// Cargar video para configurar ROI
async function loadROIVideo(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Guardar referencia al archivo para testing posterior
    window.roiTestVideoFile = file;
    
    showNotification('📹 Cargando video...', 'info');
    
    let videoUrl;
    let isDAV = false;
    
    // Si es archivo DAV, convertir en el servidor primero
    if (file.name.toLowerCase().endsWith('.dav')) {
        isDAV = true;
        console.log('Iniciando conversión de archivo DAV...');
        
        try {
            const formData = new FormData();
            formData.append('video', file);
            
            const response = await fetch(buildApiUrl('/api/convert-dav'), {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!result.success) {
                showNotification('❌ Error al convertir video: ' + result.error, 'danger');
                console.error('Error de conversión:', result);
                return;
            }
            
            // Construir URL completa con prefijo correcto
            if (result.video_url.startsWith('/')) {
                // Usar buildApiUrl para agregar el prefijo /proyect1/ automáticamente
                videoUrl = window.location.origin + buildApiUrl(result.video_url);
            } else {
                videoUrl = result.video_url;
            }
            
            console.log('Video DAV convertido, URL completa:', videoUrl);
            console.log('Frames convertidos:', result.frames_converted);
        } catch (error) {
            showNotification('❌ Error al convertir video: ' + error.message, 'danger');
            console.error('Error:', error);
            return;
        }
    } else {
        // Para MP4 y otros formatos compatibles, usar directamente
        videoUrl = URL.createObjectURL(file);
        console.log('Video MP4 cargado directamente, URL:', videoUrl);
    }
    
    // Crear elemento de video oculto
    roiVideo = document.createElement('video');
    roiVideo.src = videoUrl;
    roiVideo.preload = 'metadata';
    roiVideo.muted = true;
    
    console.log('Configurando video element con src:', videoUrl);
    
    // Agregar listener de error
    roiVideo.addEventListener('error', (e) => {
        console.error('❌ Error al cargar el video:', e);
        
        let errorMsg = 'Error al cargar el video';
        let errorDetails = '';
        
        if (roiVideo.error) {
            switch(roiVideo.error.code) {
                case 1: 
                    errorMsg = 'Carga de video abortada';
                    errorDetails = 'La carga fue interrumpida';
                    break;
                case 2: 
                    errorMsg = 'Error de red al cargar video';
                    errorDetails = 'Verifica tu conexión o que el archivo exista';
                    break;
                case 3: 
                    errorMsg = 'Error al decodificar video';
                    errorDetails = 'El video puede estar corrupto o usar un codec no soportado';
                    break;
                case 4: 
                    errorMsg = 'Formato de video no soportado';
                    errorDetails = 'Tu navegador no puede reproducir este formato';
                    break;
                default: 
                    errorMsg = 'Error desconocido al cargar video';
            }
        }
        
        showNotification(`❌ ${errorMsg}. ${errorDetails}`, 'danger');
    });
    
    roiVideo.addEventListener('loadedmetadata', () => {
        console.log('Video metadata cargada:', roiVideo.videoWidth, 'x', roiVideo.videoHeight);
    });
    
    roiVideo.addEventListener('loadeddata', () => {
        console.log('Video cargado:', roiVideo.videoWidth, 'x', roiVideo.videoHeight);
        roiVideo.currentTime = 0;
    });
    
    roiVideo.addEventListener('seeked', function captureFirstFrame() {
        console.log('Frame listo para capturar');
        
        // Ocultar área de carga y mostrar coordenadas + canvas
        document.getElementById('videoUploadArea').style.display = 'none';
        document.getElementById('coordinatesSection').style.display = 'block';
        document.getElementById('canvasArea').style.display = 'block';
        
        // Configurar canvas con escala razonable
        const maxWidth = 1000;
        const maxHeight = 600;
        const scale = Math.min(maxWidth / roiVideo.videoWidth, maxHeight / roiVideo.videoHeight, 1);
        
        roiCanvas.width = Math.floor(roiVideo.videoWidth * scale);
        roiCanvas.height = Math.floor(roiVideo.videoHeight * scale);
        videoScale = scale;
        
        console.log('Video:', roiVideo.videoWidth, 'x', roiVideo.videoHeight);
        console.log('Canvas:', roiCanvas.width, 'x', roiCanvas.height, 'Escala:', scale);
        
        // Dibujar frame
        roiCtx.drawImage(roiVideo, 0, 0, roiCanvas.width, roiCanvas.height);
        
        showNotification('✅ Video cargado. Dibuja un rectángulo sobre la zona de hora', 'success');
        
        // Quitar este listener
        roiVideo.removeEventListener('seeked', captureFirstFrame);
        
        // Configurar seekbar para cambiar frames
        const seekBar = document.getElementById('videoSeekBar');
        seekBar.addEventListener('input', (e) => {
            const time = (e.target.value / 100) * roiVideo.duration;
            roiVideo.currentTime = time;
        });
        
        // Actualizar canvas cuando cambie el frame
        roiVideo.addEventListener('seeked', () => {
            drawVideoFrame();
        });
    });
}

// Dibujar frame del video en canvas
function drawVideoFrame() {
    if (!roiVideo || !roiCtx) return;
    
    // Limpiar canvas
    roiCtx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
    
    // Dibujar video actual escalado
    roiCtx.drawImage(roiVideo, 0, 0, roiCanvas.width, roiCanvas.height);
    
    console.log('Dibujando frame');
    
    // Dibujar ROI si existe
    if (currentROI.w > 0 && currentROI.h > 0) {
        roiCtx.strokeStyle = '#3B82F6';
        roiCtx.lineWidth = 3;
        roiCtx.strokeRect(currentROI.x, currentROI.y, currentROI.w, currentROI.h);
        
        // Dibujar área semi-transparente fuera del ROI
        roiCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        roiCtx.fillRect(0, 0, roiCanvas.width, currentROI.y);
        roiCtx.fillRect(0, currentROI.y, currentROI.x, currentROI.h);
        roiCtx.fillRect(currentROI.x + currentROI.w, currentROI.y, roiCanvas.width - currentROI.x - currentROI.w, currentROI.h);
        roiCtx.fillRect(0, currentROI.y + currentROI.h, roiCanvas.width, roiCanvas.height - currentROI.y - currentROI.h);
    }
}

// Actualizar video frame continuamente (ya no se usa, pero mantenemos por compatibilidad)
function updateVideoFrame() {
    // No hace nada, ahora usamos imágenes estáticas
}

// Pausar/play video
function pauseROIVideo() {
    if (!roiVideo) return;
    
    const btn = document.getElementById('playPauseBtn');
    if (roiVideo.paused) {
        roiVideo.play();
        btn.innerHTML = '<i class="fas fa-pause"></i>';
        updateVideoFrame();
    } else {
        roiVideo.pause();
        btn.innerHTML = '<i class="fas fa-play"></i>';
    }
}

// Capturar frame actual
function captureFrame() {
    if (!roiVideo) return;
    roiVideo.pause();
    drawVideoFrame();
    document.getElementById('playPauseBtn').innerHTML = '<i class="fas fa-play"></i>';
}

// Iniciar dibujo de ROI
function startDrawing(e) {
    isDrawing = true;
    const rect = roiCanvas.getBoundingClientRect();
    startX = (e.clientX - rect.left) * (roiCanvas.width / rect.width);
    startY = (e.clientY - rect.top) * (roiCanvas.height / rect.height);
}

// Dibujar ROI mientras se arrastra
function draw(e) {
    if (!isDrawing) return;
    
    const rect = roiCanvas.getBoundingClientRect();
    const currentX = (e.clientX - rect.left) * (roiCanvas.width / rect.width);
    const currentY = (e.clientY - rect.top) * (roiCanvas.height / rect.height);
    
    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const w = Math.abs(currentX - startX);
    const h = Math.abs(currentY - startY);
    
    currentROI = { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) };
    
    // Actualizar inputs
    document.getElementById('roiX').value = currentROI.x;
    document.getElementById('roiY').value = currentROI.y;
    document.getElementById('roiW').value = currentROI.w;
    document.getElementById('roiH').value = currentROI.h;
    
    drawVideoFrame();
}

// Detener dibujo
function stopDrawing() {
    isDrawing = false;
}

// Actualizar preview del ROI
function updateROIPreview() {
    if (!roiVideo) return;
    
    const x = parseInt(document.getElementById('roiX').value);
    const y = parseInt(document.getElementById('roiY').value);
    const w = parseInt(document.getElementById('roiW').value);
    const h = parseInt(document.getElementById('roiH').value);
    
    currentROI = { x, y, w, h };
    
    drawVideoFrame();
}

// Limpiar ROI
function clearROI() {
    if (!confirm('¿Deseas limpiar el video y empezar de nuevo?')) {
        return;
    }
    
    currentROI = { x: 0, y: 0, w: 0, h: 0 };
    document.getElementById('roiX').value = 0;
    document.getElementById('roiY').value = 0;
    document.getElementById('roiW').value = 200;
    document.getElementById('roiH').value = 80;
    
    // Limpiar el video cargado
    if (roiVideo) {
        roiVideo.pause();
        roiVideo.src = '';
        roiVideo = null;
    }
    
    // Limpiar canvas
    const canvas = document.getElementById('roiCanvas');
    const ctx = canvas.getContext('2d');
    if (ctx && canvas) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    
    // Limpiar input de archivo
    const videoInput = document.getElementById('roiVideoInput');
    if (videoInput) {
        videoInput.value = '';
    }
    
    // Mostrar área de carga nuevamente y ocultar todo lo demás
    document.getElementById('videoUploadArea').style.display = 'flex';
    document.getElementById('coordinatesSection').style.display = 'none';
    document.getElementById('canvasArea').style.display = 'none';
    
    showNotification('✓ Video eliminado. Sube uno nuevo para continuar', 'info');
}

// Actualizar canvas de preview del ROI
function updateROIPreviewCanvas() {
    if (!roiVideo) return;
    
    const previewCanvas = document.getElementById('roiPreviewCanvas');
    if (!previewCanvas) return;
    
    const previewCtx = previewCanvas.getContext('2d');
    
    const x = parseInt(document.getElementById('roiX').value);
    const y = parseInt(document.getElementById('roiY').value);
    const w = parseInt(document.getElementById('roiW').value);
    const h = parseInt(document.getElementById('roiH').value);
    
    if (w <= 0 || h <= 0) return;
    
    // Configurar tamaño del canvas de preview
    previewCanvas.width = w;
    previewCanvas.height = h;
    
    // Dibujar la región recortada del video
    try {
        previewCtx.drawImage(
            roiVideo,
            x / videoScale, y / videoScale, w / videoScale, h / videoScale,
            0, 0, w, h
        );
    } catch (e) {
        console.error('Error dibujando preview:', e);
    }
}

// Funciones de configuración
function loadROIConfig() {
    const config = JSON.parse(localStorage.getItem('roiConfig') || '{"x":0,"y":0,"w":200,"h":80}');
    document.getElementById('roiX').value = config.x;
    document.getElementById('roiY').value = config.y;
    document.getElementById('roiW').value = config.w;
    document.getElementById('roiH').value = config.h;
    currentROI = config;
    window.currentROI = [config.x, config.y, config.w, config.h];
}

async function saveROIConfig() {
    const x = parseInt(document.getElementById('roiX').value);
    const y = parseInt(document.getElementById('roiY').value);
    const w = parseInt(document.getElementById('roiW').value);
    const h = parseInt(document.getElementById('roiH').value);
    
    if (w <= 0 || h <= 0) {
        showNotification('❌ Las dimensiones deben ser mayores a 0', 'danger');
        return;
    }
    
    // Convertir a coordenadas reales (sin escala del canvas)
    const realX = Math.round(x / videoScale);
    const realY = Math.round(y / videoScale);
    const realW = Math.round(w / videoScale);
    const realH = Math.round(h / videoScale);
    
    const config = {
        x: realX,
        y: realY,
        w: realW,
        h: realH
    };
    
    // Guardar en localStorage (persistencia entre sesiones)
    localStorage.setItem('roiConfig', JSON.stringify(config));
    window.currentROI = [realX, realY, realW, realH];
    
    // Marcar como configurado en localStorage
    localStorage.setItem('roiConfigured', 'true');
    
    try {
        // 1. Guardar en servidor
        const saveResponse = await fetch(buildApiUrl('/api/config/roi'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const saveData = await saveResponse.json();
        
        if (!saveData.success) {
            throw new Error(saveData.error || 'Error al guardar configuración');
        }
        
        // 2. Si hay un video cargado, probar extracción de timestamp
        if (window.roiTestVideoFile) {
            showNotification('⏳ Verificando extracción de timestamp...', 'info');
            
            const formData = new FormData();
            formData.append('video', window.roiTestVideoFile);
            formData.append('roi', JSON.stringify(config));
            
            const testResponse = await fetch(buildApiUrl('/api/config/roi/test'), {
                method: 'POST',
                body: formData
            });
            
            const testData = await testResponse.json();
            
            if (testData.success && testData.timestamp) {
                showNotification(`✅ Configuración guardada. Timestamp detectado: ${testData.timestamp}`, 'success', 5000);
                
                // Mostrar tarjeta de confirmación con el timestamp
                const savedCard = document.getElementById('savedConfigCard');
                const savedText = document.getElementById('savedConfigText');
                if (savedCard && savedText) {
                    savedCard.style.display = 'block';
                    savedCard.style.background = 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)';
                    savedText.innerHTML = `
                        <strong>✅ Configuración Válida</strong><br>
                        Zona: ${realX}, ${realY} - ${realW}x${realH} px<br>
                        <span style="color: var(--success-color); font-weight: bold;">
                            Timestamp detectado: ${testData.timestamp}
                        </span>
                    `;
                }
            } else {
                showNotification('⚠️ Configuración guardada, pero no se pudo extraer timestamp. Verifica que la zona contenga la hora del video.', 'warning', 6000);
                
                const savedCard = document.getElementById('savedConfigCard');
                const savedText = document.getElementById('savedConfigText');
                if (savedCard && savedText) {
                    savedCard.style.display = 'block';
                    savedCard.style.background = 'linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%)';
                    savedText.innerHTML = `
                        <strong>⚠️ ROI Guardado (sin validar)</strong><br>
                        Zona: ${realX}, ${realY} - ${realW}x${realH} px<br>
                        <span style="color: var(--warning-color);">
                            No se detectó timestamp. Ajusta la zona.
                        </span>
                    `;
                }
            }
        } else {
            // Sin video de prueba, solo confirmar guardado
            showNotification('✅ Configuración guardada. Sube un video de prueba para validar.', 'success');
            
            const savedCard = document.getElementById('savedConfigCard');
            const savedText = document.getElementById('savedConfigText');
            if (savedCard && savedText) {
                savedCard.style.display = 'block';
                savedText.textContent = `Zona: ${realX}, ${realY} - ${realW}x${realH} px`;
            }
        }
        
    } catch (error) {
        console.error('Error guardando en servidor:', error);
        showNotification('⚠️ Guardado solo localmente. Error de conexión con servidor', 'warning');
    }
}

function resetROIConfig() {
    document.getElementById('roiX').value = 0;
    document.getElementById('roiY').value = 0;
    document.getElementById('roiW').value = 200;
    document.getElementById('roiH').value = 80;
    saveROIConfig();
    if (roiVideo) {
        updateROIPreview();
    }
}

// Nueva función para selección de ROI antes de procesar
function showROISelectionForProcessing(folderPath, uploadedFiles) {
    updateViewTitle('🎯 Configurar Área de Análisis');
    
    const content = `
        <div class="roi-processing-container">
            <div class="roi-processing-header">
                <h2><i class="fas fa-crosshairs"></i> Selecciona el Área de Movimiento</h2>
                <p class="roi-processing-description">
                    Define la zona donde quieres detectar movimiento. 
                    Solo se analizarán eventos dentro de esta área.
                </p>
            </div>
            
            <div class="roi-processing-steps">
                <div class="step-indicator">
                    <div class="step active">
                        <div class="step-number">1</div>
                        <div class="step-label">Cargando video...</div>
                    </div>
                    <div class="step-line"></div>
                    <div class="step">
                        <div class="step-number">2</div>
                        <div class="step-label">Definir ROI</div>
                    </div>
                    <div class="step-line"></div>
                    <div class="step">
                        <div class="step-number">3</div>
                        <div class="step-label">Procesar</div>
                    </div>
                </div>
            </div>
            
            <div class="roi-processing-content">
                <!-- Canvas para dibujar ROI -->
                <div class="roi-canvas-section">
                    <div class="canvas-wrapper" id="canvasWrapperProcessing">
                        <!-- Loader mientras carga el video -->
                        <div class="video-loading" id="videoLoadingIndicator">
                            <div class="spinner"></div>
                            <p id="loadingMessage">Cargando video...</p>
                            <small id="loadingSubtext" style="color: #999; margin-top: 10px;"></small>
                        </div>
                        <canvas id="roiProcessingCanvas" width="1000" height="600" style="display:none;"></canvas>
                        <div class="canvas-instructions" id="canvasInstructions" style="display:none;">
                            <i class="fas fa-mouse-pointer"></i>
                            <span>Arrastra con el mouse para dibujar el área de análisis</span>
                        </div>
                    </div>
                    
                    <div class="video-controls" style="margin-top: 15px;" id="videoControlsProcessing" style="display:none;">
                        <input type="range" id="videoProcessingSeekBar" min="0" max="100" value="0" style="flex: 1;">
                    </div>
                </div>
                
                <!-- Coordenadas y acciones -->
                <div class="roi-processing-sidebar" id="roiProcessingSidebar" style="opacity: 0.5; pointer-events: none;">
                    <div class="roi-coords-card">
                        <h3><i class="fas fa-ruler-combined"></i> Coordenadas del Área</h3>
                        <div class="roi-coords-grid">
                            <div class="coord-input">
                                <label>X:</label>
                                <input type="number" id="roiProcessingX" value="0" min="0" oninput="updateProcessingROIPreview()">
                            </div>
                            <div class="coord-input">
                                <label>Y:</label>
                                <input type="number" id="roiProcessingY" value="0" min="0" oninput="updateProcessingROIPreview()">
                            </div>
                            <div class="coord-input">
                                <label>Ancho:</label>
                                <input type="number" id="roiProcessingW" value="640" min="1" oninput="updateProcessingROIPreview()">
                            </div>
                            <div class="coord-input">
                                <label>Alto:</label>
                                <input type="number" id="roiProcessingH" value="480" min="1" oninput="updateProcessingROIPreview()">
                            </div>
                        </div>
                        
                        <button class="btn btn-secondary btn-block" onclick="resetProcessingROI()">
                            <i class="fas fa-undo"></i> Usar Video Completo
                        </button>
                    </div>
                    
                    <div class="roi-options-card">
                        <h3><i class="fas fa-sliders-h"></i> Opciones de Análisis</h3>
                        <div class="option-item">
                            <input type="checkbox" id="processingGenerateClips" checked>
                            <label for="processingGenerateClips">Generar clips de video</label>
                        </div>
                        <div class="option-item">
                            <input type="checkbox" id="processingUseAI" checked>
                            <label for="processingUseAI">Análisis con IA</label>
                        </div>
                    </div>
                    
                    <div class="roi-processing-actions">
                        <button class="btn btn-primary btn-block btn-large" onclick="confirmAndStartProcessing()">
                            <i class="fas fa-play-circle"></i> Iniciar Análisis
                        </button>
                        <button class="btn btn-secondary btn-block" onclick="cancelROIProcessing()">
                            <i class="fas fa-times"></i> Cancelar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('main-panel').innerHTML = content;
    
    console.log('📦 uploadedFiles recibidos:', uploadedFiles);
    console.log('📦 Primer archivo:', uploadedFiles[0]);
    
    // Cargar el primer video subido para mostrar el frame
    // uploadedFiles es un array de objetos {name: "...", path: "..."}
    const firstVideoName = uploadedFiles[0].name || uploadedFiles[0];
    console.log('🎬 Nombre del primer video:', firstVideoName);
    loadProcessingROIVideo(firstVideoName);
    
    // Inicializar canvas para dibujar ROI (independiente de la carga del video)
    setTimeout(() => initProcessingROICanvas(), 100);
    
    // Sincronizar checkboxes de opciones de procesamiento
    setTimeout(() => {
        syncROICheckboxesFromUpload();
        setupROICheckboxListeners();
    }, 200);
}

// Sincronizar checkboxes de ROI con los de upload/video
function syncROICheckboxesFromUpload() {
    console.log('🔄 syncROICheckboxesFromUpload llamada');
    
    const generateClipsProcessing = document.getElementById('processingGenerateClips');
    const useAIProcessing = document.getElementById('processingUseAI');
    
    // Buscar checkboxes de origen (en orden de prioridad)
    let generateClipsSource = 
        document.getElementById('videoGenerateClipsOption') ||
        document.getElementById('generateClipsOption') ||
        document.getElementById('folderGenerateClipsOption');
    
    let useAISource = 
        document.getElementById('videoUseAiAnalysisOption') ||
        document.getElementById('useAiAnalysisOption') ||
        document.getElementById('folderUseAiAnalysisOption');
    
    console.log('📋 Checkboxes encontrados:');
    console.log('  - videoGenerateClipsOption:', document.getElementById('videoGenerateClipsOption')?.checked);
    console.log('  - generateClipsOption:', document.getElementById('generateClipsOption')?.checked);
    console.log('  - folderGenerateClipsOption:', document.getElementById('folderGenerateClipsOption')?.checked);
    console.log('  - Fuente checkbox usada:', generateClipsSource?.id, '=', generateClipsSource?.checked);
    console.log('  - Estado en sessionStorage:', {
        generateClips: sessionStorage.getItem('processingOptions.generateClips'),
        useAI: sessionStorage.getItem('processingOptions.useAI')
    });
    
    // Sincronizar generateClips
    if (generateClipsProcessing) {
        let valueToUse = true; // Default
        
        if (generateClipsSource) {
            // Hay un checkbox visible, usar su valor
            valueToUse = generateClipsSource.checked;
            console.log('✅ Usando valor del checkbox:', valueToUse);
        } else {
            // No hay checkbox visible, buscar en sessionStorage
            const savedState = sessionStorage.getItem('processingOptions.generateClips');
            if (savedState !== null) {
                valueToUse = savedState === 'true';
                console.log('📂 Usando valor de sessionStorage:', valueToUse);
            } else if (window.lastProcessingOptions && window.lastProcessingOptions.generateClips !== undefined) {
                valueToUse = window.lastProcessingOptions.generateClips;
                console.log('💾 Usando valor de variable global:', valueToUse);
            } else {
                console.log('⚠️ Usando valor por defecto:', valueToUse);
            }
        }
        
        generateClipsProcessing.checked = valueToUse;
        console.log('✅ processingGenerateClips sincronizado a:', generateClipsProcessing.checked);
    } else {
        console.warn('⚠️ processingGenerateClips no existe');
    }
    
    // Sincronizar useAI
    if (useAIProcessing) {
        let valueToUse = true; // Default
        
        if (useAISource) {
            // Hay un checkbox visible, usar su valor
            valueToUse = useAISource.checked;
            console.log('✅ Usando valor del checkbox:', valueToUse);
        } else {
            // No hay checkbox visible, buscar en sessionStorage
            const savedState = sessionStorage.getItem('processingOptions.useAI');
            if (savedState !== null) {
                valueToUse = savedState === 'true';
                console.log('📂 Usando valor de sessionStorage:', valueToUse);
            } else if (window.lastProcessingOptions && window.lastProcessingOptions.useAI !== undefined) {
                valueToUse = window.lastProcessingOptions.useAI;
                console.log('💾 Usando valor de variable global:', valueToUse);
            } else {
                console.log('⚠️ Usando valor por defecto:', valueToUse);
            }
        }
        
        useAIProcessing.checked = valueToUse;
        console.log('✅ processingUseAI sincronizado a:', useAIProcessing.checked);
    } else {
        console.warn('⚠️ processingUseAI no existe');
    }
}

// Configurar listeners para los checkboxes de la vista de ROI
function setupROICheckboxListeners() {
    console.log('🎧 Configurando listeners de checkboxes de ROI');
    
    const generateClipsProcessing = document.getElementById('processingGenerateClips');
    const useAIProcessing = document.getElementById('processingUseAI');
    
    if (generateClipsProcessing) {
        generateClipsProcessing.addEventListener('change', function() {
            console.log('🔄 ROI checkbox clips cambió a:', this.checked);
            
            // Guardar en sessionStorage
            sessionStorage.setItem('processingOptions.generateClips', this.checked);
            
            // Sincronizar con TODOS los checkboxes de clips
            ['videoGenerateClipsOption', 'generateClipsOption', 'folderGenerateClipsOption'].forEach(id => {
                const checkbox = document.getElementById(id);
                if (checkbox) {
                    checkbox.checked = this.checked;
                    console.log(`  ↪️ Sincronizado ${id} a:`, this.checked);
                }
            });
        });
        console.log('✅ Listener agregado a processingGenerateClips');
    } else {
        console.warn('⚠️ processingGenerateClips no encontrado');
    }
    
    if (useAIProcessing) {
        useAIProcessing.addEventListener('change', function() {
            console.log('🔄 ROI checkbox IA cambió a:', this.checked);
            
            // Guardar en sessionStorage
            sessionStorage.setItem('processingOptions.useAI', this.checked);
            
            // Sincronizar con TODOS los checkboxes de IA
            ['videoUseAiAnalysisOption', 'useAiAnalysisOption', 'folderUseAiAnalysisOption'].forEach(id => {
                const checkbox = document.getElementById(id);
                if (checkbox) {
                    checkbox.checked = this.checked;
                    console.log(`  ↪️ Sincronizado ${id} a:`, this.checked);
                }
            });
        });
        console.log('✅ Listener agregado a processingUseAI');
    } else {
        console.warn('⚠️ processingUseAI no encontrado');
    }
}

// Variables globales para el ROI de procesamiento
let processingROIVideo = null;
let processingROICanvas = null;
let processingROICtx = null;
let processingROIDrawing = false;
let processingROIStartX = 0;
let processingROIStartY = 0;

function loadProcessingROIVideo(videoFileName) {
    console.log('🎬 loadProcessingROIVideo llamada con:', videoFileName);
    console.log('📁 window.pendingFolderPath:', window.pendingFolderPath);
    console.log('🆔 window.pendingFolderId:', window.pendingFolderId);
    
    const canvas = document.getElementById('roiProcessingCanvas');
    if (!canvas) {
        console.error('❌ Canvas no encontrado!');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // Actualizar referencias globales INMEDIATAMENTE
    processingROICanvas = canvas;
    processingROICtx = ctx;
    
    console.log('✓ Referencias del canvas actualizadas');
    console.log('✓ Canvas:', canvas.width, 'x', canvas.height);
    
    // Dibujar un mensaje temporal en el canvas
    ctx.fillStyle = '#333';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#fff';
    ctx.font = '20px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Generando preview...', canvas.width / 2, canvas.height / 2);
    
    // Actualizar mensaje de carga
    const loadingMsg = document.getElementById('loadingMessage');
    const loadingSubtext = document.getElementById('loadingSubtext');
    if (loadingMsg) loadingMsg.textContent = 'Generando preview del video...';
    if (loadingSubtext) loadingSubtext.textContent = '5 segundos en baja resolución para configurar ROI';
    
    // Extraer session folder
    let sessionFolder = '';
    if (window.pendingFolderPath.includes('\\')) {
        const parts = window.pendingFolderPath.split('\\');
        sessionFolder = parts[parts.length - 1];
    } else {
        const parts = window.pendingFolderPath.split('/');
        sessionFolder = parts[parts.length - 1];
    }
    
    console.log('📁 Session folder:', sessionFolder);
    
    // Solicitar generación de preview ligero
    fetch(buildApiUrl('/api/generate-roi-preview'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: videoFileName,
            session_folder: sessionFolder
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            throw new Error(data.error || 'Error generando preview');
        }
        
        console.log('✅ Preview generado:', data.preview_filename, `(${data.preview_size_mb || '?'}MB)`);
        
        // Ahora cargar el preview (mucho más pequeño y rápido)
        loadProcessingROIVideoElement(data.preview_url);
    })
    .catch(error => {
        console.error('❌ Error generando preview:', error);
        showNotification('Error al generar preview: ' + error.message, 'error');
        
        // Fallback: cargar video original
        const encodedFileName = encodeURIComponent(videoFileName);
        const videoPath = `/uploads/${sessionFolder}/${encodedFileName}`;
        console.log('⚠️ Cargando video original como fallback:', videoPath);
        loadProcessingROIVideoElement(videoPath);
    });
}

function loadProcessingROIVideoElement(videoUrl) {
    console.log('🎥 Cargando video element con URL:', videoUrl);
    
    const canvas = document.getElementById('roiProcessingCanvas');
    const ctx = canvas.getContext('2d');
    
    // Crear video element (oculto)
    if (!processingROIVideo) {
        processingROIVideo = document.createElement('video');
        processingROIVideo.setAttribute('crossorigin', 'anonymous');
        processingROIVideo.setAttribute('preload', 'auto');  // Necesario para capturar frame
        processingROIVideo.muted = true;
        processingROIVideo.autoplay = false;
        processingROIVideo.style.display = 'none';  // Oculto
        
        document.body.appendChild(processingROIVideo);
        console.log('✓ Elemento video creado (oculto) con preload=auto');
    } else {
        console.log('✓ Reutilizando elemento video existente');
    }
    
    // Escapar correctamente el nombre del archivo (espacios y caracteres especiales)
    console.log('🎥 URL del video:', videoUrl);
    
    // Limpiar eventos anteriores
    processingROIVideo.onloadedmetadata = null;
    processingROIVideo.onloadeddata = null;
    processingROIVideo.oncanplay = null;
    processingROIVideo.onerror = null;
    
    // Evento: Metadata cargada (duración, dimensiones)
    processingROIVideo.addEventListener('loadedmetadata', function onMetadata() {
        console.log('✓ loadedmetadata - duración:', processingROIVideo.duration, 's');
        console.log('✓ loadedmetadata - dimensiones:', processingROIVideo.videoWidth, 'x', processingROIVideo.videoHeight);
    });
    
    // Evento cuando el video está listo
    processingROIVideo.addEventListener('loadeddata', function onVideoReady() {
        console.log('✓ loadeddata - readyState:', processingROIVideo.readyState);
        console.log('✓ loadeddata - dimensiones:', processingROIVideo.videoWidth, 'x', processingROIVideo.videoHeight);
        console.log('✓ loadeddata - currentTime:', processingROIVideo.currentTime);
        
        // Verificar que tengamos dimensiones válidas
        if (!processingROIVideo.videoWidth || !processingROIVideo.videoHeight) {
            console.log('⏳ Esperando dimensiones del video...');
            return;
        }
        
        // Ocultar loader
        const loader = document.getElementById('videoLoadingIndicator');
        if (loader) {
            console.log('✓ Ocultando loader');
            loader.style.display = 'none';
        }
        
        // Mostrar canvas e instrucciones
        console.log('✓ Mostrando canvas');
        canvas.style.display = 'block';
        const instructions = document.getElementById('canvasInstructions');
        if (instructions) instructions.style.display = 'flex';
        
        // Mostrar controles
        const controls = document.getElementById('videoControlsProcessing');
        if (controls) controls.style.display = 'flex';
        
        // Habilitar sidebar
        const sidebar = document.getElementById('roiProcessingSidebar');
        if (sidebar) {
            sidebar.style.opacity = '1';
            sidebar.style.pointerEvents = 'auto';
        }
        
        // Actualizar paso
        const steps = document.querySelectorAll('.step');
        if (steps[0]) steps[0].querySelector('.step-label').textContent = 'Video cargado';
        if (steps[1]) steps[1].classList.add('active');
        
        // Actualizar seekbar
        const seekBar = document.getElementById('videoProcessingSeekBar');
        if (seekBar) {
            seekBar.max = processingROIVideo.duration;
            console.log('✓ Seekbar max:', seekBar.max);
        }
        
        // Inicializar coordenadas con el tamaño del video
        document.getElementById('roiProcessingX').value = 0;
        document.getElementById('roiProcessingY').value = 0;
        document.getElementById('roiProcessingW').value = processingROIVideo.videoWidth;
        document.getElementById('roiProcessingH').value = processingROIVideo.videoHeight;
        
        // IMPORTANTE: Esperar un poco y luego capturar frame
        console.log('⏳ Esperando 500ms antes de capturar frame...');
        setTimeout(() => {
            console.log('🎬 Intentando capturar primer frame...');
            captureProcessingFrame();
            
            // Dibujar ROI inicial
            setTimeout(() => {
                console.log('📐 Dibujando ROI inicial...');
                updateProcessingROIPreview();
            }, 200);
        }, 500);
    });
    
    // También escuchar canplay como backup
    processingROIVideo.addEventListener('canplay', function onCanPlay() {
        console.log('✓ canplay event - readyState:', processingROIVideo.readyState);
    });
    
    // Evento de error
    processingROIVideo.addEventListener('error', function(e) {
        console.error('❌ Error cargando video:', e);
        console.error('❌ Video src:', processingROIVideo.src);
        console.error('❌ Video error code:', processingROIVideo.error ? processingROIVideo.error.code : 'unknown');
        console.error('❌ Video error message:', processingROIVideo.error ? processingROIVideo.error.message : 'unknown');
        
        let errorMsg = 'Error al cargar el video';
        if (processingROIVideo.error) {
            switch(processingROIVideo.error.code) {
                case 1: errorMsg = 'Carga de video abortada'; break;
                case 2: errorMsg = 'Error de red al cargar video'; break;
                case 3: errorMsg = 'Error al decodificar el video'; break;
                case 4: errorMsg = 'Formato de video no soportado'; break;
            }
        }
        
        const loader = document.getElementById('videoLoadingIndicator');
        if (loader) {
            loader.innerHTML = `<div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${errorMsg}</p>
                <small style="color: #999; margin-top: 10px;">Ruta: ${processingROIVideo.src}</small>
            </div>`;
        }
        showNotification('❌ ' + errorMsg, 'error');
    });
    
    // Seekbar control
    const seekBar = document.getElementById('videoProcessingSeekBar');
    if (seekBar) {
        seekBar.addEventListener('input', function() {
            if (processingROIVideo) {
                processingROIVideo.currentTime = this.value;
                setTimeout(() => captureProcessingFrame(), 100); // Pequeño delay para que el frame se actualice
            }
        });
    }
    
    // Cargar el video
    console.log('📹 Cargando video desde:', videoUrl);
    processingROIVideo.src = videoUrl;
    processingROIVideo.load();
}

function captureProcessingFrame() {
    if (!processingROIVideo || !processingROICanvas) {
        console.log('⚠️ Video o canvas no disponible');
        return;
    }
    
    const canvas = processingROICanvas;
    const ctx = processingROICtx;
    const video = processingROIVideo;
    
    console.log('🎬 captureProcessingFrame - readyState:', video.readyState);
    
    // Verificar que el video esté listo (readyState >= HAVE_CURRENT_DATA = 2)
    if (video.readyState < 2) {
        console.log('⏳ Video no está listo (readyState:', video.readyState, ') - esperando...');
        // Intentar de nuevo en 100ms
        setTimeout(() => captureProcessingFrame(), 100);
        return;
    }
    
    // Verificar dimensiones válidas
    if (!video.videoWidth || !video.videoHeight) {
        console.log('⚠️ Dimensiones del video no disponibles:', video.videoWidth, 'x', video.videoHeight);
        return;
    }
    
    console.log('✓ Dibujando frame -', video.videoWidth, 'x', video.videoHeight);
    
    // Escalar video para ajustar al canvas
    const scale = Math.min(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
    const w = video.videoWidth * scale;
    const h = video.videoHeight * scale;
    const x = (canvas.width - w) / 2;
    const y = (canvas.height - h) / 2;
    
    console.log('📐 Canvas:', canvas.width, 'x', canvas.height, '| Video escalado:', w, 'x', h, '| Offset:', x, ',', y);
    
    // Limpiar canvas (fondo negro)
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Dibujar video frame
    try {
        ctx.drawImage(video, x, y, w, h);
        console.log('✓ Frame dibujado exitosamente');
    } catch (e) {
        console.error('❌ Error dibujando frame:', e);
        return;
    }
    
    // Guardar escala para conversión de coordenadas
    canvas.dataset.videoScale = scale;
    canvas.dataset.videoOffsetX = x;
    canvas.dataset.videoOffsetY = y;
    canvas.dataset.videoWidth = video.videoWidth;
    canvas.dataset.videoHeight = video.videoHeight;
}

function pauseProcessingROIVideo() {
    if (!processingROIVideo) return;
    
    const btn = document.getElementById('playPauseProcessingBtn');
    if (processingROIVideo.paused) {
        processingROIVideo.play();
        btn.innerHTML = '<i class="fas fa-pause"></i>';
    } else {
        processingROIVideo.pause();
        btn.innerHTML = '<i class="fas fa-play"></i>';
    }
}

function initProcessingROICanvas() {
    const canvas = document.getElementById('roiProcessingCanvas');
    if (!canvas) {
        console.log('❌ Canvas no encontrado');
        return;
    }
    
    console.log('✓ Inicializando canvas ROI para procesamiento');
    
    // Actualizar referencias globales
    processingROICanvas = canvas;
    processingROICtx = canvas.getContext('2d');
    
    let isDrawing = false;
    let startX, startY;
    
    // NO clonar - solo agregar eventos directamente
    canvas.addEventListener('mousedown', function(e) {
        const rect = canvas.getBoundingClientRect();
        // Convertir coordenadas del navegador a coordenadas del canvas interno
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;
        
        console.log('🖱️ Mouse down - Browser:', e.clientX - rect.left, e.clientY - rect.top);
        console.log('🖱️ Mouse down - Canvas:', x, y, '| Scale:', scaleX, scaleY);
        isDrawing = true;
        startX = x;
        startY = y;
    });
    
    canvas.addEventListener('mousemove', function(e) {
        if (!isDrawing) return;
        
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const currentX = (e.clientX - rect.left) * scaleX;
        const currentY = (e.clientY - rect.top) * scaleY;
        
        // Redibujar frame
        captureProcessingFrame();
        
        // Dibujar rectángulo temporal
        const ctx = processingROICtx;
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
        ctx.setLineDash([]);
    });
    
    canvas.addEventListener('mouseup', function(e) {
        if (!isDrawing) return;
        
        console.log('🖱️ Mouse up - finalizando selección');
        isDrawing = false;
        
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const endX = (e.clientX - rect.left) * scaleX;
        const endY = (e.clientY - rect.top) * scaleY;
        
        console.log('🖱️ Mouse up - Canvas:', endX, endY);
        
        // Convertir coordenadas de canvas a coordenadas de video
        const videoScale = parseFloat(canvas.dataset.videoScale) || 1;
        const offsetX = parseFloat(canvas.dataset.videoOffsetX) || 0;
        const offsetY = parseFloat(canvas.dataset.videoOffsetY) || 0;
        
        const videoX = Math.round((Math.min(startX, endX) - offsetX) / videoScale);
        const videoY = Math.round((Math.min(startY, endY) - offsetY) / videoScale);
        const videoW = Math.round(Math.abs(endX - startX) / videoScale);
        const videoH = Math.round(Math.abs(endY - startY) / videoScale);
        
        console.log('📐 ROI en canvas:', Math.min(startX, endX), Math.min(startY, endY), Math.abs(endX - startX), Math.abs(endY - startY));
        console.log('📐 ROI en video:', videoX, videoY, videoW, videoH);
        console.log('📐 Offset y escala:', offsetX, offsetY, videoScale);
        
        // Actualizar inputs
        document.getElementById('roiProcessingX').value = Math.max(0, videoX);
        document.getElementById('roiProcessingY').value = Math.max(0, videoY);
        document.getElementById('roiProcessingW').value = videoW;
        document.getElementById('roiProcessingH').value = videoH;
        
        // Actualizar preview
        updateProcessingROIPreview();
    });
    
    console.log('✓ Canvas ROI inicializado con eventos');
}

function updateProcessingROIPreview() {
    if (!processingROICanvas || !processingROIVideo) return;
    
    // Solo redibujar si el video ya está cargado
    if (processingROIVideo.readyState < 2) {
        console.log('⏳ Video aún no está listo para preview');
        return;
    }
    
    // Redibujar frame actual
    captureProcessingFrame();
    
    // Obtener dimensiones del video
    const videoWidth = processingROIVideo.videoWidth;
    const videoHeight = processingROIVideo.videoHeight;
    
    // Obtener coordenadas
    let x = parseInt(document.getElementById('roiProcessingX').value) || 0;
    let y = parseInt(document.getElementById('roiProcessingY').value) || 0;
    let w = parseInt(document.getElementById('roiProcessingW').value) || 0;
    let h = parseInt(document.getElementById('roiProcessingH').value) || 0;
    
    // ✅ VALIDACIÓN: Forzar valores dentro de los límites del video
    if (x < 0) {
        x = 0;
        document.getElementById('roiProcessingX').value = 0;
    }
    if (x >= videoWidth) {
        x = videoWidth - 1;
        document.getElementById('roiProcessingX').value = x;
    }
    
    if (y < 0) {
        y = 0;
        document.getElementById('roiProcessingY').value = 0;
    }
    if (y >= videoHeight) {
        y = videoHeight - 1;
        document.getElementById('roiProcessingY').value = y;
    }
    
    if (w < 1) {
        w = 1;
        document.getElementById('roiProcessingW').value = 1;
    }
    if (x + w > videoWidth) {
        w = videoWidth - x;
        document.getElementById('roiProcessingW').value = w;
    }
    
    if (h < 1) {
        h = 1;
        document.getElementById('roiProcessingH').value = 1;
    }
    if (y + h > videoHeight) {
        h = videoHeight - y;
        document.getElementById('roiProcessingH').value = h;
    }
    
    // Convertir coordenadas de video a canvas
    const canvas = processingROICanvas;
    const scale = parseFloat(canvas.dataset.videoScale) || 1;
    const offsetX = parseFloat(canvas.dataset.videoOffsetX) || 0;
    const offsetY = parseFloat(canvas.dataset.videoOffsetY) || 0;
    
    const canvasX = x * scale + offsetX;
    const canvasY = y * scale + offsetY;
    const canvasW = w * scale;
    const canvasH = h * scale;
    
    // Dibujar ROI
    const ctx = processingROICtx;
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 3;
    ctx.strokeRect(canvasX, canvasY, canvasW, canvasH);
    
    // Dibujar etiqueta
    ctx.fillStyle = '#00ff00';
    ctx.font = 'bold 14px Arial';
    ctx.fillText(`ROI: ${w}x${h}`, canvasX + 5, canvasY - 5);
}

function resetProcessingROI() {
    if (!processingROIVideo) return;
    
    document.getElementById('roiProcessingX').value = 0;
    document.getElementById('roiProcessingY').value = 0;
    document.getElementById('roiProcessingW').value = processingROIVideo.videoWidth;
    document.getElementById('roiProcessingH').value = processingROIVideo.videoHeight;
    
    updateProcessingROIPreview();
}

function confirmAndStartProcessing() {
    // Obtener coordenadas del ROI
    const x = parseInt(document.getElementById('roiProcessingX').value) || 0;
    const y = parseInt(document.getElementById('roiProcessingY').value) || 0;
    const w = parseInt(document.getElementById('roiProcessingW').value) || 0;
    const h = parseInt(document.getElementById('roiProcessingH').value) || 0;
    
    // ✅ VALIDACIÓN CRÍTICA: No permitir coordenadas negativas
    if (x < 0 || y < 0 || w <= 0 || h <= 0) {
        showNotification('❌ ROI inválido: Las coordenadas no pueden ser negativas y las dimensiones deben ser positivas', 'error');
        return;
    }
    
    // Validar ROI
    if (w === 0 || h === 0) {
        showNotification('⚠️ Debes seleccionar un área válida', 'error');
        return;
    }
    
    // Guardar ROI en variable global
    window.currentROI = [x, y, w, h];
    
    // Limpiar video temporal
    if (processingROIVideo) {
        processingROIVideo.pause();
        processingROIVideo.remove();
        processingROIVideo = null;
    }
    
    // Iniciar procesamiento con el ROI configurado
    showNotification('🚀 Iniciando análisis con área configurada...', 'success');
    startProcessing(null, window.pendingFolderId);
}

function cancelROIProcessing() {
    // Limpiar video temporal
    if (processingROIVideo) {
        processingROIVideo.pause();
        processingROIVideo.remove();
        processingROIVideo = null;
    }
    
    // Limpiar variables pendientes
    window.pendingFolderId = null;
    window.pendingFolderPath = null;
    window.currentROI = null;
    
    // ✅ Redirigir al inicio en lugar de ir a upload
    window.location.href = '/';
}

function loadAdvancedConfig() {
    const config = JSON.parse(localStorage.getItem('advancedConfig') || '{"threshold":0.5,"variance":16,"cooldown":8000,"duplicateFiles":true}');
    document.getElementById('thresholdPercentage').value = config.threshold;
    document.getElementById('varThreshold').value = config.variance;
    document.getElementById('cooldownMs').value = config.cooldown;
    
    // Cargar preferencia de carpeta local (solo en Electron)
    console.log('📋 Cargando configuración avanzada...', { isElectronApp, config });
    if (isElectronApp) {
        const duplicateFilesCheckbox = document.getElementById('duplicateFiles');
        if (duplicateFilesCheckbox) {
            duplicateFilesCheckbox.checked = config.duplicateFiles !== false; // Por defecto true
            console.log('✅ Checkbox de duplicar archivos cargado:', duplicateFilesCheckbox.checked);
        } else {
            console.warn('⚠️ No se encontró el checkbox duplicateFiles');
        }
    }
}

function saveAdvancedConfig() {
    const config = {
        threshold: parseFloat(document.getElementById('thresholdPercentage').value),
        variance: parseInt(document.getElementById('varThreshold').value),
        cooldown: parseInt(document.getElementById('cooldownMs').value)
    };
    
    // Guardar preferencia de carpeta local (solo en Electron)
    if (isElectronApp) {
        const duplicateFilesCheckbox = document.getElementById('duplicateFiles');
        if (duplicateFilesCheckbox) {
            config.duplicateFiles = duplicateFilesCheckbox.checked;
            console.log('💾 Guardando preferencia de duplicar archivos:', config.duplicateFiles);
        }
    }
    
    localStorage.setItem('advancedConfig', JSON.stringify(config));
    console.log('✅ Configuración guardada:', config);
    showNotification('✓ Configuración avanzada guardada', 'success');
}

function resetAdvancedConfig() {
    document.getElementById('thresholdPercentage').value = 0.5;
    document.getElementById('varThreshold').value = 16;
    document.getElementById('cooldownMs').value = 8000;
    saveAdvancedConfig();
}

// Cargar historial en el sidebar
async function loadSidebarHistory() {
    const sidebarTree = document.getElementById('sidebar-tree');
    
    // Verificar que el elemento existe
    if (!sidebarTree) {
        console.warn('⚠️ Elemento sidebar-tree no encontrado');
        return;
    }
    
    try {
        const response = await fetch(buildApiUrl('/api/folders'));
        const data = await response.json();
        
        if (!data.success || data.folders.length === 0) {
            sidebarTree.innerHTML = `
                <div style="text-align: center; padding: 15px; font-size: 0.85rem; color: var(--light-text);">
                    <i class="fas fa-inbox"></i><br>
                    Sin análisis previos
                </div>
            `;
            return;
        }
        
        let html = '<div class="tree-compact">';
        
        data.folders.slice(0, 5).forEach(folder => {
            html += `
                <div class="tree-item-compact" onclick="showFolderDetails(${folder.id})">
                    <i class="fas fa-folder" style="color: var(--secondary-color);"></i>
                    <span style="font-size: 0.85rem;">${folder.name}</span>
                </div>
            `;
        });
        
        html += '</div>';
        sidebarTree.innerHTML = html;
        
    } catch (error) {
        console.error('Error cargando historial:', error);
        sidebarTree.innerHTML = `
            <div style="text-align: center; padding: 15px; font-size: 0.85rem; color: var(--danger-color);">
                Error al cargar
            </div>
        `;
    }
}

// Mostrar detalles de una carpeta
function showFolderDetails(folderId) {
    loadView('folders');
    // Aquí se puede agregar lógica para resaltar la carpeta seleccionada
}

// ============================================================================
// EXPORTAR FUNCIONES AL SCOPE GLOBAL (CRÍTICO - DEBE ESTAR ANTES DE DOMContentLoaded)
// ============================================================================
console.log('Exportando funciones al scope global...');

// ======================================================
// RESTRICCIÓN: No permitir activar IA si no está Generar Clips
// ======================================================
(() => {
    // Mapa: checkbox IA -> checkbox Generar Clips dependiente
    const clipAIDependencies = {
        'useAiAnalysisOption': 'generateClipsOption',
        'folderUseAiAnalysisOption': 'folderGenerateClipsOption',
        'videoUseAiAnalysisOption': 'videoGenerateClipsOption',
        'processingUseAI': 'processingGenerateClips'
    };

    function updateAiState(generateId, aiId) {
        const gen = document.getElementById(generateId);
        const ai = document.getElementById(aiId);
        if (!ai) return;
        const shouldEnable = !!(gen && gen.checked);
        ai.disabled = !shouldEnable;
        if (!shouldEnable) {
            // Si no debería estar activo, asegurarnos que quede sin marcar
            ai.checked = false;
        }
    }

    // Inicializar estados actuales (por si ya existen en el DOM)
    function initAiClipDependencies() {
        Object.entries(clipAIDependencies).forEach(([aiId, genId]) => {
            updateAiState(genId, aiId);
        });
    }

    // Manejo por delegación: cuando cambie cualquier checkbox relevante
    document.addEventListener('change', (e) => {
        const target = e.target;
        if (!target || !target.id) return;

        // Si se ha cambiado una casilla "Generar Clips", actualizar el/los IA dependientes
        const genId = target.id;
        Object.entries(clipAIDependencies).forEach(([aiId, gId]) => {
            if (gId === genId) {
                // Actualizar el estado de la casilla de IA asociada
                updateAiState(gId, aiId);
            }
        });

        // Si se intenta marcar una casilla de IA cuando su gen está desmarcado,
        // activar automáticamente "Generar Clips" (mejor UX):
        if (clipAIDependencies.hasOwnProperty(target.id)) {
            const requiredGenId = clipAIDependencies[target.id];
            const requiredGen = document.getElementById(requiredGenId);
            if (!requiredGen) return;
            // Si el usuario acaba de marcar IA y el "Generar Clips" está desmarcado,
            // marcar "Generar Clips" automáticamente para permitir IA.
            if (target.checked && !requiredGen.checked) {
                requiredGen.checked = true;
                // Asegurar que el estado visual/disable se actualice
                updateAiState(requiredGenId, target.id);
                const msg = 'Se ha activado automáticamente "Generar Clips" porque activaste IA.';
                if (typeof showNotification === 'function') {
                    showNotification(msg, 'info');
                }
            }
        }
    }, true);

    // Inicializar al cargar el script. Si el DOM no está listo aún, también se vuelve a inicializar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAiClipDependencies);
    } else {
        initAiClipDependencies();
    }
    
    // Exponer funciones al scope global para que puedan ser llamadas desde otros lugares
    window.initAiClipDependencies = initAiClipDependencies;
    window.updateAiState = updateAiState;
})();

// Funciones de navegación
window.loadView = loadView;
window.showFoldersAndVideosView = showFoldersAndVideosView;
window.showSelectFolderView = showSelectFolderView;
window.showSelectVideoView = showSelectVideoView;
window.showProcessView = showProcessView;
window.showROIConfigView = showROIConfigView;
window.showAdvancedConfigView = showAdvancedConfigView;
window.showLogsView = showLogsView;
window.showHelpView = showHelpView;

// Funciones de carpetas y videos
window.loadFolders = loadFolders;
window.toggleFolder = toggleFolder;
window.toggleVideo = toggleVideo;
window.loadClipsForVideo = loadClipsForVideo;
window.showClipDetails = showClipDetails;
window.showFolderDetails = showFolderDetails;

// Funciones de eliminación
window.deleteClip = deleteClip;
window.showClipDetails = showClipDetails;
window.closeClipModal = closeClipModal;
window.downloadClip = downloadClip;
window.deleteClipFromModal = deleteClipFromModal;
window.deleteVideo = deleteVideo;
window.deleteFolder = deleteFolder;
window.makeFieldEditable = makeFieldEditable;
window.saveFieldValue = saveFieldValue;

// Funciones de búsqueda y filtrado
window.filterTree = filterTree;
window.sortTree = sortTree;

// Funciones de logs
window.refreshLogs = refreshLogs;
window.filterLogs = filterLogs;
window.clearLogsDisplay = clearLogsDisplay;
window.toggleAutoRefresh = toggleAutoRefresh;
window.downloadLogs = downloadLogs;

// Funciones de sistema
window.loadSystemStatus = loadSystemStatus;

// Funciones de ROI
window.initROICanvas = initROICanvas;
window.loadROIVideo = loadROIVideo;
window.pauseROIVideo = pauseROIVideo;
window.captureFrame = captureFrame;
window.updateROIPreview = updateROIPreview;
window.updateROIPreviewCanvas = updateROIPreviewCanvas;
window.clearROI = clearROI;

// Funciones de ROI para procesamiento
window.showROISelectionForProcessing = showROISelectionForProcessing;
window.loadProcessingROIVideo = loadProcessingROIVideo;
window.captureProcessingFrame = captureProcessingFrame;
window.pauseProcessingROIVideo = pauseProcessingROIVideo;
window.initProcessingROICanvas = initProcessingROICanvas;
window.updateProcessingROIPreview = updateProcessingROIPreview;
window.resetProcessingROI = resetProcessingROI;
window.confirmAndStartProcessing = confirmAndStartProcessing;
window.cancelROIProcessing = cancelROIProcessing;
window.saveROIConfig = saveROIConfig;
window.resetROIConfig = resetROIConfig;


// Funciones de Directo para procesamiento
//window.showDirectoInitView();

// Funciones de configuración
window.saveAdvancedConfig = saveAdvancedConfig;
window.resetAdvancedConfig = resetAdvancedConfig;

// Funciones de carga de archivos
window.uploadFiles = uploadFiles;
window.handleFolderSelect = handleFolderSelect;
window.handleVideoSelect = handleVideoSelect;
window.handleDragOver = handleDragOver;
window.handleDragLeave = handleDragLeave;

// Funciones de utilidad
window.loadSidebarHistory = loadSidebarHistory;

// Funciones de procesamiento
window.startProcessing = startProcessing;
window.startProcessingPolling = startProcessingPolling;
window.updateProcessingStatus = updateProcessingStatus;
window.onProcessingCompleted = onProcessingCompleted;
window.checkProcessingStatus = checkProcessingStatus;
window.showNoProcessingView = showNoProcessingView;
window.showActiveProcessingView = showActiveProcessingView;
window.showCompletedView = showCompletedView;
window.clearCompletedFlag = clearCompletedFlag;
window.clearCompletedFlagSilent = clearCompletedFlagSilent;
window.updateSidebarCompletedBadge = updateSidebarCompletedBadge;

// Funciones de dashboard/estadísticas
window.loadDashboardStats = loadDashboardStats;
window.createDashboardChart = createDashboardChart;

// Funciones de Excel
window.loadExcelFilesList = loadExcelFilesList;
window.loadSelectedExcel = loadSelectedExcel;
window.switchSheet = switchSheet;
window.saveExcelChanges = saveExcelChanges;
window.downloadExcelFile = downloadExcelFile;


console.log('✓ Funciones exportadas correctamente');
console.log('✓ loadView disponible:', typeof window.loadView);

// ============================================================================
// INICIALIZACIÓN
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('✓ DOM cargado - Inicializando aplicación...');
    
    // Cargar historial en sidebar
    if (typeof loadSidebarHistory === 'function') {
        loadSidebarHistory();
    }
    
    // Verificar si hay un parámetro 'view' en la URL para cargar una vista específica
    const urlParams = new URLSearchParams(window.location.search);
    const viewParam = urlParams.get('view');
    
    if (viewParam) {
        console.log(`📍 Parámetro 'view' detectado: ${viewParam}`);
        // Cargar la vista especificada
        loadView(viewParam, null);
    } else {
        // El contenido se cargará desde el HTML de cada ruta
        console.log('Aplicación inicializada - esperando interacción del usuario');
    }
});

// Exportar funciones globales necesarias
window.loadView = loadView;



