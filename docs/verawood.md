# Verawood compatibility review

Reviewed on 2026-09-17 against the Open edX `release/verawood` branch at
[`b5fc56a101a2a1d3fd3c3568d2719680840ca7d2`](https://github.com/openedx/edx-platform/tree/b5fc56a101a2a1d3fd3c3568d2719680840ca7d2)
and the [developer/operator release notes](https://docs.openedx.org/en/latest/community/release_notes/verawood/dev_op_release_notes.html).
This records a source compatibility review, not a full LMS deployment test.

## Runtime and dependencies

The platform's [Python metadata](https://github.com/openedx/edx-platform/blob/b5fc56a101a2a1d3fd3c3568d2719680840ca7d2/pyproject.toml)
requires Python 3.12+. Its [runtime lockfile](https://github.com/openedx/edx-platform/blob/b5fc56a101a2a1d3fd3c3568d2719680840ca7d2/requirements/edx/base.txt)
contains Django 5.2.13, django-model-utils 5.0.0, edx-django-utils 8.0.1,
and edx-completion 5.0.0.

The plugin requires Django >=5.2.13,<5.3, django-model-utils >=5.0.0,<6,
and edx-django-utils >=8.0.1,<9. These ranges accept the platform versions
without forcing an LMS dependency upgrade and allow compatible fixes.
Python 3.11 and Django 4.2 are no longer advertised or tested.
Atlas is a development translation tool, not a runtime dependency.
The platform supplies completion, opaque-keys, XBlock, and the LMS apps;
the plugin does not install a separate copy of these platform components.

`tox -e py312-verawood` tests Django 5.2.13; `tox -e py312-django52`
tests the Django 5.2 patch pinned in the test lockfile's source, `base.txt`
(currently 5.2.15; the generated test lock removes Django so tox can select it).
These are standalone plugin tests, with platform service calls mocked.
They do not reproduce the platform's entire dependency graph.

## Integration review

| Integration | Finding and action |
| --- | --- |
| `lms.djangoapps.courseware.courses.get_course_blocks_completion_summary(course_key, user)` | Signature and `complete_count`, `incomplete_count`, `locked_count` keys remain compatible. It counts units and excludes gated units from incomplete counts. No adapter change needed. |
| `lms.djangoapps.course_blocks.api.get_course_blocks` | Still accepts the explicit transformers object and `allow_start_dates_in_future`. `BlockStructureTransformers([])` has no length/truthiness override, so the empty object remains truthy and avoids the default access transformers. The unfiltered unit count remains usable. |
| `xmodule.modulestore.django.modulestore` | Still used by the upstream summary function to obtain the course usage key. |
| `CourseOverview.get_all_courses()` | Still returns a queryset supporting the backfill's ordering and `values_list`. The new catalog models do not replace this API in the reviewed branch. |
| `CourseEnrollment.objects.users_enrolled_in(course_key)` | Still returns users with active enrollments by default. The plugin's call remains valid. |
| `completion.models.BlockCompletion` | Version 5.0.0 exposes `context_key` as a learning-context key and `user_id`. Creation and changed completion submissions use Django saves, which emit the signals used here. Library contexts are also supported; the plugin now ignores keys with `is_course=False` to prevent unprocessable queue entries. This is a compatibility hardening, not a claim that library contexts first appeared in Verawood. |
| Django plugin registration | The `edx-django-utils` plugin constants and LMS/CMS entry points work with the selected 8.x dependency. No registration change needed. |
| Plugin models and migrations | Django 5.2 supports the fields, indexes, constraints, and transaction APIs used here. No schema migration is required by this update. |

The implementation sources are in the checked platform commit under
`lms/djangoapps/courseware/courses.py`, `lms/djangoapps/course_blocks/api.py`,
`openedx/core/djangoapps/content/block_structure/transformers.py`,
`openedx/core/djangoapps/content/course_overviews/models.py`, and
`common/djangoapps/student/models/course_enrollment.py`.
The completion model was inspected from the published
[edx-completion 5.0.0 distribution](https://pypi.org/project/edx-completion/5.0.0/).

## Release changes that matter operationally

The catalog backfill migration iterates course overviews and can fail on
inconsistent organization records. Complete the platform upgrade and resolve
any catalog migration failures before running this plugin's backfill.

Verawood's library and team/content-group features reinforce the need to use
learner-specific course access filtering. The plugin continues to delegate
completion to the LMS and excludes library completion events from its queue.

The documented Typesense, video storage, notification, frontend slot,
instructor dashboard, and authoring RBAC changes require no direct plugin
changes: this package does not use those integration surfaces. It also does
not read the environment's `SERVICE_VARIANT` or the removed `USE_L10N` setting.

Existing freshness limitations remain: completion save/delete signals do not
cover course publication, visibility/group membership changes, or time gates
opening without a completion event. Schedule forced backfills when needed;
the Verawood upgrade does not make the materialized summaries continuously live.

## Deployment verification

After upgrading a staging LMS and installing this plugin:

1. Run LMS migrations and system checks.
2. Backfill a known course with `backfill_course_completion_summaries --course-id
   course-v1:Org+Course+Run --force`.
3. Compare summaries against the LMS progress page for learners with complete,
   incomplete, gated, future-dated, and content-group-restricted units.
4. Save/delete a course completion, confirm one dirty row appears after commit,
   and run `process_dirty_course_completion_summaries` to verify recomputation.
5. Confirm library completion activity does not create dirty course rows.

These deployment checks require a running Verawood LMS and its backing services;
standalone unit tests cannot validate the live course transformer pipeline.
