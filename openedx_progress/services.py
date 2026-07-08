"""
Services for materializing Open edX learner course completion summaries.
"""
# pylint: disable=import-outside-toplevel,import-error
import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from openedx_progress.models import CourseCompletionSummary, CourseCompletionSummaryDirty

PERCENT_COMPLETE_QUANT = Decimal('0.00001')
log = logging.getLogger(__name__)


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


def _get_unfiltered_course_unit_count(course_key, user):
    """
    Return the number of course units before learner access transformers prune them.
    """
    from lms.djangoapps.course_blocks.api import get_course_blocks
    from openedx.core.djangoapps.content.block_structure.transformers import BlockStructureTransformers
    from xmodule.modulestore.django import modulestore

    store = modulestore()
    course_usage_key = store.make_course_usage_key(course_key)
    block_data = get_course_blocks(
        user,
        course_usage_key,
        transformers=BlockStructureTransformers([]),
        allow_start_dates_in_future=True,
    )

    unit_count = 0
    for section_key in block_data.get_children(course_usage_key):
        for subsection_key in block_data.get_children(section_key):
            unit_count += len(block_data.get_children(subsection_key))
    return unit_count


def calculate_locked_count(summary_locked_count, complete_count, incomplete_count, course_key, user):
    """
    Calculate locked units, including units removed by learner access filtering.
    """
    locked_count = int(summary_locked_count)
    try:
        total_unit_count = _get_unfiltered_course_unit_count(course_key, user)
    except ImportError:
        return locked_count
    except Exception:  # pylint: disable=broad-except
        log.exception('Unable to calculate unfiltered course unit count for %s.', course_key)
        return locked_count

    derived_locked_count = max(total_unit_count - complete_count - incomplete_count, 0)
    return max(locked_count, derived_locked_count)


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
    locked_count = calculate_locked_count(
        summary['locked_count'],
        complete_count,
        incomplete_count,
        course_key,
        user,
    )

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
