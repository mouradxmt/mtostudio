#!/usr/bin/env python3
"""Compile the pinned, rebranded sources; stage auditable offline Play assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import re
import struct
from prepare_play_sources import NAMES

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'app/src/play/assets/suite'

def build(app,env,stage_only=False,force=False):
    source=ROOT/'.tools/play-work'/app['id']
    web=source/'apps'/(app['id']+'-web')
    if not (source/'mtouaa-patch.json').is_file(): raise RuntimeError('Prepare rebranded sources first: '+app['id'])
    pin=next(p for p in json.loads((ROOT/'tools/play-source-lock.json').read_text()) if p['id']==app['id'])
    existing=DEST/app['id']/'mtouaa-build.json'
    if stage_only:
        if not existing.is_file() or json.loads(existing.read_text())['source']!=pin or json.loads(existing.read_text())['patch']['files']!=json.loads((source/'mtouaa-patch.json').read_text())['files']:
            raise RuntimeError('Source inputs changed; compile before staging: '+app['id'])
    if existing.is_file() and not stage_only and not force:
        previous=json.loads(existing.read_text())
        if previous['source']==pin and previous['patch']==json.loads((source/'mtouaa-patch.json').read_text()) and all((DEST/app['id']/name).is_file() and hashlib.sha256((DEST/app['id']/name).read_bytes()).hexdigest()==digest for name,digest in previous['files'].items()):
            print('Already built '+app['id'],flush=True);return
    env=dict(env)
    i18n_ref=source/'craft-i18n.rev'
    if i18n_ref.is_file():
        revision=i18n_ref.read_text().strip()
        i18n=source/'mtouaa-i18n'
        if not re.fullmatch('[a-f0-9]{40}',revision) or not i18n.is_dir():raise RuntimeError('Missing pinned translation input '+revision)
        env['CRAFT_I18N_DIR']=str(i18n)
        env['CRAFT_I18N_REQUIRED']='1'
    workflow=source/'.github/workflows/release.yml'
    font_ref=re.search(r'craft-fonts-ref:\s*([0-9a-f]{40})',workflow.read_text()) if workflow.is_file() else None
    if font_ref and font_ref[1]!='b076417b5880bd4154bd22f00695b1d28c6bea83':
        env['CRAFT_FONTS_DIR']=str(ROOT/'vendor/sources'/('craft-fonts-'+font_ref[1]))
        if not Path(env['CRAFT_FONTS_DIR']).is_dir():raise RuntimeError('Missing pinned font input '+font_ref[1])
    log=ROOT/'.tools/play-logs'/(app['id']+'.log');log.parent.mkdir(exist_ok=True)
    print('Compiling '+app['id']+'; log '+str(log),flush=True)
    # Keep upstream Trunk/profile settings, fonts and pinned dependency versions.
    built=source/'dist/web'
    if not stage_only:
        with log.open('w') as output:
            if app['id'] in ['filmcraft','effectcraft','lightcraft']:
                profile='web' if app['id']=='lightcraft' else 'release'
                subprocess.run([str(ROOT/'.tools/cargo/bin/cargo'),'build','--locked','--target','wasm32-unknown-unknown','--profile',profile,'-p',app['id']+'-web'],cwd=source,env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
                built.mkdir(parents=True,exist_ok=True)
                binary=ROOT/'.tools/play-target/wasm32-unknown-unknown'/profile/(app['id'].replace('-','_')+'_web.wasm')
                subprocess.run([str(ROOT/'.tools/wasm-bin/wasm-bindgen'),'--target','web','--no-typescript','--out-dir',str(built),str(binary)],env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
                static=web if app['id']=='lightcraft' else web/'web'
                for p in static.iterdir():
                    if p.is_file() and p.suffix in ['.html','.js','.png','.svg','.webmanifest'] and p.name!='sw.js':shutil.copy2(p,built/p.name)
                if app['id']=='filmcraft':
                    index=built/'index.html';index.write_text(index.read_text().replace('__FC_BUILD__',hashlib.sha256(binary.read_bytes()).hexdigest()[:16]))
                if app['id']=='effectcraft':
                    from prepare_play_sources import png
                    for size in [256,512]:(built/f'icon-{size}.png').write_bytes(png(size))
                if app['id']=='lightcraft':
                    fonts=Path(env['CRAFT_FONTS_DIR'])
                    for line in (fonts/'fonts/manifest.txt').read_text().splitlines():
                        fields=[field.strip() for field in line.split('|')]
                        if len(fields)>=6 and fields[:2]==['Noto Sans CJK SC','Regular']:
                            shutil.copy2(fonts/fields[2],built/'lightcraft_zh_hans.otf')
                            shutil.copy2(fonts/fields[5],built/'OFL-noto-sans-cjk-sc.txt');break
            else:
                subprocess.run([str(ROOT/'.tools/wasm-bin/trunk'),'build','--release','--locked'],cwd=web,env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
    if not (built/'index.html').is_file(): raise RuntimeError('Missing web output: '+app['id'])
    target=DEST/app['id']
    if target.exists():shutil.rmtree(target)
    shutil.copytree(built,target,ignore=shutil.ignore_patterns('*.gz','*.br'))
    # Browser favicons/loading tiles are separate static assets in some releases.
    # Replace these too, even when they are not compiled into the WASM module.
    from prepare_play_sources import MARK, png
    for icon in target.rglob('favicon.*'):
        if icon.suffix=='.png':icon.write_bytes(png(128))
        elif icon.suffix=='.svg':icon.write_text(MARK)
    for icon in target.rglob('*.ico'):
        image=png(128)
        icon.write_bytes(struct.pack('<HHHBBBBHHII',0,1,1,128,128,0,0,1,32,len(image),22)+image)
    index=target/'index.html'; html=index.read_text()
    if '/__native-save.js' not in html:html=html.replace('<head>','<head><script src="/__native-save.js"></script>',1)
    index.write_text(html)
    # Preserve legal notices from the verified official release as well as source
    # provenance. No upstream binary, favicon or logo is copied into this edition.
    upstream=ROOT/'app/src/main/assets/suite'/app['id']
    for p in upstream.rglob('*'):
        legal=p.name.upper().startswith(('LICENSE','LICENCE','NOTICE','OFL','ATTRIBUTION')) or 'licenses' in [part.lower() for part in p.relative_to(upstream).parts]
        if p.is_file() and legal:
            output=target/p.relative_to(upstream);output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,output)
    if (source/'ATTRIBUTION.toml').is_file():shutil.copy2(source/'ATTRIBUTION.toml',target/'MTOUAA-ASSET-ATTRIBUTION.toml')
    shutil.copy2(source/'MTOUAA-MODIFICATIONS.txt',target/'MTOUAA-MODIFICATIONS.txt')
    report={'source':pin,'fontCommit':font_ref[1] if font_ref else None,
        'patch':json.loads((source/'mtouaa-patch.json').read_text()),'files':{str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file()}}
    (target/'mtouaa-build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Ready '+app['id'],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--app');parser.add_argument('--stage-only',action='store_true');parser.add_argument('--force',action='store_true');args=parser.parse_args()
    env=dict(os.environ, RUSTUP_HOME=str(ROOT/'.tools/rustup'),CARGO_HOME=str(ROOT/'.tools/cargo'),CARGO_TARGET_DIR=str(ROOT/'.tools/play-target'),CRAFT_FONTS_DIR=str(ROOT/'vendor/sources/craft-fonts'),XDG_CACHE_HOME=str(ROOT/'.tools/cache'),CARGO_BUILD_JOBS='4',CARGO_NET_GIT_FETCH_WITH_CLI='true')
    env['PATH']=str(ROOT/'.tools/wasm-bin')+':'+str(ROOT/'.tools/cargo/bin')+':'+env['PATH']
    DEST.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ROOT/'tools/suite-lock.json').read_text())
    for app in catalog:
        if not args.app or app['id']==args.app:build(app,env,args.stage_only,args.force)
    if all((DEST/app['id']/'mtouaa-build.json').is_file() for app in catalog):
        for app in catalog:
            app['alias']=''.join(char for char in app['name'] if char.isalnum())
            app['name']=NAMES[app['id']]
        (DEST/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
