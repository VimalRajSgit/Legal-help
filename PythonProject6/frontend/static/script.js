let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function sendQuery() {
    const queryInput = document.getElementById('query-input');
    const languageSelect = document.getElementById('language-select');
    const query = queryInput.value.trim();
    const language = languageSelect.value;

    if (!query) {
        displayResponse('Please enter a legal question.');
        return;
    }

    try {
        const response = await fetch('/api/user/process_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, language, generate_audio: true })
        });

        const data = await response.json();

        if (data.success) {
            updateChatHistory(data.history);
            displayResponse(data.response);
            displayKeyPoints(data.key_points);
            if (data.audio_path) {
                playAudio(data.audio_path);
            }
        } else {
            displayResponse(`Error: ${data.error}`);
        }

        queryInput.value = '';
        queryInput.focus();
    } catch (error) {
        displayResponse(`Error: ${error.message}`);
    }
}

async function startRecording() {
    if (isRecording) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');

            displayStatus('Processing audio...');

            try {
                const response = await fetch('/api/user/transcribe_audio', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    document.getElementById('query-input').value = data.transcription;
                    document.getElementById('language-select').value = data.language;
                    await sendTranscribedQuery(data.transcription, data.language);
                    displayStatus('');
                } else {
                    displayResponse(`Error: ${data.error}`);
                    displayStatus('');
                }
            } catch (error) {
                displayResponse(`Error: ${error.message}`);
                displayStatus('');
            }
        };

        mediaRecorder.start();
        isRecording = true;

        displayStatus('Recording...');
        document.getElementById('record-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
    } catch (error) {
        displayResponse(`Error: ${error.message}`);
        displayStatus('');
    }
}

async function sendTranscribedQuery(query, language) {
    try {
        const response = await fetch('/api/user/process_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, language, generate_audio: true })
        });

        const data = await response.json();

        if (data.success) {
            updateChatHistory(data.history);
            displayResponse(data.response);
            displayKeyPoints(data.key_points);
            if (data.audio_path) {
                playAudio(data.audio_path);
            }
        } else {
            displayResponse(`Error: ${data.error}`);
        }
    } catch (error) {
        displayResponse(`Error: ${error.message}`);
    }
}

function stopRecording() {
    if (!isRecording || !mediaRecorder) return;

    mediaRecorder.stop();
    isRecording = false;

    document.getElementById('record-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
}

async function clearHistory() {
    try {
        const response = await fetch('/api/user/clear_history', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('chat-history').innerHTML = '';
            displayResponse(data.message);
            displayKeyPoints('');
            document.getElementById('response-audio').src = '';
        }
    } catch (error) {
        displayResponse(`Error: ${error.message}`);
    }
}

function updateChatHistory(history) {
    const chatHistory = document.getElementById('chat-history');
    chatHistory.innerHTML = history.map((entry, index) => `
        <div class="p-4 ${index % 2 === 0 ? 'bg-white' : 'bg-navy-50'} border-b border-navy-200">
            <p class="font-semibold text-navy-900">Question: ${entry.query}</p>
            <p class="text-navy-600">Answer: ${entry.response}</p>
        </div>
    `).join('');
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function displayResponse(response) {
    document.getElementById('response-area').innerText = response;
}

function displayKeyPoints(points) {
    document.getElementById('key-points').innerText = points;
}

function playAudio(audioPath) {
    const audio = document.getElementById('response-audio');
    audio.src = `/audio/${audioPath}`;
    audio.play().catch(error => console.error('Audio playback error:', error));
}

function displayStatus(message) {
    const statusElement = document.getElementById('recording-status');
    statusElement.innerText = message;
    statusElement.classList.toggle('hidden', !message);
}