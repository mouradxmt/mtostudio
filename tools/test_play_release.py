import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('release_guard',Path(__file__).with_name('check_play_release.py'))
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

class ReleaseGuardTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.previous=guard.ROOT;guard.ROOT=self.root
        tools=self.root/'tools';tools.mkdir()
        (self.root/'release').mkdir();(self.root/'release/brand.json').write_text(json.dumps({'appName':'Mtouaa Studio','website':'https://mtouaa.com'}))
        recipe=tools/'prepare_play_sources.py';recipe.write_text('test recipe\n')
        self.dest=self.root/'app/src/play/assets/suite';self.dest.mkdir(parents=True)
        self.catalog=[{'id':'tool'+str(i)} for i in range(15)]
        self.pins=[{'id':a['id'],'commit':'1'*40,'sha256':'2'*64} for a in self.catalog]
        (tools/'suite-lock.json').write_text(json.dumps(self.catalog))
        (tools/'play-source-lock.json').write_text(json.dumps(self.pins))
        (self.dest/'catalog.json').write_text(json.dumps(self.catalog))
        for app,pin in zip(self.catalog,self.pins):
            folder=self.dest/app['id'];folder.mkdir()
            (folder/'editor.wasm').write_bytes(b'\0asm\1\0\0\0')
            (folder/'MTOUAA-MODIFICATIONS.txt').write_text('Independent source build\n')
            report={'source':pin,'patch':{'recipeSha256':hashlib.sha256(recipe.read_bytes()).hexdigest(),'brand':{'appName':'Mtouaa Studio','website':'https://mtouaa.com'}},
                'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}}
            (folder/'mtouaa-build.json').write_text(json.dumps(report))

    def tearDown(self):guard.ROOT=self.previous;self.temp.cleanup()
    def validate(self):
        with contextlib.redirect_stdout(io.StringIO()):guard.validate_assets()
    def test_complete_pinned_outputs_are_accepted(self):self.validate()
    def test_missing_editor_is_rejected(self):
        (self.dest/'tool3/mtouaa-build.json').unlink()
        with self.assertRaises(FileNotFoundError):self.validate()
    def test_changed_binary_is_rejected(self):
        (self.dest/'tool3/editor.wasm').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'Changed engine output'):self.validate()
    def test_unrecorded_executable_asset_is_rejected(self):
        (self.dest/'tool3/injected.js').write_text('unexpected executable code')
        with self.assertRaisesRegex(ValueError,'Unrecorded or missing'):self.validate()
    def test_unchanged_stock_branding_is_rejected_even_with_matching_hash(self):
        folder=self.dest/'tool3';wasm=folder/'editor.wasm';wasm.write_bytes(b'\0asm\1\0\0\0ArtCraft')
        p=folder/'mtouaa-build.json';r=json.loads(p.read_text());r['files']['editor.wasm']=hashlib.sha256(wasm.read_bytes()).hexdigest();p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'branding remains'):self.validate()
    def test_unpinned_source_is_rejected(self):
        p=self.dest/'tool3/mtouaa-build.json';r=json.loads(p.read_text());r['source']['commit']='3'*40;p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'Unpinned source'):self.validate()
    def test_required_upstream_copyright_credit_is_preserved(self):
        folder=self.dest/'tool3';wasm=folder/'editor.wasm';wasm.write_bytes(b'\0asm\1\0\0\0Copyright (c) 2026 ArtCraft Team and contributors')
        p=folder/'mtouaa-build.json';r=json.loads(p.read_text());r['files']['editor.wasm']=hashlib.sha256(wasm.read_bytes()).hexdigest();p.write_text(json.dumps(r))
        self.validate()
    def test_stale_branding_recipe_is_rejected(self):
        (self.root/'tools/prepare_play_sources.py').write_text('changed recipe')
        with self.assertRaisesRegex(ValueError,'current branding recipe'):self.validate()

if __name__=='__main__':unittest.main()
