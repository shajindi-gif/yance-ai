# Security Policy

## Reporting a vulnerability

Do not open a public issue for suspected security vulnerabilities. Contact the
project maintainers through the private security contact configured for the
repository or deployment environment. Remove credentials and customer data
from reproduction logs.

## Supported state

This repository is currently pre-production. Security claims must be backed by
tests or deployment evidence before publication. Demo payment and demo data are
disabled by default and must never be enabled in production.

## Secrets and sensitive data

- Keep credentials, private keys, payment identifiers, customer documents, and
  production configuration out of Git.
- Copy `.env.example` to a local secret file and inject production values from a
  managed secret store.
- Rotate a credential immediately if it may have entered Git history or logs.
- Do not log prompt bodies, document text, access tokens, or payment data.

## Current limitations

The project has not completed an independent penetration test or formal
compliance certification. The current code-audit baseline and open release
blockers are documented in `docs/investor-readiness/06_SECURITY_AUDIT.md`.
