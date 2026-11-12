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

## Local release automation

Cloud workflows remain disabled to avoid repeated compilation and Actions artifact storage.
Neither pushes nor tags start a cloud job. The remaining workflows are manual-only small
checks; they do not build APKs or upload artifacts. The previous cloud build definition is
archived in `docs/ANDROID-CLOUD-BUILD.yml.example` for reference, outside the workflow folder.

Run one local command after changing the app version/code and reviewing the release notes:

```sh
python3 tools/release_local.py
# After committing the tested source, publish the same release:
python3 tools/release_local.py --publish
```

This checks the pinned editor outputs, performs an offline Gradle build using local caches,
validates APK signatures/permissions and the Play bundle, and generates the signed Huawei
update descriptor. It does not refresh upstream engines or compile Rust. The publish option
pushes the source/tag and uploads the final APKs/AAB, descriptor, hashes and verification
record directly to GitHub Releases, without Actions builds or intermediate artifact uploads.
Uploads remain a draft until complete. Published releases cannot be overwritten.
The AAB is not automatically submitted to Google Play.

The local signing key remains in ignored `.release-secrets/`. Keep its independent backup:
replacing it breaks Huawei upgrades. Previously authorized Actions signing secrets remain
unused while workflows are disabled; the manual checks do not access them.

For new upstream editor versions, run `updateBundledApps` explicitly and review its license
report before committing new pins. New editor versions reach tablets in a new Mtouaa APK.
The manual upstream-check workflow reports versions only; it has no scheduled trigger.

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

The completed public 0.6.0 → 0.6.1 upgrade is recorded in `release/ACCEPTANCE-0.6.1.md`.
The 0.7.0 editor refresh and its current checks are recorded in `release/VERIFICATION.md`.

Use only a disposable emulator or a device with exported/backed-up documents. Never install
over an emulator in which the user has unsaved work. Build matching instrumentation APKs:

```sh
./tools/build.sh assembleHuaweiReleaseAndroidTest assemblePlayReleaseAndroidTest
# Install matching release + AndroidTest APKs on the chosen disposable device, then:
adb -s SERIAL shell am instrument -w -e updatesOnly true com.mtouaa.studio.huawei.test/org.wordcraft.offline.SuiteSmokeInstrumentation
adb -s SERIAL shell am instrument -w -e updatesOnly true com.mtouaa.studio.test/org.wordcraft.offline.SuiteSmokeInstrumentation
```

`-e updatesOnly true -e live true` checks the real public descriptor and its signature
without downloading an APK. If a disposable emulator has DNS failures, supply explicit DNS
servers when launching that emulator; do not change a user device for this test.

Huawei checks exercise Android RSA verification, tampering/wrong-key rejection, downgrade
rejection, channel/package/origin checks, size bounds, and FileProvider permissions. Optional
`fixtureApk=/data/local/tmp/NAME.apk` adds real PackageManager verification of a signed future
fixture and corruption rejection. With installation permission enabled on the disposable
device, `-e installer true` additionally checks the save-state gate, native confirmation,
verified FileProvider handoff to Android's installer, and cancellation without upgrading.
`tools/ci/update_fixture.py` creates a tiny fixture for
0.6.1 tests; never install/publish it. Update the fixture's code/version for later releases.

Play checks use Google's `FakeAppUpdateManager` to test the actual native controller's
availability, consent, progress, safe-state checks, restart cancellation and confirmed restart. A real Play
test still needs a Play-owned install, matching app ID/signing identity, and a higher code
available to that tester. See https://developer.android.com/guide/playcore/in-app-updates/test.

Run the full offline suite smoke runner and import/menu regressions when those paths change.
The attached verification record distinguishes local checks from physical Huawei and real
Google Play acceptance; generating artifacts alone does not complete store submission.
