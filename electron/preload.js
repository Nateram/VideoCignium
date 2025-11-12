// Preload script - expone APIs seguras al renderer
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  platform: process.platform,
  version: process.versions.electron,
  
  // API para seleccionar carpetas y archivos locales
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  selectFiles: () => ipcRenderer.invoke('select-files'),
  getFolderInfo: (path) => ipcRenderer.invoke('get-folder-info', path),
  
  // Controles de ventana personalizados
  windowMinimize: () => ipcRenderer.send('window-minimize'),
  windowMaximize: () => ipcRenderer.send('window-maximize'),
  windowClose: () => ipcRenderer.send('window-close'),
  
  // Indicador de que estamos en Electron (no navegador)
  isElectron: true
});
