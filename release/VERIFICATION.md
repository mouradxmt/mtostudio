# Mtouaa Studio 0.4.1 — Mtouaa Labs publisher update

Verified 3 November 2026. App: **Mtouaa Studio**. Publisher: **Mtouaa Labs**.
Package `com.mtouaa.studio`, version code `6`, minimum API 26, target API 36, ARM64.
This is a release candidate; no store publication or AdMob activation has occurred.

## Fresh verification

- Signed AAB passed bundletool validation and JAR signature verification. Its upload
  certificate matches the APK generated from that exact bundle.
- The generated production APK is non-debuggable and uses the correct package/target SDK.
  All 13 native libraries passed 16 KB ELF alignment; APK alignment passed too.
- The exact-bundle APK passed all **18 offline integration checks** on disposable
  `emulator-5570`: all 15 editors and their document bridge, launcher entries,
  fullscreen/F11 and Play updater/privacy/support controls. Android 16/API 36,
  16 KB pages, 2560 × 1600 display; Google Play Services was disabled during the run.
- Native UI inspection confirmed “Published by Mtouaa Labs.” in the suite footer.
  Both release and Preview contain Mtouaa Labs in their bundled policy/notices,
  and retain Mtouaa Studio as the app name. The document bridge version follows code 6.
- All 15 pinned editor output hashes and branding checks passed. Editor files in the
  old and new AABs were compared directly with SHA-256 and are unchanged.
- Android lint: 0 errors, 1 intentional shared-shortcut-artwork warning.
- Preview was rebuilt and its packaged metadata checked. The new 18-check runtime run
  above applies to production; the earlier Preview runtime coverage is in the baseline.

Estimated compressed download: **344,419,729 bytes**.
Play Console determines the authoritative size after upload. Signing key unchanged.
Detailed new evidence is in `dist/Mtouaa-Studio-0.4.1-verification/`.

## Baseline and store assets

The unchanged editing engines retain the earlier six-menu PDF touch checks and Writer
DOCX typing/save/reopen coverage documented in `history/VERIFICATION-0.4.0.md` and
`dist/Mtouaa-Studio-0.4.0-verification/`. Those document/menu flows were not repeated for
this publisher-copy change. The six existing editor/home screenshots remain accurate
for the unchanged visible layouts; a fresh publisher-footer screenshot is in the new
verification folder. Original artwork and required author notices remain preserved.

## Monetization and remaining work

`ADMOB_PLAN.md` proposes a native home-screen banner with editing/saving independent
of ads. **No advertising SDK or ad placement is included in 0.4.1.** The listing's
long-term ad-free promise was removed, while the current privacy policy and Data safety
worksheet still describe this actual ad-free binary. An ad-enabled release needs its
own consent/privacy/disclosure updates, IDs, website verification and runtime testing.

A working support email and publicly hosted completed privacy policy are still missing.
The submission gate therefore remains closed. Publisher identity/audience declarations,
physical Huawei/file-format checks and applicable Play testing are still outstanding.
Browser edition limits, the 256 MB export limit and absence of suite-wide autosave remain
as documented in README.md. Do not treat startup checks as full format/codec validation.
