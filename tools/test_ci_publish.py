import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from ci import publish_release

class ReleasePublicationTest(unittest.TestCase):
    def exercise(self,existing):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);assets=root/'dist/release';assets.mkdir(parents=True)
            (assets/'mtouaa-update.json').write_text('{}');(assets/'app.apk').write_bytes(b'fixture')
            calls=[]
            def run(args,**kwargs):
                calls.append(args)
                if args[1:3]==['release','view']:
                    return SimpleNamespace(returncode=1 if existing is None else 0,stdout=json.dumps({'isDraft':existing}))
                return SimpleNamespace(returncode=0)
            with patch.object(publish_release,'ROOT',root),patch('ci.publish_release.subprocess.run',side_effect=run),patch.dict('os.environ',RELEASE_TAG='v0.6.1',GITHUB_REPOSITORY='mouradxmt/mtostudio'):
                if existing is False:
                    with self.assertRaisesRegex(ValueError,'already public'):publish_release.main()
                else:publish_release.main()
            return calls
    def test_published_assets_are_never_overwritten(self):
        self.assertEqual([c[2] for c in self.exercise(False)],['view'])
    def test_partial_draft_resumes_before_publication(self):
        calls=self.exercise(True);self.assertEqual([c[2] for c in calls],['view','upload','edit'])
        self.assertIn('--clobber',calls[1]);self.assertIn('--draft=false',calls[2])
    def test_new_release_is_private_until_assets_finish_uploading(self):
        calls=self.exercise(None);self.assertEqual([c[2] for c in calls],['view','create','upload','edit'])
        self.assertIn('--draft',calls[1]);self.assertIn('--verify-tag',calls[1])

if __name__=='__main__':unittest.main()
