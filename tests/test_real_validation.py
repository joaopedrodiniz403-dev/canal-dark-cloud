import tempfile
import unittest
from pathlib import Path
from nuvem.real_validation import word_error, obtain_movie


class RealValidationTests(unittest.TestCase):
    def test_word_error_normalizes_case_and_punctuation(self):
        result=word_error("We're here!", "we're HERE")
        self.assertEqual(result['wer'],0)
        self.assertEqual(result['reference_words'],3)

    def test_word_error_accounts_for_insert_delete_substitute(self):
        self.assertEqual(word_error('one two','one three')['word_errors'],1)
        self.assertEqual(word_error('one two','one')['word_errors'],1)
        self.assertEqual(word_error('one two','one two three')['word_errors'],1)
        self.assertEqual(word_error('one two','one three')['wer'],.5)
        with self.assertRaises(ValueError):word_error('', 'one')

    def test_wrong_existing_source_hash_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'movie.mov';path.write_bytes(b'human file')
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):obtain_movie(path)
            self.assertEqual(path.read_bytes(),b'human file')
