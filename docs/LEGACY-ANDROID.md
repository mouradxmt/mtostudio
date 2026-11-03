# ArtCraft Offline for Android

An independent Android port of the complete 15-app [ArtCraft suite](https://getartcraft.com/apps).
Every official web package is included in the APK and runs locally, including on first launch
with airplane mode enabled. No account is required. The default build includes Mozilla GeckoView 159, so it needs no
Google Play Services or system WebView update. It targets ARM64 devices with Android APK
support, including compatible HarmonyOS versions on the Huawei MatePad 11.5. The Android
minimum is 8.0; device graphics support and upstream app capabilities still apply. A physical
MatePad has not been tested. HarmonyOS editions without Android APK support need a different
native package and cannot run this APK.

## Included apps

| App | Bundled version | Purpose |
| --- | --- | --- |
| PhotoCraft | 0.19.0 | Photo and image editing |
| VectorCraft | 0.20.0 | Vector illustration |
| FilmCraft | 0.16.0 | Video editing |
| LightCraft | 0.17.0 | Photo library and RAW development |
| PdfCraft | 0.17.0 | PDF editing and organization |
| EffectCraft | 0.20.0 | Motion graphics and visual effects |
| DesignCraft | 0.16.0 | Page layout and publishing |
| FigCraft | 0.14.0 | Interface design and prototyping |
| TextureCraft | 0.2.0 | 3D texture painting |
| WordCraft | 0.14.0 | Writing and document design |
| SoundCraft | 0.16.0 | Audio editing and mixing |
| DeckCraft | 0.14.1 | Presentations and slides |
| CADCraft | 0.16.0 | Computer-aided design |
| GridCraft | 0.15.0 | Spreadsheets and data analysis |
| Craft Anything | 0.2.0 | Software exploration and creation |

The Huawei-oriented APK is approximately 342 MB because it includes the entire suite and
its browser engine. Apps load one at a time. Each app has its own local origin on a loopback
asset server, so preferences and browser databases do not collide across apps. The server is
bound to 127.0.0.1 and serves public engine assets only, never user documents. The original package ID `org.wordcraft.offline` is retained to allow
upgrading the earlier WordCraft-only APK; the visible name is now **ArtCraft Offline**.

## Tablet view, fullscreen and app shortcuts

The `artcraft-tablet` virtual device uses a wide **2560 × 1600** display. Its emulator window
can be resized by dragging its edges; the tablet aspect ratio is preserved. The earlier phone
virtual device is retained separately.

Inside Android, tap **Full screen** in the suite or an editor to hide Android's system bars.
Tap **Exit full screen**, press **F11**, or press **Ctrl+Alt+F** to toggle back. This controls the
Android display, rather than macOS's desktop fullscreen state. The toolbar remains available
for switching apps safely. Fullscreen mode persists between launches.

The APK now registers the suite icon plus **15 individual app icons** in Android's app drawer.
To put an editor on the tablet's home screen, tap **Add to Home** beside it in the suite and
confirm the launcher dialog. If that launcher does not support pin requests, drag the editor's
icon from the app drawer onto the home screen. Each shortcut opens its selected editor directly.
Switching to a different editor asks you to save active work first. All icons belong to one
installed suite package.

The icons are unmodified upstream assets; source and license attribution is preserved in
`app/src/main/assets/APP_ICON_ATTRIBUTION.md`.

Verified on the landscape Android 15 tablet emulator: **21 integration checks passed**, including
all 15 direct app-icon launches offline, registration of all 16 launcher entries, actual status-bar
hiding/restoration through the fullscreen button and F11, and the existing verified update flow.

## GitHub updates

- Open the launcher and tap **Check GitHub updates**. It checks the latest stable release of
  each official `storytold/<app>` repository. Available versions appear on their app cards.
- Tap **Update** for one app or **Update all**. A successful install is available offline afterward.
- **Check daily when the launcher opens online** is enabled by default and can be turned off.
  Checks run in the background while installed apps remain available. Nothing downloads until
  you choose an update. Checks do not run while the Android app is closed.
- Downloads must have a GitHub-provided SHA-256 digest and the expected official repository
  URL. Only HTTPS connections to GitHub and its release asset hosts are allowed. Package size,
  expanded size, file count and archive paths are checked before activation.
- Updates extract into a separate staging folder. The active package pointer changes only
  after successful extraction and a synchronous preference commit. A failed download, bad
  checksum or failed extraction leaves the current version active. Older downloaded versions
  are removed after successful replacement; bundled versions remain inside the APK.
- **Use bundled <version>** restores that app's original bundled version. Saved documents are
  outside the package folders. Shared browser storage is retained across engine updates and
  may follow the upstream app's own version compatibility rules.
- GitHub's public unauthenticated API limits apply. Failed checks show a status message and
  can be retried later; offline editing continues.

These are updates to the suite's **web engines**, not updates to the Android wrapper itself.
Changes to native Android integration still require a new APK. There is no wrapper release
repository or APK self-update endpoint configured in this workspace.

The app requests Internet and network-state permissions for the native updater. Editor
sessions use an app-owned built-in extension to restrict HTTP resources to the loopback asset
server, and navigation delegates block remote pages.
The updater sends no document contents to GitHub.

## Opening, saving and switching apps

Choose an app from the launcher. Its **File → Open / Import** uses Android's local document
picker. **Save / Save As / Export** opens a destination picker. The top **Apps** button returns
to the launcher after a reminder to save your work. Rotation keeps the active editor running.

For engines using `showSaveFilePicker`, a save is acknowledged only after the destination
stream closes; cancellation and write failures propagate back to the engine. Legacy blob
exports are also routed to Android's save picker and queued one at a time. Legacy engines may
mark a document saved before their asynchronous blob export completes; heed any save error
and verify the output before closing. Files are transferred in bounded chunks with a 256 MB
save limit. No broad storage permissions are requested.

## Build and maintain

Install JDK 17, Android SDK platform **37.0** and build-tools **36.0.0**, then set `JAVA_HOME`
and `ANDROID_HOME`. The project pins Android Gradle Plugin 9.1.1 and Gradle 9.3.1:

```sh
./tools/build.sh
```

The script prepares the pinned web packages, builds the APK and runs Android lint. On the
workspace used to create this port, it automatically reuses isolated tools under `.tools/`.
For Android Studio or direct Gradle usage:

```sh
python3 tools/prepare_suite.py
./gradlew assembleDebug lintDebug
```

The APK is `app/build/outputs/apk/debug/app-debug.apk`. The deliverable copy is
`dist/ArtCraft-Offline-0.3.1-Huawei-arm64-debug.apk`. Install it over the earlier WordCraft-only build, or use
`adb install -r <apk>`. Debug builds use a development signing key; release signing is not
configured. A production release needs its own stable signing key.

`tools/suite-lock.json` pins all official package URLs, versions, sizes and SHA-256 digests.
`tools/prepare_suite.py` downloads and verifies those packages, preserves upstream notices,
removes redundant precompressed files for Android packaging, and injects the shared native
save adapter before each engine starts. It never rebuilds or modifies the WASM engines.
`tools/prepare_editor.py` remains as a compatibility entry point.

To deliberately refresh the bundled baseline from official GitHub releases:

```sh
python3 tools/discover_suite.py
# Review tools/suite-lock.json, then rebuild.
./tools/build.sh
```

Updating an engine from the Android launcher does not change this source lockfile. New apps
added to the upstream suite require adding a reviewed catalog entry and rebuilding the wrapper.

## Verification

```sh
node --test tools/test_save_bridge.mjs
./tools/test_packages.sh
./tools/build.sh assembleDebug assembleDebugAndroidTest lintDebug
```

Seven save-adapter tests cover the native channel handshake, binary chunks, acknowledgement timing, cancellation, disk errors,
legacy blob exports and ordinary links. Package tests cover numeric stable versions, checksum
failures, path traversal, missing/ambiguous entry points, intact previous versions and extraction
of all 15 real official releases.

Verified on 2026-11-02: all 15 apps started with airplane mode enabled using the bundled
Gecko runtime on an ARM64 Android 15 emulator. All **19 Android integration checks** passed,
including real GitHub discovery/download/activation, checksum rejection, bundled fallback,
and relaunching the fallback offline. Seven save-adapter tests and 23 package/version checks
also pass. Android lint has zero errors and one tool-version reminder. Screenshots and the
Android test result are saved under `dist/`. These are startup/update tests, not a full
document-editing or media-export acceptance suite.

The device integration runner is `org.wordcraft.offline.SuiteSmokeInstrumentation`. Run it only
on a disposable Android emulator: it toggles airplane mode, launches all apps, performs a real
GitHub update using a simulated older version, checks rejection of a bad checksum, and tests
bundled fallback. Screenshots go to the target app's private `files/smoke-results` directory.

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb install -r app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb shell am instrument -w org.wordcraft.offline.test/org.wordcraft.offline.SuiteSmokeInstrumentation
```

## Huawei runtime choice

Earlier testing with the emulator's original Chromium WebView 124 exposed a 4096-pixel WebGL
texture cap; several engines request 8192. Chromium later raised that cap on newer Android
versions. All 15 engines passed with a current WebView, but relying on a system-provider
upgrade is unsuitable for many Huawei installations. The default APK therefore includes its
own Firefox/Gecko runtime. This was also tested offline with all 15 engines.

The earlier system-WebView implementation is retained as an internal diagnostic fallback;
the default launcher uses Gecko. Its old APK is under `dist/ArtCraft-Offline-0.2.0-webview-debug.apk`
and requires a compatible current system runtime. Use the Huawei-oriented APK for this task.

Gecko's Android integration uses a built-in WebExtension with session, top-frame and origin
validation for the file bridge. The shared save adapter and legacy blob download adapter are
served before each engine starts. A compatibility alias also repairs PhotoCraft 0.19's misplaced
relative snippet import, without altering its generated JavaScript or WASM bytes.

Version 0.3.1 also filters duplicate finger PointerEvents on the editor canvas. The bundled
eframe builds process both PointerEvents and TouchEvents; on Android a single tap could
therefore open and immediately close PdfCraft's menu. The original TouchEvent path remains
responsible for finger input, including drag, multi-touch and cancellation. Mouse and pen
PointerEvents, keyboard input and native Android controls are unaffected.

The dedicated menu regression mode runs offline on the 2560 × 1600 tablet test AVD. It checks
all six PdfCraft menu titles: a tap must leave the rendered dropdown open after release, and
a second tap must close it. Run only on a disposable emulator; it opens PdfCraft and changes
test preferences:

```sh
adb -s emulator-5570 shell am instrument -w -e menusOnly true org.wordcraft.offline.test/org.wordcraft.offline.SuiteSmokeInstrumentation
```

## Limits and device checks

The upstream web apps have desktop-style interfaces and do not expose every desktop feature.
For example, SoundCraft's web build has playback but no recording or device routing. Each
engine retains its upstream format, codec and browser limitations. Direct PDF printing,
native sharing, opening attachments from other apps, and directory-picker APIs are not
integrated. Fonts and preferences persist only where the individual web engine supports them.

There is no wrapper-wide background autosave. Some engines have their own browser recovery,
but save explicitly before switching apps, leaving Android, or installing an engine update.
Unsaved work may be lost if Android terminates the app. Phone layout, touch selection, soft
keyboard/IME, document round-trips, large media files and graphics performance still require
physical phone/tablet acceptance testing. An engine starting successfully does not prove
full editing/export compatibility.

## Licensing

This is an independent Android port, not an official ArtCraft Android release. Each bundled
engine retains its upstream license, NOTICE, ATTRIBUTION and font licenses within its package.
Original source and release links are recorded in the lockfile. Mozilla GeckoView is included
unmodified under MPL 2.0 and applicable third-party licenses. **About & licenses** in the launcher
provides license/source notices. The exact runtime source revision is
[5add844c26613d7e4d84c799d6e23cf987b1240d](https://hg.mozilla.org/releases/mozilla-release/rev/5add844c26613d7e4d84c799d6e23cf987b1240d). Android integration follows
[Android's local content guidance](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content)
and the [Storage Access Framework](https://developer.android.com/training/data-storage/shared/documents-files).
