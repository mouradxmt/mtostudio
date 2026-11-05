import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ci.bootstrap import download

class ToolDownloadTest(unittest.TestCase):
    def test_valid_cached_archive_does_not_access_network(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'tool';target.write_bytes(b'valid')
            with patch('ci.bootstrap.urllib.request.urlopen',side_effect=AssertionError('Unexpected network')):
                download('https://example.test/tool',target,hashlib.sha256(b'valid').hexdigest())
    def test_bad_download_never_becomes_executable_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'tool'
            with patch('ci.bootstrap.urllib.request.urlopen',return_value=io.BytesIO(b'corrupt')):
                with self.assertRaisesRegex(ValueError,'checksum'):download('https://example.test/tool',target,'0'*64)
            self.assertFalse(target.exists());self.assertFalse(target.with_suffix('.partial').exists())
    def test_verified_replacement_is_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'tool';target.write_bytes(b'incomplete old download')
            with patch('ci.bootstrap.urllib.request.urlopen',return_value=io.BytesIO(b'verified')):
                download('https://example.test/tool',target,hashlib.sha256(b'verified').hexdigest())
            self.assertEqual(target.read_bytes(),b'verified');self.assertFalse(target.with_suffix('.partial').exists())

if __name__=='__main__':unittest.main()
