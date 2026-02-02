import os
import unittest

os.environ.setdefault('POSTGRES_URL', 'postgresql://user:pass@localhost:5432/test')
os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('MONGO_DB', 'test')
os.environ.setdefault('TELEGRAM_API_ID', '12345')
os.environ.setdefault('TELEGRAM_API_HASH', 'hash')
os.environ.setdefault('TELETHON_SESSION', 'session')
os.environ.setdefault('DEEPSEEK_API_KEY', 'test')

from app.api.channels import normalize_username


class NormalizeUsernameTests(unittest.TestCase):
    def test_strips_at_symbol(self) -> None:
        self.assertEqual(normalize_username('@news'), 'news')

    def test_strips_t_me_links(self) -> None:
        self.assertEqual(normalize_username('https://t.me/news'), 'news')
        self.assertEqual(normalize_username('http://t.me/news'), 'news')

    def test_strips_telegram_me_links(self) -> None:
        self.assertEqual(normalize_username('https://telegram.me/news'), 'news')
        self.assertEqual(normalize_username('http://telegram.me/news'), 'news')

    def test_trims_whitespace(self) -> None:
        self.assertEqual(normalize_username('  @news  '), 'news')
