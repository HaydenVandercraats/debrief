import os


def transcribe_free(audio_path, whisper_model=None):
    if whisper_model is None:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel('base')
    segments, _info = whisper_model.transcribe(audio_path)
    return ''.join(segment.text for segment in segments).strip()


def transcribe_pro(audio_path, client=None):
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    with open(audio_path, 'rb') as audio_file:
        response = client.audio.transcriptions.create(model='whisper-1', file=audio_file)
    return response.text.strip()


def transcribe(audio_path, tier, **kwargs):
    if tier == 'free':
        return transcribe_free(audio_path, **kwargs)
    if tier == 'pro':
        return transcribe_pro(audio_path, **kwargs)
    raise ValueError(f"Unknown tier: {tier!r}")
