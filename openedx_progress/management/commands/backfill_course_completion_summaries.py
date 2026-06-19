"""
Backfill learner course completion summaries.
"""
# pylint: disable=import-outside-toplevel,import-error
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from openedx_progress import services
from openedx_progress.models import CourseCompletionSummary


def parse_course_key(course_id):
    """
    Parse a course key when opaque-keys is available.
    """
    try:
        from opaque_keys.edx.keys import CourseKey
    except ImportError:
        return course_id

    return CourseKey.from_string(course_id)


def enrolled_users_for_course(course_key):
    """
    Return active users enrolled in a course.
    """
    from common.djangoapps.student.models import CourseEnrollment

    manager = CourseEnrollment.objects
    if hasattr(manager, 'users_enrolled_in'):
        return manager.users_enrolled_in(course_key)

    enrollments = manager.select_related('user').filter(course_id=str(course_key), is_active=True)
    return get_user_model().objects.filter(id__in=enrollments.values('user_id'))


def user_queryset_for_ids(user_ids):
    """
    Return users for explicit ids, preserving database batching behavior.
    """
    return get_user_model().objects.filter(id__in=user_ids).order_by('id')


def batched(iterable, batch_size):
    """
    Yield lists of up to batch_size objects from iterable.
    """
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


class Command(BaseCommand):
    """
    Materialize course completion summaries for learners in a course.
    """

    help = 'Backfill learner course completion summaries for one Open edX course.'

    def add_arguments(self, parser):
        parser.add_argument('--course-id', required=True, help='Opaque course id, for example course-v1:Org+Num+Run.')
        parser.add_argument(
            '--user-id',
            dest='user_ids',
            action='append',
            type=int,
            default=None,
            help='Optional learner user id. Can be supplied multiple times.',
        )
        parser.add_argument('--batch-size', type=int, default=500, help='Number of learners to process per batch.')
        parser.add_argument('--sleep', type=float, default=0, help='Seconds to sleep between batches.')
        parser.add_argument('--dry-run', action='store_true', help='Compute work without writing summary rows.')
        parser.add_argument('--force', action='store_true', help='Recompute rows that already exist.')

    def handle(self, *args, **options):
        course_id = options['course_id']
        course_key = parse_course_key(course_id)
        batch_size = options['batch_size']
        sleep_seconds = options['sleep']
        dry_run = options['dry_run']
        force = options['force']

        if batch_size < 1:
            raise CommandError('--batch-size must be greater than 0.')
        if sleep_seconds < 0:
            raise CommandError('--sleep cannot be negative.')

        users = self._users_for_options(course_key, options['user_ids'])
        stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
        }
        failures = []

        for batch_number, user_batch in enumerate(batched(self._iter_users(users, batch_size), batch_size), start=1):
            for user in user_batch:
                try:
                    action = self._process_user(course_key, user, force=force, dry_run=dry_run)
                except Exception as exc:  # pylint: disable=broad-except
                    stats['failed'] += 1
                    failures.append((getattr(user, 'id', user), str(exc)))
                    self.stderr.write('Failed user {}: {}'.format(getattr(user, 'id', user), exc))
                    continue

                stats['processed'] += 1
                stats[action] += 1

            self.stdout.write(
                'Batch {} complete: processed={}, updated={}, skipped={}, failed={}'.format(
                    batch_number,
                    stats['processed'],
                    stats['updated'],
                    stats['skipped'],
                    stats['failed'],
                )
            )
            if sleep_seconds:
                time.sleep(sleep_seconds)

        self.stdout.write(
            'Done: processed={}, updated={}, skipped={}, failed={}'.format(
                stats['processed'],
                stats['updated'],
                stats['skipped'],
                stats['failed'],
            )
        )

        if failures:
            raise CommandError('{} learner(s) failed while backfilling summaries.'.format(len(failures)))

    def _users_for_options(self, course_key, user_ids):
        """
        Return the user queryset or iterable requested by command options.
        """
        if user_ids:
            return user_queryset_for_ids(user_ids)
        return enrolled_users_for_course(course_key)

    def _iter_users(self, users, batch_size):
        """
        Iterate users with database chunking when available.
        """
        if hasattr(users, 'iterator'):
            return users.iterator(chunk_size=batch_size)
        return iter(users)

    def _process_user(self, course_key, user, force, dry_run):
        """
        Process one learner and return the stats bucket to increment.
        """
        exists = CourseCompletionSummary.objects.filter(course_id=str(course_key), user_id=user.id).exists()
        if exists and not force:
            return 'skipped'

        if dry_run:
            return 'updated'

        services.upsert_completion_summary(course_key, user)
        return 'updated'
