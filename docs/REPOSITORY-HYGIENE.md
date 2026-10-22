# Workspace Instructions — Sensitive Info, Structure, Hygiene

## 1. Sensitive Information Check
- Search for secrets:
  - `grep -RI --exclude-dir=.git -nE "AKIA|api[_-]?key|secret|passwd|token|PRIVATE_KEY|-----BEGIN" .`
- Ensure secrets are not committed:
  - Confirm `.gitignore` excludes: `certs/*.key`, `certs/*.csr`, `certs/*.srl`, `data/es_data/`, `data/vscode/`, `.env`
- If secret found in Git history:
  - Rotate/revoke the credential immediately.
  - Remove from history: `git filter-repo --invert-paths --path <file>` (or use BFG).
- Key file permissions:
  - `chmod 600 certs/*.key`
  - Keep private keys off VCS and shared drives.

## 2. Directory Structure Maintenance
- Keep large/binary data out of repo:
  - `data/es_data/` and `data/vscode/` must remain ignored (see `.gitignore`).
- Backups & retention:
  - Periodic backup: `tar -czf backups/es_data_$(date +%F).tar.gz data/es_data/`
  - Retain incremental snapshots; rotate older than retention period.
- Elasticsearch index hygiene:
  - Use ES snapshots instead of copying raw files.
  - Do not commit Lucene files found under `data/es_data/`.
- File ownership & permissions:
  - Follow the setup note: `sudo mkdir -p data/es_data data/pihole data/vscode logs/nginx logs/pihole && sudo chown -R 1000:1000 data/ logs/`

## 3. Workspace Control & Hygiene
- Container secrets:
  - Use Docker secrets or environment files outside repo; do not keep passwords in compose.
  - See `docker-compose.yml` for cert-gen and pihole services — ensure runtime secrets are injected at deploy time.
- Clean workspace before commits:
  - `git status --porcelain` and `git add -p` for precise staging.
  - Remove accidental large files: `git rm --cached <file>`
- Local dev hygiene:
  - Prune docker: `docker system prune -af` (careful — removes images/containers)
  - Clear logs periodically: rotate or truncate files under `logs/`
- Access & audit:
  - Limit access to `certs/` and `data/` directories.
  - Record changes to secrets and backups in a secure changelog (outside repo).

## 4. Quick remediation commands
- Find likely secrets:
  - `grep -RI --exclude-dir=.git -nE "token|secret|passwd|PRIVATE_KEY|-----BEGIN" .`
- Remove keys from index and commit:
  - `git rm --cached certs/*.key certs/*.csr && git commit -m "remove keys from repo"`
- Set strict permissions:
  - `find certs -type f -name "*.key" -exec chmod 600 {} \;`

## 5. Notes & References
- Ensure `.gitignore` is accurate and covers all sensitive paths
- Use `cert-gen` service in `docker-compose.yml` to generate certs locally; never commit produced private keys.
- Follow the local setup commands for directory initialization.

## Host hardening maintenance

See `docs/security/HOST-HARDENING.md` before changing or applying host utilities.
Keep actual `config/host-hardening/local.env`, `lan-hardening.nft`, and all
`backups/host-hardening/` reports out of Git. Version only example settings and
reviewed scripts. File organization must not execute privileged hardening or
change active networking. Keep existing rollback safeguards and verify fresh
SSH connections before confirming any hardening trial.
