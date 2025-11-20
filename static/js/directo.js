// directo.js - Gestión de análisis en directo y logs de eventos

let liveLogsInterval = null;
let roi = null;
let capturedFrame = null;

// Estado global para saber si el análisis está activo y el ROI confirmado
window.directoAnalysisActive = false;
window.directoROI = null;

// Variable global para el ROI actual
window.currentROI = null;

// Captura el primer frame del stream MJPEG y lo muestra en el canvas
window.captureLiveFrame = async function() {
    // Asegurarse de que el canvas está renderizado
    const canvas = document.getElementById('roiProcessingCanvas');
    if (!canvas) {
        showNotification('No se encontró el canvas para mostrar el frame. Recarga la pestaña de configuración.', 'error');
        return;
    }
    const streamUrl = document.getElementById('streamUrlInput').value;
    try {
        // Obtener el primer frame JPEG del stream
        const response = await fetch(streamUrl, { method: 'GET' });
        const reader = response.body.getReader();
        let bytes = [];
        let foundStart = false, foundEnd = false;
        while (!foundEnd) {
            const { value, done } = await reader.read();
            if (done) break;
            for (let i = 0; i < value.length; i++) {
                if (!foundStart && value[i] === 0xFF && value[i+1] === 0xD8) {
                    foundStart = true;
                    bytes = [];
                }
                if (foundStart) bytes.push(value[i]);
                if (foundStart && value[i] === 0xFF && value[i+1] === 0xD9) {
                    bytes.push(value[i+1]);
                    foundEnd = true;
                    break;
                }
            }
        }
        // Convertir a imagen
        const blob = new Blob([new Uint8Array(bytes)], { type: 'image/jpeg' });
        const imgUrl = URL.createObjectURL(blob);
        const img = new window.Image();
        img.onload = function() {
            capturedFrame = img;
            canvas.width = img.width;
            canvas.height = img.height;
            canvas.getContext('2d').drawImage(img, 0, 0, img.width, img.height);
            // Inicializar canvas y eventos de ROI
            initDirectoProcessingCanvas();
            updateStartLiveBtnState();
        };
        img.src = imgUrl;
    } catch (err) {
        showNotification('Error al capturar frame del directo', 'error');
    }
};

// Iniciar análisis en directo solo tras confirmar ROI
function startLiveAnalysis() {
    const streamUrl = document.getElementById('streamUrlInput').value;
    if (!roi) {
        showNotification('Confirma primero la zona de interés (ROI)', 'warning');
        return;
    }
    fetch(buildApiUrl('/api/live/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            stream_url: streamUrl,
            roi: roi
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showNotification('Análisis en directo iniciado', 'success');
            startLiveLogsPolling();
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    });
}

function startLiveLogsPolling() {
    if (liveLogsInterval) clearInterval(liveLogsInterval);
    liveLogsInterval = setInterval(loadLiveLogs, 1000);
}

async function showDirectoView() {
    // Solo actualizar el título sin tocar los botones del top-bar
    if (window.updateViewTitle) {
        updateViewTitle('📡 Análisis en Directo');
    }
    // Carga el HTML de la vista en directo (puedes usar un template string aquí)
    const content = `
        <div class="directo-container" style="display: flex; gap: 32px; margin-top: 40px;">
            <div style="flex: 2;">
                <h2>Stream en Directo</h2>
                <input type="text" id="streamUrlInput" value="http://localhost:8080/video_feed" style="width:100%;margin-bottom:10px;">
                <button class="btn" id="captureFrameBtn" onclick="captureLiveFrame()" style="margin-bottom:10px;">
                    <i class="fas fa-camera"></i> Capturar Frame
                </button>
                <div id="liveFrameContainer" style="position:relative; display:none;">
                    <canvas id="roiCanvas" width="480" height="360" style="border-radius:8px; border:2px solid #3B82F6; cursor:crosshair;"></canvas>
                </div>
                <button class="btn" onclick="confirmROI()" id="confirmROIBtn" disabled>
                    <i class="fas fa-check"></i> Confirmar ROI
                </button>
                <button class="btn" onclick="resetROI()" id="resetROIBtn" style="display:none;">
                    <i class="fas fa-eraser"></i> Resetear ROI
                </button>
                <div id="roiCoordsDisplay" style="margin-top:10px; color:#3B82F6;"></div>
                <button class="btn" id="startLiveBtn" onclick="startLiveAnalysis()" disabled>
                    <i class="fas fa-play"></i> Iniciar Análisis Directo
                </button>
            </div>
            <div style="flex: 1; background: #1e293b; border-radius: 12px; padding: 18px; color: #fff; min-width: 260px;">
                <h3>Logs de Eventos</h3>
                <div id="liveLogsPanel" style="height: 400px; overflow-y: auto; background: #222; border-radius: 8px; padding: 10px; font-size: 1.05em;"></div>
            </div>
        </div>
    `;
    document.getElementById('main-panel').innerHTML = content;
    // Eliminar carga dinámica de directo.js para evitar duplicados
    // if (!window.captureLiveFrame) {
    //     const script = document.createElement('script');
    //     script.src = '/static/js/directo.js';
    //     document.body.appendChild(script);
    // }
}

function loadLiveLogs() {
    fetch(buildApiUrl('/api/live/logs'))
        .then(res => res.json())
        .then (data => {
            if (data.success) {
                const logsPanel = document.getElementById('liveLogsPanel');
                if (logsPanel) {
                    logsPanel.innerHTML = data.logs.map(log =>
                        `<div class="live-log-entry">
                            <span class="live-log-time">${log.timestamp}</span>
                            <span class="live-log-msg">${log.message}</span>
                        </div>`
                    ).join('');
                }
            }
        });
}

// Exportar funciones globales
window.startLiveAnalysis = startLiveAnalysis;
window.startLiveLogsPolling = startLiveLogsPolling;
window.loadLiveLogs = loadLiveLogs;
window.confirmROI = window.confirmROI;
window.resetROI = window.resetROI;
window.showDirectoView = showDirectoView;

// Actualizar el src del <img> cuando cambie el campo de URL
const streamUrlInput = document.getElementById('streamUrlInput');
const liveStreamImg = document.getElementById('liveStreamImg');
if (streamUrlInput && liveStreamImg) {
    streamUrlInput.addEventListener('input', function() {
        liveStreamImg.src = this.value;
    });
}



window.showDirectoInitView = function() {
    // Si el análisis está activo, mostrar la vista de análisis directo
    if (window.directoAnalysisActive) {
        window.showDirectoLiveView();
        return;
    }
    // Solo actualizar el título sin tocar el top-bar completo
    if (window.updateViewTitle) {
        updateViewTitle('🎯 Análisis en Directo - Configurar ROI');
    }
    const content = `
        <div class="roi-processing-container">
            <!-- Banner de desarrollo -->
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%); border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <span style="font-size: 2.5em;">🚧</span>
                    <div>
                        <h3 style="margin: 0; color: #fff; font-size: 1.3em; font-weight: 600;">Apartado en Desarrollo</h3>
                        <p style="margin: 8px 0 0 0; color: #fff; opacity: 0.95; font-size: 1.05em;">
                            Esta sección es una <strong>demo de procesamiento en tiempo real personal</strong>. Las funcionalidades están en fase de pruebas y desarrollo.
                        </p>
                    </div>
                </div>
            </div>
            
            <div style="margin-bottom:24px;">
                <label for="streamUrlInput"><strong>URL del Stream MJPEG:</strong></label>
                <input type="text" id="streamUrlInput" value="http://localhost:8080/video_feed" style="width:100%;margin-bottom:10px;">
                <button class="btn" id="captureFrameBtn" onclick="captureLiveFrame()" style="margin-bottom:10px;">
                    <i class="fas fa-camera"></i> Capturar Frame
                </button>
            </div>
            <div class="roi-processing-content">
                <div class="roi-canvas-section">
                    <div class="canvas-wrapper" id="canvasWrapperProcessing">
                        <canvas id="roiProcessingCanvas" width="1000" height="600" style="display: block;"></canvas>
                        <div class="canvas-instructions" id="canvasInstructions" style="display: flex; margin-top: 10px;">
                            <i class="fas fa-mouse-pointer"></i>
                            <span>Arrastra con el mouse para dibujar el área de análisis</span>
                        </div>
                    </div>
                </div>
                <div class="roi-processing-sidebar" id="roiProcessingSidebar" style="opacity: 1; pointer-events: auto;">
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
                    <div class="roi-processing-actions">
                        <button class="btn btn-primary btn-block btn-large" onclick="confirmDirectoROI()">
                            <i class="fas fa-play-circle"></i> Iniciar Análisis
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('main-panel').innerHTML = content;
    // Inicializar canvas y eventos
    initDirectoProcessingCanvas();
    setTimeout(updateStartLiveBtnState, 100);
};

// ROI por defecto: ninguno seleccionado
function getDefaultROI() {
    return null;
}

// Al inicializar la selección de ROI, usar null si no hay uno guardado
function initDirectoProcessingCanvas() {
    const canvas = document.getElementById('roiProcessingCanvas');
    let ctx = canvas.getContext('2d');
    let isDrawing = false;
    let startX = 0, startY = 0;
    // Usar el ROI global si existe
    window.currentROI = window.directoROI || getDefaultROI();
    let frameImg = capturedFrame;
    // Dibuja el frame y el ROI
    function drawFrame() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (frameImg) ctx.drawImage(frameImg, 0, 0, canvas.width, canvas.height);
        if (window.currentROI && window.currentROI.w > 0 && window.currentROI.h > 0) {
            ctx.strokeStyle = '#3B82F6';
            ctx.lineWidth = 3;
            ctx.strokeRect(window.currentROI.x, window.currentROI.y, window.currentROI.w, window.currentROI.h);
            ctx.fillStyle = 'rgba(0,0,0,0.5)';
            ctx.fillRect(0, 0, canvas.width, window.currentROI.y);
            ctx.fillRect(0, window.currentROI.y, window.currentROI.x, window.currentROI.h);
            ctx.fillRect(window.currentROI.x + window.currentROI.w, window.currentROI.y, canvas.width - window.currentROI.x - window.currentROI.w, window.currentROI.h);
            ctx.fillRect(0, window.currentROI.y + window.currentROI.h, canvas.width, canvas.height - window.currentROI.y - window.currentROI.h);
        }
    }
    canvas.onmousedown = function(e) {
        isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        startX = (e.clientX - rect.left) * (canvas.width / rect.width);
        startY = (e.clientY - rect.top) * (canvas.height / rect.height);
    };
    canvas.onmousemove = function(e) {
        if (!isDrawing) return;
        const rect = canvas.getBoundingClientRect();
        const currentX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const currentY = (e.clientY - rect.top) * (canvas.height / rect.height);
        const x = Math.min(startX, currentX);
        const y = Math.min(startY, currentY);
        const w = Math.abs(currentX - startX);
        const h = Math.abs(currentY - startY);
        window.currentROI = { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) };
        document.getElementById('roiProcessingX').value = window.currentROI.x;
        document.getElementById('roiProcessingY').value = window.currentROI.y;
        document.getElementById('roiProcessingW').value = window.currentROI.w;
        document.getElementById('roiProcessingH').value = window.currentROI.h;
        drawFrame();
    };
    canvas.onmouseup = function(e) {
        isDrawing = false;
        drawFrame();
    };
    canvas.onmouseleave = function(e) {
        isDrawing = false;
    };
    if (window.currentROI) {
        document.getElementById('roiProcessingX').value = window.currentROI.x;
        document.getElementById('roiProcessingY').value = window.currentROI.y;
        document.getElementById('roiProcessingW').value = window.currentROI.w;
        document.getElementById('roiProcessingH').value = window.currentROI.h;
    } else {
        document.getElementById('roiProcessingX').value = '';
        document.getElementById('roiProcessingY').value = '';
        document.getElementById('roiProcessingW').value = '';
        document.getElementById('roiProcessingH').value = '';
    }
    drawFrame();
    // Inputs manuales
    window.updateProcessingROIPreview = function() {
        window.currentROI.x = parseInt(document.getElementById('roiProcessingX').value) || 0;
        window.currentROI.y = parseInt(document.getElementById('roiProcessingY').value) || 0;
        window.currentROI.w = parseInt(document.getElementById('roiProcessingW').value) || 640;
        window.currentROI.h = parseInt(document.getElementById('roiProcessingH').value) || 480;
        drawFrame();
        updateStartLiveBtnState();
    };
    window.resetProcessingROI = function() {
        window.currentROI = { x: 0, y: 0, w: capturedFrame ? capturedFrame.width : 640, h: capturedFrame ? capturedFrame.height : 480 };
        document.getElementById('roiProcessingX').value = window.currentROI.x;
        document.getElementById('roiProcessingY').value = window.currentROI.y;
        document.getElementById('roiProcessingW').value = window.currentROI.w;
        document.getElementById('roiProcessingH').value = window.currentROI.h;
        drawFrame();
        updateStartLiveBtnState();
    };
}

function updateStartLiveBtnState() {
    const hasFrame = !!capturedFrame;
    let roiToCheck = window.currentROI;
    const hasROI = roiToCheck && typeof roiToCheck.x === 'number' && typeof roiToCheck.y === 'number' && typeof roiToCheck.w === 'number' && typeof roiToCheck.h === 'number' && roiToCheck.w > 0 && roiToCheck.h > 0;
    const btn = document.getElementById('startLiveBtn');
    if (btn) {
        btn.disabled = !(hasFrame && hasROI);
    }
}

window.confirmDirectoROI = function() {
    // Validar frame y ROI antes de continuar
    if (!capturedFrame) {
        showNotification('Primero captura un frame del directo', 'warning');
        return;
    }
    if (!window.currentROI || typeof window.currentROI.x !== 'number' || typeof window.currentROI.y !== 'number' || typeof window.currentROI.w !== 'number' || typeof window.currentROI.h !== 'number' || window.currentROI.w < 10 || window.currentROI.h < 10) {
        showNotification('Selecciona una zona válida en el frame capturado (mínimo 10x10 px)', 'warning');
        return;
    }
    window.directoROI = [window.currentROI.x, window.currentROI.y, window.currentROI.w, window.currentROI.h];
    roi = window.directoROI; // Sincronizar variable global roi
    window.directoAnalysisActive = true;
    showNotification('ROI confirmado. Iniciando análisis en directo...', 'success');
    startLiveAnalysis();
    window.showDirectoLiveView();
    updateStartLiveBtnState();
};

// Vista principal tras confirmar ROI: muestra logs y estado del análisis en directo
window.showDirectoLiveView = function() {
    if (document.querySelector('.top-bar')) {
        document.querySelector('.top-bar').innerHTML = `
            <h2 id="view-title" style="display:flex;align-items:center;gap:10px;">
                <i class="fas fa-broadcast-tower" style="color:#EF4444;"></i> 🔴 Análisis en Directo
            </h2>
            <div class="top-bar-actions">
                <button class="btn-top-bar" onclick="loadView('logs', event)" title="Ver logs del sistema">
                    <i class="fas fa-file-alt"></i>
                    Ver Logs
                </button>
            </div>
        `;
    }
    if (window.updateViewTitle) {
        updateViewTitle('<i class="fas fa-broadcast-tower" style="color:#EF4444;"></i> 🔴 Análisis en Directo');
    }
    // Panel principal: muestra el stream en directo y logs, y el ROI
    document.getElementById('main-panel').innerHTML = `
        <div style="display: flex; gap: 32px; margin-top: 40px;">
            <div style="flex: 2;">
                <h2>Directo en Tiempo Real</h2>
                <div id="liveStreamContainer" style="position:relative; width:100%; max-width:640px;">
                    <img id="liveStreamVideo" src="${document.getElementById('streamUrlInput') ? document.getElementById('streamUrlInput').value : 'http://localhost:8080/video_feed'}" style="width:100%;max-width:640px;border-radius:8px;box-shadow:0 2px 8px #0002;display:block;" alt="Stream en directo" />
                    <canvas id="roiOverlayCanvas" width="640" height="480" style="position:absolute;top:0;left:0;pointer-events:none;z-index:2;border-radius:8px;"></canvas>
                </div>
                <button class="btn" onclick="forceDirectoConfigView()">
                    <i class="fas fa-arrow-left"></i> Volver a configuración
                </button>
            </div>
            <div style="flex: 1; background: #1e293b; border-radius: 12px; padding: 18px; color: #fff; min-width: 260px;">
                <h3>Logs de Eventos</h3>
                <div id="liveLogsPanel" style="height: 400px; overflow-y: auto; background: #222; border-radius: 8px; padding: 10px; font-size: 1.05em;"></div>
            </div>
        </div>
    `;
    // Dibuja el ROI sobre el canvas, sombreando el resto
    function drawROIOverlay() {
        const roi = window.directoROI;
        const canvas = document.getElementById('roiOverlayCanvas');
        const img = document.getElementById('liveStreamVideo');
        if (!canvas || !roi || roi.length !== 4 || !img || !img.complete) {
            return;
        }
        
        // Ajustar el canvas al tamaño real del video mostrado
        canvas.width = img.clientWidth;
        canvas.height = img.clientHeight;
        const ctx = canvas.getContext('2d');
        
        // Limpiar todo el canvas primero
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Calcular escala si el ROI viene de una imagen de diferente tamaño
        let scaleX = img.clientWidth / (capturedFrame ? capturedFrame.width : img.clientWidth);
        let scaleY = img.clientHeight / (capturedFrame ? capturedFrame.height : img.clientHeight);
        
        // El ROI se define sobre la imagen original, hay que escalar a la vista
        const roiX = roi[0] * scaleX;
        const roiY = roi[1] * scaleY;
        const roiW = roi[2] * scaleX;
        const roiH = roi[3] * scaleY;
        
        // Dibujar sombreado en las 4 áreas fuera del ROI
        ctx.fillStyle = 'rgba(0,0,0,0.45)';
        // Área superior
        ctx.fillRect(0, 0, canvas.width, roiY);
        // Área izquierda
        ctx.fillRect(0, roiY, roiX, roiH);
        // Área derecha
        ctx.fillRect(roiX + roiW, roiY, canvas.width - (roiX + roiW), roiH);
        // Área inferior
        ctx.fillRect(0, roiY + roiH, canvas.width, canvas.height - (roiY + roiH));
        
        // Dibujar el marco del ROI
        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 2;
        ctx.strokeRect(roiX, roiY, roiW, roiH);
    }
    // Esperar a que la imagen cargue y luego dibujar
    const imgElement = document.getElementById('liveStreamVideo');
    if (imgElement) {
        // Remover cualquier listener anterior para evitar dibujar múltiples veces
        imgElement.removeEventListener('load', drawROIOverlay);
        if (imgElement.complete) {
            drawROIOverlay();
        } else {
            imgElement.addEventListener('load', drawROIOverlay, { once: true });
        }
    }
    // Iniciar polling de logs si no está activo
    if (!liveLogsInterval) {
        startLiveLogsPolling();
    }
    loadLiveLogs();
};

window.forceDirectoConfigView = function() {
    // Fuerza la vista de configuración de ROI, ignorando el estado de análisis
    if (document.querySelector('.top-bar')) {
        document.querySelector('.top-bar').innerHTML = `
            <h2 id="view-title"><i class="fas fa-broadcast-tower" style="color:#EF4444;"></i> Selección de ROI en Directo</h2>
        `;
    }
    const content = `
        <div class="roi-processing-container">
            <!-- Banner de desarrollo -->
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%); border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <span style="font-size: 2.5em;">🚧</span>
                    <div>
                        <h3 style="margin: 0; color: #fff; font-size: 1.3em; font-weight: 600;">Apartado en Desarrollo</h3>
                        <p style="margin: 8px 0 0 0; color: #fff; opacity: 0.95; font-size: 1.05em;">
                            Esta sección es una <strong>demo de procesamiento en tiempo real personal</strong>. Las funcionalidades están en fase de pruebas y desarrollo.
                        </p>
                    </div>
                </div>
            </div>
            
            <div style="margin-bottom:24px;">
                <label for="streamUrlInput"><strong>URL del Stream MJPEG:</strong></label>
                <input type="text" id="streamUrlInput" value="${document.getElementById('streamUrlInput') ? document.getElementById('streamUrlInput').value : 'http://localhost:8080/video_feed'}" style="width:100%;margin-bottom:10px;">
                <button class="btn" id="captureFrameBtn" onclick="captureLiveFrame()" style="margin-bottom:10px;">
                    <i class="fas fa-camera"></i> Capturar Frame
                </button>
            </div>
            <div class="roi-processing-content">
                <div class="roi-canvas-section">
                    <div class="canvas-wrapper" id="canvasWrapperProcessing">
                        <canvas id="roiProcessingCanvas" width="1000" height="600" style="display: block;"></canvas>
                        <div class="canvas-instructions" id="canvasInstructions" style="display: flex; margin-top: 10px;">
                            <i class="fas fa-mouse-pointer"></i>
                            <span>Arrastra con el mouse para dibujar el área de análisis</span>
                        </div>
                    </div>
                </div>
                <div class="roi-processing-sidebar" id="roiProcessingSidebar" style="opacity: 1; pointer-events: auto;">
                    <div class="roi-coords-card">
                        <h3><i class="fas fa-ruler-combined"></i> Coordenadas del Área</h3>
                        <div class="roi-coords-grid">
                            <div class="coord-input">
                                <label>X:</label>
                                <input type="number" id="roiProcessingX" value="" min="0" oninput="updateProcessingROIPreview()">
                            </div>
                            <div class="coord-input">
                                <label>Y:</label>
                                <input type="number" id="roiProcessingY" value="" min="0" oninput="updateProcessingROIPreview()">
                            </div>
                            <div class="coord-input">
                                <label>Ancho:</label>
                                <input type="number" id="roiProcessingW" value="" min="1" oninput="updateProcessingROIPreview()">
                            </div>
                            <div class="coord-input">
                                <label>Alto:</label>
                                <input type="number" id="roiProcessingH" value="" min="1" oninput="updateProcessingROIPreview()">
                            </div>
                        </div>
                        <button class="btn btn-secondary btn-block" onclick="resetProcessingROI()">
                            <i class="fas fa-undo"></i> Usar Video Completo
                        </button>
                    </div>
                    <div class="roi-processing-actions">
                        <button class="btn btn-primary btn-block btn-large" onclick="confirmDirectoROI()">
                            <i class="fas fa-play-circle"></i> Iniciar Análisis
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('main-panel').innerHTML = content;
    // Inicializar canvas y eventos
    capturedFrame = null;
    window.currentROI = null;
    initDirectoProcessingCanvas();
    setTimeout(updateStartLiveBtnState, 100);
    // Si hay enlace, capturar frame automáticamente
    setTimeout(function() {
        const url = document.getElementById('streamUrlInput').value;
        if (url && url.trim().length > 0) {
            document.getElementById('captureFrameBtn').click();
        }
    }, 200);
};

