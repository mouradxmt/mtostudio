# Mtouaa Studio 0.7.0 — editor refresh

Release preparation: 12 November 2026. Publisher: **Mtouaa Labs**.
Version code **11**, Android 8/API 26 minimum, target API 36, ARM64.
Packages and signing key remain unchanged from 0.6.1.

## Source and license inputs

All 15 stable upstream releases were discovered from GitHub on 12 November 2026.
Exact versions, source commits and archive hashes are recorded in `tools/suite-lock.json`
and `tools/play-source-lock.json`; README.md and RELEASE_NOTES.md list the versions.
Each editor is rebuilt from source with original Mtouaa artwork and display branding.
Android, GeckoView and the build tools remain pinned; Cargo uses upstream locked versions.

The changed-input review is in `editor-update-review.json`. All 15 top-level MIT and
Apache-2.0 license texts match the previous reviewed release. New dependency archives
were verified against Cargo.lock checksums, and new Git dependencies were inspected at
exact immutable revisions. Original notices, contributor credits, font terms and asset
attribution remain bundled; added license and attribution texts are in
`dependency-notices.txt`. The objc2-io-kit archive omits its license; the same exact upstream
VCS license retained for objc2-core-text supplies that notice.

All 18 embedded language-data paths in the reviewed craft-proof revisions have one
Embeddable attribution row at each of the three new craft-i18n pins. No GPL/AGPL/LGPL or
CC-BY-SA dictionary data is embedded. Optional language-pack downloads are unavailable in
the web backend. Font archives remain at each upstream release's pinned commit.
Vectors reports optional Arabic font families absent from its pinned archive; these
additional families are not bundled. This is changed-input/notice verification, not a
comprehensive legal or security audit.

## Executed verification

- Passed 35 host regression tests and 7 JavaScript save-bridge tests.
- All 15 source engines compiled and passed output hashes and protected-brand scanning.
- Built signed Huawei/Play release APKs and the Play AAB; Android lint has zero errors
  and one intentional shared-shortcut-icon warning in each edition.
- On only the disposable `mtouaa-play-16k` emulator (5570), Android 16/API 36, ARM64,
  16 KB pages, 2560 × 1600: **18 offline suite checks** passed with Google Play Services
  disabled, including all 15 editor shortcuts/startup, fullscreen/F11, packaged-engine
  enforcement, privacy and support.
- **6 PDF touch-menu checks**, **7 document-provider import checks**, **18 Huawei
  update-security checks**, and **9 Play update-controller checks** passed. The Play
  tests use Google's FakeAppUpdateManager; they do not claim actual Play delivery.
- In airplane mode, PDF 0.21.1 loaded the external two-page PDF selected in Android's
  real file picker. Cancelling another selection retained the document. Writer 0.18.1
  loaded the external DOCX, rendered both pages and its final test paragraph. Original
  Downloads file SHA-256 hashes match the synthetic fixture originals. Missing Aptos
  family fonts use the editor's fallback; proprietary font files are not bundled.
- The exact signed Play AAB passed bundletool and JAR-signature validation. Its generated
  universal APK passed package, target SDK, non-debuggable, signing-certificate and
  16 KB ZIP checks. All **13 native libraries** passed ELF 16 KB alignment checks.
- Estimated compressed Play download: **381,724,390 bytes**; Play Console determines
  final delivery size. Native About contains **902,987 bytes**, below its 1 MiB limit.
- Signing certificate SHA-256:
  `c4388b1fc99fe8bf576970455a0f4089bffe8d272583f53500a8f8eee6dd1576`.
- Device logs, synthetic-import screenshots and bundle verification evidence are saved
  locally in `dist/Mtouaa-Studio-0.7.0-verification/`. Other emulators were untouched.
  The Huawei public descriptor will be checked after the release is published.

## Delivery and remaining external work

Builds run locally using existing caches. GitHub Actions workflows remain disabled;
no cloud build or Actions artifact storage is used. Final release files are uploaded
straight to GitHub Releases. The Huawei updater uses the existing app-signing key and
Android's installation confirmation; the Play package uses Play delivery only.

Physical Huawei acceptance, actual Google Play delivery, full editing/export/format and
codec coverage remain separate tasks. Play publication is not claimed. Support contact,
hosted privacy policy and publisher declarations remain pending. AdMob is not included.
Historical 0.6.1 update-channel and public-upgrade acceptance is retained in
`history/VERIFICATION-0.6.1.md` and `ACCEPTANCE-0.6.1.md`.
