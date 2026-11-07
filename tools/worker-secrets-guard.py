"""Stop a community Worker deploy that would lose secrets.

`wrangler deploy` copies secrets from the most recently UPLOADED version of the Worker, which is not always the one
that is live: an upload that was never deployed (dashboard, API, `wrangler versions upload`) with fewer secrets makes
the next deploy drop the rest. That is how 28 secrets, the sign-in keys among them, went on 2026-11-06.

    python3 tools/worker-secrets-guard.py [script]        (CLOUDFLARE_API_TOKEN in the environment)

Exits non-zero, naming the missing secrets (never values: Cloudflare does not return them), when the newest upload
lacks a secret the live version has. Only reads.
"""
import json, os, sys, urllib.request

H = {"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"], "User-Agent": "HaslaLab deploy guard"}
SECRET = ("secret_text", "secret_key")


def get(path):
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["result"]


script = sys.argv[1] if len(sys.argv) > 1 else "haslalab-community"
acct = get("/accounts")[0]["id"]
base = f"/accounts/{acct}/workers/scripts/{script}"
live = max(get(base + "/deployments")["deployments"][0]["versions"], key=lambda v: v["percentage"])["version_id"]
newest = get(base + "/versions?per_page=1")["items"][0]["id"]
names = lambda vid: {b["name"] for b in get(f"{base}/versions/{vid}").get("resources", {}).get("bindings", [])
                     if b.get("type") in SECRET}
have, upload = names(live), names(newest)
missing = sorted(have - upload)
print(f"live {live}: {len(have)} secrets; newest upload {newest}: {len(upload)} secrets")
if missing:
    sys.exit(f"::error::Not deploying: the newest uploaded version {newest} lacks {len(missing)} secrets the live "
             f"version has ({', '.join(missing)}); wrangler deploy would drop them. Deploy the live version's "
             f"secrets onto a new version first (see .github/workflows/deploy-worker.yml).")
