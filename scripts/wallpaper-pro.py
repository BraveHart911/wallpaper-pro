#!/usr/bin/env python3
"""Wallpaper Pro's library and settings. Stdlib only; never evaluates shell input."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.parse
import urllib.request

IMAGE = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif'}
VIDEO = {'.mp4', '.webm', '.mkv', '.mov', '.m4v'}
MAX_BYTES = 512 * 1024 * 1024


def directories():
    home = Path.home()
    return (Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'wallpaper-pro',
            Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'wallpaper-pro')


def default():
    return {'version': 1, 'enabled': False, 'mode': 'individual', 'default': '',
            'assignments': {}, 'library': [], 'pauseOnBattery': True}


def load(path):
    if not path.exists():
        return default()
    value = json.loads(path.read_text())
    if value.get('version') != 1:
        raise ValueError('Unsupported settings version')
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


def import_media(source, data):
    """Copy media into managed storage; remote sources must be direct media URLs."""
    library = data / 'library'
    library.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(source)
    remote = parsed.scheme in ('https', 'http')
    if parsed.scheme and not remote and parsed.scheme != 'file':
        raise ValueError('Use a local file or a direct HTTP(S) media link')
    source_path = Path(urllib.request.url2pathname(parsed.path)) if parsed.scheme == 'file' else Path(source).expanduser()
    name = Path(urllib.parse.unquote(parsed.path)).name if remote else source_path.name
    suffix = Path(name).suffix.lower()
    if suffix not in IMAGE | VIDEO:
        raise ValueError('Supported: JPG, PNG, WebP, BMP, AVIF, MP4, WebM, MKV, MOV, M4V. Use a direct media link, not a web page.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=library, delete=False) as target:
            temporary = Path(target.name)
            if remote:
                request = urllib.request.Request(source, headers={'User-Agent': 'Wallpaper-Pro/0.1'})
                stream = urllib.request.build_opener(WebRedirects()).open(request, timeout=30)
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
        identity = digest.hexdigest()
        destination = library / (identity + suffix)
        os.replace(temporary, destination)
        return {'id': identity, 'name': name, 'path': str(destination.resolve()),
                'url': destination.resolve().as_uri(), 'kind': 'image' if suffix in IMAGE else 'video',
                'source': source if remote else str(source_path.resolve())}
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def update(state, args, data):
    if args.command == 'import':
        media = import_media(args.source, data)
        if not any(item['id'] == media['id'] for item in state['library']):
            state['library'].append(media)
    elif args.command == 'apply':
        media = next((item for item in state['library'] if item['id'] == args.id), None)
        if media is None:
            raise ValueError('Select an imported wallpaper first')
        if args.mode == 'span' and media['kind'] != 'image':
            raise ValueError('Panoramic spanning currently supports images. Use All monitors for video.')
        state['mode'] = args.mode
        if args.mode == 'individual':
            if not args.monitor:
                raise ValueError('Select a monitor')
            state['assignments'][args.monitor] = args.id
        else:
            state['default'] = args.id
        state['enabled'] = True
    elif args.command == 'off':
        state['enabled'] = False
    elif args.command == 'remove':
        # Forget the entry; never delete original files or currently assigned media.
        if args.id == state['default'] or args.id in state['assignments'].values():
            raise ValueError('This wallpaper is assigned. Assign another wallpaper before removing it.')
        state['library'] = [item for item in state['library'] if item['id'] != args.id]
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('off')
    imp = commands.add_parser('import')
    imp.add_argument('source')
    apply = commands.add_parser('apply')
    apply.add_argument('id')
    apply.add_argument('--mode', choices=['individual', 'all', 'span'], default='individual')
    apply.add_argument('--monitor')
    remove = commands.add_parser('remove')
    remove.add_argument('id')
    args = parser.parse_args()
    config, data = directories()
    config.mkdir(parents=True, exist_ok=True)
    with (config / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = config / 'settings.json'
        state = load(path)
        if args.command != 'status':
            state = update(state, args, data)
        save(path, state)
        print(json.dumps(state))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
