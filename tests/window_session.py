#!/usr/bin/env python3
"""Manual installed-plugin test for native tiling and compositor close/reopen."""
import json
import subprocess
import time
from integration_session import status, wait_for

ID = 'bravehart911.wallpaper-pro'


def clients():
    return json.loads(subprocess.check_output(['hyprctl', 'clients', '-j'], text=True))


def window():
    return next((item for item in clients() if item['title'] == 'Wallpaper Pro'), None)


def wait_window(present):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        current = window()
        if bool(current) == present:
            return current
        time.sleep(.1)
    raise AssertionError('Native window visibility did not match expected state')


def main():
    before = wait_for(lambda s: True)
    subprocess.run(['omarchy-shell', 'shell', 'summon', ID, '{}'], check=True, stdout=subprocess.DEVNULL)
    current = wait_window(True)
    assert not current['floating'], current
    assert current['mapped'] and not current['hidden'], current
    print('PASS: Wallpaper Pro is a mapped, tiled Hyprland client:', current['size'], flush=True)
    layers = json.loads(subprocess.check_output(['hyprctl', 'layers', '-j'], text=True))
    assert not any(surface['namespace'] == 'wallpaper-pro-manager' for monitor in layers.values()
                   for level in monitor['levels'].values() for surface in level), layers
    print('PASS: the manager no longer creates a fixed shell-layer surface', flush=True)
    subprocess.run(['hyprctl', 'dispatch', 'closewindow', 'address:' + current['address']], check=True, stdout=subprocess.DEVNULL)
    wait_window(False)
    after = status()
    assert (after['enabled'], after['mode']) == (before['enabled'], before['mode']), after
    subprocess.run(['omarchy-shell', 'shell', 'toggle', ID, '{}'], check=True, stdout=subprocess.DEVNULL)
    reopened = wait_window(True)
    assert not reopened['floating'], reopened
    print('PASS: compositor close preserves wallpapers; bar-style toggle reopens a tiled window', flush=True)


if __name__ == '__main__':
    main()
