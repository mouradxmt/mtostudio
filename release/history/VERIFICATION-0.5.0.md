# Mtouaa Studio 0.5.0 — all 15 editors refreshed

Verified 3 November 2026. App: **Mtouaa Studio**. Publisher: **Mtouaa Labs**.
Package `com.mtouaa.studio`, version code `8`, minimum API 26, target API 36, ARM64.
Preview: `com.mtouaa.studio.preview`, version `0.5.0-preview`.
This is a release candidate; no store publication or AdMob activation has occurred.

## Updated source and license inputs

All 15 editors were updated to the stable GitHub releases discovered during this run,
then rebuilt from immutable source commits with the independent branding recipe.
Versions are listed in README.md; source/archive hashes are in the two tools lockfiles.
The Gradle updater completed successfully, including all output-hash and branding checks.

Changed attribution, contributor records and dependency inputs were reviewed before
updating the license baseline. Top-level editor MIT OR Apache-2.0 texts are unchanged.
Original legal documents and font notices are retained alongside modified-artwork
attribution. Additional MIT/Apache/BSD, Unicode and CDLA notices are recorded in
`dependency-notices.txt`; provenance and review scope are in `editor-update-review.json`.
The combined native About notice is 674,137 bytes, below its 1 MiB reader limit.

Writer's pinned craft-i18n input was added to the source pipeline so interface translations,
spelling dictionaries and hyphenation data remain packaged offline. Its archive hash is
in `build-tools.json`. Interface branding changes use a private source copy; dictionary
files stay unchanged. All 21 embedded language-data files passed the attribution/class
check (one Embeddable entry each; no GPL/AGPL/LGPL or CC-BY-SA dictionary data).
This is input/notice verification, not a comprehensive legal or source-security audit.

## Fresh verification

- All 15 independently branded Rust/WASM editors compiled successfully.
- **14 updater regression tests**, **8 release-guard tests** and **3 branding-lexer tests** passed.
- Production APK generated from the exact signed AAB passed **31 device checks**:
  seven document-provider import checks, 18 offline suite/shortcut/bridge/fullscreen/Play
  controls checks, and six PDF touch-menu checks (File, Edit, View, Sign, Window, Help).
- Device: disposable `emulator-5570`, Android 16/API 36, 16 KB pages, 2560 × 1600.
  Google Play Services was disabled. The suite/menu runs enabled airplane mode.
- The new Preview was installed over the existing Preview on that disposable emulator.
  In airplane mode, PDF 0.18.0 loaded an external two-page PDF from Android Downloads;
  cancelling another selection retained it. Writer 0.15.0 loaded the external DOCX,
  rendered both pages and its final test paragraph. Original Downloads file hashes
  remained unchanged. These were synthetic files placed outside this app.
- Signed AAB passed bundletool and JAR-signature verification. Its certificate matches
  the generated APK. Production package/target SDK/non-debuggable checks passed.
  All 13 native libraries and APK ZIP alignment passed 16 KB checks. Signing key unchanged.
- Release and Preview builds and lint completed: 0 errors, 1 intentional shared-icon warning.
- Packaged Preview editor/legal files were compared with their build-manifest hashes;
  aggregate notices match the source asset exactly. Hidden build-cache files are excluded.

Estimated compressed Play download: **354,485,505 bytes**. Play Console determines the
final download size after upload. Evidence and screenshots are under
`dist/Mtouaa-Studio-0.5.0-verification/`. Your running emulators 5554 and 5560 were not
reinstalled, stopped or navigated during this work.

## Remaining release work

No ad SDK is included; AdMob remains a separate planned change. Support mailbox, public
completed privacy policy, publisher/audience declarations, physical Huawei acceptance,
full file-format/edit/export coverage and applicable Play testing remain outstanding.
The submission gate stays closed. Existing store screenshots predate this engine refresh
and should be refreshed before a store submission. Earlier verification reports are in
`history/`; they describe those older binaries, including prior Writer export coverage.
Browser-edition limitations, the 256 MB export limit and lack of suite-wide autosave remain
in README.md. These checks do not validate every document layout, format or codec.
