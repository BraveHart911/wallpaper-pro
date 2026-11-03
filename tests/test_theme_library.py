from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_library import app, PNG


class ThemeLibraryTests(unittest.TestCase):
    def test_all_theme_locations_nested_files_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = [(base / 'stock', True), (base / 'custom', True), (base / 'backgrounds', False)]
            for parent, nested in roots:
                folder = parent / parent.name
                if nested:
                    folder /= 'backgrounds'
                folder /= 'nested'
                folder.mkdir(parents=True)
                (folder / 'wallpaper.png').write_bytes(PNG)
            (base / 'custom/custom/backgrounds/loop').symlink_to(base / 'custom/custom/backgrounds', target_is_directory=True)
            result = app.discover_theme_library(base / 'data', roots)
            self.assertEqual(result['report']['files'], 3)
            self.assertEqual(result['report']['wallpapers'], 1)
            media = result['library'][0]
            self.assertEqual(media['themes'], ['Backgrounds', 'Custom', 'Stock'])
            self.assertTrue(media['themeManaged'])
            self.assertTrue(media['thumbnailUrl'])
            with patch.object(app, 'validate_media', side_effect=AssertionError('Unchanged themes must not decode again')):
                second = app.discover_theme_library(base / 'data', roots, result['cache'])
            self.assertEqual(second['library'], result['library'])

    def test_unchanged_scan_does_not_checkpoint_or_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            folder = base / 'themes/example/backgrounds'
            folder.mkdir(parents=True)
            for index in range(26):
                (folder / (str(index) + '.png')).write_bytes(PNG)
            roots = [(base / 'themes', True)]
            first = app.discover_theme_library(base / 'data', roots)
            def unexpected(value):
                raise AssertionError('Unchanged scan must not write checkpoints')
            with patch.object(app, 'validate_media', side_effect=AssertionError('Unchanged scan must not decode')):
                app.discover_theme_library(base / 'data', roots, first['cache'], checkpoint=unexpected)

    def test_theme_discovery_preserves_latest_assignments_and_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            folder = base / 'themes/example/backgrounds'
            folder.mkdir(parents=True)
            (folder / 'a.png').write_bytes(PNG)
            discovery = app.discover_theme_library(base / 'data', [(base / 'themes', True)])
            state = app.default()
            personal = dict(discovery['library'][0])
            personal.pop('themeManaged')
            state.update(enabled=True, mode='individual', default='saved', assignments={'DP-1': personal['id']}, library=[personal])
            app.merge_theme_library(state, discovery)
            self.assertEqual(len(state['library']), 1)
            self.assertFalse(state['library'][0].get('themeManaged', False))
            self.assertEqual(state['assignments'], {'DP-1': personal['id']})
            self.assertEqual(state['default'], 'saved')
            self.assertTrue(state['enabled'])

    def test_removed_theme_is_pruned_but_selected_wallpaper_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            folder = base / 'themes/example/backgrounds'
            folder.mkdir(parents=True)
            image = folder / 'a.png'
            image.write_bytes(PNG)
            discovery = app.discover_theme_library(base / 'data', [(base / 'themes', True)])
            state = app.merge_theme_library(app.default(), discovery)
            identity = state['library'][0]['id']
            state.update(enabled=True, default=identity, mode='span')
            image.unlink()
            empty = app.discover_theme_library(base / 'data', [(base / 'themes', True)], discovery['cache'])
            app.merge_theme_library(state, empty)
            self.assertEqual(state['default'], identity)
            self.assertTrue(state['library'][0]['themeMissing'])
            state['default'] = ''
            app.merge_theme_library(state, empty)
            self.assertEqual(state['library'], [])

    def test_explicit_import_promotes_theme_reference_to_personal_copy(self):
        old = {'id': 'a', 'path': '/theme/a.png', 'themeManaged': True, 'themes': ['Theme'], 'themeMissing': True}
        app.refresh_import(old, {'id': 'a', 'path': '/library/a.png', 'thumbnailUrl': 'file:///preview.jpg'})
        self.assertEqual(old['path'], '/library/a.png')
        self.assertNotIn('themeManaged', old)
        self.assertNotIn('themeMissing', old)
        self.assertEqual(old['themes'], ['Theme'])
