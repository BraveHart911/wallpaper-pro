import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zlib
from types import SimpleNamespace
from test_library import app, png_chunk


def png(rgb):
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 2, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress((b'\x00' + bytes(rgb) * 16) * 16)) + png_chunk(b'IEND', b''))


class ColorTests(unittest.TestCase):
    def test_dominant_color_matches_real_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'sample.png'
            for rgb, name, neutral in [((255,0,0),'Red',False), ((0,255,0),'Green',False),
                                       ((0,0,255),'Blue',False), ((0,0,0),'Black',True), ((255,255,255),'White',True)]:
                source.write_bytes(png(rgb))
                color = app.dominant_color(source)
                self.assertEqual(color['colorName'], name)
                self.assertEqual(color['colorNeutral'], neutral)
                self.assertEqual(color['dominantColor'], '#' + ''.join(f'{c:02x}' for c in rgb))

    def test_color_cache_reuses_samples_and_invalidates_changed_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / 'preview.png'
            source.write_bytes(png((255,0,0)))
            media = {'id':'sample', 'thumbnailUrl':source.as_uri()}
            app.analyze_library_colors([media], base / 'data')
            with patch.object(app, 'dominant_color', side_effect=AssertionError('Cached colors must not decode again')):
                app.analyze_library_colors([media], base / 'data')
            source.write_bytes(png((0,0,255)))
            app.analyze_library_colors([media], base / 'data')
            self.assertEqual(media['colorName'], 'Blue')
            self.assertEqual(app.read_color_cache(base / 'data')[str(source)]['colors']['colorName'], 'Blue')

    def test_sort_preference_does_not_change_wallpaper_assignments(self):
        state = app.default()
        state.update(enabled=True, default='chosen', assignments={'DP-1':'chosen'})
        app.update(state, SimpleNamespace(command='sort', order='color'), Path('/unused'))
        self.assertEqual(state['sortOrder'], 'color')
        self.assertEqual(state['assignments'], {'DP-1':'chosen'})
        self.assertEqual(state['default'], 'chosen')
        self.assertTrue(state['enabled'])

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for JS ordering checks')
    def test_color_order_places_spectrum_before_neutrals_and_unknowns(self):
        path = Path(__file__).parents[1] / 'js/Library.js'
        script = '''const vm=require('vm'), fs=require('fs'), assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
const items=[{id:'white',name:'White',dominantColor:'#ffffff',colorNeutral:true,colorValue:1},
{id:'blue',name:'Blue',dominantColor:'#0000ff',colorHue:240,colorValue:1},
{id:'unknown',name:'Unknown'}, {id:'red',name:'Red',dominantColor:'#ff0000',colorHue:0,colorValue:1},
{id:'black',name:'Black',dominantColor:'#000000',colorNeutral:true,colorValue:0},
{id:'green',name:'Green',dominantColor:'#00ff00',colorHue:120,colorValue:1}];
const ids=items=>JSON.parse(JSON.stringify(items.map(i=>i.id)));
assert.deepStrictEqual(ids(c.ordered(items,'color')),['red','green','blue','black','white','unknown']);
assert.deepStrictEqual(ids(c.ordered(items,'name')),['black','blue','green','red','unknown','white']);
assert.deepStrictEqual(ids(c.ordered(items,'original')),ids(items));
assert.equal(items[0].id,'white');
assert.equal(c.spectrumIndex(0,0.5),-1);
assert.equal(c.spectrumIndex(100,-1),0);
assert.equal(c.spectrumIndex(100,2),99);
assert.equal(c.spectrumIndex(101,0.5),50);
const stops=c.spectrumStops(c.ordered(items,'color'),6);
assert.equal(stops[0].color,'#ff0000');assert.equal(stops[0].position,0);
assert.equal(stops[stops.length-1].position,1);
const single=c.spectrumStops([items[0]],96);assert.equal(single.length,2);assert.equal(single[1].color,'#ffffff');
const large=Array.from({length:1000},()=>items[0]);assert.equal(c.spectrumStops(large,96).length,96);
assert.equal(c.spectrumStops([],96).length,2);
'''
        subprocess.run(['node','-e',script,str(path)],check=True)
