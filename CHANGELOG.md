# Change Log

## Version 1.0.0 (2026-09-17)

- Target Open edX Verawood with Python 3.12+ and Django 5.2.
- Bound runtime dependencies to the Verawood-compatible major versions and move
  the Atlas translation CLI to development dependencies.
- Test both the Verawood Django baseline and the locked Django 5.2 patch release.
- Document the release impact on completion, course structure, signals, and backfill.
- Ignore library completion signals instead of queuing non-course keys for the
  LMS course completion API.

## 0.1.0 – 2026-06-19
- First release on PyPI.
