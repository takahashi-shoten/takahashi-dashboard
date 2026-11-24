# YouTube API notes (studio/youtube.py)

Status legend: **[in code]** = what the code does; **[UNVERIFIED]** = from memory, must be checked against current Google docs / a real account before relying on it.

## Auth
- [in code] OAuth2 refresh-token flow: POST `https://oauth2.googleapis.com/token` with client id/secret/refresh token from env `YT_OAUTH_CLIENT_ID`, `YT_OAUTH_CLIENT_SECRET`, `YT_OAUTH_REFRESH_TOKEN`. Missing vars raise `NotConnected`. Values are never logged or put in exceptions.
- [in code] A Data API *key* is a separate credential for public reads only; this module does not use one.
- Obtaining the refresh token (consent flow) is not implemented here.

## Scopes (what each needs) [UNVERIFIED mapping]
| Scope | Used for |
|---|---|
| `https://www.googleapis.com/auth/youtube.upload` | videos.insert (upload) |
| `https://www.googleapis.com/auth/youtube` (or force-ssl) | videos.update (set_privacy) — verify whether `youtube.upload` alone suffices |
| `https://www.googleapis.com/auth/youtube.readonly` | channels.list mine, videos.list statistics/status of own private videos |
| `https://www.googleapis.com/auth/yt-analytics.readonly` | Analytics reports (views, watch time, retention, subs, traffic source, country) |
| `https://www.googleapis.com/auth/yt-analytics-monetary.readonly` | revenue metrics (`estimatedRevenue`) |

## Metrics
- [in code] CORE_METRICS: views, estimatedMinutesWatched, averageViewDuration, averageViewPercentage, subscribersGained, subscribersLost.
- [in code] Impressions are requested separately, new names first (`videoThumbnailImpressions`, `videoThumbnailImpressionsClickRate`), then old (`impressions`, `impressionsClickThroughRate`). [UNVERIFIED] which names work (coordinator note: new names documented 2026; old may be channel-level only or 400). Code treats HTTP 400 (and 403) for a metric as "unavailable", drops it, and lists it in `unavailable_metrics`.
- [in code] `estimatedRevenue` requested separately; 400/403 => unavailable. [UNVERIFIED] requires monetization + the monetary scope.
- [in code] Dimensions: `insightTrafficSourceType`, `country`. [UNVERIFIED] that these combine with views/estimatedMinutesWatched exactly as queried; a rejection is reported as unavailable metrics rather than a crash.
- Because 400 is ambiguous (bad metric vs bad query), the fallback probes each metric alone; a malformed query (e.g. bad date) would also show up as "all unavailable". Check `unavailable_metrics` before trusting a null result.
- Analytics data lag (often ~1-2 days) [UNVERIFIED]; checkpoints at 24h may be incomplete.

## Upload
- [in code] Resumable: POST `.../upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` (JSON body, `X-Upload-*` headers) -> `Location` header -> PUT bytes -> JSON with `id`. Single PUT, no chunk-resume on failure (not implemented).
- [in code] `status.containsSyntheticMedia` is set from `synthetic_media` (default True). [UNVERIFIED] exact field name/availability in the current API.
- [in code] Default privacy `private`; `public` needs a `publish_public` row in the ledger `approvals` for that project_id.

## Open verification questions (verify)
1. **Quota**: videos.insert costs 1600 units and the default daily quota is 10,000 units — verify current numbers in the quota calculator / console.
2. **Unverified API projects**: coordinator reports Google's revision history (2026-11-02) says unverified-project uploads are no longer forced private — verify. Code still defaults to private and records the `status.privacyStatus` from the upload response (the real value).
3. **Consent screen in "Testing"**: for External apps in Testing status, refresh tokens may expire after 7 days — verify; publish the app (or use Internal) if so.
4. Minimum scope for videos.update (see table).
5. Whether impressions/CTR are available via Analytics API (else manual Studio export).
6. Whether `containsSyntheticMedia` is accepted on insert.
7. Analytics freshness/lag and whether per-video filter + dimensions is allowed for all listed combos.
8. Data API `statistics` for private videos returns what fields (stored as `data_api.*` metrics).
