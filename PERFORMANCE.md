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
