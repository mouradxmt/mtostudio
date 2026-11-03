# AdMob plan for Mtouaa Studio

Publisher: **Mtouaa Labs**. Reviewed 3 November 2026.
Status: planning only. Version 0.4.1 has no advertising SDK, ad requests or ad placements.
No AdMob account, production IDs or app-ads.txt record has been created by this project.

## Recommended first placement

Start with one adaptive banner in the native suite home screen, separated from the
Open/Add to Home controls and labelled as advertising. Keep it outside the Gecko editor.
Do not interrupt editing, opening, saving or exports with ads. Collapse the placement
when offline, unavailable or ineligible; there should be no empty reserved workspace
and no waiting for an ad before opening a tool. This is a proposed product design.

Core editing remains offline. Online advertising is a separate service; an offline
session should make no ad requests and is not a source of new served-ad impressions.
Do not pass document contents, filenames, file URIs, selected text or document metadata
to the advertising SDK. The editor's existing network restrictions remain in place.

## Information needed from the owner

1. Set up an AdMob account and register **Mtouaa Studio**, Android package
   `com.mtouaa.studio`, under the owner's verified account details.
2. Obtain the **AdMob App ID** and a **banner ad-unit ID**. They are different identifiers:
   the app ID contains `~`, while an ad-unit ID contains `/`. Production IDs must come
   from the owner's account; do not invent them or reuse another publisher's IDs.
3. Obtain AdMob's personalized app-ads.txt snippet and configure privacy messages for
   the actual audience and distribution regions.

Google's current [Android setup guide](https://developers.google.com/admob/android/next-gen/quick-start)
uses GMA Next-Gen SDK `ads-mobile-sdk:1.6.0`. Its minimum API 24 / compile API 35
requirements fit this app's API 26 / compile API 37 configuration. Recheck versions when
implementing, since this is a plan rather than a dependency added to the build.

## Implementation approach

Create a native ad controller with home-screen lifecycle handling and production/test
configuration separated. Use the [current banner guide](https://developers.google.com/admob/android/next-gen/banner)
when implementing the placement. Initialize the SDK once on a background thread, after
consent eligibility is established; initialization itself can preload ads. Those ordering
requirements come from the [SDK setup guide](https://developers.google.com/admob/android/next-gen/quick-start).

Follow Google's [UMP consent flow](https://developers.google.com/admob/android/next-gen/privacy):
refresh consent information each launch, show required forms, check `canRequestAds()`,
and provide the privacy-options entry point when required. With Next-Gen, the app ID
belongs in SDK initialization and in the manifest for UMP. Do not infer consent from an
app-owned preference. If consent or networking fails, keep the suite usable and show
no ads unless UMP permits requests. Defer a required form to an appropriate home-screen
moment rather than disrupting an active document.

Keep preview/testing on Google's test inventory or registered test devices; never click
live ads during development. Use the [test-ads guide](https://developers.google.com/admob/android/next-gen/test-ads).
Verify ad lifecycle behavior when switching tools, rotating, backgrounding, going offline
and returning online. Test separately on the Huawei tablet without Google Play Services;
core editing must remain available even when advertising cannot load. Do not promise
that ads will fill on every device.

## Website, disclosures and release

Publish the exact personalized snippet at `https://mtouaa.com/app-ads.txt`, accounting for
the domain's existing redirect to `www.mtouaa.com`. Include the developer website in the
Play listing and verify that the crawler sees the correct publisher record. See Google's
[app-ads.txt setup instructions](https://support.google.com/admob/answer/9363762?hl=en).
Full ad serving also requires app verification and an app-readiness review; it is not
enabled just by adding the SDK. See [AdMob app verification](https://support.google.com/admob/answer/14538460?hl=en).

Before distributing an ad-enabled build, change the current privacy policy, Play ads
declaration and Data safety answers to match its actual behavior. Google's
[SDK disclosure guide](https://developers.google.com/admob/android/next-gen/privacy/play-data-disclosure)
lists IP address, interactions, diagnostics and device/account identifiers among default
SDK collection/sharing. Non-personalized advertising is not a guarantee of no collection.
Inspect the merged permissions and all added SDKs. Do not describe the ad-enabled edition
as transmitting no data merely because documents stay local.

Release the ad-enabled candidate through testing with a higher Android version code,
repeat offline/document checks and update screenshots if placements change. The existing
ad-free candidate's verification does not establish the future SDK's privacy or compatibility.

## Revenue expectations

A home-only banner may produce relatively few impressions because users spend time in
editors. Measure actual delivered impressions, earnings and retention before expanding
placements. A rough calculation is impressions / 1,000 × actual eCPM; there is no promised
income before real traffic and account/ad approval. Any later paid ad-removal option is a
separate product and billing decision.
