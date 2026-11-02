Change Log
##########

Unreleased
**********

2.1.10 - 2026-11-02
*******************

Changed
========

* Move the package version to ``qualtricssurvey/__init__.py`` and read it from ``setup.py`` without importing runtime dependencies.
* Defer shared runtime dependency versions to the host Ulmo edx-platform environment, removing compiled runtime pins and legacy constraints.
* Declare directly imported runtime dependencies without version pins.
* Preserve unpinned runtime requirements during ``make upgrade``.
* Document installation into a provisioned platform environment without changing its shared dependencies.

Fixed
=====

* Point ESLint and CSSLint at the current ``qualtricssurvey/static/`` assets.
* Remove ESLint's ``--fix`` option so CI checks files without modifying them.
* Align ESLint parsing with ES2015 and correct JavaScript formatting, naming, documentation, and unused-variable issues while preserving grading, polling,
  and iframe resizing behavior.
* Isolate standalone Django tests from LMS-only services using test settings and explicit service doubles, while loading Ulmo's real score field.
* Replace obsolete survey-link assertions with iframe, asset, escaping, and score tests for the current XBlock.
* Pin shared test dependencies to Ulmo versions without constraining runtime package metadata, and select Django 5.2.11 for the Ulmo test job.
* Fetch the required Ulmo score-field source in CI and disable fail-fast so every matrix job reports its result.
* Fix Python formatting, import order, unused code, and documentation reported by the quality job.
* Align pycodestyle and pylint on a 120-character line limit and exclude generated migrations.
* Run quality checks with Django 5.2.11, Ulmo test constraints, and minimal standalone Django settings.
* Declare the pylint plugins used by the generated configuration and preserve quality requirements during ``make upgrade``.
* Import ``InvalidKeyError`` so invalid course block identifiers raise the intended ``ValueError``.
* Catch the correct requests HTTP exception, preserve failed HTTP responses for callers, and propagate transport failures.
* Make ``calculate_score()`` compatible with the no-argument XBlock scoring interface.
* Add regression tests for invalid identifiers, request error handling, and no-argument score calculation.

Added
=====

* Add this changelog to the source distribution.
