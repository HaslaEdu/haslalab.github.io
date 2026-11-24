# Workshop storage connectors: owner setup

The storage page (`#/workshop/storage`) can link a member's own Google Drive and GitHub. The code is in
`src/workshop-connectors.js`, the page in `../workshop-connectors.js`. Until the settings below are in place, the page
shows each connector as "준비 중 — 관리자 설정 후 열립니다" and every connector route answers `503 not_configured`.
Nothing else on the site changes.

What HaslaLab can reach once a member connects:

- **Google Drive**: only files HaslaLab created (scope `drive.file`) and only inside the folder «HaslaLab» it makes in
  the member's Drive. Deleting moves a file to the member's Drive trash.
- **GitHub**: only the repositories the member includes in the installation, and only the one they pick, inside one
  folder (default `haslalab/`). Commits are titled `HaslaLab: …`. HaslaLab cannot create repositories.

The values below are entered only by you, in the Google or GitHub console and with `wrangler secret put`. Never put
them in this repository, a commit or a chat. Adding a secret with `wrangler secret put` does not remove the others.

## Exact callback addresses

| Provider | Register this exact URL |
|---|---|
| Google (OAuth client, "Authorized redirect URIs") | `https://haslalab-community.haslalab.workers.dev/api/workshop/connectors/google/callback` |
| GitHub App ("Callback URL" and "Setup URL") | `https://haslalab-community.haslalab.workers.dev/api/workshop/connectors/github/callback` |

These are on the community Worker's own address, not on `https://haslaedu.kr` (the haslaedu Worker forwards only
`/api/oauth/<provider>/callback`). The origin is the constant `CONNECTOR_ORIGIN` in `src/workshop-connectors.js`.
An optional variable `WORKSHOP_CONNECTOR_ORIGIN` (an https origin, e.g. a future passthrough on haslaedu.kr) replaces it.
If you set it, register the new URLs first.

## 1. Google Drive

Use the same Google Cloud project and OAuth client as "Sign in with Google" (the Worker's `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET`). No new client ID or secret is needed.

1. Google Cloud console → **APIs & Services → Library** → enable **Google Drive API**.
2. **Google Auth Platform → Data access** (older consoles: "OAuth consent screen → Scopes") → **Add or remove scopes**:
   add `https://www.googleapis.com/auth/drive.file` ("See, edit, create and delete only the specific Google Drive
   files you use with this app"). Keep `openid` and `email` (the page shows which Google account is linked).
   `drive.file` is a non-sensitive scope, the one Google recommends, so it needs no security assessment. If the app is
   published, Google may still ask for a brand verification of the consent screen when a scope is added. Until that
   is done, users can see an "unverified app" notice.
3. **Clients → (the web client used for sign-in) → Authorized redirect URIs** → add
   `https://haslalab-community.haslalab.workers.dev/api/workshop/connectors/google/callback` and save. Keep the
   existing sign-in URI.
4. **Branding → Authorized domains**: if Google refuses the redirect URI because `haslalab.workers.dev` is not an
   authorized domain, the callback has to move to a domain you have verified. The way to do that is a passthrough for
   `/api/workshop/connectors/google/callback` on haslaedu.kr (like the existing `/api/oauth/<provider>/callback` one in
   the haslaedu Worker), then `WORKSHOP_CONNECTOR_ORIGIN = "https://haslaedu.kr"`.
5. Make the key that encrypts the members' Google tokens in D1 (AES-256-GCM). Run this on your own machine:

   ```sh
   openssl rand -base64 32
   ```

   Then store the output as a secret. Paste it when wrangler asks for it, and do not keep it anywhere else:

   ```sh
   cd community
   npx wrangler secret put WORKSHOP_TOKEN_KEY
   ```

   Do not change this key later. If it changes, the stored tokens can no longer be decrypted, and every member has to
   connect again.

Drive is "configured" once `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and a valid 32-byte `WORKSHOP_TOKEN_KEY` are present.

## 2. GitHub App

Do not reuse the login OAuth app. GitHub → **Settings → Developer settings → GitHub Apps → New GitHub App**:

- **GitHub App name**: e.g. `HaslaLab Storage`. Its URL slug (`github.com/apps/<slug>`) is `GITHUB_APP_SLUG`.
- **Homepage URL**: `https://haslalab.org`
- **Callback URL**: `https://haslalab-community.haslalab.workers.dev/api/workshop/connectors/github/callback`
- **Expire user authorization tokens**: on (HaslaLab uses the user token once, then revokes it).
- **Request user authorization (OAuth) during installation**: **on**.
- **Enable Device Flow**: off.
- **Setup URL**: the same URL as the Callback URL. GitHub greys this field out when "Request user authorization during
  installation" is on, and sends the browser to the Callback URL instead. That is expected.
- **Redirect on update**: **on**.
- **Webhook**: **Active off** (no webhook URL, no secret).
- **Permissions → Repository**: **Contents: Read and write**, **Metadata: Read-only** (mandatory). Nothing else, no
  organization or account permissions.
- **Where can this GitHub App be installed?**: **Any account**.

After creating it:

1. Note the **App ID** and the **Client ID** shown on the App's page.
2. **Generate a new client secret**.
3. **Private keys → Generate a private key**. GitHub downloads a `.pem` in PKCS#1 form (`BEGIN RSA PRIVATE KEY`). The
   Worker accepts that as it is, but PKCS#8 is the documented format. To convert it:

   ```sh
   openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in haslalab-storage.private-key.pem -out app-key-pkcs8.pem
   ```

Store them as secrets. Each command asks for the value; paste it there, and for the key use the file with `<`:

```sh
cd community
npx wrangler secret put GITHUB_APP_ID
npx wrangler secret put GITHUB_APP_CLIENT_ID
npx wrangler secret put GITHUB_APP_CLIENT_SECRET
npx wrangler secret put GITHUB_APP_PRIVATE_KEY < app-key-pkcs8.pem
```

Then delete the downloaded `.pem` files from your machine, or keep them in a password manager.

`GITHUB_APP_SLUG` is public (it is in the install URL), so it is a variable rather than a secret. Add it to
`community/wrangler.toml` under `[vars]`, e.g. `GITHUB_APP_SLUG = "haslalab-storage"`, or set it as a plain-text
variable in the dashboard. Do not commit it as an empty string: with `keep_vars = true`, a value in the file replaces
the dashboard's on the next deploy.

GitHub is "configured" once all five (`GITHUB_APP_ID`, `GITHUB_APP_SLUG`, `GITHUB_APP_CLIENT_ID`,
`GITHUB_APP_CLIENT_SECRET`, `GITHUB_APP_PRIVATE_KEY`) are present.

## How it works

- **State**: `/start` (signed-in member only) stores the SHA-256 of a random state, bound to the member, for 10 minutes.
  A callback can use it once. The callback never signs anything in. It hands the browser a one-time ticket and sends it
  back to `#/workshop/storage` on an allowed https origin. The link is made only when the same member posts that
  ticket with their own HaslaLab token. A link started by someone else is refused (`wrong_user`).
- **Google**: authorization code with PKCE (S256), `access_type=offline`, `include_granted_scopes=true`,
  `prompt=consent`. The code is kept encrypted until the member finishes. The refresh and access tokens are stored
  encrypted with AES-GCM (`WORKSHOP_TOKEN_KEY`, bound to the member's id). Disconnecting or deleting the account
  revokes the token at Google (`oauth2.googleapis.com/revoke`) and deletes the row. A grant without the Drive box
  ticked is refused and revoked.
- **GitHub**: the callback trades the code for a user token only to check, with `GET /user/installations`, that the
  installation belongs to this App and that the GitHub user who came back can reach it. The token is then revoked.
  Only the installation id is kept. If GitHub ever returns from the install without the state, nothing is linked. The
  page then starts GitHub's plain user authorization with a fresh state, and the installation is taken from the
  user's own installations of this App. Each operation mints a token of about an hour, valid only for this session's
  requests: a JWT (RS256, signed with the App key through WebCrypto) is exchanged at
  `POST /app/installations/{id}/access_tokens`, with `repository_ids` narrowed to the member's chosen repository and
  `contents: read` or `write`. That token stays in the Worker's memory. Disconnecting deletes the stored installation;
  the page links to GitHub's installation settings, where the member uninstalls the App.
- **Files**: the storage limits apply (20 MB a file, the same type list, first bytes checked). GitHub paths allow
  letters, digits, spaces and `. _ - ( )`. No segment may be `..` or start with a dot (so nothing reaches `.github/`),
  there is no leading `/`, and at most 8 levels and 300 characters. A Drive file is reached only if its parents lead
  up to the «HaslaLab» folder.
- No Google or GitHub token is ever sent to the browser or written to the logs.

> **Optional since 2026-11-24:** without `WORKSHOP_TOKEN_KEY` the Worker derives the Drive token key from the existing `GOOGLE_CLIENT_SECRET` (HKDF). Changing that client secret, or adding `WORKSHOP_TOKEN_KEY` later, only means members link Drive again.
