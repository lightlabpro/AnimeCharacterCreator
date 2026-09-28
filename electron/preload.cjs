const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('creatorHost', {
  pickFolder: (title) => ipcRenderer.invoke('dialog:pickFolder', title),
  scanLibrary: (folder) => ipcRenderer.invoke('library:scan', folder),
  saveJson: (defaultName, text) => ipcRenderer.invoke('file:saveJson', defaultName, text),
  openJson: () => ipcRenderer.invoke('file:openJson'),
});
