"""No network or real builds: exercise failure paths before touching the current bundle."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import update_bundled_apps as updater
import build_play_engines as builder


class ReleaseDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.app = dict(id='pdfcraft', name='PdfCraft', description='PDF', repo='storytold/pdfcraft', version='1.0.0')
        self.release = dict(tag_name='v1.2.0', draft=False, prerelease=False, assets=[dict(
            name='pdfcraft-web-1.2.0.zip', digest='sha256:'+'a'*64, size=123,
            browser_download_url='https://github.com/storytold/pdfcraft/releases/download/v1.2.0/pdfcraft-web-1.2.0.zip')])

    def discover(self):
        with patch.object(updater, 'github', side_effect=[self.release, {'object': {'type': 'commit', 'sha': 'b'*40}}]):
            return updater.latest(self.app)

    def test_stable_release_is_pinned_to_exact_archive_and_commit(self):
        app, pin = self.discover()
        self.assertEqual(app['sha256'], 'a'*64); self.assertEqual(pin['commit'], 'b'*40)
        self.assertEqual(app['version'], '1.2.0')

    def test_prerelease_and_missing_digest_or_archive_are_rejected(self):
        for mode in ('prerelease', 'digest', 'archive', 'url'):
            with self.subTest(mode=mode):
                original = json.loads(json.dumps(self.release))
                if mode == 'prerelease': self.release['prerelease'] = True
                if mode == 'digest': self.release['assets'][0]['digest'] = None
                if mode == 'archive': self.release['assets'] = []
                if mode == 'url': self.release['assets'][0]['browser_download_url'] = 'https://untrusted.invalid/archive.zip'
                with self.assertRaises((ValueError, TypeError)): self.discover()
                self.release = original

    def test_no_implicit_downgrade(self):
        self.app['version'] = '2.0.0'
        with self.assertRaisesRegex(ValueError, 'downgrade'): self.discover()

    def test_annotated_tag_is_resolved_without_trusting_returned_urls(self):
        replies = [self.release, {'object': {'type': 'tag', 'sha': 'c'*40, 'url': 'https://untrusted.invalid'}},
                   {'object': {'type': 'commit', 'sha': 'd'*40}}]
        with patch.object(updater, 'github', side_effect=replies) as request:
            _, pin = updater.latest(self.app)
        self.assertEqual(pin['commit'], 'd'*40)
        self.assertIn('/git/tags/'+'c'*40, request.call_args.args[0])

    def test_rate_limit_has_actionable_error_without_exposing_token(self):
        error = updater.urllib.error.HTTPError('https://api.github.com/test',403,'rate limited',{},None)
        with patch.object(updater.urllib.request,'urlopen',side_effect=error), patch.dict(updater.os.environ,{'GITHUB_TOKEN':'secret-value'}):
            with self.assertRaisesRegex(ValueError,'Set GITHUB_TOKEN') as caught:
                updater.github('https://api.github.com/test')
        self.assertNotIn('secret-value',str(caught.exception))


class IsolatedFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.base = Path(self.temp.name)
        self.root = self.base/'root'; self.root.mkdir()
        self.previous = updater.ROOT; updater.ROOT = self.root
    def tearDown(self): updater.ROOT = self.previous; self.temp.cleanup()
    def put(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)

    def test_license_and_dependency_changes_include_additions_and_removals(self):
        source = self.root/'source'; self.put(source/'LICENSE-MIT', 'copyright original')
        self.put(source/'Cargo.lock', 'old dependencies'); self.put(source/'src/lib.rs', 'old code')
        old = {'inputs': {'pdfcraft': updater.inventory(source)}}
        self.put(source/'src/lib.rs', 'new code')
        self.assertEqual(updater.policy_changes(old, {'inputs': {'pdfcraft': updater.inventory(source)}}), {})
        self.put(source/'Cargo.lock', 'new dependencies'); (source/'LICENSE-MIT').unlink()
        self.put(source/'assets/fonts/OFL-new.txt', 'new font terms')
        changed = updater.policy_changes(old, {'inputs': {'pdfcraft': updater.inventory(source)}})
        self.assertEqual(set(changed['pdfcraft']), {'Cargo.lock','LICENSE-MIT','assets/fonts/OFL-new.txt'})

    def test_promotion_restores_all_old_outputs_if_any_rename_fails(self):
        # Fail each rename, including after one complete path was replaced.
        for fail_at in range(1, 5):
            with self.subTest(fail_at=fail_at):
                case = self.root/str(fail_at); case.mkdir(); updater.ROOT = case
                stage = case/'stage'; backup = case/'previous'
                self.put(case/'locks.json', 'old-lock'); self.put(case/'assets/index.html', 'old-editor')
                self.put(stage/'locks.json', 'new-lock'); self.put(stage/'assets/index.html', 'new-editor')
                calls = [0]
                def replace(source, dest):
                    calls[0] += 1
                    if calls[0] == fail_at: raise OSError('Simulated disk failure')
                    updater.os.replace(source, dest)
                with self.assertRaisesRegex(OSError, 'disk failure'):
                    updater.promote(stage, ['locks.json','assets'], backup, replace=replace)
                self.assertEqual((case/'locks.json').read_text(), 'old-lock')
                self.assertEqual((case/'assets/index.html').read_text(), 'old-editor')
        updater.ROOT = self.root

    def test_license_gate_stops_before_build_or_live_lock_changes(self):
        catalog = [dict(id=a[0], name=a[1], description=a[2], repo='storytold/'+a[0], version='1.0.0') for a in updater.discover_suite.APPS]
        updater.write_json(self.root/'tools/suite-lock.json', catalog)
        updater.write_json(self.root/updater.POLICY, {'format':1,'inputs': {'pdfcraft': {'NOTICE':'old'}}})
        def configure(stage): stage.mkdir(parents=True)
        with patch.object(updater,'latest',side_effect=lambda app:(dict(app,version='1.1.0'), {'id':app['id'],'commit':'a'*40})), \
             patch.object(updater,'configure_stage',side_effect=configure), \
             patch.object(updater,'stage_inputs',return_value=([],[])), \
             patch.object(updater,'policy_for',return_value={'format':1,'inputs':{'pdfcraft':{'NOTICE':'new'}}}), \
             patch.object(updater.subprocess,'run') as build:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'License/attribution'):
                updater.run(type('Args',(),{'check':False})())
            build.assert_not_called()
        self.assertEqual(updater.read_json(self.root/'tools/suite-lock.json'),catalog)
        self.assertEqual(updater.read_json(self.root/updater.REPORT/'report.json')['status'],'license-review-required')

    def test_missing_license_or_changed_engine_license_is_rejected(self):
        source=self.root/'vendor/sources/pdfcraft'
        app={'id':'pdfcraft'}
        with self.assertRaisesRegex(ValueError,'missing required'): updater.policy_for(self.root,[app],[])
        for name in ('LICENSE-MIT','LICENSE-APACHE','NOTICE','Cargo.toml','Cargo.lock'): self.put(source/name,'text')
        self.put(source/'Cargo.toml','[workspace.package]\nlicense = "Different-License"\n')
        with self.assertRaisesRegex(ValueError,'top-level license changed'): updater.policy_for(self.root,[app],[])

    def test_moved_existing_release_tag_stops_before_downloading(self):
        updater.write_json(self.root/'tools/play-source-lock.json',[{'id':'pdfcraft','version':'1.0.0','commit':'old'}])
        with patch.object(updater.fetch_play_sources,'fetch') as fetch:
            with self.assertRaisesRegex(ValueError,'release tag moved'):
                updater.stage_inputs(self.root/'stage',[{'id':'pdfcraft'}],[{'id':'pdfcraft','version':'1.0.0','commit':'new'}])
            fetch.assert_not_called()

    def test_successful_promotion_preserves_previous_tree(self):
        stage=self.root/'stage'; backup=self.root/'previous'
        self.put(self.root/'assets/index.html','old'); self.put(stage/'assets/index.html','new')
        updater.promote(stage,['assets'],backup)
        self.assertEqual((self.root/'assets/index.html').read_text(),'new')
        self.assertEqual((backup/'assets/index.html').read_text(),'old')

    def test_original_legal_and_font_files_are_copied_without_rebranding(self):
        stage = self.root/'stage'; source = stage/'vendor/sources/pdfcraft'
        self.put(source/'NOTICE', 'Copyright ArtCraft Team')
        self.put(source/'LICENSE-MIT', 'original license text')
        self.put(source/'ATTRIBUTION.toml', 'original asset authors')
        self.put(stage/'vendor/sources/craft-fonts/OFL.txt', 'reserved font names')
        self.put(stage/('vendor/sources/craft-i18n-'+'c'*40+'/language-data/en-us/LICENCE-SCOWL.txt'), 'original dictionary terms')
        target = stage/'app/src/play/assets/suite/pdfcraft'
        self.put(target/'MTOUAA-ASSET-ATTRIBUTION.toml', 'independent artwork')
        updater.write_json(target/'mtouaa-build.json', {'files': {}})
        self.put(stage/'app/src/play/assets/THIRD_PARTY_NOTICES.txt', 'Base runtime notices\n')
        updater.write_json(stage/'tools/play-source-lock.json', [{'id':'pdfcraft','commit':'a'*40}])
        updater.write_json(stage/'release/build-tools.json', {'additionalSourceInputs':[{'repo':'storytold/craft-i18n','commit':'c'*40}]})
        self.put(stage/'release/dependency-notices.txt', 'extra dependency copyright')
        updater.preserve_notices(stage,[{'id':'pdfcraft','repo':'storytold/pdfcraft','name':'PdfCraft','version':'1.0.0'}],[('craft-fonts',{'commit':'b'*40})])
        self.assertEqual((target/'upstream-legal/source/NOTICE').read_text(), 'Copyright ArtCraft Team')
        self.assertEqual((target/'upstream-legal/source/ATTRIBUTION.toml').read_text(),'original asset authors')
        self.assertEqual((target/('upstream-legal/fonts/'+'b'*40+'/OFL.txt')).read_text(),'reserved font names')
        self.assertEqual((target/('upstream-legal/inputs/craft-i18n/'+'c'*40+'/language-data/en-us/LICENCE-SCOWL.txt')).read_text(),'original dictionary terms')
        self.assertEqual((target/'MTOUAA-ASSET-ATTRIBUTION.toml').read_text(),'independent artwork')
        self.assertIn('original license text',(stage/'app/src/play/assets/THIRD_PARTY_NOTICES.txt').read_text())
        self.assertIn('extra dependency copyright',(stage/'app/src/play/assets/THIRD_PARTY_NOTICES.txt').read_text())
        report=updater.read_json(target/'mtouaa-build.json')
        for name, checksum in report['files'].items(): self.assertEqual(updater.digest(target/name),checksum)

    def test_new_commit_with_identical_brand_patch_still_rebuilds(self):
        source=self.root/'.tools/play-work/pdfcraft'; source.mkdir(parents=True)
        updater.write_json(source/'mtouaa-patch.json', {'files':{}})
        pin={'id':'pdfcraft','commit':'new'}
        updater.write_json(self.root/'tools/play-source-lock.json',[pin])
        dest=self.root/'assets'; target=dest/'pdfcraft'
        self.put(target/'editor.wasm','old binary')
        updater.write_json(target/'mtouaa-build.json', {'source':{'id':'pdfcraft','commit':'old'},'patch':{'files':{}},'files':{'editor.wasm':updater.digest(target/'editor.wasm')}})
        with patch.object(builder,'ROOT',self.root), patch.object(builder,'DEST',dest), patch.object(builder.subprocess,'run',side_effect=RuntimeError('Build invoked')):
            with self.assertRaisesRegex(RuntimeError,'Build invoked'): builder.build({'id':'pdfcraft'}, {})
        with patch.object(builder,'ROOT',self.root), patch.object(builder,'DEST',dest):
            with self.assertRaisesRegex(RuntimeError,'compile before staging'): builder.build({'id':'pdfcraft'}, {},stage_only=True)

    def test_resume_rejects_incomplete_snapshot_without_network(self):
        catalog=[dict(id=a[0], name=a[1], description=a[2], repo='storytold/'+a[0], version='1.0.0') for a in updater.discover_suite.APPS]
        updater.write_json(self.root/'tools/suite-lock.json',catalog)
        stage=self.root/updater.REPORT/'workspace'
        updater.write_json(stage/'tools/suite-lock.json',catalog)
        updater.write_json(stage/'tools/play-source-lock.json',[])
        with patch.object(updater,'latest') as discover:
            with self.assertRaisesRegex(ValueError,'Invalid staged catalog'):
                updater.run(type('Args',(),{'check':False,'resume':True})())
            discover.assert_not_called()


if __name__ == '__main__': unittest.main()
