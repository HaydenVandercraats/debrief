(function () {
  const startBtn = document.getElementById('start-btn');
  const stopBtn = document.getElementById('stop-btn');
  const statusEl = document.getElementById('recorder-status');
  const form = document.getElementById('call-form');

  let mediaRecorder = null;
  let recordedChunks = [];
  let audioContext = null;
  let activeStreams = [];
  let analyserNode = null;
  let peakAmplitude = 0;
  let samplingInterval = null;

  function stopAllTracks() {
    activeStreams.forEach((stream) => stream.getTracks().forEach((track) => track.stop()));
    activeStreams = [];
  }

  function stopSampling() {
    if (samplingInterval) {
      clearInterval(samplingInterval);
      samplingInterval = null;
    }
  }

  startBtn.addEventListener('click', async () => {
    try {
      statusEl.textContent = 'Requesting screen/tab audio share...';
      const displayStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
      activeStreams = [displayStream];

      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      activeStreams = [displayStream, micStream];

      audioContext = new AudioContext();
      const destination = audioContext.createMediaStreamDestination();
      const mixBus = audioContext.createGain();

      if (displayStream.getAudioTracks().length > 0) {
        audioContext.createMediaStreamSource(new MediaStream(displayStream.getAudioTracks())).connect(mixBus);
      }
      audioContext.createMediaStreamSource(micStream).connect(mixBus);

      analyserNode = audioContext.createAnalyser();
      mixBus.connect(destination);
      mixBus.connect(analyserNode);

      recordedChunks = [];
      peakAmplitude = 0;
      mediaRecorder = new MediaRecorder(destination.stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunks.push(event.data);
      };
      mediaRecorder.start();

      // Start sampling analyser for silence detection
      const dataArray = new Uint8Array(analyserNode.frequencyBinCount);
      samplingInterval = setInterval(() => {
        analyserNode.getByteTimeDomainData(dataArray);
        for (let i = 0; i < dataArray.length; i++) {
          const sample = Math.abs(dataArray[i] - 128);
          if (sample > peakAmplitude) {
            peakAmplitude = sample;
          }
        }
      }, 500);

      statusEl.textContent = 'Recording...';
      startBtn.disabled = true;
      startBtn.classList.add('is-recording');
      stopBtn.disabled = false;
    } catch (err) {
      statusEl.textContent = 'Could not start recording: ' + err.message;
      startBtn.classList.remove('is-recording');
      stopAllTracks();
    }
  });

  stopBtn.addEventListener('click', () => {
    if (!mediaRecorder) return;
    mediaRecorder.onstop = () => {
      stopSampling();
      stopAllTracks();
      if (audioContext) audioContext.close();

      startBtn.classList.remove('is-recording');

      const blob = new Blob(recordedChunks, { type: 'audio/webm' });
      if (blob.size < 1000 || peakAmplitude < 10) {
        statusEl.textContent = 'Recording appears silent — check your share/mic selection and try again.';
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
