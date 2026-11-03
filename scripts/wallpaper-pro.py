#!/usr/bin/env python3
"""Wallpaper Pro's library and settings. Stdlib only; never evaluates shell input."""
import argparse
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
    except subprocess.TimeoutExpired as error:
        raise ValueError('Media inspection timed out') from error


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
        raise ValueError('Supported: JPG, PNG, WebP, BMP, AVIF, MP4, WebM, MKV, MOV, M4V. Use a direct media link, not a web page.')
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
        validate_media(temporary)
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
    elif args.command == 'battery':
        state['pauseOnBattery'] = args.value == 'on'
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
    unassign = commands.add_parser('unassign')
    unassign.add_argument('monitor')
    battery = commands.add_parser('battery')
    battery.add_argument('value', choices=['on', 'off'])
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
