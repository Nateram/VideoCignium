# 🔧 Arreglo: Subida de Archivos Grandes

## Problema
Los archivos se quedaban atascados en un porcentaje aleatorio durante la subida sin mostrar errores.

## Causas Identificadas

### 1. ❌ Frontend: `fetch()` no soporta progreso de subida
- **Problema**: El código usaba `fetch()` que no puede monitorear el progreso real de uploads
- **Síntoma**: La barra de progreso no se actualizaba, parecía congelada
- **Solución**: Cambiado a `XMLHttpRequest` con eventos `upload.progress`

### 2. ❌ Backend (Nginx): Límite de tamaño por defecto
- **Problema**: Nginx tiene un límite de 1MB por defecto para uploads
- **Síntoma**: Archivos grandes se rechazaban silenciosamente sin llegar a Flask
- **Solución**: Agregado `client_max_body_size 500M` en configuración

## Cambios Realizados

### ✅ 1. Frontend (`upload.js`)
**ANTES** (con `fetch()`):
```javascript
const response = await fetch(buildApiUrl('/api/upload'), {
    method: 'POST',
    body: formData
});
```

**AHORA** (con `XMLHttpRequest`):
```javascript
const xhr = new XMLHttpRequest();

// Monitorear progreso REAL de subida
xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        uploadProgressBar.style.width = percentComplete + '%';
        uploadProgressText.textContent = `Subiendo... ${Math.round(percentComplete)}%`;
    }
});

xhr.open('POST', buildApiUrl('/api/upload'));
xhr.timeout = 300000; // 5 minutos
xhr.send(formData);
```

**Mejoras adicionales:**
- ✅ Eventos `progress` muestran porcentaje exacto en tiempo real
- ✅ Timeout de 5 minutos (300s) para archivos grandes
- ✅ Manejo de errores de red y timeout mejorado
- ✅ Logs en consola para debugging (`console.log()`)

### ✅ 2. Backend Nginx (`server.txt`)
**Configuración agregada:**
```nginx
# 🔥 CONFIGURACIÓN PARA SUBIDA DE ARCHIVOS GRANDES
client_max_body_size 500M;           # Hasta 500MB
client_body_timeout 300s;            # 5 minutos para recibir datos
client_header_timeout 60s;           # 1 minuto para headers
proxy_request_buffering off;         # No almacenar en buffer

location /proyect1/ {
    # ... configuración existente ...
    proxy_request_buffering off;     # Enviar datos directamente a Flask
    proxy_buffering off;              # No almacenar respuesta
}
```

## 📋 Pasos para Aplicar los Cambios

### En tu PC Windows (Ya hecho ✅)
Los archivos ya están actualizados:
- ✅ `static/js/upload.js` - Usa XMLHttpRequest
- ✅ `server.txt` - Configuración de Nginx actualizada

### En tu Raspberry Pi (⚠️ DEBES HACER ESTO)

#### 1. Actualizar configuración de Nginx
```bash
# Conectar por SSH a la Raspberry Pi
ssh tu_usuario@192.168.1.XXX

# Editar la configuración de Nginx
sudo nano /etc/nginx/sites-available/natera.dev

# Copiar TODO el contenido del archivo server.txt actualizado
# (desde tu PC Windows: c:\Users\pabli\Desktop\web_app\server.txt)

# Guardar: Ctrl+O, Enter
# Salir: Ctrl+X
```

#### 2. Verificar y recargar Nginx
```bash
# Verificar que la configuración es correcta
sudo nginx -t

# Si dice "syntax is ok" y "test is successful":
sudo systemctl reload nginx

# Verificar que Nginx está corriendo
sudo systemctl status nginx
```

#### 3. Reiniciar tu aplicación Flask
```powershell
# En tu PC Windows, detener el servidor actual (Ctrl+C)
# Luego iniciar de nuevo:
.\run-with-prefix.bat
```

## 🧪 Cómo Probar

1. **Abre tu aplicación**: https://natera.dev/proyect1/

2. **Abre la consola del navegador** (F12 → Consola)

3. **Sube un archivo de video** (puede ser grande, hasta 500MB)

4. **Verifica en la consola:**
   ```
   📤 Iniciando subida de 1 archivo(s)...
   📤 Progreso de subida: 10% (5242880/52428800 bytes)
   📤 Progreso de subida: 25% (13107200/52428800 bytes)
   📤 Progreso de subida: 50% (26214400/52428800 bytes)
   📤 Progreso de subida: 75% (39321600/52428800 bytes)
   📤 Progreso de subida: 100% (52428800/52428800 bytes)
   ```

5. **La barra de progreso debe moverse suavemente** de 0% a 100%

## ⚠️ Problemas Comunes

### La barra sigue sin moverse
- **Verifica** que actualizaste Nginx en la Raspberry Pi
- **Comprueba** los logs de Nginx: `sudo tail -f /var/log/nginx/error.log`
- **Revisa** el tamaño del archivo: debe ser < 500MB

### Error "413 Request Entity Too Large"
- **Causa**: Nginx no tiene la configuración actualizada
- **Solución**: Repite los pasos de actualización de Nginx

### Error de timeout
- **Si el archivo es MUY grande** (>500MB):
  - Opción 1: Dividirlo en partes más pequeñas
  - Opción 2: Aumentar timeouts en `server.txt` (ej: `600s`)

### Error de red durante la subida
- **Comprueba** tu conexión WiFi/Ethernet
- **Verifica** que tu PC está en la misma red que la Raspberry Pi
- **Intenta** con un archivo más pequeño primero (< 50MB)

## 📊 Límites Actuales

- **Tamaño máximo por archivo**: 500 MB
- **Timeout de subida**: 5 minutos (300 segundos)
- **Timeout de Nginx**: 10 minutos (600 segundos)
- **Múltiples archivos**: Sí (suma total < 500MB)

## 🎯 Próximos Pasos (Opcional)

Si necesitas subir archivos **AÚN MÁS GRANDES**:

1. Aumentar límites en `server.txt`:
   ```nginx
   client_max_body_size 2G;        # 2 GB
   client_body_timeout 900s;       # 15 minutos
   ```

2. Aumentar timeout en Flask (`app.py`):
   ```python
   app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB
   ```

3. Aumentar timeout en JavaScript (`upload.js`):
   ```javascript
   xhr.timeout = 900000; // 15 minutos
   ```

## ✅ Verificación Final

Después de aplicar todos los cambios, deberías ver:
- ✅ Barra de progreso moviéndose suavemente de 0% a 100%
- ✅ Porcentaje actualizado en tiempo real en la UI
- ✅ Logs detallados en la consola del navegador
- ✅ Subida exitosa sin errores ni timeouts
- ✅ Archivos grandes (100MB+) subiéndose correctamente

---
**Última actualización**: 4 de noviembre de 2025
**Archivos modificados**: 
- `static/js/upload.js` ✅
- `server.txt` ✅
