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

from app.analysis_utils import chunk_blocks
from app.analysis_utils import estimate_tokens
from app.analysis_utils import format_message_block
from app.analysis_utils import normalize_tag
from app.analysis_utils import trim_message_texts


class AnalysisUtilsTests(unittest.TestCase):
    def test_estimate_tokens(self) -> None:
        self.assertEqual(estimate_tokens(''), 0)
        self.assertEqual(estimate_tokens('abcd'), 1)
        self.assertEqual(estimate_tokens('abcde'), 2)

    def test_normalize_tag(self) -> None:
        self.assertEqual(normalize_tag('Tag'), '#tag')
        self.assertEqual(normalize_tag(' #Tag '), '#tag')
        self.assertIsNone(normalize_tag('bad tag'))

    def test_chunk_blocks(self) -> None:
        blocks = ['a' * 20, 'b' * 20, 'c' * 20]
        chunks = chunk_blocks(blocks, base_tokens=5, max_tokens=12)
        self.assertEqual(len(chunks), 3)

    def test_trim_message_texts_respects_limit(self) -> None:
        message = {
            'channel_id': 1,
            'message_id': 2,
            'user_id': 3,
            'date': datetime(2026, 1, 1, tzinfo=timezone.utc),
            'text': 'a' * 400,
            'reply_to': {
                'message_id': 1,
                'user_id': 2,
                'text': 'b' * 400,
            },
            'forwarded': None,
        }
        trim_message_texts(message, 50)
        block = format_message_block(message)
        self.assertLessEqual(estimate_tokens(block), 50)
