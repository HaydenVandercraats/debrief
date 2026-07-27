# tests/test_transcription.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import transcription


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeWhisperModel:
    def transcribe(self, audio_path):
        segments = [FakeSegment(' Hello.'), FakeSegment(' World.')]
        info = None
        return segments, info


def test_transcribe_free_joins_segments():
    result = transcription.transcribe_free('fake.wav', whisper_model=FakeWhisperModel())
    assert result == 'Hello. World.'


class FakeOpenAITranscription:
    text = 'Hello from the cloud.'


class FakeOpenAIClient:
    class audio:
        class transcriptions:
            @staticmethod
            def create(model, file):
                return FakeOpenAITranscription()


def test_transcribe_pro_returns_api_text(tmp_path):
    audio_file = tmp_path / 'fake.wav'
    audio_file.write_bytes(b'not-real-audio')
    result = transcription.transcribe_pro(str(audio_file), client=FakeOpenAIClient())
    assert result == 'Hello from the cloud.'


def test_transcribe_dispatches_by_tier(tmp_path, monkeypatch):
    audio_file = tmp_path / 'fake.wav'
    audio_file.write_bytes(b'not-real-audio')

    monkeypatch.setattr(transcription, 'transcribe_free', lambda path, whisper_model=None: 'free-result')
    monkeypatch.setattr(transcription, 'transcribe_pro', lambda path, client=None: 'pro-result')

    assert transcription.transcribe(str(audio_file), 'free') == 'free-result'
    assert transcription.transcribe(str(audio_file), 'pro') == 'pro-result'
