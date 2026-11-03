# Mtouaa Studio 0.4.2 — Android document imports

Verified 3 November 2026. App: **Mtouaa Studio**. Publisher: **Mtouaa Labs**.
Package `com.mtouaa.studio`, version code `7`, minimum API 26, target API 36, ARM64.
This is a release candidate; no store publication or AdMob activation has occurred.

## Import defect and fix

Version 0.4.1 was reproduced returning to PDF's welcome screen after selecting an
external PDF in Android Downloads. The pinned GeckoView file picker attempts to
convert document-provider URIs into filesystem paths; Downloads cannot be resolved
by that code, and an external-storage raw path can lose Android's URI read grant.
The observed error was `NS_ERROR_FILE_UNRECOGNIZED_PATH` / `Unrecognized path`.

The wrapper now streams selected files with `ContentResolver` into session-private
cache before confirming the Gecko prompt. Names and extensions are retained safely,
duplicate names remain separate, failed or cancelled copies are rolled back, and
session copies are removed after editor close or on the next launch. Importing never
changes the original. No broad storage permission or remote service was added.

## Fresh verification

- On Preview 0.4.2, selected a two-page external PDF through Android Downloads.
  The filename, both-page count and first-page test text rendered correctly.
  Cancelling another picker retained that open PDF.
- On Preview 0.4.2, selected an external DOCX through Android Downloads.
  Writer rendered both pages, the document title and the final test paragraph.
  Both fixtures were placed in Downloads outside this app, rather than exported by
  the installed app under test. The old own-export roundtrip had missed this defect.
- Seven provider regression checks passed on both Preview and the production APK
  generated from the exact signed AAB. A synthetic test-only provider has no `_data`
  column or usable filesystem path. Checks cover complete binary reads, Unicode
  names, Gecko's staged-path resolution, duplicate names, safe paths, cancellation,
  unavailable files, MIME fallback, rollback and cleanup without changing originals.
- The exact-bundle production APK passed all **18 offline integration checks**:
  all 15 editor startups and their document bridge, launcher entries, fullscreen/F11,
  and Play updater/privacy/support controls. Tests ran in airplane mode on disposable
  `emulator-5570`, Android 16/API 36, 16 KB pages, 2560 × 1600 display. Google Play
  Services was installed in this run; earlier no-GMS coverage is in the 0.4.1 report.
- Signed AAB passed bundletool validation and JAR signature verification; its upload
  certificate matches the generated APK. Package, target SDK and non-debuggable
  production configuration passed. All 13 native libraries and APK ZIP entries
  passed 16 KB alignment checks. The existing signing key is unchanged.
- Release and Preview builds completed. Android lint: 0 errors, 1 intentional
  shared-shortcut-artwork warning. The synthetic provider is confined to the test APK.

Estimated compressed download: **344,421,690 bytes**. Play Console determines the
authoritative size after upload. Detailed evidence and synthetic test files are in
`dist/Mtouaa-Studio-0.4.2-verification/`.

## Baseline and remaining work

Unchanged editor engines retain the earlier six-menu PDF touch checks and Writer
typing/save/reopen coverage in `history/VERIFICATION-0.4.0.md`. Publisher and earlier
no-GMS checks are in `history/VERIFICATION-0.4.1.md`. These startup/import checks do
not validate every file format, codec or document layout on a physical Huawei tablet.
Existing store screenshots remain applicable to the unchanged editor layouts.

No advertising SDK or ad placement is included in 0.4.2. `ADMOB_PLAN.md` describes
future work; an ad-enabled build requires its own consent/privacy/disclosure updates.
A working support mailbox, publicly hosted completed privacy policy, publisher and
audience declarations, physical-device checks and applicable Play testing remain
outstanding. The submission gate stays closed. Browser-edition limits, the 256 MB
export limit and absence of suite-wide autosave remain documented in README.md.
