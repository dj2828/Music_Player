window.addEventListener('keydown', function(e) {
    keybinds(e);
});

function keybinds(e) {
    // Ignore events if the user is typing in an input, textarea, or editable element
    if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName) || document.activeElement.isContentEditable) {
        return;
    }

    switch (e.code) {
        case "Space":
        case "": // Fallback for some browsers
            if (e.key === " ") {
                e.preventDefault();
                togglePlay();
            }
            break;
            
        case "Digit0":
        case "Numpad0":
            e.preventDefault();
            audioPlayer.currentTime = 0;
            break;
            
        case "KeyF":
            e.preventDefault();
            if (document.getElementById('lyricsModal').style.display === "none" || document.getElementById('lyricsModal').style.display === "") {
                openlyricsModal();
            }
            
            if (!document.fullscreenElement) {
                fullscreenLyrics();
            } else {
                document.exitFullscreen();
            }
            break;
    }
}