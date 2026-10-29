"""Free local transcription smoke check; requires .local/whisper-smoke.mp4."""
from pathlib import Path
import json
import os
import sys
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env.local', override=True)
sys.path.insert(0, str(ROOT / 'backend'))
os.chdir(ROOT / 'backend')
from src.media.transcription import transcribe_with_whisper, _whisper_result_to_transcript_data
result = transcribe_with_whisper(ROOT / '.local/whisper-smoke.mp4', model_name='tiny.en', language='en')
words = [w for s in result.get('segments', []) for w in s.get('words', [])]
assert len(words) > 15, result.get('text')
assert all(w['end'] >= w['start'] for w in words)
(ROOT / '.local/whisper-smoke-result.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'model': 'tiny.en', 'text': result.get('text'), 'word_count': len(words),
                  'word_timestamps_valid': True,
                  'cached_words': len(_whisper_result_to_transcript_data(result).get('words', []))}))
