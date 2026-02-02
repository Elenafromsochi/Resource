import os
import sys
from pathlib import Path
import unittest
from datetime import datetime
from datetime import timezone

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / 'backend'
sys.path.append(str(BACKEND_DIR))

os.environ.setdefault('POSTGRES_URL', 'postgresql://user:pass@localhost:5432/test')
os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('MONGO_DB', 'test')
os.environ.setdefault('TELEGRAM_API_ID', '12345')
os.environ.setdefault('TELEGRAM_API_HASH', 'hash')
os.environ.setdefault('TELETHON_SESSION', 'session')
os.environ.setdefault('DEEPSEEK_API_KEY', 'test')

from app.analysis_utils import ensure_aware
from app.analysis_utils import extract_json_payload
from app.analysis_utils import format_message_block
from app.analysis_utils import normalize_tag


class AnalysisUtilsTests(unittest.TestCase):
    def test_ensure_aware(self) -> None:
        value = datetime(2026, 1, 1)
        aware = ensure_aware(value)
        self.assertIsNotNone(aware.tzinfo)

    def test_normalize_tag(self) -> None:
        self.assertEqual(normalize_tag('Tag'), '#tag')
        self.assertEqual(normalize_tag(' #Tag '), '#tag')
        self.assertIsNone(normalize_tag('bad tag'))

    def test_extract_json_payload_handles_fenced(self) -> None:
        payload = extract_json_payload('```json\n{"hashtags": []}\n```')
        self.assertEqual(payload, {'hashtags': []})

    def test_format_message_block_includes_reply(self) -> None:
        message = {
            'channel_id': 1,
            'message_id': 2,
            'user_id': 3,
            'date': datetime(2026, 1, 1, tzinfo=timezone.utc),
            'text': 'hello',
            'reply_to': {
                'message_id': 1,
                'user_id': 2,
                'text': 'reply text',
            },
            'forwarded': None,
        }
        block = format_message_block(message)
        self.assertIn('reply:', block)
        self.assertIn('text:', block)
        self.assertIn('reply text', block)
