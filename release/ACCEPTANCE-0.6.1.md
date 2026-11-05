# Mtouaa Studio 0.6.1 — public update acceptance

Verified 5 November 2026 against the published release:
https://github.com/mouradxmt/mtostudio/releases/tag/v0.6.1

The APKs were built, signed and verified locally. Publication used direct GitHub Release
uploads. Cloud workflows stayed disabled; no new Actions run or artifact was created.

Huawei APK SHA-256:
`62af4ef9850028148bdba48f15236e2179d7fe6f5aa5974c7100bf96aef256ab`

On the disposable `mtouaa-play-16k` emulator (port 5570, Android 16, ARM64, 16 KB pages):

1. Installed the signed 0.6.0 Huawei edition, version code 9.
2. Used **Check for updates** to discover public 0.6.1 and validate its signed descriptor.
3. Downloaded the public APK through the production app. Its size, hash, package/version
   and signing certificate passed the app's checks.
4. Confirmed the save-work prompt, allowed installation from this app in Android Settings,
   and confirmed Android's **Update** prompt.
5. Verified the installed app became **0.6.1, version code 10**.
6. Relaunched it; **Check for updates** reported **Mtouaa Studio is up to date**.
7. Disabled Google Play Services and ran the common offline suite runner: **18 checks
   passed**, including all 15 editor shortcuts/startups and the native controls.

The first connection attempt exposed a DNS failure in the emulator, not an APK signature
failure. Restarting only this disposable emulator with `-dns-server 1.1.1.1,8.8.8.8`
restored resolution. The diagnostic `-e updatesOnly true -e live true` then passed its
three real public-descriptor checks. User emulators were left untouched.

The previous 24 Huawei security/installer checks, 9 Play controller checks with Google's
fake service, 35 host regressions, 7 save-bridge checks and signed-bundle validation are
recorded in VERIFICATION.md. The published runtime source matches release tag v0.6.1.

Physical Huawei acceptance and actual Google Play update delivery remain separate checks.
No Google Play submission or AdMob activation is claimed. Preview has separate app storage;
export its documents before importing them into the Huawei edition.
