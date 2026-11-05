# Mtouaa Studio 0.6.0 — native update channels

Verified locally 5 November 2026. Publisher: **Mtouaa Labs**. Version code **9**.
Android 8.0/API 26 minimum, target API 36, ARM64. Packages:
`com.mtouaa.studio` (Play), `com.mtouaa.studio.huawei` (Huawei), and
`com.mtouaa.studio.preview` (development Preview).

## Changes and trust

The native Apps screen now offers optional update checks. Play uses the unmodified Google
Play In-App Updates 2.1.0 SDK and flexible delivery. Huawei uses public Mtouaa GitHub release
metadata signed with the existing RSA APK key; it checks package, increasing versionCode,
version name, canonical repository URL, APK length/hash and certificate before handing it
to Android's installer. The installer permission/FileProvider exists only in Huawei;
the Play APK neither requests it nor contains the Huawei updater classes. Both editions
keep external editor ZIP activation disabled. Installation/restart requires a safe Apps
state and an explicit save-work confirmation.

Signing certificate SHA-256:
`c4388b1fc99fe8bf576970455a0f4089bffe8d272583f53500a8f8eee6dd1576`.
All 15 reviewed editor source pins and compiled engines remain those of 0.5.0. Original
licenses, contributor records, fonts and dependency notices remain bundled. The visible
About notices now also identify the Play SDK and contain 674,779 bytes, below the 1 MiB limit.
The source pipeline's license inventory and branding/output hashes passed again.

## Executed checks

All device checks used only the disposable `mtouaa-play-16k` emulator on port 5570:
Android 16/API 36, ARM64, 16 KB pages, tablet landscape. User emulators were left untouched.

- **24 Huawei update checks:** Android RSA verification, tampering and wrong-key rejection,
  downgrade rejection, channel/package/URL checks, private provider, real signed future-APK
  parsing, corrupt-APK rejection, active-editor gate, save-work confirmation, FileProvider
  handoff to Android's package installer, and cancellation without changing the installed
  version. The tiny future fixture was never installed.
- **9 Play update checks:** production controller with Google's `FakeAppUpdateManager`;
  availability, flexible consent, progress/duplicate-download guard, active-editor gate,
  downloaded state, cancelled restart and explicit confirmed restart.
- **18 offline suite checks in Huawei:** all 15 editors started through their launcher
  shortcuts with Google Play Services disabled; fullscreen/F11, launcher registrations,
  packaged-engine enforcement, and offline privacy/support controls passed. Network and
  Google services were restored afterward.
- **26 host regressions** for bundle maintenance, license/rollback gates and branding,
  plus **7 JavaScript save-bridge tests**, passed.
- Signed Huawei/Play APKs and Play AAB built; lint reported no errors. Remaining warnings
  concern the intentionally pinned Gradle version and shared shortcut icon artwork.
- Final Play AAB passed bundletool validation and JAR signature verification. Its exact
  universal APK passed certificate, package, non-debuggable, 16 KB ZIP alignment and all
  13 native-library ELF alignment checks. Estimated compressed Play download: 354,504,405 bytes.
- Pinned CI tool URLs/checksums, CI source preparation, source lock stability, workflow
  YAML parsing and whitespace checks were validated locally.

The prior file-import/PDF-menu acceptance and full editor refresh are recorded in
`history/VERIFICATION-0.5.0.md`; those engine changes were not repeated in this release.

## Remaining external acceptance

Actual Google Play update delivery still needs a Play-owned installation and a higher
version available to that tester. No Google Play publication is claimed. Physical Huawei
acceptance, including that tablet's installation-permission UI, is still required.

GitHub source/build workflows are configured for `mouradxmt/mtostudio`. A clean hosted build
must pass before release publication. The publisher explicitly authorized transferring the existing signing credentials to
GitHub Actions, and the four encrypted repository secrets are configured. Hosted signing
and publication still require a successful tag workflow; local artifacts alone do not
prove that workflow passed.
The public Huawei update feed becomes available when a stable signed release is published.

AdMob remains planned, not installed. Support email, hosted privacy policy and the other
Play submission gates remain unfinished in `submission-status.json`.
