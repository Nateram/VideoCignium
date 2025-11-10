// dashboard.js - Gestión del dashboard

let objectsChart = null;

// Cargar datos al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadFolders();
    
    // Si viene de un procesamiento completado, forzar reload
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('reload') === 'true') {
        // Limpiar el parámetro de la URL
        window.history.replaceState({}, '', '/dashboard');
        
        // Forzar recarga después de un pequeño delay
        setTimeout(() => {
            loadStats();
            loadFolders();
        }, 500);
    }
});

// Cargar estadísticas
async function loadStats() {
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
            
            // Crear gráfico de objetos
            createObjectsChart(stats.objects);
        }
    } catch (error) {
        console.error('Error al cargar estadísticas:', error);
        showNotification('Error al cargar estadísticas', 'error');
    }
}

// Crear gráfico de objetos detectados
function createObjectsChart(objects) {
    const ctx = document.getElementById('objectsChart');
    
    if (!ctx) return;
    
    // Destruir gráfico anterior si existe
    if (objectsChart) {
        objectsChart.destroy();
    }
    
    const labels = objects.map(obj => obj.type || 'Desconocido');
    const values = objects.map(obj => obj.count);
    
    const colors = [
        '#3498DB', '#E74C3C', '#27AE60', '#F39C12', 
        '#9B59B6', '#1ABC9C', '#E67E22', '#95A5A6'
    ];
    
    objectsChart = new Chart(ctx, {
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

// Cargar carpetas
async function loadFolders() {
    const foldersList = document.getElementById('foldersList');
    
    try {
        const response = await fetch(buildApiUrl('/api/folders'));
        const data = await response.json();
        
        if (data.success) {
            foldersList.innerHTML = '';
            
            if (data.folders.length === 0) {
                foldersList.innerHTML = '<p class="loading-text">No hay carpetas analizadas aún</p>';
                return;
            }
            
            data.folders.forEach(folder => {
                const folderItem = document.createElement('div');
                folderItem.className = 'folder-item';
                folderItem.innerHTML = `
                    <div class="folder-name">
                        <i class="fas fa-folder"></i> ${folder.name}
                    </div>
                    <div class="folder-info">
                        <i class="fas fa-calendar"></i> ${formatDate(folder.upload_date)}
                        <br>
                        <i class="fas fa-map-marker-alt"></i> ${folder.path}
                    </div>
                `;
                folderItem.onclick = () => showFolderVideos(folder.id, folder.name);
                foldersList.appendChild(folderItem);
            });
        }
    } catch (error) {
        console.error('Error al cargar carpetas:', error);
        foldersList.innerHTML = '<p class="loading-text" style="color: #E74C3C;">Error al cargar carpetas</p>';
    }
}

// Mostrar videos de una carpeta
async function showFolderVideos(folderId, folderName) {
    const modal = document.getElementById('videosModal');
    const modalTitle = document.getElementById('modalTitle');
    const videosList = document.getElementById('videosList');
    
    modalTitle.innerHTML = `<i class="fas fa-video"></i> Videos - ${folderName}`;
    videosList.innerHTML = '<p class="loading-text"><i class="fas fa-spinner fa-spin"></i> Cargando...</p>';
    
    modal.classList.add('show');
    
    try {
        const response = await fetch(`/api/folder/${folderId}`);
        const data = await response.json();
        
        if (data.success) {
            videosList.innerHTML = '';
            
            if (data.videos.length === 0) {
                videosList.innerHTML = '<p class="loading-text">No hay videos en esta carpeta</p>';
                return;
            }
            
            data.videos.forEach(video => {
                const videoItem = document.createElement('div');
                videoItem.className = 'video-item';
                videoItem.innerHTML = `
                    <div class="video-info">
                        <h3><i class="fas fa-file-video"></i> ${video.name}</h3>
                        <p>
                            <i class="fas fa-calendar"></i> ${formatDate(video.creation_date)}
                            <br>
                            <i class="fas fa-film"></i> ${video.clip_count} clips detectados
                        </p>
                    </div>
                    <button class="btn btn-primary" onclick="showVideoClips(${video.id}, '${video.name}')">
                        <i class="fas fa-eye"></i> Ver Clips
                    </button>
                `;
                videosList.appendChild(videoItem);
            });
        }
    } catch (error) {
        console.error('Error al cargar videos:', error);
        videosList.innerHTML = '<p class="loading-text" style="color: #E74C3C;">Error al cargar videos</p>';
    }
}

// Cerrar modal de videos
function closeVideosModal() {
    const modal = document.getElementById('videosModal');
    modal.classList.remove('show');
}

// Mostrar clips de un video
async function showVideoClips(videoId, videoName) {
    const modal = document.getElementById('clipsModal');
    const modalTitle = document.getElementById('clipsModalTitle');
    const clipsList = document.getElementById('clipsList');
    
    modalTitle.innerHTML = `<i class="fas fa-film"></i> Clips - ${videoName}`;
    clipsList.innerHTML = '<p class="loading-text"><i class="fas fa-spinner fa-spin"></i> Cargando clips...</p>';
    
    // Cerrar modal de videos
    closeVideosModal();
    
    modal.classList.add('show');
    
    try {
        const response = await fetch(`/api/video/${videoId}/clips`);
        const data = await response.json();
        
        if (data.success) {
            clipsList.innerHTML = '';
            
            if (data.clips.length === 0) {
                clipsList.innerHTML = '<p class="loading-text">No hay clips para este video</p>';
                return;
            }
            
            data.clips.forEach(clip => {
                console.log('🎬 Renderizando clip:', clip);
                console.log('📹 URL del clip:', clip.url);
                
                const clipItem = document.createElement('div');
                clipItem.className = 'clip-item';
                clipItem.innerHTML = `
                    <video class="clip-video" controls>
                        <source src="${clip.url}" type="video/mp4">
                        Tu navegador no soporta el tag de video.
                    </video>
                    <div class="clip-info">
                        <h4><i class="fas fa-film"></i> ${clip.name}</h4>
                        <div class="clip-meta">
                            <span class="clip-tag">
                                <i class="fas fa-clock"></i> ${formatDate(clip.event_date)}
                            </span>
                            ${clip.object_type ? `
                                <span class="clip-tag object">
                                    <i class="fas fa-tag"></i> ${clip.object_type}
                                </span>
                            ` : ''}
                            ${clip.object_color ? `
                                <span class="clip-tag color">
                                    <i class="fas fa-palette"></i> ${clip.object_color}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                `;
                
                // Agregar listener de error al video
                const videoElement = clipItem.querySelector('video');
                videoElement.addEventListener('error', (e) => {
                    console.error('❌ Error al cargar video:', clip.url);
                    console.error('Error del video:', e);
                    console.error('Error de la fuente:', videoElement.error);
                });
                
                videoElement.addEventListener('loadeddata', () => {
                    console.log('✅ Video cargado correctamente:', clip.url);
                });
                
                clipsList.appendChild(clipItem);
            });
        }
    } catch (error) {
        console.error('Error al cargar clips:', error);
        clipsList.innerHTML = '<p class="loading-text" style="color: #E74C3C;">Error al cargar clips</p>';
    }
}

// Cerrar modal de clips
function closeClipsModal() {
    const modal = document.getElementById('clipsModal');
    modal.classList.remove('show');
    
    // Pausar todos los videos
    const videos = modal.querySelectorAll('video');
    videos.forEach(video => video.pause());
}

// Cerrar modales al hacer clic fuera
window.onclick = function(event) {
    const videosModal = document.getElementById('videosModal');
    const clipsModal = document.getElementById('clipsModal');
    
    if (event.target === videosModal) {
        closeVideosModal();
    }
    if (event.target === clipsModal) {
        closeClipsModal();
    }
}

// Exportar funciones globales
window.showFolderVideos = showFolderVideos;
window.closeVideosModal = closeVideosModal;
window.showVideoClips = showVideoClips;
window.closeClipsModal = closeClipsModal;


