import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('wallpaper_pro', Path(__file__).parents[1] / 'scripts/wallpaper-pro.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class LibraryTests(unittest.TestCase):
    def test_import_and_independent_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "a ' quoted image.png"
            source.write_bytes(b'test fixture')
            media = app.import_media(str(source), base / 'data')
            source.unlink()
            self.assertTrue(Path(media['path']).exists())
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

    def test_video_span_rejected_without_mutation(self):
        state = app.default()
        state['library'] = [{'id': 'v', 'kind': 'video'}]
        with self.assertRaises(ValueError):
            app.update(state, SimpleNamespace(command='apply', id='v', mode='span'), Path('/unused'))
        self.assertFalse(state['enabled'])

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
