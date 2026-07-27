import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tagging
import summarization


def test_summarize_free_delegates_to_tagging():
    transcript = "We have about fifty grand set aside for this."
    result = summarization.summarize_free(transcript)
    assert set(result.keys()) == set(tagging.FIELDS)
    assert 'fifty grand' in result['budget']


class FakeContentBlock:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, payload):
        self.content = [FakeContentBlock(json.dumps(payload))]


class FakeAnthropicClient:
    def __init__(self, payload):
        self._payload = payload
        self.messages = self

    def create(self, **kwargs):
        return FakeMessage(self._payload)


def test_summarize_pro_parses_json_response():
    payload = {field: '' for field in tagging.FIELDS}
    payload['budget'] = 'Roughly $50k allocated for this initiative.'
    client = FakeAnthropicClient(payload)

    result = summarization.summarize_pro('transcript text', client=client)
    assert result['budget'] == 'Roughly $50k allocated for this initiative.'
    assert set(result.keys()) == set(tagging.FIELDS)


def test_summarize_dispatches_by_tier(monkeypatch):
    monkeypatch.setattr(summarization, 'summarize_free', lambda transcript: {'free': True})
    monkeypatch.setattr(summarization, 'summarize_pro', lambda transcript, client=None: {'pro': True})

    assert summarization.summarize('text', 'free') == {'free': True}
    assert summarization.summarize('text', 'pro') == {'pro': True}


def test_summarize_pro_raises_on_missing_api_key(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

    import pytest
    with pytest.raises(RuntimeError, match='ANTHROPIC_API_KEY is not set'):
        summarization.summarize_pro('transcript text')
