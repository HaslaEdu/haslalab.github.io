# Latency and traffic

The site keeps the existing GitHub Pages front end and Cloudflare Worker/D1/R2 service. Performance changes should reduce requests and transferred data before increasing infrastructure or AI concurrency.

## Front end

- Load the small archive metadata on entry; load a competition's question data only when that route needs it. Keep the original source manifests and generated bundles in sync with `node tools/build-site-catalogue.cjs` and verify with `--check`.
- Merge simultaneous identical GETs, separate cache entries by API origin, account and language, and invalidate affected data after writes. Balances, payments and current answers must not use stale shared data.
- Initial exam screens use the bootstrap API instead of a chain of settings, identity, balance and session requests. Load transaction history only when requested.
- Poll only while a visible screen needs fresh work status. Avoid overlapping polls; back off when nothing changes and stop after a terminal result. Local exam deadlines continue to run while a tab is hidden.

## Worker

- Public, account-independent lists can use the edge cache. Private answers, identity, token balances and payment data must never enter that cache. Short cache writes can run through `ctx.waitUntil`.
- A status GET must not wait for OCR or AI grading. Persist the job, enqueue its ID, and return the current state. Queue messages contain IDs rather than scans, proofs or credentials.
- Jobs use a database claim/lease and bounded retries. Preserve the existing atomic token ledger; transport retries must not spend another token. Store the final state so a reload can recover it.
- Keep the queue consumer concurrency small. More simultaneous model calls do not reduce the model's own computation time and can increase rate-limit failures.

## Deployment and verification

The existing `deploy-worker.yml` workflow runs `community/provision-jobs.mjs` before deploying. It reuses the two named queues; the fixed additive schema documented in `0013_lab_jobs.sql` initializes once through the existing Worker D1 binding. This does not require the deployment token to manage or import databases. Queue authentication, permission or network errors fail deployment instead of silently disabling grading. Both Wrangler entry points declare the same queue binding and consumer. The minute recovery sweep retries stranded outbox work, while photo cleanup runs only every fifteen minutes.

Use `Server-Timing` (`db` and `total`), `X-Edge-Cache` and `cf-placement` to separate Worker work, database round trips and network latency. Database timings can overlap and must not be added to elapsed response time. Compare first loads with warm loads, and cached public requests with authenticated requests. Do not spend production tokens for a performance test; use the SQLite and fake-provider integration suites.

Long jobs use the queue consumer's lifecycle. `waitUntil` alone is unsuitable for grading that can take more than 30 seconds after an HTTP response has ended. Measure Worker placement before relocating the database or adding read replicas; Sessions API and write consistency need explicit treatment if replicas are introduced. Production probes on 30 October showed `local-LAX` Worker execution, approximately 160ms per binding call, and less than 1ms SQL execution. Additional D1 metadata identified the primary's actual serving colo as `HKG`. Both Wrangler entry points use the explicit nearby target `aws:ap-east-1` (Hong Kong). Compare uncached DB-bound request latency as well as DB wait; placement affects HTTP fetch handlers rather than queue consumers. A no-database cache hit is a separate control because forwarding a request to a placed Worker adds transport time.

## Community and account reads

Weekly/rank/post-detail responses carry the identity validated for that request and an API version. Their main content and the account chip share the same read instead of waiting for a separate `/me` round trip. The account page uses `/api/me/overview`: one authentication lookup followed by a transaction fetching only that account's statistics history, linked provider names, password-presence flag, token balance and active sitting. The old endpoints remain available; client fallback occurs only on a 404 and starts independent sections concurrently. Private reads have zero response TTL and coalesce only while in flight. Account/language changes prevent old responses from updating the new screen.

The weekly problem metadata and public leaderboard projection have a bounded five-second isolate cache and coalesce concurrent loads. Individual scores are fetched separately and merged into a clone, never into the reusable object. Public projections are invalidated after relevant successful writes; a client that has just changed related data requests fresh results. Public author profiles skip unnecessary authentication but retain uncached rename/deletion visibility. Sessions, roles, balances, identities and private answer histories are never shared-cache entries. A public cache is an optimization, not an authority for authentication or payment.

Post detail batches the post, comments, current reaction and optional atomic view increment into one transaction after authentication. Votes use an atomic rate-limit UPSERT and an ordered transaction that toggles one reaction, removes the opposite, and recomputes indexed counters. Comments return their canonical public representation so the client updates the thread without fetching the whole article again; reply deletion and counter recount occur in one transaction. Validation, ownership checks, escaping and the server's session check remain in place.

These choices follow the short-lived non-personalized cache described in [Reddit's current Devvit cache helper](https://developers.reddit.com/docs/capabilities/server/cache-helper) and the batching advice in [its Redis documentation](https://developers.reddit.com/docs/capabilities/server/redis). [Reddit's archived architecture](https://github.com/reddit-archive/reddit/wiki/Architecture-Overview) is a historical reference for batch reads and background work, not a claim about today's core service. No verifiable primary technical description of DCInside's internal server architecture was found; its internals are not assumed here. No new Redis/Kafka service or extra cross-service hop is required for these changes.

`Server-Timing` now separates full binding wait (`db`) from D1-reported SQL execution (`sql`), rows read (`d1_read`) and coarse serving region/primary status (`d1_region`) when D1 returns that metadata. `public_cache` counts reusable projection hits and misses. Concurrent DB timings can exceed elapsed time. Use this evidence before attributing latency to SQL, geography or Smart Placement. The local SQLite suites exercise permissions, account isolation, revoked sessions, concurrent votes/rate limits, cache invalidation and binding-call budgets without calling an AI provider or changing production data.

The lazily loaded arena module also supplies compatible identity/overview readers when an older cached HTML page does not yet define the new inline helpers. This keeps mixed static deployment versions functional while browsers refresh their HTML cache.

## Edge gateway and regional data work

The public `haslalab-community-edge` Worker has no placement, D1 binding, provider secrets, or job consumer. It handles CORS preflight and short-lived invariant public cache entries at the visitor's edge. Cache misses and private requests use a Service Binding to the existing `haslalab-community` Worker near the measured HKG primary. This preserves fast public cache hits while removing repeated cross-Pacific DB round trips. The browser still makes one API request; hits avoid the backend entirely. Private response bodies never enter the gateway cache.

The gateway preserves the request's method, stream, Authorization and scan headers. It rewrites the request URL to the original backend origin so registered OAuth callbacks and signed payment webhook processing keep their established behavior. Existing production API overrides are migrated to the gateway; custom development origins remain selectable. Secrets and queue consumers stay on the original Worker. Deployment creates/updates that Worker before its gateway and requires no extra API-key provisioning. A read-only health transport check compares the forwarded Cloudflare client-IP digest and returns only a boolean, allowing IP-based login rate limiting to be verified without logging or returning addresses.
