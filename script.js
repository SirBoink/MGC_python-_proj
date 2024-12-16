let currentPanel = 1;
const totalPanels = 5;

function nextPanel() {
    // If we're on the name input panel (panel 4), don't handle click events
    if (currentPanel === 4) {
        return; // Let the saveName function handle the transition
    }

    // Hide current panel
    document.getElementById(`panel${currentPanel}`).classList.remove('active');
    
    // Move to next panel
    currentPanel++;
    
    // If we're at the end, don't increment further
    if (currentPanel > totalPanels) {
        currentPanel = totalPanels;
    }
    
    // Show new panel
    document.getElementById(`panel${currentPanel}`).classList.add('active');
    
    // Hide click text on last panel
    if (currentPanel === totalPanels) {
        document.querySelector('.click-text').style.display = 'none';
    }
}

function saveName() {
    const userName = document.getElementById('user-name').value;
    if (userName.trim() !== '') {
        localStorage.setItem('userName', userName);
        document.querySelector('.name-highlight').textContent = userName;
        
        // Hide current panel
        document.getElementById(`panel${currentPanel}`).classList.remove('active');
        
        // Move to next panel
        currentPanel = 5;
        
        // Show new panel
        document.getElementById(`panel${currentPanel}`).classList.add('active');
        
        // Hide click text
        document.querySelector('.click-text').style.display = 'none';
    } else {
        // Visual feedback if name is empty
        const nameInput = document.getElementById('user-name');
        nameInput.style.borderColor = 'rgba(255,0,0,0.5)';
        setTimeout(() => {
            nameInput.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        }, 1000);
    }
}

// Add this to handle Enter key press
document.getElementById('user-name').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        saveName();
    }
});

// Initialize when page loads
window.onload = function() {
    // Show first panel
    document.getElementById('panel1').classList.add('active');
    
    // Set welcome message if name exists
    const userName = localStorage.getItem('userName');
    if (userName) {
        document.querySelector('.name-highlight').textContent = userName;
    }

    // Hide loading and results initially
    document.getElementById('loading-container').style.display = 'none';
    document.getElementById('results').style.display = 'none';
}

// Add your file upload and processing logic here
// This should include the event listeners for file upload, drag and drop,
// and the API calls to your classifier backend

document.getElementById('file-upload').addEventListener('change', handleFileUpload);

// Handle drag and drop
const uploadSection = document.querySelector('.upload-section');

uploadSection.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadSection.style.borderColor = '#cbd5e1';
});

uploadSection.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadSection.style.borderColor = '#94a3b8';
});

uploadSection.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadSection.style.borderColor = '#94a3b8';
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('audio/')) {
        handleFile(file);
    }
});

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

// Audio player functionality
const audioPlayer = document.getElementById('audio-player');
const playBtn = document.querySelector('.play-btn');
const progress = document.querySelector('.progress');
const currentTime = document.querySelector('.time .current');
const duration = document.querySelector('.time .duration');
const volumeControl = document.querySelector('.volume-control input');
const volumeIcon = document.querySelector('.volume-control i');

// Play/Pause
playBtn.addEventListener('click', () => {
    if (audioPlayer.paused) {
        audioPlayer.play();
        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
    } else {
        audioPlayer.pause();
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
    }
});

// Update progress bar
audioPlayer.addEventListener('timeupdate', () => {
    const percent = (audioPlayer.currentTime / audioPlayer.duration) * 100;
    progress.style.width = `${percent}%`;
    
    // Update current time
    const minutes = Math.floor(audioPlayer.currentTime / 60);
    const seconds = Math.floor(audioPlayer.currentTime % 60);
    currentTime.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
});

// Set duration when metadata is loaded
audioPlayer.addEventListener('loadedmetadata', () => {
    const minutes = Math.floor(audioPlayer.duration / 60);
    const seconds = Math.floor(audioPlayer.duration % 60);
    duration.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
});

// Click on progress bar to seek
document.querySelector('.progress-bar').addEventListener('click', (e) => {
    const percent = e.offsetX / e.target.offsetWidth;
    audioPlayer.currentTime = percent * audioPlayer.duration;
});

// Volume control
volumeControl.addEventListener('input', (e) => {
    audioPlayer.volume = e.target.value / 100;
    updateVolumeIcon(e.target.value);
});

function updateVolumeIcon(value) {
    if (value == 0) {
        volumeIcon.className = 'fas fa-volume-mute';
    } else if (value < 50) {
        volumeIcon.className = 'fas fa-volume-down';
    } else {
        volumeIcon.className = 'fas fa-volume-up';
    }
}

// Update handleFile function
function handleFile(file) {
    // Validate file type
    if (!file.type.startsWith('audio/')) {
        showError('Please upload an audio file');
        return;
    }

    // Show loading spinner
    document.getElementById('loading-container').style.display = 'flex';

    const formData = new FormData();
    formData.append('file', file);

    console.log('Sending request to server...');  // Debug log

    fetch('http://localhost:8000/analyze', {  // Make sure port matches your server
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status); // Debug log
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Analysis failed');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Received data:', data);  // Debug log
        document.getElementById('loading-container').style.display = 'none';
        
        // Hide current panel
        document.getElementById('panel5').classList.remove('active');
        
        // Show analysis panel
        const analysisPanel = document.getElementById('analysis-panel');
        analysisPanel.classList.add('active');
        
        // Display results
        const resultsContainer = document.getElementById('results-container');
        resultsContainer.innerHTML = `
            <div class="artistic-description">${data.artisticDescription}</div>
            <div class="genre-bars">
                ${Object.entries(data.predictions)
                    .sort(([,a], [,b]) => b - a)
                    .map(([genre, percentage], index) => `
                        <div class="genre-bar">
                            <span class="genre-label">
                                <i class="fas ${getGenreIcon(genre)}"></i>
                                ${genre}
                            </span>
                            <div class="percentage-bar-container">
                                <div class="percentage-bar" style="width: 0%"></div>
                            </div>
                            <span class="percentage-value">${percentage.toFixed(1)}%</span>
                        </div>
                    `).join('')}
            </div>
        `;

        // Animate the bars
        setTimeout(() => {
            resultsContainer.querySelectorAll('.percentage-bar').forEach((bar, index) => {
                const percentage = Object.values(data.predictions)
                    .sort((a, b) => b - a)[index];
                bar.style.width = `${percentage}%`;
            });
        }, 100);
    })
    .catch(error => {
        console.error('Error:', error);  // Debug log
        document.getElementById('loading-container').style.display = 'none';
        showError(`Error: ${error.message || 'Something went wrong while analyzing the music.'}`);
    });
}

function getGenreIcon(genre) {
    const icons = {
        blues: 'fa-guitar',
        classical: 'fa-music',
        country: 'fa-hat-cowboy',
        disco: 'fa-compact-disc',
        hiphop: 'fa-microphone',
        jazz: 'fa-music',
        metal: 'fa-bolt',
        pop: 'fa-music',
        reggae: 'fa-cannabis',
        rock: 'fa-hand-rock'
    };
    return icons[genre] || 'fa-music';
}

function returnToUpload() {
    document.getElementById('analysis-panel').classList.remove('active');
    document.getElementById('panel5').classList.add('active');
}

function showAbout() {
    document.getElementById('panel5').style.display = 'none';
    document.getElementById('about-panel').style.display = 'block';
}

function showCreators() {
    document.getElementById('panel5').style.display = 'none';
    document.getElementById('creators-panel').style.display = 'block';
}

function hideInfoPanels() {
    document.getElementById('about-panel').style.display = 'none';
    document.getElementById('creators-panel').style.display = 'none';
    document.getElementById('panel5').style.display = 'flex';
}

function resetForNewAnalysis() {
    // Hide analysis panel
    document.getElementById('analysis-panel').classList.remove('active');
    
    // Show upload panel
    document.getElementById('panel5').classList.add('active');
    
    // Clear the file input
    document.getElementById('file-upload').value = '';
    
    // Reset the audio player if it exists
    const audioPlayer = document.getElementById('audio-player');
    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.src = '';
    }
    
    // Hide any existing results
    document.getElementById('results-container').innerHTML = '';
}

function showError(message) {
    // Show error message
    const resultsContainer = document.getElementById('results-container');
    resultsContainer.innerHTML = `
        <div class="error-message">
            <i class="fas fa-exclamation-circle"></i>
            <p>${message}</p>
        </div>
    `;
    
    // Automatically reset after 3 seconds
    setTimeout(() => {
        resetForNewAnalysis();
    }, 3000);
}