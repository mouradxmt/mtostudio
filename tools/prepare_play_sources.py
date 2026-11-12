#!/usr/bin/env python3
"""Create independently branded source trees; never patch compiled WASM or licence notices."""
import argparse
import functools
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import zlib
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '.tools/play-work'
NAMES = {'photocraft':'Photos','vectorcraft':'Vectors','filmcraft':'Video','lightcraft':'Photo Library',
    'pdfcraft':'PDF','effectcraft':'Motion','designcraft':'Layouts','figcraft':'Interface Design',
    'texturecraft':'Textures','wordcraft':'Writer','soundcraft':'Audio','deckcraft':'Slides',
    'cadcraft':'CAD','gridcraft':'Sheets','craft-anything':'Explorer'}
MARK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect x="4" y="4" width="120" height="120" rx="28" fill="#142838"/><path d="M30 91V37L64 69L98 37V91" fill="none" stroke="#68E1CB" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M64 87V99" stroke="#FFC46B" stroke-width="10" stroke-linecap="round"/></svg>'''
# Original geometric lettering; no font files or upstream artwork are used.
WORDMARK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 64"><g fill="none" stroke="COLOR" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 49V15L26 34L42 15V49 M57 15H89 M73 15V49 M108 15H130V49H108Z M150 15V49H174V15 M194 49L208 15L222 49 M199 37H217 M241 49L255 15L269 49 M246 37H264"/></g></svg>'''
RUST_CHAR=re.compile(r"'(?:\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.)|[^\\'\n])'")
RUST_RAW=re.compile(r'r(#{0,16})"')

def rust_strings(text, transform):
    """Rewrite string tokens while preserving comments, char literals and identifiers."""
    output=[];i=0
    while i<len(text):
        if text.startswith('//',i):
            end=text.find('\n',i);end=len(text) if end<0 else end
        elif text.startswith('/*',i):
            end=i+2;depth=1
            while depth and end<len(text):
                if text.startswith('/*',end):depth+=1;end+=2
                elif text.startswith('*/',end):depth-=1;end+=2
                else:end+=1
        elif text[i]=="'" and (char:=RUST_CHAR.match(text,i)):
            end=i+len(char[0])
        elif text[i]=='r' and (raw:=RUST_RAW.match(text,i)):
            stop='"'+raw[1];end=text.find(stop,i+len(raw[0]))
            if end<0:raise ValueError('Unterminated Rust raw string')
            end+=len(stop);output.append(transform(text[i:end]));i=end;continue
        elif text[i]=='"':
            end=i+1
            while end<len(text):
                if text[end]=='\\':end+=2
                elif text[end]=='"':end+=1;break
                else:end+=1
            output.append(transform(text[i:end]));i=end;continue
        else:end=i+1
        output.append(text[i:end]);i=end
    return ''.join(output)

@functools.lru_cache(maxsize=32)
def png(size):
    rows = []
    segments = [(30,91,30,37),(30,37,64,69),(64,69,98,37),(98,37,98,91)]
    def distance(x,y,a,b,c,d):
        t = max(0, min(1, ((x-a)*(c-a)+(y-b)*(d-b))/((c-a)**2+(d-b)**2)))
        return ((x-a-t*(c-a))**2+(y-b-t*(d-b))**2)**0.5
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            xx=(x+.5)*128/size; yy=(y+.5)*128/size
            corner = (max(32-xx,0,xx-96)**2 + max(32-yy,0,yy-96)**2)**0.5
            color=(20,40,56,255) if 4<=xx<=124 and 4<=yy<=124 and corner<=28 else (0,0,0,0)
            if min(distance(xx,yy,*s) for s in segments)<=6: color=(104,225,203,255)
            if distance(xx,yy,64,87,64,99)<=5: color=(255,196,107,255)
            row.extend(color)
        rows.append(bytes(row))
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows),9))+chunk(b'IEND',b'')

def prepare(app):
    brand=json.loads((ROOT/'release/brand.json').read_text())
    original=ROOT/'vendor/sources'/app['id']; final=WORK/app['id']
    dest=ROOT/'.tools/play-prepared'/app['id']
    if not (original/'Cargo.toml').is_file(): raise RuntimeError('Fetch pinned sources first: '+app['id'])
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(original,dest,ignore=shutil.ignore_patterns('target','dist','.git'))
    i18n_ref=original/'craft-i18n.rev'
    if i18n_ref.is_file():
        revision=i18n_ref.read_text().strip()
        translations=ROOT/'vendor/sources'/('craft-i18n-'+revision)
        if not re.fullmatch('[a-f0-9]{40}',revision) or not translations.is_dir():raise RuntimeError('Fetch pinned translations first: '+app['id'])
        shutil.copytree(translations,dest/'mtouaa-i18n',ignore=shutil.ignore_patterns('target','dist','.git'))
    changed=[]
    # Keep NOTICE, LICENSE*, ATTRIBUTION*, contributor records and fonts intact.
    for parent in ['crates','apps','mtouaa-i18n/locales']:
        for p in (dest/parent).rglob('*'):
            locale_path=any(part in ['i18n','locales'] for part in p.parts)
            is_locale=p.suffix in ['.json','.toml'] and locale_path
            if not p.is_file() or (p.suffix not in ['.rs','.tsv','.html','.webmanifest'] and not is_locale): continue
            before=p.read_text()
            def transform(value):
                # Attribution is not product branding. Never claim the upstream
                # team's copyright for the publisher of this independent port.
                if 'ArtCraft Team' in value:return value
                value=value.replace('the ArtCraft team','the upstream team').replace('ArtCraft team','upstream team')
                value=re.sub(r'https://(?:discord\.gg/artcraft|getartcraft\.com)(?:/[\w/#.-]*)?', 'https://mtouaa.com', value)
                value=value.replace('ArtCraft','Mtouaa Studio').replace('getartcraft.com','mtouaa.com').replace('discord.gg/artcraft','mtouaa.com')
                value=value.replace('Get help, share feedback and follow development on Discord.','Find support and information on the publisher website.')
                value=value.replace('Join the Mtouaa Studio community on Discord','Mtouaa Studio support')
                value=value.replace('Join us on Discord','Publisher support')
                value=value.replace('Join our Discord','Support website').replace('Join Our Discord','Support website')
                value=value.replace('Discord community','Support website').replace('Join the Mtouaa Studio community','About Mtouaa Studio')
                value=value.replace('Join the Mtouaa Studio Discord','Mtouaa Studio support').replace('"Discord"','"Support"')
                value=value.replace('Mtouaa Studio',brand['appName']).replace('https://mtouaa.com',brand['website'])
                value=re.sub(r'(?<![\w./])mtouaa\.com',urlparse(brand['website']).netloc,value)
                return value.replace(app['name'],NAMES[app['id']])
            if is_locale and p.suffix=='.json':
                def translate(node):
                    if isinstance(node,dict):return {transform(key):translate(value) for key,value in node.items()}
                    if isinstance(node,list):return [translate(value) for value in node]
                    return transform(node) if isinstance(node,str) else node
                after=json.dumps(translate(json.loads(before)),ensure_ascii=False,indent=2)+'\n'
            elif p.suffix=='.rs':after=rust_strings(before,transform)
            elif p.suffix=='.tsv' or (is_locale and p.suffix=='.toml'):
                # Use the intact English copyright fallback rather than changing
                # author names inside translated legal-credit rows.
                after=''.join(transform(line) for line in before.splitlines(keepends=True) if not ('ArtCraft' in line and ('Copyright' in line or '©' in line or 'Made by the ArtCraft team' in line)))
            else:after=transform(before)
            runtime=[]
            if p.suffix=='.rs':rust_strings(after,lambda value:runtime.append(value) or value)
            else:runtime=[after]
            for value in runtime:
                value=value.replace('ArtCraft Team','upstream authors')
                if any(mark in value for mark in ['ArtCraft','getartcraft.com','discord.gg/artcraft']):
                    raise ValueError('Unreplaced runtime branding in '+str(p.relative_to(dest)))
            if after!=before: p.write_text(after);changed.append(str(p.relative_to(dest)))
    # Remove protected marks, then put original artwork at the source include paths.
    # Paths stay stable to avoid changing engine code or binary document formats.
    for p in (dest/'docs/brand').glob('*'):
        if p.suffix=='.svg':
            image=WORDMARK.replace('COLOR','#ffffff' if 'white' in p.name else '#142838') if 'logo' in p.name else MARK
            p.write_text(image);changed.append(str(p.relative_to(dest)))
        elif p.suffix=='.png':
            p.write_bytes(png(128));changed.append(str(p.relative_to(dest)))
    # The Craft Anything icon is also protected. Use our own icon for all editors
    # so packaging and editor title bars have a consistent independent identity.
    for p in (dest/'assets/app-icon').rglob('*'):
        if not p.is_file():continue
        if p.suffix=='.png':
            b=p.read_bytes();size=struct.unpack_from('>I',b,16)[0] if b.startswith(b'\x89PNG') else 128
            p.write_bytes(png(min(size,512)));changed.append(str(p.relative_to(dest)))
        elif p.suffix=='.svg': p.write_text(MARK);changed.append(str(p.relative_to(dest)))
    # Record replacement artwork in source asset manifests. Keep upstream legal
    # notices unchanged; their authorship still applies to the editing engines.
    attribution=dest/'ATTRIBUTION.toml'
    if attribution.is_file():
        replacements=set(name for name in changed if Path(name).suffix in ['.svg','.png'])
        def update_asset(match):
            section=match[0];path=re.search(r'^path = "([^"]+)"',section,re.M)
            if not path or path[1] not in replacements:return section
            fields={'title':'Mtouaa original geometric artwork','author':'Mtouaa Studio contributors',
                'source':'Original vector and raster generator: tools/prepare_play_sources.py in the Mtouaa Studio Android project',
                'licence':'MIT OR Apache-2.0','licence_file':'LICENSE-MIT',
                'usage':'Independent branding; replaces the upstream asset for this Android edition',
                'sha256':hashlib.sha256((dest/path[1]).read_bytes()).hexdigest()}
            for key,value in fields.items():
                line=key+' = '+json.dumps(value)
                section=re.sub(r'^'+key+r' = .*$',lambda _:line,section,flags=re.M) if re.search(r'^'+key+r' = ',section,re.M) else section.rstrip()+'\n'+line+'\n\n'
            return section
        attribution.write_text(re.sub(r'^\[\[asset\]\]\n.*?(?=^\[\[|\Z)',update_asset,attribution.read_text(),flags=re.M|re.S))
        changed.append('ATTRIBUTION.toml')
    notice=dest/'MTOUAA-MODIFICATIONS.txt'
    notice.write_text('Mtouaa Studio independent Android edition.\n'
        'Modified 2026-11-12: replaced protected ArtCraft branding and app-icon artwork with original Mtouaa artwork; '
        'redirected community links to the publisher website. Upstream engine code, authorship and licence notices remain credited.\n'
        'Original Mtouaa geometric artwork is distributed under MIT OR Apache-2.0 for this source build.\n')
    manifest={'id':app['id'],'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'brand':{key:brand[key] for key in ['appName','website']},
        'files':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in sorted(set(changed))}}
    (dest/'mtouaa-patch.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Preserve unchanged source mtimes so a branding-script correction does not
    # force all 15 engines and their dependency graphs to recompile needlessly.
    final.mkdir(parents=True,exist_ok=True)
    for p in dest.rglob('*'):
        if not p.is_file():continue
        target=final/p.relative_to(dest)
        if not target.is_file() or p.read_bytes()!=target.read_bytes():
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    shutil.rmtree(dest)
    print(app['id']+': '+str(len(manifest['files']))+' rebranded source/assets',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--app');parser.add_argument('--skip');args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ROOT/'tools/suite-lock.json').read_text())
    for app in catalog:
        if (not args.app or app['id']==args.app) and app['id']!=args.skip: prepare(app)
