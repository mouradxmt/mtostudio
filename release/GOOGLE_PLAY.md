# Mtouaa Studio — Google Play preparation

App name: **Mtouaa Studio**. Publisher display brand: **Mtouaa Labs**.
Package: `com.mtouaa.studio`. Version: `0.4.1` / code `6`. ARM64, Android 8.0+,
target API 36. These settings do not establish the publisher's legal identity in Play Console.

## Prepared files

- `brand.json`: one source for public name, package, website, support email and privacy URL.
- `store/`: original 512 px icon, SVG mark/wordmark, listing text and privacy-policy draft.
- `store/screenshots/tablet-10-inch/`: six actual fullscreen tablet screenshots.
- `submission-status.json`: explicit external/physical-device tasks that are still outstanding.
- `DATA_SAFETY.md`: a worksheet to review, not a submitted declaration.
- `VERIFICATION.md`: actual release/Preview test results and remaining limitations.
- `ADMOB_PLAN.md`: proposed online monetization and the work required to enable ads.
- `../tools/play-source-lock.json`: exact upstream source commits and archive checksums.
- `../tools/prepare_play_sources.py`: reproducible source-level branding changes.

The Play edition contains independently rebuilt editors; it never substitutes the stock
ArtCraft-branded ZIPs. Required upstream copyright/licence notices remain. The app and each
editor's `mtouaa-build.json` record the source and modification provenance.

## Build

Use the workspace-isolated JDK 17 / Android SDK / Gradle toolchain and Rust 1.99.1 with
`wasm32-unknown-unknown`, Trunk 0.22.1 and wasm-bindgen 0.2.129. The optional open-font input
defaults to `storytold/craft-fonts` commit `b076417b5880bd4154bd22f00695b1d28c6bea83`.
Slides and Interface Design use `37827adc41fd165f9a9234ac40f94dbad353aa69`; Textures uses
`aced4137c022f1f587624d48e81ec77e1914a9cc`, as pinned by their release workflows. Font
archive hashes are in `build-tools.json`. Font licences remain with the editor notices.
The fetch script downloads and verifies all three pinned font archives along with the engines.

```sh
python3 tools/fetch_play_sources.py
python3 tools/prepare_play_sources.py
python3 tools/build_play_engines.py
python3 tools/prepare_play_metadata.py
python3 tools/check_play_release.py --assets-only
./tools/build.sh --offline bundlePlayRelease assemblePlayRelease assemblePlayReleaseAndroidTest assemblePlayPreview lintPlayRelease
python3 tools/verify_play_bundle.py
```

`tools/build_play_engines.py --app pdfcraft` rebuilds one editor. Do not change pinned source
revisions without reviewing/retesting the new sources and reapplying the independent branding.

Output AAB: `app/build/outputs/bundle/playRelease/app-play-release.aab`.
Output release APK: `app/build/outputs/apk/play/release/app-play-release.apk`.
Installable Preview: `app/build/outputs/apk/play/preview/app-play-preview.apk` (separate
`com.mtouaa.studio.preview` package). Use Preview for local trials; get the production-signed
test app from your Play Console testing track when testing future Play updates.
The Play AAB, rather than the previous debug APK, is the upload artifact.

## Signing and account ownership

An upload key is stored locally in `.release-secrets/mtouaa-upload.p12`; private Gradle
credentials are in `.release-secrets/upload.properties`. Both are excluded from source
control and readable only by the local user. Back them up securely outside the workspace.
Do not put their contents into chat, store assets, public repositories or build logs.
`tools/create_upload_key.py` creates a key only if none exists; it refuses to overwrite one.

Use your own Google Play developer account and enable Play App Signing when setting up the
app. This upload key is separate from the final app-signing key Google can manage. The new
package installs alongside the old `org.wordcraft.offline` prototype; it does not silently
replace that app or migrate unsaved projects. Export documents from the old app and import
them into the new one as needed.

## Before submission

1. Create an actual support mailbox (suggested: `support@mtouaa.com`) and put the working
   address into `brand.json`. It is deliberately empty until it exists.
2. Publish the completed privacy policy at `https://mtouaa.com/privacy/mtouaa-studio`, or
   change the configured URL to the real public page. The generated HTML is a file ready
   to host, not proof that the policy has been published.
3. Regenerate metadata and rebuild after changing the public contact/policy details.
4. Confirm your publisher identity, countries, price, intended audience, content rating,
   ads declaration, app-access instructions and Data safety answers in Play Console.
5. Run real-device import/edit/export/reopen tests for the document and media formats you
   plan to advertise. Emulator startup checks are not full format compatibility tests.
6. Upload to **Internal testing** and review Play's pre-launch report, device compatibility,
   compressed download size and policy messages.
7. Complete closed testing if your account requires it, then request production access.

Record only completed tasks as `true` in `submission-status.json`, then run:

```sh
python3 tools/check_play_release.py --submission
```

This gate is expected to fail while contact, hosting, real-device validation or Play account
tasks are unfinished. Do not upload the privacy draft with a placeholder contact address.

## AdMob monetization

AdMob is planned; version 0.4.1 does not include an advertising SDK or serve ads.
The public listing no longer promises an ad-free product indefinitely. The current
privacy policy and Data safety worksheet still describe the actual ad-free binary.
Before adding ads, follow `ADMOB_PLAN.md`, update the policy and Play declarations,
and test the ad-enabled build separately, including offline and Huawei behavior.

## Future upstream updates

The installed Play app receives updates through Google Play. A new GitHub release is an input
for a new publisher build; it is not installed directly into the Play edition.
Run `python3 tools/discover_suite.py` deliberately to refresh `suite-lock.json`, review the
changed versions, licences and release notes, then fetch their new immutable source pins.
For each changed editor, remove only its generated `.tools/play-work/<id>` directory before
preparing its new sources, so removed upstream files cannot survive from the previous tree.
Rebuild, repeat the release/device checks, increment Android `versionCode` and `versionName`,
and upload the new signed AAB to a testing track before production.
The metadata generator derives the bundled document-bridge extension version from
`versionCode`, so GeckoView refreshes that bridge when the Android app is updated.

## References checked 3 November 2026

- [Target API requirements](https://support.google.com/googleplay/android-developer/answer/11926878)
- [Play App Signing](https://developer.android.com/studio/publish/app-signing)
- [16 KB compatibility](https://developer.android.com/guide/practices/page-sizes)
- [User data and privacy policy](https://support.google.com/googleplay/android-developer/answer/10144311)
- [Testing for new personal accounts](https://support.google.com/googleplay/android-developer/answer/14151465)
- [External updates and interpreted code](https://support.google.com/googleplay/android-developer/answer/16559646)
