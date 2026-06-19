"""
Process queued dirty learner course completion summaries.
"""
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from openedx_progress import services
from openedx_progress.management.commands.backfill_course_completion_summaries import batched, parse_course_key
from openedx_progress.models import CourseCompletionSummaryDirty


class Command(BaseCommand):
    """
    Recompute summaries previously marked dirty by event hooks.
    """

    help = 'Process queued learner course completion summary recomputations.'

    def add_arguments(self, parser):
        parser.add_argument('--course-id', default=None, help='Optional course id to restrict processing.')
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='Optional learner user id to restrict processing.',
        )
        parser.add_argument('--limit', type=int, default=None, help='Maximum dirty rows to process.')
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of dirty rows to process per batch.',
        )
        parser.add_argument(
            '--sleep',
            type=float,
            default=0,
            help='Seconds to sleep between batches.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report queued rows without recomputing or deleting them.',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        sleep_seconds = options['sleep']
        if batch_size < 1:
            raise CommandError('--batch-size must be greater than 0.')
        if sleep_seconds < 0:
            raise CommandError('--sleep cannot be negative.')

        dirty_rows = self._dirty_rows(options)
        stats = {
            'processed': 0,
            'updated': 0,
            'failed': 0,
        }

        dirty_batches = batched(dirty_rows.iterator(chunk_size=batch_size), batch_size)
        for batch_number, dirty_batch in enumerate(dirty_batches, start=1):
            for dirty in dirty_batch:
                try:
                    if options['dry_run']:
                        stats['updated'] += 1
                    else:
                        self._process_dirty_row(dirty)
                        stats['updated'] += 1
                except Exception as exc:  # pylint: disable=broad-except
                    stats['failed'] += 1
                    dirty.attempts += 1
                    dirty.last_error = str(exc)
                    dirty.save(update_fields=['attempts', 'last_error', 'modified'])
                    self.stderr.write('Failed dirty row {}: {}'.format(dirty.id, exc))
                    continue

                stats['processed'] += 1

            self.stdout.write(
                'Batch {} complete: processed={}, updated={}, failed={}'.format(
                    batch_number,
                    stats['processed'],
                    stats['updated'],
                    stats['failed'],
                )
            )
            if sleep_seconds:
                time.sleep(sleep_seconds)

        self.stdout.write(
            'Done: processed={}, updated={}, failed={}'.format(
                stats['processed'],
                stats['updated'],
                stats['failed'],
            )
        )
        if stats['failed']:
            raise CommandError('{} dirty row(s) failed while processing summaries.'.format(stats['failed']))

    def _dirty_rows(self, options):
        """
        Return the queued rows matching command filters.
        """
        queryset = CourseCompletionSummaryDirty.objects.order_by('modified', 'id')
        if options['course_id']:
            queryset = queryset.filter(course_id=options['course_id'])
        if options['user_id']:
            queryset = queryset.filter(user_id=options['user_id'])
        if options['limit']:
            queryset = queryset[:options['limit']]
        return queryset

    def _process_dirty_row(self, dirty):
        """
        Recompute and remove one dirty queue row.
        """
        user = get_user_model().objects.get(id=dirty.user_id)
        services.upsert_completion_summary(parse_course_key(dirty.course_id), user)
        dirty.delete()
