import importlib.util
import tempfile
import unittest
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('wallpaper_pro', Path(__file__).parents[1] / 'scripts/wallpaper-pro.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def png_chunk(kind, value):
    return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value))


PNG = (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 2, 0, 0, 0))
       + png_chunk(b'IDAT', zlib.compress((b'\x00' + b'\x40\x90\xc0' * 16) * 16)) + png_chunk(b'IEND', b''))


class LibraryTests(unittest.TestCase):
    def test_import_and_independent_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "a ' quoted image.png"
            source.write_bytes(PNG)
            media = app.import_media(str(source), base / 'data')
            source.unlink()
            self.assertTrue(Path(media['path']).exists())
            self.assertTrue(media['thumbnailUrl'].endswith('.jpg'))
            self.assertTrue(media['url'].startswith('file:///'))
            state = app.default()
            state['library'] = [media]
            for monitor in ['DP-1', 'HDMI-A-1']:
                app.update(state, SimpleNamespace(command='apply', id=media['id'], mode='individual', monitor=monitor), base)
            self.assertEqual(len(state['assignments']), 2)
            app.save(base / 'settings.json', state)
            self.assertEqual(app.load(base / 'settings.json'), state)
            with self.assertRaises(ValueError):
                app.update(state, SimpleNamespace(command='remove', id=media['id']), base)

    def test_video_span_and_clear_monitor(self):
        with tempfile.TemporaryDirectory() as tmp:
            media_path = Path(tmp) / 'movie.mp4'
            media_path.touch()
            state = app.default()
            state['library'] = [{'id': 'v', 'kind': 'video', 'path': str(media_path)}]
            app.update(state, SimpleNamespace(command='apply', id='v', mode='span'), Path(tmp))
            self.assertEqual(state['mode'], 'span')
            self.assertTrue(state['enabled'])
            state['assignments']['DP-2'] = 'v'
            app.update(state, SimpleNamespace(command='unassign', monitor='DP-2'), Path(tmp))
            self.assertEqual(state['assignments'], {})

    def test_corrupt_import_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'broken.png'
            source.write_bytes(b'not an image')
            with self.assertRaises(ValueError):
                app.import_media(str(source), Path(tmp) / 'data')
            self.assertEqual(list((Path(tmp) / 'data/library').iterdir()), [])

    def test_missing_assignment_file_preserves_mode(self):
        state = app.default()
        state['library'] = [{'id': 'gone', 'kind': 'image', 'path': '/nonexistent/wallpaper.png'}]
        with self.assertRaises(ValueError):
            app.update(state, SimpleNamespace(command='apply', id='gone', mode='span'), Path('/unused'))
        self.assertEqual(state['mode'], 'individual')

    def test_invalid_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            for source in ['https://example.com/page.html', 'ftp://example.com/video.mp4']:
                with self.assertRaises(ValueError):
                    app.import_media(source, Path(tmp))

    def test_failed_apply_preserves_state(self):
        state = app.default()
        with self.assertRaises(ValueError):
            app.update(state, SimpleNamespace(command='apply', id='missing'), Path('/unused'))
        self.assertEqual(state, app.default())


if __name__ == '__main__':
    unittest.main()
