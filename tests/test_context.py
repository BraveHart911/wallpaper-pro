import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_library import app, PNG


class ContextTests(unittest.TestCase):
    def test_cached_visual_labels_use_precise_thumbnail_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            image = data / 'preview.png'
            image.write_bytes(PNG)
            media = {'id':'sample','thumbnailUrl':image.as_uri(),'dominantColor':'#0000ff','colorHue':240,'colorValue':1}
            record = app.context_records([media])[0]
            self.assertIsInstance(record['fingerprint'][1], str)
            self.assertEqual(int(record['fingerprint'][1]), image.stat().st_mtime_ns)
            cache = {'items':{str(image):{'fingerprint':record['fingerprint'],'group':'Forests','rank':3,'similarity':.3,'uncertain':False}}}
            state = app.default()
            state['library'] = [media]
            app.apply_cached_context(state, cache, data)
            self.assertEqual(media['contextGroup'], 'Forests')
            self.assertEqual(media['contextRank'], 3)
            self.assertEqual(state['contextReport']['analyzed'], 1)
            cache['items'][str(image)]['fingerprint'] = [0,'old']
            app.apply_cached_context(state, cache, data)
            self.assertNotIn('contextGroup', media)

    def test_unchanged_context_never_loads_model_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            image = data / 'preview.png'
            image.write_bytes(PNG)
            media = {'id':'sample','thumbnailUrl':image.as_uri(),'dominantColor':'#0000ff','colorHue':240,'colorValue':1}
            record = app.context_records([media])[0]
            cache = {'version':app.CONTEXT_VERSION,'labelVersion':app.CONTEXT_LABEL_VERSION,
                     'membership':[[record['id'],record['fingerprint'],app.context_band(record)]],
                     'items':{str(image):{'fingerprint':record['fingerprint'],'group':'Forests'}}}
            (data/'context-index.json').write_text(json.dumps(cache))
            with patch.object(app,'context_node',return_value='/fake/node'), patch.object(app,'run_context_process',side_effect=AssertionError('Cached grouping must not load models')):
                self.assertEqual(app.analyze_library_context([media],data,data),cache)

    def test_enabling_context_requires_local_runtime(self):
        state = app.default()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                app.update(state,SimpleNamespace(command='context',value='on'),Path(tmp))
        self.assertFalse(state.get('contextEnabled', False))

    @unittest.skipUnless(shutil.which('node'),'Node required for visual-order checks')
    def test_color_then_subject_then_visual_neighbors(self):
        project = Path(__file__).parents[1]
        script = '''import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const {normalize,assignVisualRanks,band}=await import(pathToFileURL(process.argv[1]+'/context/similarity.mjs'));
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1]+'/js/Library.js','utf8'),context);
const blue={dominantColor:'#0000ff',colorHue:240,colorValue:.7};
const records=[{...blue,id:'a',path:'a'},{...blue,id:'b',path:'b'},{...blue,id:'c',path:'c'},{...blue,id:'city',path:'city'},
 {...blue,id:'red',path:'red',colorHue:5,dominantColor:'#ff0000'}];
const entries={a:{embedding:normalize([1,0]),group:'Forests'},b:{embedding:normalize([.99,.1]),group:'Forests'},
 c:{embedding:normalize([0,1]),group:'Forests'},city:{embedding:[-1,0],group:'Cities'},red:{embedding:[1,0],group:'Forests'}};
assignVisualRanks(records,entries);
assert.equal(Math.abs(entries.a.rank-entries.b.rank),1);assert.equal(entries.c.rank,2);
assert.equal(entries.city.rank,0);assert.equal(entries.red.rank,0);
const items=records.map(r=>({...r,name:r.id,contextGroup:entries[r.path].group,contextRank:entries[r.path].rank}));
const ordered=context.ordered(items,'color',true).map(i=>i.id);
assert.equal(ordered[0],'red');assert.equal(ordered[1],'city');assert.equal(ordered.at(-1),'c');
for (const item of items) assert.equal(context.colorBand(item),band(item));
assert.equal(context.colorBand({...blue,colorHue:355}),0);
assert.equal(context.ordered(items,'color',false)[0].id,'red');
'''
        subprocess.run(['node','--input-type=module','-e',script,str(project)],check=True)
