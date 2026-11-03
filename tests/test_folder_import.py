from pathlib import Path
import subprocess
import tempfile
import unittest
from test_library import app, PNG


class FolderImportTests(unittest.TestCase):
    def test_recursive_import_deduplicates_and_makes_previews(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'My wallpapers'
            nested = root / 'videos' / 'deep'
            nested.mkdir(parents=True)
            (root / 'image.PNG').write_bytes(PNG)
            (nested / 'duplicate.png').write_bytes(PNG)
            (nested / 'readme.txt').write_text('ignored')
            video = nested / 'live.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'color=c=green:size=640x360:rate=10', '-t', '0.4', '-c:v', 'libx264', str(video)], check=True)
            (nested / 'broken.jpg').write_bytes(b'broken')
            data = Path(tmp) / 'data'
            state = app.default()
            events, checkpoints = [], []
            app.import_folder(state, root.as_uri(), data, events.append, lambda s: checkpoints.append(len(s['library'])))
            report = state['lastFolderImport']
            self.assertEqual((report['added'], report['duplicates'], report['failed'], report['skipped']), (2, 1, 1, 1))
            self.assertEqual(len(events), 4)
            self.assertTrue(checkpoints)
            self.assertEqual({m['kind'] for m in state['library']}, {'image', 'video'})
            for media in state['library']:
                self.assertTrue(media['thumbnailUrl'].endswith('.jpg'))
                self.assertEqual(media['sourceFolder'], str(root))
            self.assertFalse(state['enabled'])
            app.import_folder(state, str(root), data)
            self.assertEqual(len(state['library']), 2)
            self.assertEqual(state['lastFolderImport']['added'], 0)
            self.assertEqual(state['lastFolderImport']['duplicates'], 3)
            self.assertTrue(video.exists())

    def test_cache_and_symlink_directories_are_not_recursed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'managed'
            (data / 'library').mkdir(parents=True)
            (data / 'library' / 'image.png').write_bytes(PNG)
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'image.png').write_bytes(PNG)
            source = root / 'source'
            source.mkdir()
            (source / 'linked').symlink_to(outside, target_is_directory=True)
            state = app.default()
            app.import_folder(state, str(source), data)
            self.assertEqual(state['lastFolderImport']['found'], 0)
            with self.assertRaises(ValueError):
                app.import_folder(state, str(data), data)
            app.import_folder(state, str(root), data)
            self.assertEqual(state['lastFolderImport']['found'], 1)

    def test_missing_folder_does_not_change_library(self):
        state = app.default()
        with self.assertRaises(ValueError):
            app.import_folder(state, '/nonexistent/wallpaper-pro-folder', Path('/unused'))
        self.assertEqual(state, app.default())
