# Yance.ai Git Security Policy

1. All secrets managed via environment variables only.
2. `.env*` files never enter Git.
3. `env.prod` never enters Git.
4. Production database dumps never enter Git.
5. API Keys never hardcoded.
6. Private keys never enter Git.
7. All production changes must be committed.
8. Deploy must record commit hash.
9. Benchmark runs must record git commit hash.
10. Production must track running version.
