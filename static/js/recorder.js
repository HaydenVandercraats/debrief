(function () {
  const startBtn = document.getElementById('start-btn');
  const stopBtn = document.getElementById('stop-btn');
  const statusEl = document.getElementById('recorder-status');
  const form = document.getElementById('call-form');

  let mediaRecorder = null;
  let recordedChunks = [];
  let audioContext = null;
  let activeStreams = [];

  function stopAllTracks() {
    activeStreams.forEach((stream) => stream.getTracks().forEach((track) => track.stop()));
    activeStreams = [];
  }

  startBtn.addEventListener('click', async () => {
    try {
      statusEl.textContent = 'Requesting screen/tab audio share...';
      const displayStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      activeStreams = [displayStream, micStream];

      audioContext = new AudioContext();
      const destination = audioContext.createMediaStreamDestination();

      if (displayStream.getAudioTracks().length > 0) {
        audioContext.createMediaStreamSource(new MediaStream(displayStream.getAudioTracks())).connect(destination);
      }
      audioContext.createMediaStreamSource(micStream).connect(destination);

      recordedChunks = [];
      mediaRecorder = new MediaRecorder(destination.stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunks.push(event.data);
      };
      mediaRecorder.start();

      statusEl.textContent = 'Recording...';
      startBtn.disabled = true;
      stopBtn.disabled = false;
    } catch (err) {
      statusEl.textContent = 'Could not start recording: ' + err.message;
      stopAllTracks();
    }
  });

  stopBtn.addEventListener('click', () => {
    if (!mediaRecorder) return;
    mediaRecorder.onstop = () => {
      stopAllTracks();
      if (audioContext) audioContext.close();

      const blob = new Blob(recordedChunks, { type: 'audio/webm' });
      if (blob.size < 1000) {
        statusEl.textContent = 'Recording appears empty (no audio captured) — check your share/mic selection and try again.';
        startBtn.disabled = false;
        stopBtn.disabled = true;
        return;
      }

      statusEl.textContent = 'Uploading and processing (this can take a minute)...';
      const formData = new FormData(form);
      formData.delete('audio');
      formData.append('audio', blob, 'call.webm');

      fetch(form.action, { method: 'POST', body: formData })
        .then((response) => {
          if (response.redirected) {
            window.location.href = response.url;
          } else {
            statusEl.textContent = 'Upload failed — please try again.';
          }
        })
        .catch(() => {
          statusEl.textContent = 'Upload failed — please try again.';
        });

      startBtn.disabled = false;
      stopBtn.disabled = true;
    };
    mediaRecorder.stop();
  });
})();
