# Updating the bundled editors

Run this explicit maintenance task from the project root with JDK 17 and the existing
Rust/WASM build prerequisites installed:

```sh
./gradlew updateBundledApps
```

On this workspace, `./tools/build.sh updateBundledApps` selects the local JDK, Android
SDK and Gradle cache for you. Omit `--offline`: release discovery and downloads need
network access. If GitHub rate-limits requests, set `GITHUB_TOKEN` in the process
environment using your normal secret manager. Public-repository read access is enough;
do not put tokens in Gradle properties, command-line arguments or committed files.

To check versions without changing locks or assets:

```sh
./gradlew checkBundledUpdates
```

## Scope and behavior

The task updates **all 15 existing editors** to their upstream GitHub `releases/latest`
stable release and uses each release's pinned font, translation and dictionary inputs. It rejects prereleases,
downgrades, missing/ambiguous web archives, absent SHA-256 release digests and moved
release tags. A missing web build stops the update; an editor is never silently dropped.
It resolves annotated tags to immutable commits and hashes downloaded source archives.
New source archives are pinned on first download; unchanged sources must match their
existing hash. Hashes provide integrity/repeatability, not independent publisher identity
verification or a security audit.

The Android app, GeckoView, AndroidX, Gradle/AGP, Rust, Trunk, wasm-bindgen and other build
tools stay pinned. The editors' Cargo dependencies stay at their upstream lockfile
versions (`--locked`). Upgrading these independently to arbitrary latest versions could
break the engines or require new licensing/source-delivery work. New upstream toolchain
requirements stop the build and need a separate reviewed toolchain change.

Work happens in `.tools/bundled-update/workspace/`. Shared immutable downloads and compiler
caches reduce repeated downloads/builds; current locks, engine assets and source trees are
replaced only after every editor passes source compilation, output hashes and branding checks.
Unchanged verified engine builds can be reused. Ordinary promotion failures and interrupts
roll back all replaced paths. The previous successful inputs/outputs remain under
`.tools/bundled-update/previous/`; hard termination/power loss during file replacement may
need manual recovery from that folder. Avoid running another Android build or maintenance
process while updating. App tasks in the same Gradle invocation run after the updater.

Results and errors are recorded in `.tools/bundled-update/report.json`. This task builds
editor assets; it does not install, sign, publish, commit, or declare a release tested.

## License and attribution review

`tools/bundled-license-policy.json` records the existing pinned release's license,
attribution, contributor, dependency-manifest/lock and font/build-input hashes. It is a
baseline for detecting changes, not a declaration that every future dependency is permitted.

If any recorded input changes, or a new legal/font input appears, the task stops before
building or replacing the current bundle. It writes:

- `.tools/bundled-update/report.json`: changed input names and candidate commits/versions.
- `.tools/bundled-update/candidate-license-policy.json`: candidate input hashes.
- `.tools/bundled-update/workspace/vendor/sources/`: exact candidate sources and legal files.

Review the changed files against the current sources. Check dependency/asset/font license
terms, notices, copyright and reserved font names, distribution requirements, and any
required corresponding-source delivery. Review new Cargo dependencies even when upstream
notice files did not change. Update the notice implementation or source-delivery process
when required. The existing pipeline supports the current `MIT OR Apache-2.0` engine
license; a different top-level engine license stops and needs an implementation review.

After reviewing and accepting those **exact inputs**, record the new baseline:

```sh
cp .tools/bundled-update/candidate-license-policy.json tools/bundled-license-policy.json
./gradlew updateBundledApps
```

Do not copy the candidate file just to bypass a failed check. The rerun rediscovers releases
and rechecks hashes; a newer or changed input requires another review. There is no blanket
ignore-license switch.

To continue the exact already-discovered snapshot after review, use
`./gradlew -PresumeBundledUpdate=true updateBundledApps`. This rechecks staged source/archive
pins and license inputs without another latest-release lookup or discarding completed
editor builds. Run without that property when you want a fresh discovery. Several editor releases also pin `craft-i18n.rev`; translations and dictionary data are
fetched at each required commit with archive hashes in `release/build-tools.json`.
Dictionary files remain intact; private source copies of interface translations receive
the branding patch.

The update preserves original legal files byte for byte under each editor's
`upstream-legal/source/`, alongside the official web package's notices and the independently
adjusted artwork attribution. Font legal files are retained under `upstream-legal/fonts/`.
The visible Android About notice gains exact source links and original top-level
LICENSE/NOTICE text. Existing Mozilla notices remain. Original upstream marks are replaced
through the existing source recipe, while copyright and required author credits remain.
Unrecognized branding or packaging changes fail verification and need a recipe update.

These checks enforce the recorded policy and preserve notice material; they cannot make
new license obligations or missing upstream notices disappear. Relevant primary references:
[GitHub release API](https://docs.github.com/en/rest/releases/releases),
[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0), and
[MIT license conditions](https://choosealicense.com/licenses/mit/).

## Before releasing the result

Review `git diff` (pins, license baseline, build inputs and notices). Update the version table
in README.md and the Android version/code, rebuild the APK/AAB, then run device offline,
menu and real import/edit/export checks. Old verification reports describe old binaries;
this task does not update them or mark Play submission tasks complete. The Google Play app
continues to receive updates through Google Play; no runtime GitHub updater is enabled.

Run the updater's offline regression tests with:

```sh
./gradlew testBundledUpdater
```
