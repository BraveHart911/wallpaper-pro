import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import {normalize, dot, band, assignVisualRanks} from './similarity.mjs';

const VERSION = 'clip-context-v3';
const LABEL_VERSION = 'subjects-v2';
const MODEL = 'Xenova/clip-vit-base-patch32';
const [, , dataDir, manifestFile] = process.argv;
const warmup = manifestFile === '--warmup';
const cacheFile = path.join(dataDir, 'context-index.json');
const emit = value => process.stdout.write(JSON.stringify(value) + '\n');
async function save(value) {
    const temporary = cacheFile + '.tmp-' + process.pid;
    await fs.writeFile(temporary, JSON.stringify(value));
    await fs.rename(temporary, cacheFile);
}
const categories = [
 ['Mountains', ['mountain peaks and alpine scenery', 'rocky mountains and valleys', 'snowy mountain landscape']],
 ['Forests', ['a forest of trees and woodland', 'a dense green forest', 'a forest path with trees']],
 ['Oceans & coasts', ['ocean waves and sea water', 'a beach and coastline', 'an underwater ocean scene']],
 ['Lakes & rivers', ['a lake reflecting the landscape', 'a river and waterfall', 'a calm lake surrounded by nature']],
 ['Deserts', ['sand dunes in a desert', 'a rocky desert landscape', 'a desert canyon']],
 ['Countryside', ['a grassy meadow and rolling hills', 'farmland and countryside', 'a field of grass in nature']],
 ['Sky & clouds', ['fluffy clouds across the sky', 'a cloudy sunset sky', 'storm clouds in the sky']],
 ['Space', ["a planet's curved horizon and atmosphere viewed from space", 'outer space with planets and stars', 'galaxies and nebulae in space']],
 ['Cities', ['an outdoor city skyline with buildings and skyscrapers', 'an outdoor urban street with buildings', 'an outdoor futuristic neon city skyline']],
 ['Architecture', ['architecture and buildings', 'a castle or temple', 'a building interior or architectural structure']],
 ['Technology', ['a computer desk with multiple glowing screens and monitors', 'a futuristic computer terminal or control room', 'a circuit board and electronic technology']],
 ['Vehicles', ['a car or motorcycle', 'an aircraft or spaceship', 'a train or vehicle']],
 ['Animals', ['a wild animal or bird', 'a cat or dog', 'wildlife such as a deer or fox']],
 ['Flowers & plants', ['flowers and blossoms', 'a closeup of plant leaves', 'a botanical garden or flowers']],
 ['People', ['a human portrait and face', 'a person or human silhouette', 'people in a photographic scene']],
 ['Illustrated characters', ['an anime character illustration', 'a cartoon character', 'a fantasy character or warrior']],
 ['Abstract', ['abstract geometric shapes', 'an abstract gradient artwork', 'abstract flowing shapes and waves']],
 ['Minimal & typography', ['minimalist graphic design and a logo', 'text typography and symbols', 'a simple minimal graphic wallpaper']],
 ['Patterns & textures', ['a repeating decorative pattern', 'a material texture', 'a textured surface or fabric pattern']],
 ['Food & drink', ['food and fruit', 'a cup of coffee or drink', 'food photography']]
];


let cache;
try { cache = JSON.parse(await fs.readFile(cacheFile, 'utf8')); } catch { cache = {}; }
if (cache.version !== VERSION) cache = {version: VERSION, model: MODEL, items: {}};
const records = warmup ? [] : JSON.parse(await fs.readFile(manifestFile, 'utf8'));
const pending = records.filter(record => JSON.stringify(cache.items[record.path]?.fingerprint) !== JSON.stringify(record.fingerprint));
const relabel = cache.labelVersion !== LABEL_VERSION;
let vision, processor, textVectors;
function classify(embedding) {
 const ranked = categories.map(([label], i) => ({label, similarity: Math.max(...textVectors.slice(i*3, i*3+3).map(text => dot(text, embedding)))})).sort((a,b) => b.similarity-a.similarity);
 return {group:ranked[0].label, similarity:ranked[0].similarity, uncertain:ranked[0].similarity-ranked[1].similarity < .005 || ranked[0].similarity < .23, candidates:ranked.slice(0,3)};
}
if (warmup || pending.length || relabel) {
 const modulePath = path.join(dataDir, 'context-runtime/node_modules/@huggingface/transformers/src/transformers.js');
 const {env, AutoTokenizer, AutoProcessor, CLIPTextModelWithProjection, CLIPVisionModelWithProjection, RawImage} = await import(pathToFileURL(modulePath));
 env.cacheDir = path.join(dataDir, 'context-models');
 env.allowLocalModels = true;
 env.localModelPath = path.join(dataDir, 'context-models');
 env.allowRemoteModels = warmup;
 const options = {dtype: 'q8', device: 'cpu', local_files_only: !warmup,
     session_options: {intraOpNumThreads: 2, interOpNumThreads: 1, logSeverityLevel: 3}};
 emit({event: 'context-progress', done: 0, total: pending.length, message: warmup ? 'Downloading and preparing local visual model…' : 'Loading local visual model…'});
 if (warmup || pending.length) {
  processor = await AutoProcessor.from_pretrained(MODEL, options);
  vision = await CLIPVisionModelWithProjection.from_pretrained(MODEL, options);
 }
 const tokenizer = await AutoTokenizer.from_pretrained(MODEL, options);
 const textModel = await CLIPTextModelWithProjection.from_pretrained(MODEL, options);
 const prompts = categories.flatMap(([, concepts]) => concepts.map(concept => `A wallpaper showing ${concept}.`));
 const encoded = await textModel(await tokenizer(prompts, {padding: true, truncation: true}));
 const textData = Array.from(encoded.text_embeds.data);
 const dimension = encoded.text_embeds.dims[1];
 textVectors = prompts.map((_, i) => normalize(textData.slice(i * dimension, (i + 1) * dimension)));
 await textModel.dispose();
 for (let index = 0; index < pending.length; index++) {
  const record = pending[index];
  try {
   const image = await RawImage.read(record.path);
   // Blend the complete composition with detail crops. Wide panoramas must not
   // be classified solely from the center of the image.
   const scale = 224 / Math.max(image.width, image.height);
   const fitted = await image.resize(Math.max(1, Math.round(image.width*scale)), Math.max(1, Math.round(image.height*scale)));
   const dx = 224-fitted.width, dy = 224-fitted.height;
   const whole = await fitted.pad([Math.floor(dx/2), Math.ceil(dx/2), Math.floor(dy/2), Math.ceil(dy/2)]);
   const views = [whole, image];
   let weights = [.5, .5];
   if (image.width/image.height > 2.3) {
    views.push(await image.crop([0,0,image.height-1,image.height-1]), await image.crop([image.width-image.height,0,image.width-1,image.height-1]));
    weights = [.4,.3,.15,.15];
   } else if (image.height/image.width > 2.3) {
    views.push(await image.crop([0,0,image.width-1,image.width-1]), await image.crop([0,image.height-image.width,image.width-1,image.height-1]));
    weights = [.4,.3,.15,.15];
   }
   const result = await vision(await processor(views));
   const dimension = result.image_embeds.dims[1];
   const features = Array.from(result.image_embeds.data);
   const vectors = views.map((_,i)=>normalize(features.slice(i*dimension,(i+1)*dimension)));
   const embedding = normalize(Array.from({length:dimension},(_,i)=>vectors.reduce((sum,vector,j)=>sum+weights[j]*vector[i],0)));
   cache.items[record.path] = {fingerprint: record.fingerprint, embedding: embedding.map(value => Math.round(value*100000)/100000), ...classify(embedding)};
  } catch (error) { emit({event:'context-error', file:record.path, message:String(error.message)}); }
  if ((index+1)%10 === 0) await save(cache);
  emit({event:'context-progress', done:index+1, total:pending.length});
 }
 if (vision) await vision.dispose();
 if (relabel) {
  for (const entry of Object.values(cache.items)) Object.assign(entry,classify(entry.embedding));
  cache.labelVersion = LABEL_VERSION;
 }
}
if (warmup) {
 await fs.writeFile(path.join(dataDir, 'context-runtime/ready.json'), JSON.stringify({version:VERSION, model:MODEL, node:process.execPath}));
 emit({event:'context-ready'});
 process.exit(0);
}
assignVisualRanks(records, cache.items);
cache.membership = records.map(record => [record.id, record.fingerprint, band(record)]);
await save(cache);
emit({event:'context-complete', analyzed:records.filter(record=>cache.items[record.path]).length, total:records.length});
