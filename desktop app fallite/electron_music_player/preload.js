const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    callNode: (name, args) => ipcRenderer.invoke('call-node', { name, args }),
    minimize: () => ipcRenderer.send('minimize'),
    close: () => ipcRenderer.send('close')
});