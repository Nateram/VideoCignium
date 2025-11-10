// Preload script - expone APIs seguras al renderer
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  platform: process.platform,
  version: process.versions.electron,
  
  // API para seleccionar carpetas
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  
  // API para seleccionar archivos
  selectFiles: () => ipcRenderer.invoke('select-files')
});
