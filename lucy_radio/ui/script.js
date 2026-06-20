const audioPlayer = document.getElementById('lucy-audio-player');
const defaultStreamUrl = 'http://127.0.0.1:8000/lucy.mp3'; // Matches Liquidsoap Icecast mount

window.addEventListener('message', (event) => {
    const data = event.data;

    if (data.type === 'PLAY') {
        if (data.url) {
            audioPlayer.src = data.url;
        } else if (!audioPlayer.src) {
            audioPlayer.src = defaultStreamUrl;
        }
        
        audioPlayer.volume = data.volume !== undefined ? data.volume : 0.5;
        audioPlayer.play().catch(e => console.error("Audio play failed:", e));
    } 
    else if (data.type === 'STOP') {
        audioPlayer.pause();
        audioPlayer.src = ''; // Clear source to stop buffering
    } 
    else if (data.type === 'VOLUME') {
        audioPlayer.volume = data.volume;
    }
    else if (data.type === 'METADATA') {
        // Optional: Update HUD with track info
        const hud = document.getElementById('lucy-hud');
        const trackName = document.getElementById('track-name');
        
        trackName.innerText = data.text || 'Lucy Radio Live';
        hud.classList.remove('hidden');
        
        // Hide after 5 seconds
        setTimeout(() => {
            hud.classList.add('hidden');
        }, 5000);
    }
});
