import json
import os

import db
import summarization
import transcription


def run_pipeline(call_id, audio_path, tier, keep_audio, db_path=None):
    try:
        transcript = transcription.transcribe(audio_path, tier)
        db.update_call(call_id, db_path=db_path, transcript=transcript, status='summarizing')

        summary = summarization.summarize(transcript, tier)
        db.update_call(
            call_id,
            db_path=db_path,
            summary_json=json.dumps(summary),
            status='done',
        )
    except Exception as error:
        db.update_call(call_id, db_path=db_path, status='failed', error_message=str(error))
    finally:
        if not keep_audio and audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
