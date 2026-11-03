---
applyTo: "plugins/**,scripts/**"
---

# Loon ad-blocking: agent handoff and verified lessons

> Agent-facing maintenance guidance. Keep this file out of README and user-facing plugin descriptions. This is a technical handoff, not a guarantee that future app versions will behave identically.

## Verified outcome (2026-11-03)

The user **confirmed that the persistent 123 Cloud Drive (123云盘) ads were resolved after updating** `plugins/AdPlatform-Supplement.plugin` to its DNS-first version.

The successful release changed multiple things together:
- Added exact DOMAIN/REJECT entries for `mssdk.volces.com` and `tnc3-alisc1.zijieapi.com`. These appeared in the user's Jinx request screenshots but were absent from the then-active Kelee + supplement hostname rules. The two hosts may be shared with other ByteDance/Volcengine features; do not expand them to broad suffix blocking without separate proof.
- Kept the other 23 supplemental exact-host DOMAIN rules (25 total).
- **Removed six HTTP request-rewrite mocks**, including `reject_img(200)` for `pgdt.ugdtimg.com`, and removed the supplemental MitM section; DNS/domain rejection is now the intended first line of defense.
- Left the specialized `plugins/123Pan-Splash-Enhanced.plugin` (v6) unchanged. It contains only four first-party 123pan API response rewrites; it must remain decoupled from third-party SDK domain rules.

**Important evidence vs inference:** The user reported success **after the plugin update**, but did not establish which of the simultaneous changes was necessary or sufficient, nor confirm that their main Loon `[General]` settings were changed. Do not claim a single proven root cause. The observed success is a regression baseline for future work.

## Failure modes established during debugging

1. **Do not equate HTTP success with useful ad content.** A 200 from an SDK bidding endpoint may contain `is_success: 0` and an empty response; inspect the body and the creative payload before calling it a leak.
2. **Do not mistake request logging for the ad render source.** An SDK's `win_notice`, `event`, or telemetry calls may happen after the creative was acquired; correlate timestamps and response content.
3. **Do not conclude 'cached ads' just because no new image download appears.** The user tested offline: the app showed a **black ad placeholder**, whereas enabling Jinx removed the ad entirely. This undermines the earlier overconfident cache hypothesis. Distinguish cached pixels, a blocked-but-preserved ad container, and independent SDK/network paths.
4. **Avoid fake HTTP success for ad SDK asset delivery.** A rewrite like `reject_img(200)` returns a 1x1 placeholder and can allow the SDK/app to consider the request completed, leaving a black/full-screen ad container. This is a plausible mechanism, not proven in isolation. Prefer native DOMAIN,REJECT where precise host evidence exists; do not reintroduce broad `response.body.mock` / `reject_img(200)` as a general fix.
5. **Inspect the execution stage**, not just whether a hostname appears in a rule list. Compare DNS-stage behavior, rule match and policy, HTTP Rewrite precedence, TCP/QUIC and potential DoH/HTTPDNS bypasses, and whether a successful real network response was seen before a config was rewritten.
6. **Server flags can be too late**: in 123pan iOS 3.3.4 captures, ad creatives were acquired before the application's `/api/config/get` rewrite. Later changes to `isOpenSplash` or `iosSplash` cannot retroactively prevent that download. Do not endlessly tweak first-party config when the third-party ad path is responsible.
7. **Do not multiply duplicate rules**. Compare Kelee's live `BlockAdvertisers.plugin` and `Remove_ads_by_keli.plugin` (DOMAIN, DOMAIN-SUFFIX and DOMAIN-KEYWORD) with current supplemental entries. For example, Kelee already covered `pgdt.ugdtimg.com` at the time; duplication was unnecessary.
8. **Protect app functionality**. Do not wildcard `*.qq.com`, `*.zijieapi.com`, `*.volces.com`, `*.123pan*`, file transfer, auth, entitlement or video-source hosts. Shared SDK hosts may carry legitimate functions. Preserve optional 'watch ads for rewards' behavior unless specifically requested.

## Current plugin design and boundaries

- `plugins/AdPlatform-Supplement.plugin`: general cross-app supplemental filter; as of the successful user test, **25 exact DOMAIN, REJECT rules; no [Rewrite] and no [MitM]**. Keep new third-party ad domains here only after evidence and upstream de-duplication.
- `plugins/123Pan-Splash-Enhanced.plugin`: minimal app-specific v6, with only these 123pan responses: `/api/config/get`, `/api/app/config/get`, `/api/user/info`, `/api/taku/ad/config`. Preserve fallback origins `api.123278.com`, `api.123panapi.com`, `api.123panapi.cn`; keep upload/download and user rights intact.
- `plugins/123Pan-Splash-Full.plugin`: independently usable legacy full variant, **not** intended to be enabled alongside the minimal version. Do not silently rewrite it when editing the minimal pair.
- Kelee advertisement platform blocker remains the base filter; the supplemental filter is only an additive layer.

## Loon configuration: scope and validation

- The global options `domain-reject-mode = DNS`, `dns-reject-mode = NXDOMAIN`, and optional `hijack-dns = *:53` belong to the user's **main** `[General]` configuration, **not an ordinary plugin**. Do not write them into a plugin file or claim the plugin changed them. Check current Loon documentation/version before recommending exact settings.
- DNS hijacking of UDP/53 is not equivalent to universally capturing DoH, HTTPDNS, QUIC or app-private resolvers. Do not promise Jinx-identical behavior in every network mode.
- Check whether the user already has an upstream Kelee HTTPDNS module. Do not blindly add another.
- Verify Loon **syntax and section order**, not only regex matching. In earlier Mango TV iterations, a JS response script was placed in the wrong section and its parameter shape was invalid; don't repeat that failure.
- Keep stable raw GitHub plugin URLs and one-tap import paths unless the user asks for a separate version. No unrelated plugin edits.

## Diagnostic workflow for the next agent

1. Ask which app/version, exact ad behavior (normal video vs black rectangle vs skipped), whether the user used Jinx or Loon for the same test, and which plugins/config were enabled. If the user supplies a capture, prioritize it over assumptions and avoid repeated questions.
2. From the capture, identify the **actual creative** (image/video/redirect), SDK, host/path, response status **and body**, timestamps, cache headers and the original vs rewritten responses. Match against the active plugin source, not remembered rule lists.
3. Compare the active Kelee rules, the current supplemental rules, and any Jinx blocked-host evidence. Categorize: uncovered exact hosts; covered but rule not executed; covered but HTTP mock/precedence took priority; third-party cached content; or app-internal content.
4. Prefer the smallest exact-host DOMAIN rejection for **verified advertisement infrastructure**. Use a path-scoped rewrite only if it is truly needed and check whether the chosen rejection semantics preserve an unwanted ad placeholder.
5. Run static checks: rule count, duplicate hosts (including suffix/keyword coverage), valid sections/arguments, URL regex matches, harmless URLs not matched, no accidental account or file-transfer blocking. Then require user-device testing for real efficacy.
6. For changes, keep shared ad infrastructure in the supplemental plugin and 123pan-only API mutations in the 123pan plugin. Do not silently conflate them.
7. Report **confirmed results vs hypotheses** separately. Do not claim complete ad removal based on static tests; a prior successful user report is not a guarantee for a later release.

## Historical case anchors

- Screenshot evidence: Jinx blocked ~40 visible advertising/tracking hosts; Kelee + the then-supplemental rules covered 38, leaving `mssdk.volces.com` and `tnc3-alisc1.zijieapi.com`.
- Earlier 123pan capture: real `pgdt.ugdtimg.com` creative and Hongguo short-drama icon, GDTMobSDK User-Agent; later capture showed no fresh asset despite persistent ad behavior. Avoid treating this alone as proof of local caching.
- User-observed contrast: Loon displayed a black JD ad frame and an ordinary Hongguo ad; Jinx eliminated the ad. After DNS-first supplement update, the user explicitly confirmed the 123pan issue was resolved.
- This note is a handoff for agents: keep it in this path-specific instruction file; never paste these debugging notes into the public README unless explicitly requested.

