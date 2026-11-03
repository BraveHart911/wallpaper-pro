import json
from pathlib import Path
import shutil
import subprocess
import unittest
from test_library import app


class DesktopCompatibilityTests(unittest.TestCase):
    def test_stock_background_and_bars_are_not_conflicts(self):
        monitor = {'name': 'DP-1', 'width': 3840, 'height': 2160, 'scale': 2}
        layers = {'DP-1': {'levels': {'0': [{'namespace': 'omarchy-background', 'w': 1920, 'h': 1080}],
                                      '1': [{'namespace': 'wallpaper-pro', 'w': 1920, 'h': 1080}],
                                      '2': [{'namespace': 'omarchy-bar', 'w': 1920, 'h': 24}]}}}
        self.assertEqual(app.competing_wallpapers(layers, [monitor]), [])
        layers['DP-1']['levels']['1'].append({'namespace': 'livewall', 'w': 1920, 'h': 1080})
        self.assertIn('livewall', app.competing_wallpapers(layers, [monitor])[0])

    def test_rotated_output_detects_competing_wallpaper(self):
        monitor = {'name': 'DP-1', 'width': 1920, 'height': 1080, 'scale': 1, 'transform': 1}
        layers = {'DP-1': {'levels': {'0': [{'namespace': 'swaybg', 'w': 1080, 'h': 1920}]}}}
        self.assertEqual(len(app.competing_wallpapers(layers, [monitor])), 1)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for pure JS geometry checks')
    def test_logical_bounds_and_theme_parsing(self):
        path = Path(__file__).parents[1] / 'js/Desktop.js'
        script = '''const fs = require('fs'), vm = require('vm'), assert = require('assert');
const context = {}; vm.createContext(context); vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const bounds = value => JSON.parse(JSON.stringify(context.bounds(value)));
assert.deepStrictEqual(bounds([]), {left:0,top:0,width:0,height:0});
assert.deepStrictEqual(bounds([{x:-1920,y:0,width:1920,height:1080},{x:0,y:-200,width:1280,height:720}]), {left:-1920,top:-200,width:3200,height:1280});
assert.deepStrictEqual(bounds([{x:0,y:0,width:1080,height:1920},{x:1080,y:0,width:1920,height:1080}]), {left:0,top:0,width:3000,height:1920});
assert.equal(context.colors('background = "#abcdef"\\naccent = "#123456"').background, '#abcdef');
assert.equal(context.colors('background = "not-a-color"').background, '#111820');
'''
        subprocess.run(['node', '-e', script, str(path)], check=True)
