# Deploy runbook: City of Spring Branch website

Everything below runs under **city-owned accounts**, separate from any personal
account. Steps marked (you) are signups only you can do; the rest is prepared in
this repo.

## 1. GitHub org + repo (you)
1. Create a GitHub **organization** owned by a city account (not personal).
2. Create an **empty** repo in it (do not add a README/license). Suggested name: `website`.
3. Note the `ORG/REPO` (for example `city-of-spring-branch/website`).

## 2. Push this repo
From this project directory:
```
git remote add origin https://github.com/ORG/REPO.git
git push -u origin main
```
(Use an SSH URL instead if you prefer SSH auth.)

## 3. Cloudflare Pages (you + config below)
1. Log into the **city** Cloudflare account. Pages > Create > Connect to Git > pick the repo.
2. Build settings:
   - Framework preset: **Hugo** (or None)
   - Build command: `hugo --gc --minify`
   - Build output directory: `public`
   - Environment variable: `HUGO_VERSION` = `0.164.0` (must match `.tool-versions`)
3. Deploy. You get a `*.pages.dev` URL.
4. Preview deployments are on by default: **every branch gets its own preview URL.**
   That is the post-preview mechanism.

## 4. Sveltia GitHub auth (so editors can edit the live site)
Local editing needs nothing. Editing the live site needs GitHub OAuth via a small worker.
1. Create a GitHub **OAuth App** (Settings > Developer settings > OAuth Apps):
   - Homepage URL: your Pages URL or domain
   - Authorization callback URL: `https://WORKER.workers.dev/callback` (fill after the next step)
2. Deploy the **sveltia-cms-auth** worker (https://github.com/sveltia/sveltia-cms-auth)
   in the city Cloudflare account. Set worker variables:
   - `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` (from the OAuth App)
   - `ALLOWED_DOMAINS` = your domain (optional, restricts who can start auth)
3. Go back and set the OAuth App callback URL to the deployed worker `/callback`.
4. In `static/admin/config.yml` fill:
   - `backend.repo: ORG/REPO`
   - `backend.base_url: https://WORKER.workers.dev`
5. Commit + push. `/<domain>/admin/` now logs in with GitHub and edits the live repo.

## 5. Custom domain (later)
Move `cityofspringbranch.org` DNS to the city Cloudflare account, then add the
domain to the Pages project.

## 6. How preview works day to day
`publish_mode: editorial_workflow` is set. A new or edited post is saved as a
**draft on a branch**. Cloudflare builds a **preview URL** for that branch. Open it,
review the fully rendered page, share the link if needed, then mark it Ready /
publish to merge to `main` and go live.

## Notes
- Content lives in git as Markdown. The CMS is only a convenience layer; if it ever
  breaks, the site and all content are intact.
- `HUGO_VERSION` + `.tool-versions` pin the build engine so old pages rebuild verbatim.
