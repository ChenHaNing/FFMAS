# Security Policy

## Supported Versions

This is a research prototype. Security fixes are applied on the default branch (`main`).

## Reporting a Vulnerability

Please do not open public issues for sensitive security problems.

Suggested process:

1. Revoke/rotate affected credentials immediately.
2. Share a private report with reproduction steps and impact.
3. Include commit hash/time window if a secret may have been committed.

## Secret Handling Rules

- Never commit `.env` or real credentials.
- Keep `.env.example` as placeholders only.
- Use repository/organization secrets in GitHub Actions.
- Do not store runtime outputs/logs with credentials in git.

## If a Secret Was Committed

1. Rotate the credential first.
2. Remove tracked secret files from git index.
3. Rewrite git history to purge leaked content (for example `git filter-repo`), then force-push.
4. Invalidate all tokens that appeared in history.

Rotation first, cleanup second.
