const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const kill = require('tree-kill');
const fs = require('fs');

let mainWindow;
let flaskProcess;
let isQuitting = false;
const FLASK_PORT = 5000;
const isDev = process.argv.includes('--dev');

// Rutas base según si es desarrollo o producción
// En desarrollo, la carpeta del proyecto está un nivel arriba de electron/
// En producción empaquetada, usar process.resourcesPath
const BASE_DIR = isDev || !app.isPackaged
  ? path.join(__dirname, '..')  // Subir un nivel desde electron/ al proyecto
  : process.resourcesPath;

const PYTHON_SCRIPT = path.join(BASE_DIR, 'app.py');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      cache: false  // Desactivar caché
    },
    icon: path.join(__dirname, 'icon.png'),
    title: 'Detector de Movimiento',
    backgroundColor: '#f5f5f5'
  });

  // Ocultar menú en producción
  if (!isDev) {
    mainWindow.setMenuBarVisibility(false);
  }

  // LIMPIAR TODO EL CACHÉ AL INICIAR
  mainWindow.webContents.session.clearCache().then(() => {
    console.log('✅ Caché de Electron limpiado');
  });
  
  mainWindow.webContents.session.clearStorageData({
    storages: ['appcache', 'cookies', 'filesystem', 'indexdb', 'localstorage', 'shadercache', 'websql', 'serviceworkers', 'cachestorage']
  }).then(() => {
    console.log('✅ Almacenamiento de Electron limpiado');
  });

  // Cargar la aplicación Flask
  const loadApp = () => {
    mainWindow.loadURL(`http://localhost:${FLASK_PORT}`, {
      extraHeaders: 'pragma: no-cache\n'
    })
      .catch(err => {
        console.log('Esperando a Flask...', err.message);
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
      console.log('🛑 Cerrando ventana - deteniendo Flask...');
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
    console.log('🚀 Iniciando servidor Flask...');
    console.log('📁 BASE_DIR:', BASE_DIR);
    console.log('📄 Python script:', PYTHON_SCRIPT);

    // Buscar Python en el sistema (Windows específico)
    const { spawnSync } = require('child_process');
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
    
    let pythonCmd = null;
    let pythonArgs = [];

    // Encontrar el comando Python disponible
    for (const cmd of pythonCommands) {
      try {
        const parts = cmd.split(' ');
        const executable = parts[0];
        const args = parts.slice(1);
        
        const result = spawnSync(executable, [...args, '--version'], { 
          shell: true,
          windowsHide: true 
        });
        
        if (result.status === 0 || result.stdout.toString().includes('Python')) {
          pythonCmd = executable;
          pythonArgs = args;
          const version = (result.stdout || result.stderr).toString().trim();
          console.log(`✅ Python encontrado: ${cmd}`);
          console.log(`   Versión: ${version}`);
          break;
        }
      } catch (e) {
        console.log(`   ❌ No funciona: ${cmd}`, e.message);
        continue;
      }
    }

    if (!pythonCmd) {
      const errorMsg = 'No se encontró Python instalado en el sistema.\n\n' +
        'Por favor instala Python 3.8 o superior desde:\n' +
        'https://www.python.org/downloads/\n\n' +
        'Comandos probados:\n' + pythonCommands.join('\n');
      
      console.error('❌', errorMsg);
      dialog.showErrorBox('Python no encontrado', errorMsg);
      reject(new Error('Python no encontrado'));
      return;
    }

    // Configurar variables de entorno
    const env = { ...process.env };
    env.PYTHONUNBUFFERED = '1';
    env.FLASK_ENV = 'production';
    
    // Iniciar Flask con shell en Windows
    const allArgs = [...pythonArgs, PYTHON_SCRIPT];
    console.log(`🔧 Comando: ${pythonCmd} ${allArgs.join(' ')}`);
    console.log(`📁 Working dir: ${BASE_DIR}`);
    
    flaskProcess = spawn(pythonCmd, allArgs, {
      cwd: BASE_DIR,
      env: env,
      shell: true,
      windowsHide: false,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let flaskReady = false;
    
    flaskProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log('[Flask STDOUT]', output);
      
      // Detectar cuando Flask está listo
      if (!flaskReady && (output.includes('Running on') || output.includes('http://') || output.includes('WARNING'))) {
        flaskReady = true;
        console.log('✅ Flask está listo!');
        setTimeout(() => resolve(), 1000);
      }
    });

    flaskProcess.stderr.on('data', (data) => {
      const output = data.toString();
      console.log('[Flask STDERR]', output);
      
      // Flask a veces escribe mensajes normales en stderr
      if (!flaskReady && (output.includes('Running on') || output.includes('http://') || output.includes('WARNING'))) {
        flaskReady = true;
        console.log('✅ Flask está listo!');
        setTimeout(() => resolve(), 1000);
      }
    });

    flaskProcess.on('error', (err) => {
      console.error('❌ Error al iniciar Flask:', err);
      const errorMsg = `No se pudo iniciar el servidor Flask:\n\n${err.message}\n\n` +
        `Python: ${pythonCmd}\n` +
        `Script: ${PYTHON_SCRIPT}\n\n` +
        `Asegúrate de que Python y todas las dependencias estén instaladas.\n` +
        `Ejecuta: pip install -r requirements.txt`;
      
      dialog.showErrorBox('Error al iniciar el servidor', errorMsg);
      reject(err);
    });

    flaskProcess.on('close', (code) => {
      console.log(`⚠️ Flask cerrado con código: ${code}`);
      if (code !== 0 && code !== null && !app.isQuitting) {
        console.error('❌ Flask cerró inesperadamente con código:', code);
        dialog.showErrorBox(
          'Error del servidor',
          `El servidor Flask se cerró inesperadamente.\n\nCódigo: ${code}\n\nRevisa la consola para más detalles.`
        );
      }
    });

    // Timeout de 15 segundos para el inicio
    setTimeout(() => {
      if (!flaskReady) {
        console.log('⏰ Timeout alcanzado, continuando de todas formas...');
        resolve(); // Continuar de todas formas
      }
    }, 15000);
  });
}

function stopFlask() {
  return new Promise((resolve) => {
    if (flaskProcess) {
      console.log('🛑 Deteniendo servidor Flask...');
      
      // Matar el proceso y todos sus hijos
      kill(flaskProcess.pid, 'SIGTERM', (err) => {
        if (err) {
          console.error('Error al detener Flask:', err);
          // Intentar forzar
          try {
            flaskProcess.kill('SIGKILL');
          } catch (e) {
            console.error('Error al forzar cierre:', e);
          }
        }
        flaskProcess = null;
        resolve();
      });
    } else {
      resolve();
    }
  });
}

// Evento cuando Electron está listo
app.whenReady().then(async () => {
  try {
    await startFlask();
    createWindow();
  } catch (err) {
    console.error('Error al iniciar:', err);
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
    console.log('🛑 Cerrando aplicación...');
    await stopFlask();
    app.exit(0);
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// ====================================================================
// 🔥 IPC Handlers - Comunicación con el renderer
// ====================================================================

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
  console.error('Error no capturado:', error);
});
