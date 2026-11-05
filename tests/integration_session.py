#!/usr/bin/env python3
"""Manual graphical-session check. Temporarily switches wallpapers, then restores settings."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from test_library import app


@contextmanager
def settings_lock(config):
    config.mkdir(parents=True, exist_ok=True)
    with (config / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def save_test_settings(settings, state):
    with settings_lock(settings.parent):
        app.save(settings, state)


def restore_settings(settings, original):
    with settings_lock(settings.parent):
        if original is None:
            settings.unlink(missing_ok=True)
        else:
            fd, temporary = tempfile.mkstemp(dir=settings.parent, prefix='.restore-')
            with os.fdopen(fd, 'wb') as output:
                output.write(original)
            os.replace(temporary, settings)


def status():
    result = subprocess.run(['omarchy-shell', 'wallpaper-pro', 'status'], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def wait_for(predicate):
    current = None
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            current = status()
        except subprocess.CalledProcessError:
            time.sleep(.2)
            continue
        if predicate(current):
            return current
        time.sleep(.2)
    raise AssertionError('Renderer did not reach expected state: ' + json.dumps(current))


def main():
    initial = wait_for(lambda s: True)
    monitors = initial['monitors']
    if len(monitors) < 2:
        raise RuntimeError('This integration check needs at least two monitors')
    config, _ = app.directories()
    config.mkdir(parents=True, exist_ok=True)
    settings = config / 'settings.json'
    original = settings.read_bytes() if settings.exists() else None
    try:
        with tempfile.TemporaryDirectory(prefix='wallpaper-pro-integration-') as tmp:
            base = Path(tmp)
            video = base / 'test.mp4'
            image = base / 'test.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc2=size=1920x540:rate=24', '-t', '5', '-c:v', 'libx264',
                            '-preset', 'ultrafast', str(video)], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-frames:v', '1', str(image)], check=True)
            state = app.default()
            state.update(enabled=True, pauseOnBattery=False, pauseOnFullscreen=False,
                         library=[{'id': 'image', 'kind': 'image', 'path': str(image), 'url': image.as_uri()},
                                  {'id': 'video', 'kind': 'video', 'path': str(video), 'url': video.as_uri()}],
                         assignments={monitors[0]: 'image', monitors[1]: 'video'})
            save_test_settings(settings, state)
            independent = wait_for(lambda s: s['enabled'] and s['mode'] == 'individual'
                                   and len(s['players']) == 1 and s['players'][0]['monitor'] == monitors[1] and s['players'][0]['position'] > 300)
            assert independent['players'][0]['state'] == 1, independent
            assert all(not p['error'] for p in independent['players']), independent
            print('PASS: independent image/video assignments on', ', '.join(monitors[:2]))
            for mode in ['all', 'span']:
                state.update(mode=mode, default='video')
                save_test_settings(settings, state)
                playing = wait_for(lambda s: s['mode'] == mode and len(s['players']) == len(monitors) and all(p['position'] > 500 and p['state'] == 1 for p in s['players']))
                assert all(not p['error'] for p in playing['players']), playing
                print('PASS:', mode, 'video playback:', json.dumps(playing))
            time.sleep(5.5)
            looped = status()
            assert all(p['state'] == 1 and not p['error'] for p in looped['players']), looped
            positions = [p['position'] for p in looped['players']]
            assert max(positions) - min(positions) < 350, looped
            print('PASS: video continues beyond one loop with monitor drift under 350 ms')
            state.update(enabled=False)
            save_test_settings(settings, state)
            wait_for(lambda s: not s['enabled'] and not s['players'])
            print('PASS: turning off stops video players')
    finally:
        restore_settings(settings, original)
        wait_for(lambda s: s['enabled'] == initial['enabled'] and s['mode'] == initial['mode'])
        print('Restored original Wallpaper Pro settings')


if __name__ == '__main__':
    main()
