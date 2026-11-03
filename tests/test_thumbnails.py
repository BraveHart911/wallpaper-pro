from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from test_library import app, PNG


class ThumbnailTests(unittest.TestCase):
    def test_image_preview_is_cached_and_regenerated_when_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = data / 'image.png'
            source.write_bytes(PNG)
            media = app.import_media(str(source), data)
            preview = Path(app.urllib.request.url2pathname(app.urllib.parse.urlparse(media['thumbnailUrl']).path))
            self.assertGreater(preview.stat().st_size, 0)
            state = app.default()
            state['library'] = [media]
            with patch.object(app.subprocess, 'run', side_effect=AssertionError('Should reuse cached preview')):
                app.ensure_thumbnails(state, data)
            preview.unlink()
            app.ensure_thumbnails(state, data)
            self.assertTrue(preview.exists())
            self.assertNotIn('thumbnailError', media)

    def test_existing_short_video_gets_frame_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = data / "short ' video.mp4"
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'color=c=blue:size=640x360:rate=10', '-t', '0.4', '-c:v', 'libx264', str(source)], check=True)
            media = {'id': 'legacy-video', 'kind': 'video', 'path': str(source)}
            state = app.default()
            state['library'] = [media]
            app.ensure_thumbnails(state, data)
            self.assertIn('thumbnailUrl', media, media)
            preview = Path(app.urllib.request.url2pathname(app.urllib.parse.urlparse(media['thumbnailUrl']).path))
            dimensions = app.validate_media(preview)
            self.assertEqual(dimensions, {'width': 480, 'height': 270})

    def test_failed_preview_preserves_entry_and_cleans_partial_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = data / 'broken.mp4'
            source.write_bytes(b'bad')
            state = app.default()
            state['library'] = [{'id': 'broken', 'kind': 'video', 'path': str(source)}]
            app.ensure_thumbnails(state, data)
            self.assertIn('thumbnailError', state['library'][0])
            self.assertEqual(list((data / 'thumbnails').iterdir()), [])
            self.assertTrue(source.exists())
