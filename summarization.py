import json
import os

import tagging

MEDDIC_BANT_PROMPT = """You are extracting a MEDDIC/BANT sales-qualification summary from a call transcript.
Return ONLY a JSON object with exactly these keys, each a string (use "" if the signal isn't present in the transcript):
metrics, economic_buyer, decision_criteria, decision_process, identify_pain, champion, budget, authority, need, timeline.
Each value should be a 1-2 sentence synthesis grounded in what was actually said — never invent information.

Transcript:
{transcript}
"""


def summarize_free(transcript):
    return tagging.tag_transcript(transcript)


def summarize_pro(transcript, client=None):
    if client is None:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    message = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': MEDDIC_BANT_PROMPT.format(transcript=transcript)}],
    )
    raw_text = message.content[0].text
    parsed = json.loads(raw_text)
    return {field: parsed.get(field, '') for field in tagging.FIELDS}


def summarize(transcript, tier, **kwargs):
    if tier == 'free':
        return summarize_free(transcript, **kwargs)
    if tier == 'pro':
        return summarize_pro(transcript, **kwargs)
    raise ValueError(f"Unknown tier: {tier!r}")
