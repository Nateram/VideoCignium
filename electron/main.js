const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const kill = require('tree-kill');
const fs = require('fs');

// Single instance lock - solo permitir una instancia de la app
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  // Si ya hay otra instancia corriendo, salir inmediatamente
  app.quit();
} else {
  // Si somos la primera instancia, manejar intentos de abrir otra
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Si alguien intenta abrir otra instancia, enfocar la ventana existente
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

let mainWindow;
let splashWindow;
let flaskProcess;
let isQuitting = false;
const FLASK_PORT = 5000;
const isDev = process.argv.includes('--dev');

// Función para hacer console.log solo en modo desarrollo
const devLog = (...args) => {
  if (isDev) {
    console.log(...args);
  }
};

const devError = (...args) => {
  if (isDev) {
    console.error(...args);
  }
};

// Rutas base según si es desarrollo o producción
// En desarrollo, la carpeta del proyecto está un nivel arriba de electron/
// En producción empaquetada, usar process.resourcesPath
const BASE_DIR = isDev || !app.isPackaged
  ? path.join(__dirname, '..')  // Subir un nivel desde electron/ al proyecto
  : process.resourcesPath;

const PYTHON_SCRIPT = path.join(BASE_DIR, 'app.py');

function createSplashScreen() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 250,
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    resizable: false,
    backgroundColor: '#1E293B',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // HTML simple para la pantalla de carga
  const splashHTML = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          margin: 0;
          padding: 0;
          background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 100vh;
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          color: white;
        }
        .logo {
          font-size: 48px;
          margin-bottom: 20px;
        }
        h1 {
          font-size: 24px;
          margin: 0 0 10px 0;
          font-weight: 600;
        }
        .loading {
          font-size: 14px;
          color: #94A3B8;
          margin-top: 20px;
        }
        .spinner {
          width: 40px;
          height: 40px;
          margin: 20px 0;
          border: 4px solid rgba(255, 255, 255, 0.1);
          border-top: 4px solid #3B82F6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    </head>
    <body>
      <div class="logo">🎥</div>
      <h1>Detector de Movimiento IA</h1>
      <div class="spinner"></div>
      <div class="loading">Iniciando aplicación...</div>
    </body>
    </html>
  `;

  splashWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHTML));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    frame: false,
    show: false, // No mostrar hasta que esté lista
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      cache: false
    },
    icon: path.join(__dirname, 'icon.png'),
    title: 'Detector de Movimiento',
    backgroundColor: '#1E293B',
    titleBarStyle: 'hidden'
  });

  // Ocultar menú en producción
  if (!isDev) {
    mainWindow.setMenuBarVisibility(false);
  }

  // LIMPIAR TODO EL CACHÉ AL INICIAR
  mainWindow.webContents.session.clearCache().then(() => {
    devLog('✅ Caché de Electron limpiado');
  });
  
  mainWindow.webContents.session.clearStorageData({
    storages: ['appcache', 'cookies', 'filesystem', 'indexdb', 'localstorage', 'shadercache', 'websql', 'serviceworkers', 'cachestorage']
  }).then(() => {
    devLog('✅ Almacenamiento de Electron limpiado');
  });

  // Cargar la aplicación Flask
  const loadApp = () => {
    mainWindow.loadURL(`http://localhost:${FLASK_PORT}`, {
      extraHeaders: 'pragma: no-cache\n'
    })
      .then(() => {
        // Cuando la app esté cargada, cerrar splash y mostrar ventana principal
        setTimeout(() => {
          if (splashWindow && !splashWindow.isDestroyed()) {
            splashWindow.close();
          }
          mainWindow.show();
        }, 500);
      })
      .catch(err => {
        devLog('Esperando a Flask...', err.message);
        setTimeout(loadApp, 500);
      });
  };

  // Esperar un poco para que Flask inicie Y el caché se limpie
  setTimeout(loadApp, 2500);

  // Atajos de teclado para recargar (útil durante desarrollo)
  mainWindow.webContents.on('before-input-event', (event, input) => {
    // F5 o Ctrl+R: recargar sin caché
    if (input.key === 'F5' || (input.control && input.key === 'r')) {
      event.preventDefault();
      mainWindow.webContents.reloadIgnoringCache();
    }
    // Ctrl+Shift+R: hard reload
    if (input.control && input.shift && input.key === 'R') {
      event.preventDefault();
      mainWindow.webContents.session.clearCache().then(() => {
        mainWindow.webContents.reloadIgnoringCache();
      });
    }
  });

  mainWindow.on('close', async (event) => {
    if (!isQuitting) {
      event.preventDefault();
      isQuitting = true;
      devLog('🛑 Cerrando ventana - deteniendo Flask...');
      await stopFlask();
      mainWindow.destroy();
      app.quit();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startFlask() {
  return new Promise((resolve, reject) => {
    devLog('🚀 Iniciando servidor Flask...');
    devLog('📁 BASE_DIR:', BASE_DIR);
    devLog('📄 Python script:', PYTHON_SCRIPT);

    // Buscar Python PORTABLE primero, luego Python del sistema
    const { spawnSync } = require('child_process');
    
    // PRIORIDAD 1: Python portable incluido en la aplicación
    // Usar pythonw.exe (sin ventana) en lugar de python.exe
    const portablePythonW = path.join(BASE_DIR, 'python-portable', 'pythonw.exe');
    const portablePython = path.join(BASE_DIR, 'python-portable', 'python.exe');
    
    let pythonCmd = null;
    let pythonArgs = [];
    
    // Si existe Python portable, usar pythonw.exe para NO mostrar terminal
    if (fs.existsSync(portablePythonW)) {
      devLog('✨ Python PORTABLE (sin ventana) detectado en:', portablePythonW);
      pythonCmd = portablePythonW;
      pythonArgs = [];
      
      // Intentar obtener versión con python.exe (pythonw no muestra output)
      try {
        const result = spawnSync(portablePython, ['--version'], { 
          shell: true,
          windowsHide: true,
          timeout: 3000
        });
        const version = (result.stdout || result.stderr).toString().trim();
        if (version) {
          devLog(`   Versión: ${version}`);
        }
      } catch (e) {
        devLog('   ⚠️ No se pudo verificar versión, pero se usará Python portable');
      }
    } else if (fs.existsSync(portablePython)) {
      // Fallback a python.exe si pythonw.exe no existe (desarrollo)
      devLog('✨ Python PORTABLE detectado en:', portablePython);
      pythonCmd = portablePython;
      pythonArgs = [];
    } else {
      // Si NO existe Python portable, buscar Python del sistema
      devLog('🔍 Buscando Python del sistema...');
      
      const pythonCommands = [
        'python',
        'python3', 
        'py',
        'py -3',
        'C:\\Users\\pabli\\AppData\\Local\\Microsoft\\WindowsApps\\python3.13.exe',
        'C:\\Python313\\python.exe',
        'C:\\Python312\\python.exe',
        'C:\\Python311\\python.exe',
        'C:\\Python310\\python.exe'
      ];

      // Encontrar el comando Python disponible
      for (const cmd of pythonCommands) {
        try {
          const parts = cmd.split(' ');
          const executable = parts[0];
          const args = parts.slice(1);
          
          const result = spawnSync(executable, [...args, '--version'], { 
            shell: true,
            windowsHide: true,
            timeout: 3000
          });
          
          if (result.status === 0 || result.stdout.toString().includes('Python')) {
            pythonCmd = executable;
            pythonArgs = args;
            const version = (result.stdout || result.stderr).toString().trim();
            devLog(`✅ Python encontrado: ${cmd}`);
            devLog(`   Versión: ${version}`);
            break;
          }
        } catch (e) {
          devLog(`   ❌ No funciona: ${cmd}`, e.message);
          continue;
        }
      }

      if (!pythonCmd) {
        const errorMsg = 'No se encontró Python instalado en el sistema.\n\n' +
          'Por favor instala Python 3.8 o superior desde:\n' +
          'https://www.python.org/downloads/\n\n' +
          'Comandos probados:\n' + pythonCommands.join('\n');
        
        devError('❌', errorMsg);
        dialog.showErrorBox('Python no encontrado', errorMsg);
        reject(new Error('Python no encontrado'));
        return;
      }
    }

    // Configurar variables de entorno
    const env = { ...process.env };
    env.PYTHONUNBUFFERED = '1';
    env.FLASK_ENV = 'production';
    
    // Iniciar Flask con shell en Windows
    const allArgs = [...pythonArgs, PYTHON_SCRIPT];
    
    // En Windows con rutas con espacios, usar comillas y comando completo
    const fullCommand = `"${pythonCmd}" ${allArgs.map(arg => `"${arg}"`).join(' ')}`;
    devLog(`🔧 Comando completo: ${fullCommand}`);
    devLog(`📁 Working dir: ${BASE_DIR}`);
    
    flaskProcess = spawn(fullCommand, [], {
      cwd: BASE_DIR,
      env: env,
      shell: true,
      windowsHide: true,  // ✅ Ocultar ventana del terminal
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let flaskReady = false;
    
    flaskProcess.stdout.on('data', (data) => {
      const output = data.toString();
      devLog('[Flask STDOUT]', output);
      
      // Detectar cuando Flask está listo
      if (!flaskReady && (output.includes('Running on') || output.includes('http://') || output.includes('WARNING'))) {
        flaskReady = true;
        devLog('✅ Flask está listo!');
        setTimeout(() => resolve(), 1000);
      }
    });

    flaskProcess.stderr.on('data', (data) => {
      const output = data.toString();
      devLog('[Flask STDERR]', output);
      
      // Flask a veces escribe mensajes normales en stderr
      if (!flaskReady && (output.includes('Running on') || output.includes('http://') || output.includes('WARNING'))) {
        flaskReady = true;
        devLog('✅ Flask está listo!');
        setTimeout(() => resolve(), 1000);
      }
    });

    flaskProcess.on('error', (err) => {
      devError('❌ Error al iniciar Flask:', err);
      const errorMsg = `No se pudo iniciar el servidor Flask:\n\n${err.message}\n\n` +
        `Python: ${pythonCmd}\n` +
        `Script: ${PYTHON_SCRIPT}\n\n` +
        `Asegúrate de que Python y todas las dependencias estén instaladas.\n` +
        `Ejecuta: pip install -r requirements.txt`;
      
      dialog.showErrorBox('Error al iniciar el servidor', errorMsg);
      reject(err);
    });

    flaskProcess.on('close', (code) => {
      devLog(`⚠️ Flask cerrado con código: ${code}`);
      // ✅ NO mostrar diálogo si la app se está cerrando intencionalmente
      // Solo alertar si el código es anormal Y no estamos cerrando la app
      if (code !== 0 && code !== 1 && code !== null && !app.isQuitting) {
        devError('❌ Flask cerró inesperadamente con código:', code);
        dialog.showErrorBox(
          'Error del servidor',
          `El servidor Flask se cerró inesperadamente.\n\nCódigo: ${code}\n\nRevisa la consola para más detalles.`
        );
      }
    });

    // Timeout de 15 segundos para el inicio
    setTimeout(() => {
      if (!flaskReady) {
        devLog('⏰ Timeout alcanzado, continuando de todas formas...');
        resolve(); // Continuar de todas formas
      }
    }, 15000);
  });
}

function stopFlask() {
  return new Promise((resolve) => {
    if (flaskProcess) {
      devLog('🛑 Deteniendo servidor Flask...');
      
      // En Windows, usar taskkill para matar Python/Flask
      if (process.platform === 'win32') {
        const { exec } = require('child_process');
        
        // Matar TODOS los procesos de python y pythonw que ejecutan app.py
        const killCommands = [
          'taskkill /F /IM python.exe /T',
          'taskkill /F /IM pythonw.exe /T'
        ];
        
        let completed = 0;
        killCommands.forEach(cmd => {
          exec(cmd, (error, stdout, stderr) => {
            if (error) {
              devLog(`Proceso ya no existe o no se pudo matar: ${cmd}`);
            } else {
              devLog(`✅ Proceso terminado: ${cmd}`);
            }
            completed++;
            if (completed === killCommands.length) {
              flaskProcess = null;
              resolve();
            }
          });
        });
        
        // Timeout de seguridad
        setTimeout(() => {
          if (completed < killCommands.length) {
            devLog('⏰ Timeout alcanzado, continuando...');
            flaskProcess = null;
            resolve();
          }
        }, 2000);
      } else {
        // En Linux/Mac, usar tree-kill
        kill(flaskProcess.pid, 'SIGTERM', (err) => {
          if (err) {
            devError('Error al detener Flask:', err);
            try {
              flaskProcess.kill('SIGKILL');
            } catch (e) {
              devError('Error al forzar cierre:', e);
            }
          }
          flaskProcess = null;
          resolve();
        });
      }
    } else {
      resolve();
    }
  });
}

// Evento cuando Electron está listo
app.whenReady().then(async () => {
  try {
    // Primero mostrar la pantalla de carga
    createSplashScreen();
    
    // Luego iniciar Flask
    await startFlask();
    
    // Crear la ventana principal (oculta)
    createWindow();
  } catch (err) {
    devError('Error al iniciar:', err);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Cerrar Flask cuando se cierra la aplicación
app.on('before-quit', async (event) => {
  if (flaskProcess && !isQuitting) {
    event.preventDefault();
    isQuitting = true;
    devLog('🛑 Cerrando aplicación (before-quit)...');
    await stopFlask();
    app.exit(0);
  }
});

app.on('will-quit', async (event) => {
  if (flaskProcess) {
    event.preventDefault();
    devLog('🛑 Cerrando aplicación (will-quit)...');
    await stopFlask();
    app.exit(0);
  }
});

app.on('window-all-closed', async () => {
  devLog('🛑 Todas las ventanas cerradas...');
  await stopFlask();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// ====================================================================
// 🔥 IPC Handlers - Comunicación con el renderer
// ====================================================================

// Controles de ventana personalizados
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

// Selector de carpeta nativo
ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Seleccionar carpeta con videos'
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    return { 
      success: true, 
      path: result.filePaths[0],
      name: path.basename(result.filePaths[0])
    };
  }
  return { success: false };
});

// Selector de archivos múltiples
ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    title: 'Seleccionar videos',
    filters: [
      { name: 'Videos', extensions: ['mp4', 'avi', 'mov', 'dav', 'mkv'] },
      { name: 'Todos', extensions: ['*'] }
    ]
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    return { 
      success: true, 
      files: result.filePaths  // Array simple de rutas
    };
  }
  return { success: false };
});

// Obtener información de carpeta
ipcMain.handle('get-folder-info', async (event, folderPath) => {
  try {
    const stats = fs.statSync(folderPath);
    const files = fs.readdirSync(folderPath);
    const videoExtensions = ['.mp4', '.avi', '.mov', '.dav', '.mkv'];
    const videos = files.filter(f => {
      const ext = path.extname(f).toLowerCase();
      return videoExtensions.includes(ext);
    });
    
    return {
      success: true,
      path: folderPath,
      name: path.basename(folderPath),
      totalFiles: files.length,
      videoFiles: videos.length,
      videos: videos
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

// Manejo de errores no capturados
process.on('uncaughtException', (error) => {
  devError('Error no capturado:', error);
});
