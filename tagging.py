import re

FIELDS = (
    'metrics',
    'economic_buyer',
    'decision_criteria',
    'decision_process',
    'identify_pain',
    'champion',
    'budget',
    'authority',
    'need',
    'timeline',
)

FIELD_KEYWORDS = {
    'metrics': ['roi', 'savings', 'increase', 'reduce', 'percent', '%', 'metric', 'measure'],
    'economic_buyer': ['sign off', 'signs off', 'approve the budget', 'writes the check', 'final say'],
    'decision_criteria': ['criteria', 'must have', 'requirement', 'evaluating on', 'checklist'],
    'decision_process': ['procurement', 'legal review', 'security review', 'steps to close', 'approval process'],
    'identify_pain': ['problem', 'pain', 'frustrat', 'struggl', 'issue with', "isn't working"],
    'champion': ['internally push', 'advocate', 'championing', 'on our side', 'root for us'],
    'budget': ['budget', 'set aside', 'grand', 'dollars', 'price range', 'spend'],
    'authority': ['who else is involved', 'decision maker', 'i need to check with', 'report to'],
    'need': ['we need', 'looking for', 'want to', 'trying to'],
    'timeline': ['by q', 'deadline', 'go live', 'timeline', 'end of', 'next quarter'],
}


def _split_sentences(transcript):
    sentences = re.split(r'(?<=[.!?])\s+', transcript.strip())
    return [s.strip() for s in sentences if s.strip()]


def tag_transcript(transcript):
    result = {field: '' for field in FIELDS}
    sentences = _split_sentences(transcript)
    for field in FIELDS:
        keywords = FIELD_KEYWORDS[field]
        matches = [
            sentence for sentence in sentences
            if any(keyword in sentence.lower() for keyword in keywords)
        ]
        result[field] = ' '.join(matches)
    return result
