Change Log
##########

..
   All enhancements and patches to openedx_progress will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

Changed
=======

* Target Open edX Verawood with Python 3.12+ and Django 5.2.
* Bound runtime dependencies to the Verawood-compatible major versions and move
  the Atlas translation CLI to development dependencies.
* Test both the Verawood Django baseline and the locked Django 5.2 patch release.
* Document the release impact on completion, course structure, signals, and backfill.

Fixed
=====

* Ignore library completion signals instead of queuing non-course keys for the
  LMS course completion API.

0.1.0 – 2026-06-19
**********************************************

Added
=====

* First release on PyPI.
