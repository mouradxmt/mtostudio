from pathlib import Path
import unittest
from unittest.mock import patch
import package_release

class ReleasePackagingTest(unittest.TestCase):
    def test_android_sdk_codename_cannot_replace_application_identity(self):
        output = "package: name='com.mtouaa.studio.huawei' versionCode='9' versionName='0.6.0' platformBuildVersionName='17' platformBuildVersionCode='37' compileSdkVersion='37' compileSdkVersionCodename='17'\n"
        with patch('package_release.subprocess.check_output', return_value=output):
            self.assertEqual(package_release.apk_info(Path('fixture.apk')), {'name':'com.mtouaa.studio.huawei','versionCode':'9','versionName':'0.6.0'})

if __name__ == '__main__': unittest.main()
