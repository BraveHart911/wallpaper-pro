#!/usr/bin/env python3
"""Wallpaper Pro's library and settings. Stdlib only; never evaluates shell input."""
import argparse
import colorsys
import math
import re
import tomllib
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import time

IMAGE = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif'}
VIDEO = {'.mp4', '.webm', '.mkv', '.mov', '.m4v', '.gif'}
MAX_BYTES = 512 * 1024 * 1024


def directories():
    home = Path.home()
    return (Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'wallpaper-pro',
            Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'wallpaper-pro')


def default():
    return {'version': 1, 'enabled': False, 'mode': 'individual', 'default': '',
            'assignments': {}, 'library': [], 'favorites': [], 'pauseOnBattery': True, 'pauseOnFullscreen': True}


def load(path):
    if not path.exists():
        return default()
    value = json.loads(path.read_text())
    if value.get('version') != 1:
        raise ValueError('Unsupported settings version')
    value.setdefault('favorites', [])
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.settings-')
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class WebRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme not in ('http', 'https'):
            raise ValueError('Redirect must use HTTP or HTTPS')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_media(path):
    if not shutil.which('ffprobe'):
        raise ValueError('Install ffmpeg (ffprobe) to validate wallpaper media')
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height', '-of', 'json', str(path)],
            capture_output=True, text=True, timeout=20, check=False)
        streams = json.loads(result.stdout or '{}').get('streams', [])
        if result.returncode or not streams or streams[0].get('width', 0) <= 0 or streams[0].get('height', 0) <= 0:
            raise ValueError('This file has no readable image or video stream')
        return {key: streams[0][key] for key in ('width', 'height')}
    except subprocess.TimeoutExpired as error:
        raise ValueError('Media inspection timed out') from error


def generate_thumbnail(source, kind, data, identity, force=False):
    """Cache a real image/frame preview, publishing it only after a successful decode."""
    if not shutil.which('ffmpeg'):
        raise ValueError('Install ffmpeg to generate wallpaper previews')
    directory = data / 'thumbnails'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (hashlib.sha256(identity.encode()).hexdigest() + '.jpg')
    if not force and target.is_file() and target.stat().st_size:
        return target.resolve().as_uri()
    fd, name = tempfile.mkstemp(dir=directory, prefix='.preview-', suffix='.jpg')
    os.close(fd)
    temporary = Path(name)
    try:
        # Skip video intros and choose a representative frame from a short sample.
        # Short clips and still images fall back to decoding from the beginning.
        offsets = [1, 0] if kind == 'video' else [0]
        for offset in offsets:
            temporary.unlink(missing_ok=True)
            command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                       '-threads', '1', '-filter_threads', '1', '-protocol_whitelist', 'file,pipe']
            if offset:
                command += ['-ss', str(offset)]
            command += ['-i', str(source), '-map', '0:v:0', '-an', '-sn', '-dn',
                        '-vf', ('thumbnail=60,' if kind == 'video' else '') +
                        'scale=480:270:force_original_aspect_ratio=decrease:force_divisible_by=2',
                        '-frames:v', '1', '-q:v', '3', '-update', '1', str(temporary)]
            try:
                result = subprocess.run(command, capture_output=True, timeout=25, check=False)
            except subprocess.TimeoutExpired:
                continue
            if result.returncode == 0 and temporary.is_file() and temporary.stat().st_size:
                os.replace(temporary, target)
                return target.resolve().as_uri()
        raise ValueError('Could not decode a thumbnail image from this media file')
    finally:
        temporary.unlink(missing_ok=True)


def ensure_thumbnails(state, data, force=False):
    for media in state['library']:
        if media.get('bundled'):
            continue
        current = urllib.parse.urlparse(media.get('thumbnailUrl', ''))
        if not force and current.scheme == 'file' and Path(urllib.request.url2pathname(current.path)).is_file():
            continue
        try:
            media['thumbnailUrl'] = generate_thumbnail(Path(media['path']), media['kind'], data, media['id'], force)
            media.pop('thumbnailError', None)
        except (ValueError, OSError) as error:
            media.pop('thumbnailUrl', None)
            media['thumbnailError'] = str(error)
    return state


COLOR_FIELDS = ('dominantColor', 'colorHue', 'colorValue', 'colorNeutral', 'colorName', 'colorFingerprint')


def dominant_color(source):
    result = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-filter_threads', '1',
                             '-protocol_whitelist', 'file,pipe', '-i', str(source),
                             '-vf', 'scale=32:32', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
                            capture_output=True, timeout=15, check=False)
    if result.returncode or len(result.stdout) != 32 * 32 * 3:
        raise ValueError('Could not analyze thumbnail colors')
    groups = {}
    raw = result.stdout
    for offset in range(0, len(raw), 3):
        rgb = tuple(channel / 255 for channel in raw[offset:offset + 3])
        hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
        neutral = saturation < .12 or value < .10
        group = 24 if neutral else int(hue * 24) % 24
        weight = (.35 if neutral else .35 + .65 * saturation) * math.sqrt(max(.02, value))
        sums = groups.setdefault(group, [0., 0., 0., 0.])
        sums[0] += weight
        for channel in range(3):
            sums[channel + 1] += rgb[channel] * weight
    group, sums = max(groups.items(), key=lambda pair: pair[1][0])
    rgb = [channel / sums[0] for channel in sums[1:]]
    hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
    degrees = hue * 360
    if group == 24:
        name = 'Black' if value < .15 else 'White' if value > .85 else 'Gray'
    else:
        name = next(label for boundary, label in [(15, 'Red'), (45, 'Orange'), (70, 'Yellow'), (165, 'Green'),
                    (195, 'Cyan'), (255, 'Blue'), (285, 'Purple'), (345, 'Pink'), (361, 'Red')] if degrees < boundary)
    return {'dominantColor': '#' + ''.join(f'{round(channel * 255):02x}' for channel in rgb),
            'colorHue': round(degrees, 3), 'colorValue': round(value, 5), 'colorNeutral': group == 24, 'colorName': name}


def thumbnail_path(media):
    url = urllib.parse.urlparse(media.get('thumbnailUrl', ''))
    return Path(urllib.request.url2pathname(url.path)) if url.scheme == 'file' else None


def read_color_cache(data):
    try:
        value = json.loads((data / 'color-index.json').read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def apply_cached_colors(state, cache):
    for media in state['library']:
        path = thumbnail_path(media)
        if path is None:
            continue
        try:
            stat = path.stat()
            fingerprint = [stat.st_size, stat.st_mtime_ns]
        except OSError:
            continue
        entry = cache.get(str(path), {})
        if entry.get('fingerprint') == fingerprint:
            media.update(entry['colors'])
            media['colorFingerprint'] = fingerprint
    return state


def analyze_library_colors(media_list, data, progress=None):
    cache = read_color_cache(data)
    updated = dict(cache)
    for index, media in enumerate(media_list):
        if progress and (index % 10 == 0 or index == len(media_list) - 1):
            progress({'event': 'color-progress', 'done': index + 1, 'total': len(media_list)})
        path = thumbnail_path(media)
        if path is None:
            continue
        try:
            stat = path.stat()
            fingerprint = [stat.st_size, stat.st_mtime_ns]
            old = updated.get(str(path), {})
            if old.get('fingerprint') == fingerprint:
                colors = old['colors']
            elif media.get('colorFingerprint') == fingerprint and media.get('dominantColor'):
                colors = {key: media[key] for key in COLOR_FIELDS if key in media and key != 'colorFingerprint'}
            else:
                colors = dominant_color(path)
            media.update(colors)
            media['colorFingerprint'] = fingerprint
            updated[str(path)] = {'fingerprint': fingerprint, 'colors': colors}
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    if updated != cache:
        save(data / 'color-index.json', updated)
    return updated


def import_media(source, data):
    """Copy media into managed storage; remote sources must be direct media URLs."""
    library = data / 'library'
    library.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(source)
    remote = parsed.scheme in ('https', 'http')
    if parsed.scheme and not remote and parsed.scheme != 'file':
        raise ValueError('Use a local file or a direct HTTP(S) media link')
    if parsed.scheme == 'file' and parsed.netloc not in ('', 'localhost'):
        raise ValueError('File URLs must refer to this computer')
    source_path = Path(urllib.request.url2pathname(parsed.path)) if parsed.scheme == 'file' else Path(source).expanduser()
    name = Path(urllib.parse.unquote(parsed.path)).name if remote else source_path.name
    suffix = Path(name).suffix.lower()
    if suffix not in IMAGE | VIDEO:
        raise ValueError('Supported: JPG, PNG, WebP, BMP, AVIF, MP4, WebM, MKV, MOV, M4V, GIF. Use a direct media link, not a web page.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=library, delete=False) as target:
            temporary = Path(target.name)
            if remote:
                request = urllib.request.Request(source, headers={'User-Agent': 'Wallpaper-Pro/0.1'})
                try:
                    stream = urllib.request.build_opener(WebRedirects()).open(request, timeout=30)
                except urllib.error.HTTPError as error:
                    error.close()
                    raise ValueError('Download failed: HTTP ' + str(error.code)) from error
            else:
                stream = source_path.open('rb')
            digest = hashlib.sha256()
            size = 0
            with stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError('Media exceeds the 512 MiB import limit')
                    digest.update(chunk)
                    target.write(chunk)
            if not size:
                raise ValueError('Media is empty')
        dimensions = validate_media(temporary)
        identity = digest.hexdigest()
        destination = library / (identity + suffix)
        kind = 'image' if suffix in IMAGE else 'video'
        thumbnail_url = generate_thumbnail(temporary, kind, data, identity)
        thumbnail = Path(urllib.request.url2pathname(urllib.parse.urlparse(thumbnail_url).path))
        colors = dominant_color(thumbnail)
        stat = thumbnail.stat()
        colors['colorFingerprint'] = [stat.st_size, stat.st_mtime_ns]
        os.replace(temporary, destination)
        return {'id': identity, 'name': name, 'path': str(destination.resolve()),
                'url': destination.resolve().as_uri(), 'kind': kind, 'thumbnailUrl': thumbnail_url,
                'source': source if remote else str(source_path.resolve()),
                'layout': 'panoramic' if dimensions['width'] / dimensions['height'] >= 2.7 else 'single',
                **dimensions, **colors}
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def refresh_import(existing, media):
    if existing.get('themeManaged'):
        existing.update(media)
        existing.pop('themeManaged', None)
        existing.pop('themeMissing', None)
    else:
        existing['thumbnailUrl'] = media['thumbnailUrl']
    existing.update({key: media[key] for key in COLOR_FIELDS if key in media})
    existing.pop('thumbnailError', None)


def import_folder(state, source, data, progress=None, checkpoint=None):
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme == 'file' and parsed.netloc in ('', 'localhost'):
        folder = Path(urllib.request.url2pathname(parsed.path)).expanduser().resolve()
    elif parsed.scheme:
        raise ValueError('Choose a local folder')
    else:
        folder = Path(source).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError('The selected folder does not exist or is not a directory')
    managed = data.resolve()
    if folder.is_relative_to(managed):
        raise ValueError('Choose your original media folder, not Wallpaper Pro cache storage')
    report = {'folder': str(folder), 'found': 0, 'added': 0, 'duplicates': 0, 'skipped': 0, 'failed': 0, 'errors': []}
    def failure(path, error):
        report['failed'] += 1
        if len(report['errors']) < 100:
            report['errors'].append({'file': str(path), 'error': str(error)})
    candidates = []
    for directory, dirs, files in os.walk(folder, followlinks=False, onerror=lambda e: failure(e.filename, e)):
        dirs[:] = sorted(name for name in dirs if not (Path(directory) / name).is_symlink()
                         and not (Path(directory) / name).resolve().is_relative_to(managed))
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or path.suffix.lower() not in IMAGE | VIDEO:
                report['skipped'] += 1
                continue
            candidates.append(path)
    report['found'] = len(candidates)
    known = {item['id']: item for item in state['library']}
    for index, path in enumerate(candidates):
        if progress:
            progress({'event': 'progress', 'done': index, 'total': len(candidates), 'file': str(path.relative_to(folder))})
        try:
            media = import_media(str(path), data)
            media['sourceFolder'] = str(folder)
            media['relativePath'] = str(path.relative_to(folder))
            if media['id'] in known:
                refresh_import(known[media['id']], media)
                report['duplicates'] += 1
            else:
                state['library'].append(media)
                known[media['id']] = media
                report['added'] += 1
            # Keep completed imports if a later file fails or the process is interrupted.
            state['lastFolderImport'] = report
            if checkpoint:
                checkpoint(state)
        except (ValueError, OSError) as error:
            failure(path.relative_to(folder), error)
    state['lastFolderImport'] = report
    return state


def with_starter_library(state, root=None):
    library_root = (root or Path(__file__).resolve().parents[1]) / 'assets/library'
    catalog_path = library_root / 'catalog.json'
    if not catalog_path.exists():
        return state
    starters = []
    for entry in json.loads(catalog_path.read_text()):
        path = (library_root / entry['file']).resolve()
        thumbnail = (library_root / entry['thumbnail']).resolve()
        if not path.is_file() or not thumbnail.is_file():
            continue
        starters.append({**entry, 'path': str(path), 'url': path.as_uri(),
                         'thumbnailUrl': thumbnail.as_uri(), 'bundled': True,
                         'source': 'Wallpaper Pro original starter collection'})
    state['library'] = starters + [item for item in state['library'] if not item.get('bundled')]
    return state


def update(state, args, data):
    if args.command == 'import':
        media = import_media(args.source, data)
        if not any(item['id'] == media['id'] for item in state['library']):
            state['library'].append(media)
        else:
            existing = next(item for item in state['library'] if item['id'] == media['id'])
            refresh_import(existing, media)
    elif args.command == 'apply':
        media = next((item for item in state['library'] if item['id'] == args.id), None)
        if media is None:
            raise ValueError('Select an imported wallpaper first')
        if not Path(media['path']).is_file():
            raise ValueError('This library file is missing. Import it again before applying.')
        if args.mode == 'individual' and not args.monitor:
            raise ValueError('Select a monitor')
        state['mode'] = args.mode
        if args.mode == 'individual':
            state['assignments'][args.monitor] = args.id
        else:
            state['default'] = args.id
        state['enabled'] = True
    elif args.command == 'unassign':
        state['assignments'].pop(args.monitor, None)
    elif args.command == 'fullscreen':
        state['pauseOnFullscreen'] = args.value == 'on'
    elif args.command == 'battery':
        state['pauseOnBattery'] = args.value == 'on'
    elif args.command == 'context':
        if args.value == 'on' and not context_node(data):
            raise ValueError('Enable smart grouping in Settings to install the local image model first')
        state['contextEnabled'] = args.value == 'on'
    elif args.command == 'sort':
        state['sortOrder'] = args.order
    elif args.command == 'favorite':
        if not any(item['id'] == args.id for item in state['library']):
            raise ValueError('Wallpaper not found in the library')
        favorites = state.setdefault('favorites', [])
        if args.value == 'on' and args.id not in favorites:
            favorites.append(args.id)
        elif args.value == 'off' and args.id in favorites:
            favorites.remove(args.id)
    elif args.command == 'off':
        state['enabled'] = False
    elif args.command == 'remove':
        if any(item['id'] == args.id and item.get('themeManaged') for item in state['library']):
            raise ValueError('Theme wallpapers are managed by Omarchy. Remove their theme to remove them from this collection.')
        if any(item['id'] == args.id and item.get('bundled') for item in state['library']):
            raise ValueError('Starter wallpapers stay in the collection. Filter to My imports for your own media.')
        # Forget the entry; never delete original files or currently assigned media.
        if args.id == state['default'] or args.id in state['assignments'].values():
            raise ValueError('This wallpaper is assigned. Assign another wallpaper before removing it.')
        state['library'] = [item for item in state['library'] if item['id'] != args.id]
        state['favorites'] = [item for item in state.get('favorites', []) if item != args.id]
    return state


def theme_roots():
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return [(Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'themes', True),
            (config / 'omarchy/themes', True), (config / 'omarchy/backgrounds', False)]


def discover_theme_library(data, roots=None, cache=None, progress=None, checkpoint=None):
    previous = cache or {}
    candidates = {}
    errors = []
    for base, nested_backgrounds in (theme_roots() if roots is None else roots):
        if not base.is_dir():
            continue
        try:
            themes = sorted(base.iterdir())
        except OSError as error:
            errors.append(str(error))
            continue
        for theme in themes:
            background = theme / 'backgrounds' if nested_backgrounds else theme
            if not background.is_dir():
                continue
            visited = set()
            for directory, dirs, files in os.walk(background, followlinks=True, onerror=lambda e: errors.append(str(e))):
                canonical = Path(directory).resolve()
                if canonical in visited:
                    dirs[:] = []
                    continue
                visited.add(canonical)
                dirs.sort()
                for name in sorted(files):
                    path = Path(directory) / name
                    if path.suffix.lower() in IMAGE | VIDEO and path.is_file():
                        candidates.setdefault(str(path.resolve()), set()).add(theme.name.replace('-', ' ').replace('_', ' ').title())
    discovered, refreshed = {}, {}
    dirty = False
    for index, (filename, themes) in enumerate(sorted(candidates.items())):
        if progress:
            progress({'event': 'theme-progress', 'done': index + 1, 'total': len(candidates)})
        path = Path(filename)
        fingerprint = None
        try:
            stat = path.stat()
            fingerprint = [stat.st_size, stat.st_mtime_ns]
            old = previous.get(filename, {})
            if old.get('fingerprint') == fingerprint and old.get('error'):
                refreshed[filename] = old
                errors.append(filename + ': ' + old['error'])
                continue
            if old.get('fingerprint') == fingerprint and old.get('media'):
                media = dict(old['media'])
                media['thumbnailUrl'] = generate_thumbnail(path, media['kind'], data, media['id'])
            else:
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                identity = digest.hexdigest()
                dimensions = validate_media(path)
                kind = 'video' if path.suffix.lower() in VIDEO else 'image'
                media = {'id': identity, 'name': path.name, 'path': filename, 'url': path.as_uri(),
                         'kind': kind, 'layout': 'panoramic' if dimensions['width'] / dimensions['height'] >= 2.7 else 'single',
                         'thumbnailUrl': generate_thumbnail(path, kind, data, identity), 'source': filename, **dimensions}
            refreshed[filename] = {'fingerprint': fingerprint, 'media': media}
            if media['id'] not in discovered:
                discovered[media['id']] = {**media, 'themeManaged': True, 'themes': []}
            entry = discovered[media['id']]
            entry['themes'] = sorted(set(entry['themes']) | themes)
        except (ValueError, OSError) as error:
            errors.append(filename + ': ' + str(error))
            if fingerprint is not None:
                refreshed[filename] = {'fingerprint': fingerprint, 'error': str(error)}
        dirty = dirty or refreshed.get(filename) != previous.get(filename)
        if checkpoint and dirty and (index + 1) % 25 == 0:
            checkpoint({**previous, **refreshed})
            dirty = False
    return {'library': list(discovered.values()), 'cache': refreshed,
            'report': {'files': len(candidates), 'wallpapers': len(discovered), 'failed': len(errors), 'errors': errors[:10]}}


def merge_theme_library(state, discovery):
    # Merge into the latest settings so background discovery cannot overwrite user actions.
    personal = [item for item in state['library'] if not item.get('themeManaged')]
    by_id = {item['id']: item for item in personal}
    for item in personal:
        item.pop('themes', None)
    managed = []
    for media in discovery['library']:
        if media['id'] in by_id:
            by_id[media['id']]['themes'] = media['themes']
        else:
            managed.append(media)
    discovered_ids = {item['id'] for item in discovery['library']}
    assigned = set(state['assignments'].values()) | {state['default']}
    for old in state['library']:
        if old.get('themeManaged') and old['id'] not in discovered_ids and old['id'] in assigned:
            managed.append({**old, 'themeMissing': not Path(old['path']).is_file()})
    state['library'] = personal + managed
    state['themeSyncReport'] = discovery['report']
    return state


def sync_themes(config, data, progress=None):
    data.mkdir(parents=True, exist_ok=True)
    with (config / '.theme-sync.lock').open('w') as scan_lock:
        try:
            fcntl.flock(scan_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return with_starter_library(load(config / 'settings.json'))
        cache_path = data / 'theme-index.json'
        try:
            cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        except (ValueError, OSError):
            cache = {}
        if not isinstance(cache, dict):
            cache = {}
        # Only metadata scanning and thumbnail generation happen here, outside the settings lock.
        discovery = discover_theme_library(data, cache=cache, progress=progress, checkpoint=lambda value: save(cache_path, value))
        if discovery['cache'] != cache:
            save(cache_path, discovery['cache'])
        snapshot = with_starter_library(load(config / 'settings.json'))
        samples = {media['thumbnailUrl']: media for media in discovery['library'] + snapshot['library'] if media.get('thumbnailUrl')}
        color_cache = analyze_library_colors(list(samples.values()), data, progress)
        context_cache = read_context_cache(data)
        context_error = ''
        if snapshot.get('contextEnabled'):
            try:
                context_cache = analyze_library_context(list(samples.values()), config, data, progress)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                context_error = str(error)
        with (config / '.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            path = config / 'settings.json'
            state = apply_cached_colors(merge_theme_library(with_starter_library(load(path)), discovery), color_cache)
            state = apply_cached_context(state, context_cache, data)
            state['contextError'] = context_error
            if not path.exists() or json.loads(path.read_text()) != state:
                save(path, state)
            return state


CONTEXT_VERSION = 'clip-context-v3'
CONTEXT_LABEL_VERSION = 'subjects-v2'
CONTEXT_MODEL = 'Xenova/clip-vit-base-patch32'


def context_node(data):
    try:
        ready = json.loads((data / 'context-runtime/ready.json').read_text())
        node = next((candidate for candidate in (ready.get('node'), shutil.which('node')) if candidate and os.access(candidate, os.X_OK)), None)
        if ready.get('model') == CONTEXT_MODEL and node:
            module = data / 'context-runtime/node_modules/@huggingface/transformers/src/transformers.js'
            if module.is_file():
                return node
    except (OSError, ValueError):
        pass
    return None


def read_context_cache(data):
    try:
        cache = json.loads((data / 'context-index.json').read_text())
        return cache if cache.get('version') == CONTEXT_VERSION else {}
    except (OSError, ValueError, AttributeError):
        return {}


def context_band(media):
    if not media.get('dominantColor'):
        return 15
    if media.get('colorNeutral'):
        return 12 + (0 if media.get('colorValue', 0) < .22 else 2 if media.get('colorValue', 0) > .78 else 1)
    return int(((media.get('colorHue', 0) + 15) % 360) // 30)


def context_records(media_list):
    records = {}
    for media in media_list:
        path = thumbnail_path(media)
        if path is None:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        records[str(path)] = {key: media[key] for key in ('id', 'dominantColor', 'colorHue', 'colorValue', 'colorNeutral') if key in media}
        records[str(path)].update(path=str(path), fingerprint=[stat.st_size, str(stat.st_mtime_ns)])
    return sorted(records.values(), key=lambda record: record['path'])


def apply_cached_context(state, cache, data):
    state['contextAvailable'] = bool(context_node(data))
    entries = cache.get('items', {})
    for media in state['library']:
        path = thumbnail_path(media)
        entry = entries.get(str(path), {}) if path else {}
        try:
            stat = path.stat() if path else None
            valid = stat and entry.get('group') and entry.get('fingerprint') == [stat.st_size, str(stat.st_mtime_ns)]
        except OSError:
            valid = False
        if valid:
            media.update(contextGroup=entry['group'], contextRank=entry.get('rank', 0),
                         contextSimilarity=round(entry.get('similarity', 0), 4), contextUncertain=entry.get('uncertain', True))
        else:
            for key in ('contextGroup', 'contextRank', 'contextSimilarity', 'contextUncertain'):
                media.pop(key, None)
    state['contextReport'] = {'analyzed': sum(bool(media.get('contextGroup')) for media in state['library']),
                              'total': len(state['library']), 'model': CONTEXT_MODEL}
    return state


def run_context_process(command, progress=None):
    with tempfile.TemporaryFile(mode='w+') as errors:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True) as process:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                    if progress:
                        progress(event)
                except ValueError:
                    pass
            code = process.wait()
        if code:
            errors.seek(0)
            detail = errors.read()[-1600:].strip()
            raise ValueError('Local image analysis failed: ' + (detail or str(code)))


def analyze_library_context(media_list, config, data, progress=None):
    cache = read_context_cache(data)
    node = context_node(data)
    if not node:
        return cache
    records = context_records(media_list)
    membership = [[record['id'], record['fingerprint'], context_band(record)] for record in records]
    if cache.get('labelVersion') == CONTEXT_LABEL_VERSION and cache.get('membership') == membership and all(cache.get('items', {}).get(record['path'], {}).get('fingerprint') == record['fingerprint'] for record in records):
        return cache
    with (config / '.context-sync.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return read_context_cache(data)
        fd, temporary = tempfile.mkstemp(dir=data, prefix='.context-input-', suffix='.json')
        try:
            with os.fdopen(fd, 'w') as output:
                json.dump(records, output)
            worker = Path(__file__).resolve().parents[1] / 'context/analyze.mjs'
            run_context_process([node, str(worker), str(data), temporary], progress)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return read_context_cache(data)


def install_context(data, progress=None):
    existing_node = context_node(data)
    if existing_node:
        worker = Path(__file__).resolve().parents[1] / 'context/analyze.mjs'
        run_context_process([existing_node, str(worker), str(data), '--warmup'], progress)
        return
    node, npm = shutil.which('node'), shutil.which('npm')
    if not node or not npm:
        raise ValueError('Install Node.js and npm, then enable smart grouping again')
    source = Path(__file__).resolve().parents[1] / 'context'
    runtime = data / 'context-runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(source / name, runtime / name)
    if progress:
        progress({'event': 'setup-progress', 'message': 'Installing isolated local image analysis tools…'})
    result = subprocess.run([npm, 'ci', '--prefix', str(runtime), '--ignore-scripts', '--no-audit', '--no-fund'],
                            capture_output=True, text=True, timeout=600, check=False)
    if result.returncode:
        raise ValueError('Context runtime installation failed: ' + result.stderr[-1000:])
    run_context_process([node, str(source / 'analyze.mjs'), str(data), '--warmup'], progress)


def competing_wallpapers(layers, monitors):
    warnings = []
    monitor_map = {monitor['name']: monitor for monitor in monitors}
    for name, output in layers.items():
        monitor = monitor_map.get(name, {})
        scale = monitor.get('scale', 1) or 1
        width, height = monitor.get('width', 0) / scale, monitor.get('height', 0) / scale
        if monitor.get('transform', 0) % 2:
            width, height = height, width
        for level in ('0', '1'):
            for surface in output.get('levels', {}).get(level, []):
                namespace = surface.get('namespace', '')
                if namespace in ('wallpaper-pro', 'omarchy-background'):
                    continue
                if width and height and surface.get('w', 0) >= width * .8 and surface.get('h', 0) >= height * .8:
                    warnings.append(name + ': another desktop surface (' + (namespace or 'unnamed') + ') may compete with Wallpaper Pro. Use one live wallpaper renderer per screen.')
    return warnings


def desktop_diagnostics():
    result = {'hyprland': False, 'omarchy': bool(shutil.which('omarchy')), 'warnings': []}
    if not shutil.which('hyprctl'):
        result['warnings'].append('Hyprland is not available in this session.')
        return result
    try:
        def query(name):
            output = subprocess.run(['hyprctl', name, '-j'], capture_output=True, text=True, timeout=3, check=True)
            return json.loads(output.stdout)
        monitors, layers = query('monitors'), query('layers')
        result['hyprland'] = True
        result['warnings'] = competing_wallpapers(layers, monitors)
    except (subprocess.SubprocessError, ValueError, OSError):
        result['warnings'].append('Could not inspect the Hyprland session. No desktop settings were changed.')
    return result


def theme_catalog():
    """Read installed Omarchy theme accent colors for Wallpaper Pro's color picker."""
    if not shutil.which('omarchy'):
        raise ValueError('Omarchy is not available')
    names = subprocess.run(['omarchy', 'theme', 'list'], capture_output=True, text=True, timeout=10, check=True).stdout.splitlines()
    current = subprocess.run(['omarchy', 'theme', 'current'], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    home = Path.home()
    roots = [Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'omarchy/themes',
             Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'themes']
    colors = []
    for name in names:
        theme = name.strip()
        if not theme:
            continue
        slug = re.sub(r'[^a-z0-9]+', '-', theme.lower()).strip('-')
        config = {}
        for root in roots:
            path = root / slug / 'colors.toml'
            if path.is_file():
                try:
                    config = tomllib.loads(path.read_text())
                except (OSError, tomllib.TOMLDecodeError):
                    config = {}
                break
        accent = config.get('accent') or config.get('blue') or config.get('foreground') or '#777777'
        match = re.fullmatch(r'#?([0-9a-fA-F]{6})', str(accent))
        if match:
            raw = match.group(1)
            rgb = tuple(int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4))
            hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
            group = ('Red', 'Orange', 'Yellow', 'Lime', 'Green', 'Teal', 'Cyan', 'Azure', 'Blue', 'Indigo', 'Violet', 'Purple', 'Magenta', 'Rose', 'Red')[int((hue * 360 + 12) // 24) % 15] if saturation >= .13 else 'Neutral'
        else:
            accent, hue, saturation, value, group = '#777777', 0, 0, .47, 'Neutral'
        mode = str(config.get('mode', '')).strip().lower()
        if mode not in ('light', 'dark'):
            background = re.fullmatch(r'#?([0-9a-fA-F]{6})', str(config.get('background', '')))
            if background:
                raw_bg = background.group(1)
                channels = [int(raw_bg[i:i + 2], 16) / 255 for i in (0, 2, 4)]
                luminance = sum(channel * weight for channel, weight in zip(channels, (.2126, .7152, .0722)))
                mode = 'light' if luminance >= .5 else 'dark'
            else:
                mode = 'unknown'
        colors.append({'name': theme, 'accent': accent if match else '#777777', 'group': group, 'mode': mode,
                       'hue': hue * 360 if saturation >= .13 else 999,
                       'saturation': saturation, 'value': value, 'current': theme == current})
    colors.sort(key=lambda item: (item['hue'], item['value'], item['name'].casefold()))
    print(json.dumps({'current': current, 'themes': colors}))


def monitor_catalog():
    if not shutil.which('hyprctl'):
        raise ValueError('Hyprland is not available')
    result = subprocess.run(['hyprctl', 'monitors', '-j'], capture_output=True, text=True, timeout=8, check=True)
    monitors = json.loads(result.stdout)
    displays = {}
    if shutil.which('ddcutil'):
        detected = subprocess.run(['ddcutil', 'detect', '--brief'], capture_output=True, text=True, timeout=12, check=False).stdout
        pattern = re.compile(r'Display\s+(\d+)\s+I2C bus:\s+[^\n]*i2c-(\d+)\s+DRM connector:\s+card\d+-(\S+)', re.S)
        for match in pattern.finditer(detected):
            displays[match.group(3)] = match.group(1)
    for monitor in monitors:
        mode_values = []
        seen = set()
        for item in monitor.get('availableModes', []):
            match = re.fullmatch(r'(\d+x\d+)@([\d.]+)Hz', item.strip())
            if not match:
                continue
            value = match.group(1) + '@' + str(round(float(match.group(2)), 2))
            if value in seen:
                continue
            seen.add(value)
            mode_values.append({'value': value, 'label': match.group(1).replace('x', ' × ') + ' · ' + str(round(float(match.group(2)), 2)).rstrip('0').rstrip('.') + ' Hz'})
        current = str(monitor.get('width', 0)) + 'x' + str(monitor.get('height', 0)) + '@' + str(round(monitor.get('refreshRate', 0), 2))
        mode_values.sort(key=lambda item: (item['value'] != current, -int(item['value'].split('x', 1)[0]), -float(item['value'].split('@', 1)[1])))
        monitor['modes'] = mode_values
        monitor['mode'] = current
        display = displays.get(monitor.get('name'))
        if display:
            brightness = subprocess.run(['ddcutil', 'getvcp', '10', '--display', display, '--brief'], capture_output=True, text=True, timeout=8, check=False)
            match = re.search(r'VCP\s+10\s+\S+\s+(\d+)\s+(\d+)', brightness.stdout)
            if match:
                monitor['brightness'] = {'available': True, 'value': int(match.group(1)), 'maximum': int(match.group(2)), 'display': display}
                continue
        monitor['brightness'] = {'available': False}
    print(json.dumps({'monitors': monitors}))


def monitor_set(args):
    if not shutil.which('hyprctl'):
        raise ValueError('Hyprland is not available')
    queried = subprocess.run(['hyprctl', 'monitors', '-j'], capture_output=True, text=True, timeout=8, check=True)
    monitors = json.loads(queried.stdout)
    target = next((item for item in monitors if item.get('name') == args.name), None)
    if target is None:
        raise ValueError('Monitor is not connected: ' + args.name)
    mode_match = re.fullmatch(r'(\d+x\d+)@([\d.]+)', args.mode)
    supported = next((item['modes'] for item in monitor_catalog_data([target]) if item['name'] == args.name), [])
    if not mode_match or args.mode not in {item['value'] for item in supported}:
        raise ValueError('Choose a mode supported by this monitor')
    if not (-20000 <= args.x <= 20000 and -20000 <= args.y <= 20000 and 0.5 <= args.scale <= 3.0):
        raise ValueError('Position or scale is outside the supported range')
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'hypr/monitors.lua'
    if not config.is_file():
        raise ValueError('Could not find ~/.config/hypr/monitors.lua')
    display = None
    if args.brightness is not None:
        detected = subprocess.run(['ddcutil', 'detect', '--brief'], capture_output=True, text=True, timeout=12, check=False).stdout if shutil.which('ddcutil') else ''
        for match in re.finditer(r'Display\s+(\d+)\s+I2C bus:\s+[^\n]*i2c-\d+\s+DRM connector:\s+card\d+-(\S+)', detected, re.S):
            if match.group(2) == args.name:
                display = match.group(1)
                break
        if not display:
            raise ValueError('Hardware brightness control is not available for ' + args.name)
    original = config.read_text()
    call = re.compile(r'hl\.monitor\(\s*\{([^{}]*)\}\s*\)', re.S)
    found = False
    def update_monitor(match):
        nonlocal found
        body = match.group(1)
        output = re.search(r'output\s*=\s*["\']([^"\']*)["\']', body)
        if not output or output.group(1) != args.name:
            return match.group(0)
        found = True
        fields = {'mode': '"' + args.mode + '"', 'position': '"' + str(args.x) + 'x' + str(args.y) + '"', 'scale': str(args.scale)}
        for field, value in fields.items():
            field_pattern = re.compile(r'\b' + field + r'\s*=\s*(?:"[^"]*"|\'[^\']*\'|[\d.]+|[A-Za-z_][\w.]*)')
            if field_pattern.search(body):
                body = field_pattern.sub(field + ' = ' + value, body, count=1)
            else:
                body = body.rstrip() + ', ' + field + ' = ' + value
        return 'hl.monitor({ ' + body.strip() + ' })'
    updated = call.sub(update_monitor, original)
    if not found:
        updated = updated.rstrip() + '\n\nhl.monitor({ output = "' + args.name + '", mode = "' + args.mode + '", position = "' + str(args.x) + 'x' + str(args.y) + '", scale = ' + str(args.scale) + ' })\n'
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = config.with_name(config.name + '.bak-wallpaper-pro-' + stamp)
    shutil.copy2(config, backup)
    config.write_text(updated)
    reload_result = subprocess.run(['hyprctl', 'reload'], capture_output=True, text=True, timeout=12, check=False)
    errors = subprocess.run(['hyprctl', 'configerrors'], capture_output=True, text=True, timeout=8, check=False)
    if reload_result.returncode or errors.returncode or errors.stdout.strip():
        shutil.copy2(backup, config)
        subprocess.run(['hyprctl', 'reload'], capture_output=True, text=True, timeout=12, check=False)
        raise ValueError('Hyprland rejected the monitor layout. The previous configuration was restored.')
    if args.brightness is not None:
        current_brightness = subprocess.run(['ddcutil', 'getvcp', '10', '--display', display, '--brief'], capture_output=True, text=True, timeout=8, check=False)
        brightness_match = re.search(r'VCP\s+10\s+\S+\s+(\d+)\s+(\d+)', current_brightness.stdout)
        if not brightness_match:
            shutil.copy2(backup, config)
            subprocess.run(['hyprctl', 'reload'], capture_output=True, text=True, timeout=12, check=False)
            raise ValueError('Could not read hardware brightness; the previous layout was restored.')
        maximum = int(brightness_match.group(2))
        value = round(maximum * max(0, min(100, args.brightness)) / 100)
        result = subprocess.run(['ddcutil', 'setvcp', '10', str(value), '--display', display], capture_output=True, text=True, timeout=12, check=False)
        if result.returncode:
            shutil.copy2(backup, config)
            subprocess.run(['hyprctl', 'reload'], capture_output=True, text=True, timeout=12, check=False)
            raise ValueError('Monitor layout was saved, but brightness could not be changed; the previous layout was restored: ' + result.stderr.strip()[-300:])
    print(json.dumps({'ok': True, 'backup': str(backup)}))


def monitor_brightness(args):
    if not shutil.which('hyprctl'):
        raise ValueError('Hyprland is not available')
    if not shutil.which('ddcutil'):
        raise ValueError('Install ddcutil to control this monitor’s hardware brightness')
    if not 0 <= args.value <= 100:
        raise ValueError('Brightness must be between 0 and 100')
    connected = subprocess.run(['hyprctl', 'monitors', '-j'], capture_output=True, text=True, timeout=8, check=True)
    if not any(item.get('name') == args.name for item in json.loads(connected.stdout)):
        raise ValueError('Monitor is not connected: ' + args.name)
    detected = subprocess.run(['ddcutil', 'detect', '--brief'], capture_output=True, text=True, timeout=12, check=False).stdout
    display = None
    for match in re.finditer(r'Display\s+(\d+)\s+I2C bus:\s+[^\n]*i2c-\d+\s+DRM connector:\s+card\d+-(\S+)', detected, re.S):
        if match.group(2) == args.name:
            display = match.group(1)
            break
    if not display:
        raise ValueError('Hardware brightness control is not available for ' + args.name)
    current = subprocess.run(['ddcutil', 'getvcp', '10', '--display', display, '--brief'], capture_output=True, text=True, timeout=8, check=False)
    values = re.search(r'VCP\s+10\s+\S+\s+(\d+)\s+(\d+)', current.stdout)
    if not values:
        raise ValueError('Could not read brightness from ' + args.name + ': ' + (current.stderr.strip() or current.stdout.strip())[-250:])
    maximum = int(values.group(2))
    value = round(maximum * args.value / 100)
    result = subprocess.run(['ddcutil', 'setvcp', '10', str(value), '--display', display, '--verify'], capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError('Could not set brightness on ' + args.name + ': ' + (result.stderr.strip() or result.stdout.strip())[-300:])
    confirmed = subprocess.run(['ddcutil', 'getvcp', '10', '--display', display, '--brief'], capture_output=True, text=True, timeout=8, check=False)
    actual = re.search(r'VCP\s+10\s+\S+\s+(\d+)\s+(\d+)', confirmed.stdout)
    if not actual:
        raise ValueError('Brightness was sent to ' + args.name + ', but the monitor did not report its new level')
    print(json.dumps({'ok': True, 'name': args.name, 'value': int(actual.group(1)), 'maximum': int(actual.group(2))}))


def monitor_catalog_data(monitors):
    output = []
    for monitor in monitors:
        modes = []
        seen = set()
        for item in monitor.get('availableModes', []):
            match = re.fullmatch(r'(\d+x\d+)@([\d.]+)Hz', item.strip())
            if match:
                value = match.group(1) + '@' + str(round(float(match.group(2)), 2))
                if value not in seen:
                    seen.add(value)
                    modes.append({'value': value, 'label': match.group(1) + ' @ ' + str(round(float(match.group(2)), 2)) + ' Hz'})
        output.append({'name': monitor['name'], 'modes': modes})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('install-context', help='Download and enable isolated local image analysis')
    context = commands.add_parser('context')
    context.add_argument('value', choices=['on', 'off'])
    sorting = commands.add_parser('sort')
    sorting.add_argument('order', choices=['original', 'name', 'color'])
    favorite = commands.add_parser('favorite')
    favorite.add_argument('id')
    favorite.add_argument('value', choices=['on', 'off'])
    themes = commands.add_parser('sync-themes', help='Discover wallpapers in installed Omarchy themes')
    themes.add_argument('--progress', action='store_true')
    thumbnails = commands.add_parser('thumbnails')
    thumbnails.add_argument('--force', action='store_true', help='Rebuild existing cached previews')
    commands.add_parser('doctor')
    commands.add_parser('theme-catalog', help='List installed themes with accent colors')
    commands.add_parser('monitor-catalog', help='List connected monitor details and controls')
    monitor = commands.add_parser('monitor-set', help='Save monitor layout and optional brightness')
    monitor.add_argument('name')
    monitor.add_argument('--mode', required=True)
    monitor.add_argument('--x', required=True, type=int)
    monitor.add_argument('--y', required=True, type=int)
    monitor.add_argument('--scale', required=True, type=float)
    monitor.add_argument('--brightness', type=int)
    brightness = commands.add_parser('monitor-brightness', help='Adjust display brightness without changing monitor layout')
    brightness.add_argument('name')
    brightness.add_argument('value', type=int)
    commands.add_parser('off')
    unassign = commands.add_parser('unassign')
    unassign.add_argument('monitor')
    fullscreen = commands.add_parser('fullscreen')
    fullscreen.add_argument('value', choices=['on', 'off'])
    battery = commands.add_parser('battery')
    battery.add_argument('value', choices=['on', 'off'])
    imp = commands.add_parser('import')
    imp.add_argument('source')
    folder = commands.add_parser('import-folder', help='Import a local folder and all media subfolders')
    folder.add_argument('source')
    folder.add_argument('--progress', action='store_true', help='Emit JSON progress events for the graphical manager')
    apply = commands.add_parser('apply')
    apply.add_argument('id')
    apply.add_argument('--mode', choices=['individual', 'all', 'span'], default='individual')
    apply.add_argument('--monitor')
    remove = commands.add_parser('remove')
    remove.add_argument('id')
    args = parser.parse_args()
    if args.command == 'theme-catalog':
        theme_catalog()
        return
    if args.command == 'monitor-catalog':
        monitor_catalog()
        return
    if args.command == 'monitor-set':
        monitor_set(args)
        return
    if args.command == 'monitor-brightness':
        monitor_brightness(args)
        return
    if args.command == 'doctor':
        print(json.dumps(desktop_diagnostics()))
        return
    config, data = directories()
    config.mkdir(parents=True, exist_ok=True)
    if args.command == 'sync-themes':
        os.nice(10)
        progress = (lambda event: print(json.dumps(event), flush=True)) if args.progress else None
        print(json.dumps(sync_themes(config, data, progress)))
        return
    if args.command == 'install-context':
        install_context(data, lambda event: print(json.dumps(event), flush=True))
    with (config / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = config / 'settings.json'
        state = apply_cached_context(apply_cached_colors(with_starter_library(load(path)), read_color_cache(data)), read_context_cache(data), data)
        if args.command in ('status', 'thumbnails'):
            state = ensure_thumbnails(state, data, getattr(args, 'force', False))
        if args.command == 'install-context':
            state['contextEnabled'] = True
        elif args.command == 'import-folder':
            progress = (lambda event: print(json.dumps(event), flush=True)) if args.progress else None
            state = import_folder(state, args.source, data, progress, lambda current: save(path, current))
        elif args.command not in ('status', 'thumbnails'):
            state = update(state, args, data)
        save(path, state)
        print(json.dumps(state))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
