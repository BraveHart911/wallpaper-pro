#!/usr/bin/env python3
"""Build Wallpaper Pro's original scenic starter artwork. Requires ffmpeg."""
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/library'
THEMES = [
    ('northern-lights', 'Northern Lights', '#061726', '#164958', '#7ee8ca', '#12363e', '#092630'),
    ('ember-dunes', 'Ember Dunes', '#271b36', '#c76c56', '#ffd8a4', '#694051', '#392b40'),
    ('midnight-peaks', 'Midnight Peaks', '#080d23', '#283b6c', '#b9d3ff', '#1b294b', '#101c36'),
    ('ocean-glass', 'Ocean Glass', '#092b3c', '#267d88', '#c7f7e7', '#155466', '#103e52'),
    ('solar-bloom', 'Solar Bloom', '#351d34', '#a84e6a', '#ffd5b1', '#733550', '#44293f'),
    ('indigo-horizon', 'Indigo Horizon', '#18162e', '#575e91', '#dbd9ff', '#393d67', '#242944'),
]


def scene(theme, width, height):
    slug, name, top, bottom, light, ridge, foreground = theme
    rng = random.Random(slug)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>',
             f'<radialGradient id="glow"><stop stop-color="{light}" stop-opacity=".28"/><stop offset="1" stop-color="{light}" stop-opacity="0"/></radialGradient></defs>',
             f'<rect width="{width}" height="{height}" fill="url(#sky)"/>',
             f'<ellipse cx="{width*.68}" cy="{height*.38}" rx="{width*.37}" ry="{height*.6}" fill="url(#glow)"/>']
    for _ in range(100):
        x, y = rng.random()*width, rng.random()*height*.62
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rng.uniform(.5,1.8):.2f}" fill="{light}" opacity="{rng.uniform(.12,.65):.2f}"/>')
    parts.append(f'<circle cx="{width*.68}" cy="{height*.35}" r="{height*.055}" fill="{light}" opacity=".85"/>')
    for layer, color in enumerate([ridge, foreground, top]):
        points = []
        for index in range(33):
            x = index * width / 32
            y = height * (.62 + layer*.105 + math.sin(index*.5+layer)*.05 + rng.uniform(-.08,.08))
            points.append(f'{x:.1f},{y:.1f}')
        parts.append(f'<polygon points="0,{height} ' + ' '.join(points) + f' {width},{height}" fill="{color}"/>')
    parts.append('</svg>')
    return ''.join(parts)


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *map(str, args)], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    with tempfile.TemporaryDirectory() as tmp:
        for theme in THEMES:
            slug, name, *_ = theme
            for layout, width in [('single', 1920), ('panoramic', 3840)]:
                identity = slug + '-' + layout
                svg = Path(tmp) / (identity + '.svg')
                svg.write_text(scene(theme, width, 1080))
                image = OUT / (identity + '.jpg')
                ffmpeg('-i', svg, '-frames:v', 1, '-q:v', 2, image)
                thumbnail = OUT / (identity + '-thumb.jpg')
                ffmpeg('-i', image, '-vf', 'scale=480:-2', '-frames:v', 1, '-q:v', 3, thumbnail)
                catalog.append(dict(id='starter-' + identity, name=name, file=image.name, thumbnail=thumbnail.name,
                                    kind='image', layout=layout, width=width, height=1080))
        for theme, layout in [(THEMES[0], 'panoramic'), (THEMES[1], 'single'), (THEMES[2], 'panoramic')]:
            slug, name, *_ = theme
            width = 3840 if layout == 'panoramic' else 1920
            image = OUT / (slug + '-' + layout + '.jpg')
            video = OUT / (slug + '-drift.mp4')
            # A closed sinusoidal camera orbit: the 8-second cycle loops continuously.
            motion = f'scale={int(width*1.1)}:1188,crop={width}:1080:x=54+50*sin(2*PI*t/8):y=54+40*cos(2*PI*t/8)'
            ffmpeg('-loop', 1, '-framerate', 24, '-i', image, '-t', 8, '-vf', motion,
                   '-c:v', 'libx264', '-preset', 'fast', '-crf', 25, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', video)
            catalog.append(dict(id='starter-' + slug + '-drift', name=name + ' · Slow Drift', file=video.name,
                                thumbnail=slug + '-' + layout + '-thumb.jpg', kind='video', layout=layout, width=width, height=1080))
    (OUT / 'catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')


if __name__ == '__main__':
    main()
