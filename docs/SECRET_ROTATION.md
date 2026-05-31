# Secret rotation + history purge

The repo history contains real credentials that were committed long ago (the
ones `.gitleaksignore` acknowledges). CI is green because those findings are
allowlisted, but **allowlisting hides them, it does not remove them** — they're
still in `git log` and still shipped in the app today. This is the real fix.

> Requires repo **admin** + access to the provider consoles + a **force-push**
> (history rewrite). The agent can't do any of those, so this is a human runbook.

## 1. Rotate first (this is what actually kills the exposure)

Rotating invalidates the leaked value immediately, so even though it stays in
history it becomes useless. Do this before bothering with the purge.

| Secret | Where it leaked (commit) | Rotate where |
|--------|--------------------------|--------------|
| Google OAuth client secret | `backend/apps/tools_lib/{oauth_providers,tools_lib}.py` (7239f70, 7c3da1a, cbefe89) | Google Cloud Console → APIs & Services → Credentials → the OAuth client → **Reset secret** |
| PostHog API key | `backend/apps/analytics/collector.py` (8d09e46, b6f45e8) | PostHog → Project settings → rotate project API key (note: ingest keys are public by design — rotate only if it's a private key) |
| 9router client secrets | `9router/**` (cf775b4, history-only; dir now fetched from npm) | Whichever provider each `clientSecret` belongs to; bump `ROUTER_VERSION` if the npm package itself shipped one |

After rotating, update wherever the build injects them (the `GOOGLE_OAUTH_*`
GitHub Actions secrets + `backend/.env` production-injection step) to the new
values, and cut a release so users get the rotated build.

## 2. Purge from history (optional, after rotation)

Redact the values from every commit with [git-filter-repo](https://github.com/newren/git-filter-repo):

```bash
# expressions.txt: one `OLD_SECRET==>REDACTED` per line (the real old values)
git filter-repo --replace-text expressions.txt
```

Then the destructive part (admin only):

- `git push --force --all` and `git push --force --tags` (this is why the agent
  can't do it — force-push is denied and it rewrites every downstream commit hash).
- Everyone re-clones (old clones still hold the secrets).
- Re-create any protected-branch/tag rulesets if the rewrite trips them.

Because rotation (step 1) already neutralizes the secret, the purge is about
hygiene, not urgency. Once both are done, drop the matching fingerprints from
`.gitleaksignore`.
