import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tagging


def test_tag_transcript_matches_budget_sentence():
    transcript = "We have about fifty grand set aside for this. Not sure who else is involved."
    result = tagging.tag_transcript(transcript)
    assert 'fifty grand' in result['budget']


def test_tag_transcript_all_fields_present_even_when_empty():
    transcript = "It was a nice day."
    result = tagging.tag_transcript(transcript)
    assert set(result.keys()) == set(tagging.FIELDS)
    assert all(isinstance(v, str) for v in result.values())


def test_tag_transcript_matches_timeline_sentence():
    transcript = "We'd need this live before the end of Q3."
    result = tagging.tag_transcript(transcript)
    assert 'Q3' in result['timeline']
