#!/usr/bin/env python3
"""Manual Hyprland test using its own temporary fullscreen window; restores settings/focus."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from integration_session import app, status, wait_for


def query(name):
    return json.loads(subprocess.check_output(['hyprctl', name, '-j'], text=True))


def main():
    initial = wait_for(lambda s: True)
    original_focus = query('activewindow').get('address')
    config, _ = app.directories()
    settings = config / 'settings.json'
    original = settings.read_bytes() if settings.exists() else None
    process = None
    try:
        state = app.with_starter_library(app.default())
        video = next(item for item in state['library'] if item['kind'] == 'video')
        state.update(enabled=True, mode='all', default=video['id'], pauseOnBattery=False, pauseOnFullscreen=True)
        app.save(settings, state)
        wait_for(lambda s: len(s['players']) == len(s['monitors']) and all(p['state'] == 1 for p in s['players']))
        with tempfile.TemporaryDirectory(prefix='wallpaper-pro-fullscreen-') as tmp:
            title = 'Wallpaper Pro compatibility ' + Path(tmp).name
            qml = Path(tmp) / 'shell.qml'
            qml.write_text('import QtQuick\nimport Quickshell\nShellRoot { FloatingWindow { visible: true; title: ' + json.dumps(title) + '; implicitWidth: 420; implicitHeight: 240; color: "#101315" } }')
            process = subprocess.Popen(['quickshell', '-p', str(qml)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 8
            window = None
            while time.monotonic() < deadline:
                window = next((w for w in query('clients') if w['title'] == title), None)
                if window:
                    break
                time.sleep(.1)
            if not window:
                raise AssertionError('Temporary test window did not open')
            if query('activewindow').get('address') != window['address']:
                subprocess.run(['hyprctl', 'dispatch', 'focuswindow', 'address:' + window['address']], check=True, stdout=subprocess.DEVNULL)
            if query('activewindow').get('address') != window['address']:
                raise AssertionError('Test window is not focused; refusing to fullscreen another application')
            output = subprocess.check_output(['hyprctl', 'dispatch', 'hl.dsp.window.fullscreen({ mode = "fullscreen", action = "set" })'], text=True)
            if output.strip() != 'ok':
                raise AssertionError(output)
            monitor = next(m['name'] for m in query('monitors') if m['id'] == window['monitor'])
            paused = wait_for(lambda s: any(p['monitor'] == monitor and p['state'] == 2 and p['pauseReason'] == 'fullscreen' for p in s['players']))
            assert all(p['state'] == 1 for p in paused['players'] if p['monitor'] != monitor), paused
            print('PASS: fullscreen pauses only the covered monitor:', monitor, flush=True)
            process.terminate()
            process.wait(timeout=3)
            process = None
            wait_for(lambda s: all(p['state'] == 1 and not p['suspended'] for p in s['players']))
            print('PASS: closing the fullscreen test window resumes playback', flush=True)
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=3)
        if original is None:
            settings.unlink(missing_ok=True)
        else:
            fd, temporary = tempfile.mkstemp(dir=config, prefix='.restore-')
            with os.fdopen(fd, 'wb') as output:
                output.write(original)
            os.replace(temporary, settings)
        if original_focus:
            subprocess.run(['hyprctl', 'dispatch', 'focuswindow', 'address:' + original_focus], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for(lambda s: s['enabled'] == initial['enabled'] and s['mode'] == initial['mode'])
        print('Restored wallpaper settings and previous focus', flush=True)


if __name__ == '__main__':
    main()
