"""
Services for materializing Open edX learner course completion summaries.
"""
# pylint: disable=import-outside-toplevel,import-error
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from openedx_progress.models import CourseCompletionSummary, CourseCompletionSummaryDirty

PERCENT_COMPLETE_QUANT = Decimal('0.00001')


def _course_id_for_storage(course_key):
    """
    Convert an opaque course key to its stable stored string form.
    """
    return str(course_key)


def _user_id(user):
    """
    Return the integer primary key from a user object or user id value.
    """
    return int(getattr(user, 'id', user))


def _get_course_blocks_completion_summary(course_key, user):
    """
    Load edx-platform's completion summary function lazily.
    """
    from lms.djangoapps.courseware.courses import get_course_blocks_completion_summary

    return get_course_blocks_completion_summary(course_key, user)


def calculate_percent_complete(complete_count, incomplete_count):
    """
    Calculate complete / (complete + incomplete), excluding locked blocks.
    """
    denominator = complete_count + incomplete_count
    if denominator == 0:
        return None

    return (
        Decimal(complete_count) / Decimal(denominator)
    ).quantize(PERCENT_COMPLETE_QUANT, rounding=ROUND_HALF_UP)


def compute_completion_summary(course_key, user):
    """
    Return persisted completion summary values for a learner and course.
    """
    summary = _get_course_blocks_completion_summary(course_key, user)
    complete_count = int(summary['complete_count'])
    incomplete_count = int(summary['incomplete_count'])
    locked_count = int(summary['locked_count'])

    return {
        'course_id': _course_id_for_storage(course_key),
        'user_id': _user_id(user),
        'complete_count': complete_count,
        'incomplete_count': incomplete_count,
        'locked_count': locked_count,
        'percent_complete': calculate_percent_complete(complete_count, incomplete_count),
        'computed_at': timezone.now(),
    }


def upsert_completion_summary(course_key, user):
    """
    Compute and persist the summary row for a learner and course.
    """
    values = compute_completion_summary(course_key, user)
    course_id = values.pop('course_id')
    user_id = values.pop('user_id')

    summary, _created = CourseCompletionSummary.objects.update_or_create(
        course_id=course_id,
        user_id=user_id,
        defaults=values,
    )
    return summary


def mark_completion_summary_dirty(course_key, user, reason=''):
    """
    Mark a learner/course summary for later recomputation.
    """
    dirty, _created = CourseCompletionSummaryDirty.objects.update_or_create(
        course_id=_course_id_for_storage(course_key),
        user_id=_user_id(user),
        defaults={
            'reason': reason,
            'last_error': '',
        },
    )
    return dirty


def mark_completion_summary_dirty_on_commit(course_key, user, reason=''):
    """
    Mark a learner/course summary dirty after the current transaction commits.
    """
    transaction.on_commit(lambda: mark_completion_summary_dirty(course_key, user, reason=reason))
