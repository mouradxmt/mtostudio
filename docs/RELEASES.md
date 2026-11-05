# Mtouaa releases and in-app updates

Source and public releases: https://github.com/mouradxmt/mtostudio

## Editions

| Edition | Application ID | Update delivery |
| --- | --- | --- |
| Google Play | `com.mtouaa.studio` | Play In-App Updates 2.1.0, flexible flow |
| Huawei | `com.mtouaa.studio.huawei` | Publisher-signed APKs from public Mtouaa GitHub releases |
| Preview | `com.mtouaa.studio.preview` | Development build; install a new Preview manually |

All include the same 15 offline editors. Huawei needs an OS that installs Android APKs;
HarmonyOS NEXT devices without APK support cannot run this application. The updater does
not require Google Play Services. The Google update SDK and APK-install permission are
restricted to their respective edition; the Play APK cannot install external APK updates.

Updates are initiated from the native Apps screen. No background polling, account, embedded
GitHub token, or automatic editor ZIP replacement is added. Save/export before updating.
Android may close the process during installation. Documents remain in Android's existing
package data on an ordinary same-package update, but unsaved editor state is not guaranteed.
Moving between Preview/Play/Huawei requires explicit document export/import.

## Automated builds

`.github/workflows/android.yml` builds on main pushes, pull requests, tag pushes and manual
dispatch. A macOS 15 ARM64 runner matches the reviewed Trunk/bindgen archive checksums.
Source jobs have read-only permissions and no signing secrets. Five parallel editor jobs
at most each compile one engine; compiler targets do not accumulate across all 15 engines
on a standard runner. Only completed engine assets are cached, and a native build job
combines/revalidates them. Each source job downloads the committed
source archives, verifies their checksums and the reviewed license/dependency inventory,
rebrands source, compiles/reuses matching editor outputs, preserves legal notices, then builds
both Android editions and the Play AAB. Artifacts are retained for seven days; they are
unsigned until the separate release job signs them.

Only a `vX.Y.Z` tag push starts signing/publishing. The version must match `app/build.gradle`,
and its versionCode must exceed prior release tags. Signing occurs in a separate fresh job,
using these repository Actions secrets (never commit them):

- `ANDROID_KEYSTORE_BASE64`: base64 of the existing PKCS12 upload key.
- `ANDROID_STORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

The release APK must retain certificate SHA-256
`c4388b1fc99fe8bf576970455a0f4089bffe8d272583f53500a8f8eee6dd1576`.
Keep an independent encrypted backup of this key: replacing it breaks Huawei upgrades.
GitHub Actions can sign future apps once these secrets are configured. Restrict repository
and workflow write access accordingly. Temporary key files are removed even after failure.

Before tagging, update app version/code, `release/RELEASE_NOTES.md`, and the verification
record with actual testing for the change. Rebuild/verify locally if needed:

```sh
./tools/build.sh assembleHuaweiRelease assemblePlayRelease bundlePlayRelease lintHuaweiRelease lintPlayRelease
python3 tools/verify_play_bundle.py
python3 tools/package_release.py
```

Push the reviewed source commit, then its matching `vX.Y.Z` tag. The release job publishes
Huawei APK, Play APK/AAB, `mtouaa-update.json`, hashes and the committed verification record.
The AAB is not automatically submitted to Google Play; upload it to a test track and complete
the publisher's remaining Play declarations. An existing published tag/release is not
overwritten; fix a failed unpublished job or issue a new version.

`upstream-check.yml` compares all 15 latest stable upstream versions every Monday and saves
a report. It does not silently approve new licenses, change pins, or publish upstream code.
Use the existing `updateBundledApps` maintenance task and review its license gate before
committing updated editor pins. New editor versions reach tablets in a new Mtouaa APK.

## Huawei trust and failure behavior

The updater reads only the latest stable release from the configured public repository.
The `mtouaa-update.json` envelope contains exact base64 payload bytes and a SHA256withRSA
signature made with the same key that signs the APK. The installed APK certificate provides
the trusted public key. Its signed payload binds the Huawei package, increasing versionCode,
version name, canonical repository APK URL, size and SHA-256. HTTPS redirects are restricted
to the approved GitHub/CDN hosts. Downloads are bounded, streamed into private cache and
renamed only after completion. Incomplete/corrupt files cannot be installed.

Before handing the APK to Android, the controller rechecks its hash, package, version and
certificate on a worker thread. A nonexported FileProvider grants temporary read access to
the installer for `cache/updates/` only. Android enforces its own APK signature checks and
installation confirmation. The user may first need to allow installations from Mtouaa in
Android Settings. Cancelling an update keeps the installed editors available offline.
Signed key rotation is not implemented: retain the existing key for Huawei releases.

## Testing

Use only a disposable emulator or a device with exported/backed-up documents. Never install
over an emulator in which the user has unsaved work. Build matching instrumentation APKs:

```sh
./tools/build.sh assembleHuaweiReleaseAndroidTest assemblePlayReleaseAndroidTest
# Install matching release + AndroidTest APKs on the chosen disposable device, then:
adb -s SERIAL shell am instrument -w -e updatesOnly true com.mtouaa.studio.huawei.test/org.wordcraft.offline.SuiteSmokeInstrumentation
adb -s SERIAL shell am instrument -w -e updatesOnly true com.mtouaa.studio.test/org.wordcraft.offline.SuiteSmokeInstrumentation
```

Huawei checks exercise Android RSA verification, tampering/wrong-key rejection, downgrade
rejection, channel/package/origin checks, size bounds, and FileProvider permissions. Optional
`fixtureApk=/data/local/tmp/NAME.apk` adds real PackageManager verification of a signed future
fixture and corruption rejection. With installation permission enabled on the disposable
device, `-e installer true` additionally checks the save-state gate, native confirmation,
verified FileProvider handoff to Android's installer, and cancellation without upgrading.
`tools/ci/update_fixture.py` creates a tiny fixture for
0.6.0 tests; never install/publish it. Update the fixture's code/version for later releases.

Play checks use Google's `FakeAppUpdateManager` to test the actual native controller's
availability, consent, progress, safe-state checks, restart cancellation and confirmed restart. A real Play
test still needs a Play-owned install, matching app ID/signing identity, and a higher code
available to that tester. See https://developer.android.com/guide/playcore/in-app-updates/test.

Run the full offline suite smoke runner and import/menu regressions when those paths change.
The attached verification record distinguishes local checks from physical Huawei and real
Google Play acceptance; generating artifacts alone does not complete store submission.
