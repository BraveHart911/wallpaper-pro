import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_library import app


class DesktopCompatibilityTests(unittest.TestCase):
    def test_pending_layout_decisions_preserve_external_edits(self):
        for action, external_edit, expected in (
            ('keep', False, 'candidate'),
            ('revert', False, 'original'),
            ('timeout', False, 'original'),
            ('timeout', True, 'external'),
        ):
            with self.subTest(action=action, external_edit=external_edit), tempfile.TemporaryDirectory() as directory:
                with patch.dict('os.environ', XDG_CONFIG_HOME=directory), patch.object(app, 'reload_monitor_layout'), patch.object(app.subprocess, 'Popen') as watchdog, patch.object(app.time, 'sleep'):
                    with app.monitor_layout_lock() as (config, pending):
                        config.parent.mkdir()
                        config.write_text('original')
                        backup = app.apply_monitor_layout(config, 'candidate', True, pending)
                    self.assertTrue(watchdog.call_args.kwargs['start_new_session'])
                    if external_edit:
                        config.write_text('external')
                    app.monitor_decision(SimpleNamespace(action=action, backup=backup))
                    self.assertEqual(config.read_text(), expected)
                    self.assertEqual(Path(backup).read_text(), 'original')
                    self.assertFalse(pending.exists())

    def test_layout_edits_ignore_commented_monitor_rules(self):
        commented = '-- hl.monitor({ output = "DP-1", mode = "preferred", position = "auto", scale = 1 })\n'
        monitor = {'name': 'DP-1', 'availableModes': ['1920x1080@60.00Hz']}
        rule = 'hl.monitor({ output = "DP-1", mode = "1920x1080@60.0", position = "-100x20", scale = 1.0 })'
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'hypr/monitors.lua'
            config.parent.mkdir()
            profiles = Path(directory) / 'wallpaper-pro/monitor-profiles.json'
            profiles.parent.mkdir()
            profiles.write_text(json.dumps([{'name': 'Desk', 'monitors': [
                {'name': 'DP-1', 'mode': '1920x1080@60.0', 'x': -100, 'y': 20, 'scale': 1.0}
            ]}]))
            for command, args in (
                (app.monitor_set, SimpleNamespace(name='DP-1', mode='1920x1080@60.0', x=-100, y=20, scale=1.0, brightness=None)),
                (app.monitor_profile, SimpleNamespace(action='apply', name='Desk')),
            ):
                with self.subTest(command=command.__name__):
                    config.write_text(commented)
                    with patch.dict('os.environ', XDG_CONFIG_HOME=directory), patch.object(app.shutil, 'which', return_value='hyprctl'), patch.object(app.subprocess, 'run', side_effect=[
                        subprocess.CompletedProcess([], 0, json.dumps([monitor])),
                        subprocess.CompletedProcess([], 0, ''),
                        subprocess.CompletedProcess([], 0, ''),
                    ]), patch('builtins.print'):
                        command(args)
                    self.assertEqual(config.read_text().splitlines()[0], commented.rstrip())
                    self.assertIn(rule, config.read_text().splitlines())

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
