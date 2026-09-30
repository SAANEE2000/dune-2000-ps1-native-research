"""Negative boundaries: reject unrelated images and truncated/Form2 data."""
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dune_import import extent,import_disc

class ImportSafety(unittest.TestCase):
    def test_unrecognized_image_writes_no_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source=folder/'unrelated.bin';source.write_bytes(b'not the authorized game')
            with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):import_disc(source,folder/'assets')
            self.assertFalse((folder/'assets').exists())
            self.assertEqual(source.read_bytes(),b'not the authorized game')

    def test_form2_cannot_silently_become_2048_byte_data(self):
        sector=bytearray(2352);sector[:12]=b'\0'+b'\xff'*10+b'\0';sector[15]=2;sector[18]=0x20
        with self.assertRaisesRegex(ValueError,'Form2'):extent(io.BytesIO(sector),0,2048)

    def test_short_sector_is_not_zero_filled(self):
        with self.assertRaisesRegex(ValueError,'Bad Mode2'):extent(io.BytesIO(bytes(40)),0,2048)

if __name__=='__main__':unittest.main()
