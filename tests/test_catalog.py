import unittest
from pathlib import Path
from types import SimpleNamespace
from test_library import app


class CatalogTests(unittest.TestCase):
    def test_catalog_has_playable_assets_in_all_categories(self):
        state = app.with_starter_library(app.default())
        self.assertEqual(len(state['library']), 15)
        self.assertEqual(sum(item['kind'] == 'video' for item in state['library']), 3)
        self.assertEqual(sum(item['kind'] == 'image' and item['layout'] == 'single' for item in state['library']), 6)
        self.assertEqual(sum(item['kind'] == 'image' and item['layout'] == 'panoramic' for item in state['library']), 6)
        self.assertFalse(state['enabled'])
        for item in state['library']:
            dimensions = app.validate_media(Path(item['path']))
            self.assertEqual(dimensions, {'width': item['width'], 'height': item['height']})
            self.assertTrue(item['thumbnailUrl'].startswith('file:///'))

    def test_refresh_preserves_imports_and_does_not_duplicate_starters(self):
        state = app.default()
        custom = {'id': 'custom', 'name': 'My wallpaper', 'path': '/my/image.jpg'}
        state['library'] = [custom]
        app.with_starter_library(state)
        app.with_starter_library(state)
        self.assertEqual(len(state['library']), 16)
        self.assertEqual(state['library'][-1], custom)

    def test_starter_cannot_be_removed(self):
        state = app.with_starter_library(app.default())
        with self.assertRaisesRegex(ValueError, 'Starter wallpapers'):
            app.update(state, SimpleNamespace(command='remove', id=state['library'][0]['id']), Path('/unused'))

    def test_panorama_can_be_applied_from_catalog(self):
        state = app.with_starter_library(app.default())
        media = next(item for item in state['library'] if item['layout'] == 'panoramic')
        app.update(state, SimpleNamespace(command='apply', id=media['id'], mode='span'), Path('/unused'))
        self.assertEqual(state['default'], media['id'])
        self.assertTrue(state['enabled'])
