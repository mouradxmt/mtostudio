#!/usr/bin/env python3
"""Refresh the reviewed lockfile from official stable GitHub releases (explicit maintenance tool)."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request

APPS = [
    ('photocraft', 'PhotoCraft', 'Photo and image editing'),
    ('vectorcraft', 'VectorCraft', 'Vector illustration'),
    ('filmcraft', 'FilmCraft', 'Video editing'),
    ('lightcraft', 'LightCraft', 'Photo library and RAW development'),
    ('pdfcraft', 'PdfCraft', 'PDF editing and organization'),
    ('effectcraft', 'EffectCraft', 'Motion graphics and visual effects'),
    ('designcraft', 'DesignCraft', 'Page layout and publishing'),
    ('figcraft', 'FigCraft', 'Interface design and prototyping'),
    ('texturecraft', 'TextureCraft', '3D texture painting'),
    ('wordcraft', 'WordCraft', 'Writing and document design'),
    ('soundcraft', 'SoundCraft', 'Audio editing and mixing'),
    ('deckcraft', 'DeckCraft', 'Presentations and slides'),
    ('cadcraft', 'CADCraft', 'Computer-aided design'),
    ('gridcraft', 'GridCraft', 'Spreadsheets and data analysis'),
    ('craft-anything', 'Craft Anything', 'Software exploration and creation'),
]

def discover(app):
    slug, name, description = app
    request = urllib.request.Request(f'https://api.github.com/repos/storytold/{slug}/releases/latest',
        headers={'User-Agent': 'ArtCraft-Offline-Android', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        release = json.load(response)
    entry = dict(id=slug, name=name, description=description, repo=f'storytold/{slug}',
                 version=release['tag_name'].removeprefix('v'))
    assets = [a for a in release['assets'] if a['name'].startswith(slug + '-web-') and a['name'].endswith('.zip')]
    if assets:
        asset = assets[0]
        digest = asset.get('digest', '')
        if not digest.startswith('sha256:'):
            raise ValueError(f'{slug}: GitHub release has no SHA-256 digest')
        entry.update(asset=asset['name'], url=asset['browser_download_url'], sha256=digest[7:], size=asset['size'])
    else:
        entry['unavailable'] = 'The latest official release has no web package.'
    print(name, entry['version'], f"{entry.get('size', 0) / 1048576:.1f} MB", entry.get('unavailable', ''), flush=True)
    return entry

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        catalog = list(pool.map(discover, APPS))
    target = Path(__file__).resolve().parent / 'suite-lock.json'
    target.write_text(json.dumps(catalog, indent=2) + '\n')
    print('Total compressed:', round(sum(a.get('size', 0) for a in catalog)/1048576), 'MB')
