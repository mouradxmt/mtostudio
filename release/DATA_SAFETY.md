# Mtouaa Studio — draft Data safety worksheet

These answers describe the independently branded **Play** edition. Review them against the
final signed bundle and its third-party runtime before submitting them in Play Console.
They are not a submitted or Google-approved declaration.

Publisher: **Mtouaa Labs**. The 0.4.1 candidate contains no AdMob SDK or advertising.
The planned monetized edition must use a revised policy and worksheet before launch;
see [ADMOB_PLAN.md](ADMOB_PLAN.md). An ad-supported version cannot reuse the current
"no advertising SDK" answer. Declare ads in Play Console when that edition is submitted,
and assess the SDK's actual collection/sharing, consent behavior and merged permissions.

| Item | Intended answer / evidence |
| --- | --- |
| Ads | No publisher advertising SDK or ad placements. |
| Account required | No. There is no publisher account registration or account-deletion service. |
| Documents and media | Processed locally. The wrapper does not upload document contents. User-selected Android document providers have their own storage practices. |
| Location, contacts, camera, microphone | No such Android permissions are requested. Audio recording is not supplied by this wrapper. |
| External engine updater | Disabled in the Play flavor, including the native update/check APIs and activation of external packs. Updates are distributed through Google Play. |
| Analytics | No publisher analytics SDK is added. Validate the bundled Mozilla runtime and final network behavior; do not infer SDK behavior solely from the wrapper. |
| Crash handling | Local runtime crash callback displays an error. The wrapper does not implement a crash-upload service. Review runtime configuration and the final merged manifest. |
| Local data removal | Clear app storage or uninstall. Exported documents remain in their selected locations. |
| External Support link | Opens the publisher site in the user's browser. The website needs its own accurate privacy practices. |
| Final merged permissions | Internet, network state (required by GeckoView), wake lock, audio-output settings and the app's own non-exported receiver permission. No broad storage, camera, microphone, contacts or location permission. |
| Transitive SDK inventory | GeckoView brings Google Play Services FIDO/base/task artifacts for browser capabilities. The wrapper has no sign-in or WebAuthn flow. Review this dependency inventory alongside GeckoView; the presence of these artifacts is not evidence that the offline editors need a Google account. |
| Target audience | Publisher decision still required; do not select children by default. |

Complete the actual Data safety form from the verified final behavior. In particular,
on-device processing is different from off-device collection, and the presence of Internet
permission alone does not establish collection. Do not claim encryption of exported local
files: this app does not add a document-encryption layer. Answer any encryption question in
the context of data actually transmitted by the final product.
