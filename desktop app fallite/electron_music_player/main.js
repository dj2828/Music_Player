const { app, BrowserWindow, ipcMain, nativeImage } = require('electron')
const path = require('path');

if (process.platform === 'win32') {
  // usa un app id consistente per jump list / taskbar
  app.setAppUserModelId('com.dj2828.musicplayer');
}

let win;

const createWindow = () => {
    const iconPath = app.isPackaged
      ? path.join(process.resourcesPath, 'img', 'IO.ico') // quando è pacchettizzato extraResource sarà in resources
      : path.join(__dirname, 'img', 'IO.ico');            // durante lo sviluppo usa la copia nel progetto

    win = new BrowserWindow({
        width: 400,
        height: 650,
        icon: iconPath, // BrowserWindow icon (utile su Linux e per alcune anteprime)
        frame: false,
        titleBarOverlay: {
            color: '#00000000',
            symbolColor: '#ffffff',
            height: 30
        },
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'), // qui carichi il preload
            contextIsolation: true, // consigliato per sicurezza
            nodeIntegration: false, // generalmente disattivato
        },
    });

    // forzare l'icona a runtime (utile per test in sviluppo)
    if (process.platform === 'win32') {
      const img = nativeImage.createFromPath(iconPath);
      if (!img.isEmpty()) win.setIcon(img);
    }

  win.loadFile('index.html')
}

app.whenReady().then(() => {
    createWindow()
})

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
})

// Clean up reference when window is closed
if (typeof win !== 'undefined') {
    win.on('closed', () => {
      win = null;
    });
}

ipcMain.on('minimize', () => { if (win) win.minimize(); })
ipcMain.on('close', () => { if (win) win.close(); })

const fs = require('fs').promises;
const { pathToFileURL } = require('url');
const mm = require('music-metadata');
const { create } = require('domain');

// Funzione helper per leggere le directory dal file di config
async function getConfiguredDirectories() {
    try {
        let configPath;
        if(!app.isPackaged) {
            configPath = path.join(__dirname, 'directories.txt');
        }
        else{
            configPath = path.join(process.resourcesPath, 'directories.txt');
        }
        const content = await fs.readFile(configPath, 'utf-8');

        return content
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0); // rimuovi righe vuote
    } catch (err) {
        console.error('Errore lettura directories.txt:', err.message);
        return []; // fallback a lista vuota
    }
}

async function getSongFullPath(folder, song) {
    let fullPath = '';
    const directories = await getConfiguredDirectories();
    for (const data of directories) {
        const folderName = data.split('=')[0];
        const folderPath = data.split('=')[1];
        
        if (folderName === folder) {
            fullPath = path.resolve(folderPath, song);
            return fullPath;
        }
    }
}

ipcMain.handle('call-node', async (event, { name, args }) => {
    if (name === 'getSongUrl') {
        fullPath = await getSongFullPath(args.folder, args.song);
        try {
            return pathToFileURL(fullPath).href; // es. file:///C:/... o file:///...
        } catch (err) {
            throw new Error('File non trovato: ' + fullPath);
        }
    }
    if (name === 'getSongs') {
        const result = {};
        try {
            const directories = await getConfiguredDirectories();
            for (const data of directories) {
                cose=[];
                const folderName = data.split('=')[0];
                const folderPath = data.split('=')[1];
                const files = await fs.readdir(folderPath, { withFileTypes: true });
                if (files.length) {
                    for (name of files) {
                        if (name.isDirectory()) continue;
                        if (path.extname(name.name).toLowerCase() !== '.mp3') continue;
                        cose.push(name.name);
                    }
                    result[folderName] = cose.sort();
                }
            }
            return result;
        } catch (err) {
            throw new Error('Errore lettura directory music: ' + err.message);
        }
    }
    if (name === 'getSongImg') {
        const mp3Path = await getSongFullPath(args.folder, args.song);
        try {
            const metadata = await mm.parseFile(mp3Path);
            const pics = metadata.common.picture || [];
            if (pics.length) {
                const pic = Buffer.from(pics[0].data); // usa la prima immagine
                const base64 = pic.toString('base64');
                return `data:${pic.format};base64,${base64}`; // restituisci data URL
            }
            return null; // nessuna immagine trovata
        } catch (err) {
            console.error('Errore estrazione copertina embedded:', err.message);
            return null
        }
    }
    if (name === 'config') {
        let configPath;
        if(!app.isPackaged) {
            configPath = path.join(__dirname, 'directories.txt');
        }
        else{
            configPath = path.join(process.resourcesPath, 'directories.txt');
        }
        require('electron').shell.openPath(configPath);
        return;
    }
    throw new Error('Unknown function');
});