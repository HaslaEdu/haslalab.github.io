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

Long jobs use the queue consumer's lifecycle. `waitUntil` alone is unsuitable for grading that can take more than 30 seconds after an HTTP response has ended. Keep Smart Placement enabled and measure its effect before relocating the database or adding read replicas; Sessions API and write consistency need explicit treatment if replicas are introduced.

## Community and account reads

Weekly/rank/post-detail responses carry the identity validated for that request and an API version. Their main content and the account chip share the same read instead of waiting for a separate `/me` round trip. The account page uses `/api/me/overview`: one authentication lookup followed by a transaction fetching only that account's statistics history, linked provider names, password-presence flag, token balance and active sitting. The old endpoints remain available; client fallback occurs only on a 404 and starts independent sections concurrently. Private reads have zero response TTL and coalesce only while in flight. Account/language changes prevent old responses from updating the new screen.

The weekly problem metadata and public leaderboard projection have a bounded five-second isolate cache and coalesce concurrent loads. Individual scores are fetched separately and merged into a clone, never into the reusable object. Public projections are invalidated after relevant successful writes; a client that has just changed related data requests fresh results. Public author profiles skip unnecessary authentication but retain uncached rename/deletion visibility. Sessions, roles, balances, identities and private answer histories are never shared-cache entries. A public cache is an optimization, not an authority for authentication or payment.

Post detail batches the post, comments, current reaction and optional atomic view increment into one transaction after authentication. Votes use an atomic rate-limit UPSERT and an ordered transaction that toggles one reaction, removes the opposite, and recomputes indexed counters. Comments return their canonical public representation so the client updates the thread without fetching the whole article again; reply deletion and counter recount occur in one transaction. Validation, ownership checks, escaping and the server's session check remain in place.

These choices follow the short-lived non-personalized cache described in [Reddit's current Devvit cache helper](https://developers.reddit.com/docs/capabilities/server/cache-helper) and the batching advice in [its Redis documentation](https://developers.reddit.com/docs/capabilities/server/redis). [Reddit's archived architecture](https://github.com/reddit-archive/reddit/wiki/Architecture-Overview) is a historical reference for batch reads and background work, not a claim about today's core service. No verifiable primary technical description of DCInside's internal server architecture was found; its internals are not assumed here. No new Redis/Kafka service or extra cross-service hop is required for these changes.

`Server-Timing` now separates full binding wait (`db`) from D1-reported SQL execution (`sql`), rows read (`d1_read`) and coarse serving region/primary status (`d1_region`) when D1 returns that metadata. `public_cache` counts reusable projection hits and misses. Concurrent DB timings can exceed elapsed time. Use this evidence before attributing latency to SQL, geography or Smart Placement. The local SQLite suites exercise permissions, account isolation, revoked sessions, concurrent votes/rate limits, cache invalidation and binding-call budgets without calling an AI provider or changing production data.
