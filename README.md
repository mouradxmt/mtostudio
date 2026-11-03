# Mtouaa Studio for Android

Mtouaa Studio is an independently branded offline creative suite for ARM64 Android tablets
and phones. The Google Play edition packages 15 editors built from pinned open-source
releases. Documents are processed locally, and no account is required.

The public package is `com.mtouaa.studio`; the release candidate is version `0.4.1` (code 6),
targeting Android API 36 with Android 8.0 as the minimum. The bundled Mozilla GeckoView
runtime avoids dependence on Google Play Services or a separately installed system WebView.
All editors are packaged for first-launch offline use.

## Google Play edition

The app is **Mtouaa Studio**, published by **Mtouaa Labs**, using the publisher's `mtouaa.com` domain. Its
original geometric M artwork replaces upstream protected marks and editor shortcut artwork.
The source builds also change editor display names and publisher links. Copyright, contributor
and required licence notices remain credited separately; this is not an official upstream or
Mozilla product.

| Tool | Upstream source |
| --- | --- |
| Photos | PhotoCraft 0.19.0 |
| Vectors | VectorCraft 0.20.0 |
| Video | FilmCraft 0.16.0 |
| Photo Library | LightCraft 0.17.0 |
| PDF | PdfCraft 0.17.0 |
| Motion | EffectCraft 0.20.0 |
| Layouts | DesignCraft 0.16.0 |
| Interface Design | FigCraft 0.14.0 |
| Textures | TextureCraft 0.2.0 |
| Writer | WordCraft 0.14.0 |
| Audio | SoundCraft 0.16.0 |
| Slides | DeckCraft 0.14.1 |
| CAD | CADCraft 0.16.0 |
| Sheets | GridCraft 0.15.0 |
| Explorer | Craft Anything 0.2.0 |

The Play flavor disables the GitHub engine updater, including its check/install APIs and
activation of downloaded packs. New reviewed versions are distributed through Google Play.
Editors cannot fetch remote HTTP resources. Publisher links opened by the user are handed
to the user's browser; they never replace the local editor page or acquire its document bridge.

The Play package can coexist with the earlier `org.wordcraft.offline` prototype. It uses a
separate loopback port, profile and Android data directory. Export documents from the old app
before importing them into the new one; it does not migrate unsaved work.

## Release files and remaining publisher tasks

See [Google Play preparation](release/GOOGLE_PLAY.md) for build, signing, metadata and
submission steps. Public branding is configured in [release/brand.json](release/brand.json).
Store artwork, listing text and a privacy-policy draft are in [release/store](release/store/).
The support email is intentionally unset until a real mailbox exists. The privacy HTML has
been prepared as a local file; it has not been published on the domain.

AdMob is planned for online monetization; the current candidate has no ad SDK. The
[AdMob plan](release/ADMOB_PLAN.md) recommends one native banner on the suite home screen,
with editing and saving available offline and independent of ads or consent-network errors.

A release-build success does not complete account verification, physical-device acceptance,
Play testing, Data safety declarations or Google's review. These are tracked explicitly in
[release/submission-status.json](release/submission-status.json). The submission gate refuses
to report readiness while they remain unfinished.

## Building

The workspace uses JDK 17, Android SDK platform 37.0, build-tools 36.0.0, AGP 9.1.1 and
Gradle 9.3.1. The editor pipeline uses Rust/WASM, Trunk and wasm-bindgen; exact build tools
are recorded in [release/build-tools.json](release/build-tools.json).

```sh
python3 tools/fetch_play_sources.py
python3 tools/prepare_play_sources.py
python3 tools/build_play_engines.py
python3 tools/prepare_play_metadata.py
python3 tools/create_store_graphic.py
python3 tools/check_play_release.py --assets-only
./tools/build.sh --offline bundlePlayRelease assemblePlayRelease assemblePlayReleaseAndroidTest assemblePlayPreview lintPlayRelease
python3 tools/verify_play_bundle.py
```

Source archives are verified against `tools/play-source-lock.json`. Each output editor
contains a source/patch/output-hash manifest. Android builds refuse incomplete or stock
branded Play assets. `--app pdfcraft` limits the source/engine scripts to one editor. Existing
matching builds are reused; `--force` rebuilds them, and `--stage-only` refreshes packaging
from already compiled outputs.

The upload key/config live in ignored `.release-secrets/`, never in source control or store
assets. Run `tools/create_upload_key.py` once if none exists, and back up the resulting files
securely. The script refuses to overwrite an existing key. Release builds use this key when
configured; Play App Signing manages the distribution signing key through your own account.

The `sideload` flavor preserves the old engine/update implementation for internal comparison.
It is not the independently rebuilt Play edition. Historical prototype documentation is in
[docs/LEGACY-ANDROID.md](docs/LEGACY-ANDROID.md); its old APKs remain in `dist/`.

## Verification

Release candidate results, exact test conditions and remaining publication work are in
[release/VERIFICATION.md](release/VERIFICATION.md).

```sh
node --test tools/test_save_bridge.mjs
python3 tools/test_play_release.py
./tools/test_packages.sh
```

The Android device runner exercises all 15 offline editor shortcuts, the native bridge,
fullscreen controls and the Play edition's disabled updater/privacy/support controls. Use a
disposable tablet emulator, never an emulator holding an open user project:

```sh
adb -s emulator-5570 shell am instrument -w com.mtouaa.studio.test/org.wordcraft.offline.SuiteSmokeInstrumentation
adb -s emulator-5570 shell am instrument -w -e menusOnly true com.mtouaa.studio.test/org.wordcraft.offline.SuiteSmokeInstrumentation
```

To test the separately packaged Preview, build its matching runner with
`./tools/build.sh --offline -PtestBuildType=preview assemblePlayPreviewAndroidTest` and
use `com.mtouaa.studio.preview.test` as the instrumentation package.

The menu regression checks that each PDF dropdown stays open after touch release and closes
on the second tap. The shared adapter filters duplicate finger PointerEvents from the bundled
eframe touch path while keeping original touch/drag/multi-touch handling, mouse and pen input.

## Files, offline behavior and limits

Android's document picker handles opening and exports, without broad storage permissions.
The native save bridge stages writes and acknowledges completion only after closing the
destination stream. Exports are transferred in bounded chunks with a 256 MB limit. Some
legacy engines mark blob exports saved before Android finishes its asynchronous picker;
verify the saved output before closing the document.

There is no wrapper-wide autosave. Save before switching tools, leaving Android or applying
an update. Android can terminate an app and lose unsaved work. The editors have desktop-style
interfaces; a larger screen and keyboard are recommended. Browser editions retain their
upstream limitations, and starting an editor does not prove complete editing, codec or
file-format compatibility. Native sharing, direct PDF printing, folder pickers, audio
recording and opening attachments from other apps are not integrated.

## Open-source credits

The editor projects originate from the [ArtCraft open-source projects](https://github.com/storytold).
Their exact repositories/versions are in `tools/suite-lock.json`, with source commits and
archive hashes in `tools/play-source-lock.json`. Required notices are bundled with each
editor. Original upstream marks are replaced in the Play edition.

Unmodified Mozilla GeckoView 159.0.20261022150525 is included under MPL 2.0 and its third-party
licences. Corresponding source is linked in the in-app notices at immutable revision
`5add844c26613d7e4d84c799d6e23cf987b1240d`. See the Play edition's
[third-party notices](app/src/play/assets/THIRD_PARTY_NOTICES.txt) and
[original artwork attribution](app/src/play/assets/APP_ICON_ATTRIBUTION.md).
