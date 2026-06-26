# openedx-progress

Progress tracking for Open edX students.

This Django plugin materializes learner course completion summaries for Open edX
analytics. It stores one row per learner/course pair with the counts returned by
`lms.djangoapps.courseware.courses.get_course_blocks_completion_summary` and
uses `computed_at` for when the values were last computed.

## Why this exists

In the LMS progress page, progress, also known as completion, is calculated at
runtime as:

```text
units completed / (units completed + units incomplete)
```

The caveat is that these unit counts do not include units that are locked for
that specific learner at that time. A unit can be locked because of visibility
controls, dated gates, or other course access rules.

Analytics add-ons such as Panorama often only have the total number of units
that exist in the course. They do not have learner-specific detail about how many
of those units are currently hidden or locked. As a result, analytics systems can
show a completion percentage that differs from the percentage shown in the LMS
progress page.

This plugin stores the learner-specific `complete_count`, `incomplete_count`,
and `locked_count` values in the summary table. By querying this table,
analytics systems can count locked units separately and produce a completion
calculation that more closely matches what the LMS knows about that learner at
the time the summary was computed.

For an LMS-style completion percentage, use:

```text
complete_count / (complete_count + incomplete_count)
```

If an analytics system starts from a course-wide `total_units` value, it can use
`locked_count` to derive the learner-specific denominator:

```text
complete_count / (total_units - locked_count)
```

In practice, `total_units - locked_count` should correspond to
`complete_count + incomplete_count` for the same course structure snapshot.

## Database tables

This plugin creates two tables.

### `openedx_progress_coursecompletionsummary`

Stores the latest materialized completion summary for each learner/course pair.
There is one row per `course_id` and `user_id`.

Columns:

- `id`: primary key.
- `created`: when the row was first created.
- `modified`: when the row was last saved.
- `user_id`: learner user id.
- `course_id`: Open edX course key stored as a string.
- `complete_count`: number of units completed by the learner.
- `incomplete_count`: number of visible, unlocked units not yet completed by the
  learner.
- `locked_count`: number of units currently locked or hidden for that learner.
- `percent_complete`: stored LMS-style completion ratio, calculated from
  `complete_count / (complete_count + incomplete_count)`.
- `computed_at`: when the completion summary was computed from edx-platform.

The table has a unique constraint on `course_id` and `user_id`, so repeated
backfills or dirty-queue processing update the existing learner/course summary
instead of creating duplicate rows.

### `openedx_progress_coursecompletionsummarydirty`

Stores a lightweight queue of learner/course pairs that need their completion
summary recomputed.

Columns:

- `id`: primary key.
- `created`: when the queue row was first created.
- `modified`: when the queue row was last saved.
- `user_id`: learner user id.
- `course_id`: Open edX course key stored as a string.
- `reason`: short reason why the summary was marked dirty, such as a completion
  signal.
- `attempts`: number of processing attempts.
- `last_error`: last processing error, if recomputation failed.

The table has a unique constraint on `course_id` and `user_id`, so a learner can
only have one pending recomputation row per course.

## Course completion summaries

`CourseCompletionSummary` stores:

- `user_id`
- `course_id`
- `complete_count`
- `incomplete_count`
- `locked_count`
- `percent_complete`
- `computed_at`
- `created` and `modified`

The stored `percent_complete` is calculated as:

```text
complete_count / (complete_count + incomplete_count)
```

`locked_count` is intentionally excluded from the stored denominator to match the
LMS progress page calculation. If the denominator is zero, `percent_complete` is
stored as `NULL`.

## Backfill command

Run the backfill command inside an LMS environment where edx-platform apps are
installed:

```bash
./manage.py lms backfill_course_completion_summaries --course-id course-v1:edX+DemoX+Demo_Course
```

Useful options:

- `--user-id 123` can be repeated to process specific learners.
- `--batch-size 500` controls database iteration batches.
- `--sleep 0.5` pauses between batches.
- `--dry-run` selects learners without writing rows.
- `--force` recomputes rows that already exist.

## Dirty queue

When `completion.models.BlockCompletion` is importable, the plugin registers
`post_save` and `post_delete` signal handlers that enqueue learner/course pairs
in `CourseCompletionSummaryDirty` after transaction commit. Process queued rows
with:

```bash
./manage.py lms process_dirty_course_completion_summaries
```

## Getting help

For anything non-trivial, open an issue in this repository with as many details
as you can provide:

<https://github.com/aulasneo/openedx-progress/issues>

## License

The code in this repository is licensed under the AGPL 3.0 unless otherwise
noted. See [LICENSE.txt](LICENSE.txt) for details.

## Contributing

This project is currently accepting all types of contributions, including bug
fixes, security fixes, maintenance work, and new features. Please discuss new
feature ideas with the maintainers before beginning development to maximize the
chances of your change being accepted.

## Security

Please do not report security issues in public. Email support@aulasneo.com.

## Disclaimer

Part of this code was developed with the aid of AI tools.

