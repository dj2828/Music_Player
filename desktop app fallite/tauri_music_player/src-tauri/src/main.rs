#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use tauri::{Manager, WebviewWindowBuilder};
use tauri::path::BaseDirectory;

use base64::{engine::general_purpose, Engine};
use lofty::{read_from_path, TaggedFileExt, Accessor};
use opener::open;

// ===========================================================
//  LETTURA directories.txt
// ===========================================================

fn get_configured_directories(
    app_handle: &tauri::AppHandle,
) -> Result<Vec<String>, String> {
    let path = app_handle
        .path()
        .resolve("directories.txt", BaseDirectory::Resource)
        .map_err(|e| e.to_string())?;

    let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
    // println!("[DEBUG] Righe trovate: {:?}", content);
    Ok(content
        .lines()
        .map(|l| l.trim().to_string())
        .filter(|l| !l.is_empty())
        .collect())
}

fn get_song_full_path(
    app_handle: &tauri::AppHandle,
    folder_req: &str,
    song_req: &str,
) -> Option<PathBuf> {
    let dirs = get_configured_directories(app_handle).ok()?;

    for line in dirs {
        if let Some((name, path_str)) = line.split_once('=') {
            if name.trim() == folder_req {
                return Some(Path::new(path_str.trim()).join(song_req));
            }
        }
    }
    None
}

// ===========================================================
//  COMANDI
// ===========================================================

#[tauri::command]
fn config(app_handle: tauri::AppHandle) -> Result<(), String> {
    let path = app_handle
        .path()
        .resolve("directories.txt", BaseDirectory::Resource)
        .map_err(|e| e.to_string())?;

    open(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_song_url(
    app_handle: tauri::AppHandle,
    folder: String,
    song: String,
) -> Result<String, String> {
    let path = get_song_full_path(&app_handle, &folder, &song)
        .ok_or("File non trovato".to_string())?;

    // Converti il percorso in una stringa, e poi sostituisci ogni singola barra
    // obliqua (/) nel percorso con una doppia barra (//)
    let path_with_double_slashes = path
        .to_string_lossy()
        .to_string()
        .replace("/", "//"); // Sostituisce "/" con "//"

    // La parte iniziale "file:///" viene mantenuta, e il percorso modificato viene aggiunto
    Ok(path_with_double_slashes)
}

#[tauri::command]
fn get_songs(app_handle: tauri::AppHandle) -> Result<HashMap<String, HashMap<String, Vec<String>>>, String> {
    let dirs = get_configured_directories(&app_handle)?;
    let mut result = HashMap::new();

    for line in dirs {
        if let Some((folder_name, path_str)) = line.split_once('=') {
            let p = path_str.trim();
            let mut temp_albums: HashMap<String, Vec<String>> = HashMap::new();

            // Scansione della cartella (NON ricorsiva)
            if let Ok(entries) = fs::read_dir(p) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    
                    if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("mp3") {
                        // Leggiamo il tag Album usando Lofty
                        let album_name = if let Ok(tagged_file) = read_from_path(&path) {
                            tagged_file.primary_tag()
                                .and_then(|tag| tag.album().map(|a| a.to_string()))
                                .map(|a| a.replace(['/', '\\', '?'], "_")) // Pulizia caratteri
                                .unwrap_or_else(|| "_SCONOSCIUTO_".to_string())
                        } else {
                            "_SCONOSCIUTO_".to_string()
                        };

                        if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                            temp_albums.entry(album_name).or_default().push(name.to_string());
                        }
                    }
                }
            }

            // --- LOGICA DI RAGGRUPPAMENTO (Simile al tuo Python) ---
            let mut final_structure: HashMap<String, Vec<String>> = HashMap::new();
            let mut brani_singoli = Vec::new();

            for (nome_alb, mut tracce) in temp_albums {
                tracce.sort(); 

                // Se è l'album sconosciuto o ha una sola traccia, finisce nei singoli
                if nome_alb == "_SCONOSCIUTO_" || tracce.len() <= 1 {
                    brani_singoli.extend(tracce);
                } else {
                    final_structure.insert(nome_alb, tracce);
                }
            }

            if !brani_singoli.is_empty() {
                brani_singoli.sort();
                final_structure.insert("Brani Singoli".to_string(), brani_singoli);
            }

            result.insert(folder_name.trim().to_string(), final_structure);
        }
    }

    Ok(result)
}

#[tauri::command]
fn get_song_img(
    app_handle: tauri::AppHandle,
    folder: String,
    song: String,
) -> Result<Option<String>, String> {
    let path = get_song_full_path(&app_handle, &folder, &song)
        .ok_or("File non trovato".to_string())?;

    let tagged = read_from_path(path).map_err(|e| e.to_string())?;

    if let Some(tag) = tagged.primary_tag() {
        if let Some(pic) = tag.pictures().first() {
            let base64 = general_purpose::STANDARD.encode(pic.data());
            return Ok(Some(format!("data:image/*;base64,{}", base64)));
        }
    }

    Ok(None)
}

// ===========================================================
//  CREAZIONE FINESTRA (Tauri 2)
// ===========================================================

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::App("index.html".into()))
                .title("")
                .inner_size(400.0, 650.0)
                .build()?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            config,
            get_song_url,
            get_songs,
            get_song_img
        ])
        .run(tauri::generate_context!())
        .expect("errore avvio app");
}
