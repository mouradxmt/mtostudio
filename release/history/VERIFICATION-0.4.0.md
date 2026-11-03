# Mtouaa Studio 0.4.0 — release candidate verification

Verified 3 November 2026. This is a prepared release candidate, not a published or
Google-approved app. Public package: `com.mtouaa.studio`, version code `5`, ARM64,
minimum Android API 26, target API 36. Preview uses `com.mtouaa.studio.preview`.

## Completed checks

| Check | Result |
| --- | --- |
| Editor source builds | All 15 independently rebuilt from pinned source commits. |
| Branding and provenance | Complete output hashes verified; compiled WASM and web interface files scanned for upstream branding. Required author/copyright credits retained. |
| AAB | Bundletool validation and JAR signature verification passed. Upload certificate matches the APK generated from that bundle. |
| Production APK | Generated from the exact delivered AAB, signed, non-debuggable; correct public package and target SDK. |
| Native compatibility | All 13 native libraries have 16 KB ELF load alignment; APK alignment check passed. |
| Release integration | 18 checks passed: 16 launcher entries, fullscreen/F11, all 15 offline editor startups with a responsive document bridge, and Play updater/privacy/support controls. |
| PDF touch menus | All 6 menus open, remain open after touch release and close on the second tap. Full File menu visually reviewed. |
| Preview integration | Its own 18 checks passed, including the separate local bridge port. |
| Writer document flow | Typed into a bundled sample, exported DOCX through Android's picker, validated ZIP/XML and the new sentence, then reopened it through Android's picker and saw the saved sentence. |
| Automated helpers | 7 save-bridge tests, 8 release-gate tests, 3 Rust string-rewriter regression tests and 23 archive/version checks passed. |
| Android lint | 0 errors, 1 intentional warning for the shared Mtouaa shortcut artwork. |
| Store graphics | Full-square 512 × 512 icon, 1024 × 500 RGB feature graphic and six genuine 2560 × 1600 tablet screenshots. Screenshots exported as 24-bit RGB without changing pixel colours. |

The device checks used only disposable `emulator-5570`: Android 16/API 36, ARM64,
16,384-byte memory pages, 2560 × 1600 display at density 320. Google Play Services
was disabled and airplane mode enabled during the offline runs and Writer file check.
The existing user emulators were not stopped, replaced or navigated.

Bundletool estimates a compressed download of **344,419,660 bytes** (344.4 MB), below
the current [500 MB base-module limit](https://support.google.com/googleplay/android-developer/answer/9859372).
Play Console calculates the authoritative download size after upload.

Detailed evidence is in `dist/Mtouaa-Studio-0.4.0-verification/`, including the bundle
fingerprint, test results, actual editor/menu screenshots and the exported test DOCX.
Artifact SHA-256 sidecar files accompany the AAB and Preview APK.

## Remaining publication work

The submission gate correctly fails because a working support email has not been
configured. `support@mtouaa.com` is a suggestion; no mailbox was created or verified.
The privacy policy is a local draft with an explicit contact placeholder and has not
been published on the domain. Complete it before hosting or submission, regenerate
metadata and rebuild the candidate when those details are available.

The publisher must also finish Play account/identity and audience declarations,
review the Data safety worksheet, test real file import/edit/export/reopen workflows
on the intended devices, and complete applicable Play testing and pre-launch review.
The Huawei MatePad itself has not been tested in this workspace.

Startup checks do not establish complete codec, format or desktop-feature coverage.
Textures displayed its WebGL2 fallback; Photo Library displayed a browser-storage
persistence warning. Export and keep backups of documents/catalogues. The wrapper's
export limit is 256 MB, and it does not add a suite-wide autosave. Browser imports can
require saving a new copy instead of retaining a writable handle to the original file.

The local upload key and private signing configuration are intentionally excluded
from public artifacts. Back them up securely as described in `GOOGLE_PLAY.md`.
