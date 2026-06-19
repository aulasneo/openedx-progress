"""
Tests for completion summary services.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from openedx_progress import services
from openedx_progress.models import CourseCompletionSummary, CourseCompletionSummaryDirty


@pytest.mark.django_db
def test_compute_completion_summary_excludes_locked_count(monkeypatch):
    """
    Percent complete excludes locked blocks from the denominator.
    """
    user = get_user_model().objects.create_user(username='learner')

    monkeypatch.setattr(
        services,
        '_get_course_blocks_completion_summary',
        lambda course_key, user: {
            'complete_count': 2,
            'incomplete_count': 3,
            'locked_count': 95,
        },
    )

    summary = services.compute_completion_summary('course-v1:edX+DemoX+Demo_Course', user)

    assert summary['complete_count'] == 2
    assert summary['incomplete_count'] == 3
    assert summary['locked_count'] == 95
    assert summary['percent_complete'] == Decimal('0.40000')


@pytest.mark.django_db
def test_compute_completion_summary_uses_null_percent_when_denominator_is_zero(monkeypatch):
    """
    A course with no complete or incomplete blocks stores no percent value.
    """
    user = get_user_model().objects.create_user(username='learner')

    monkeypatch.setattr(
        services,
        '_get_course_blocks_completion_summary',
        lambda course_key, user: {
            'complete_count': 0,
            'incomplete_count': 0,
            'locked_count': 4,
        },
    )

    summary = services.compute_completion_summary('course-v1:edX+DemoX+Demo_Course', user)

    assert summary['percent_complete'] is None


@pytest.mark.django_db
def test_upsert_completion_summary_is_idempotent(monkeypatch):
    """
    Re-running an upsert updates the same learner/course row.
    """
    user = get_user_model().objects.create_user(username='learner')
    counts = {
        'complete_count': 1,
        'incomplete_count': 1,
        'locked_count': 0,
    }

    monkeypatch.setattr(
        services,
        '_get_course_blocks_completion_summary',
        lambda course_key, user: counts,
    )

    first = services.upsert_completion_summary('course-v1:edX+DemoX+Demo_Course', user)
    counts.update(
        {
            'complete_count': 3,
            'incomplete_count': 1,
            'locked_count': 2,
        }
    )
    second = services.upsert_completion_summary('course-v1:edX+DemoX+Demo_Course', user)

    assert first.id == second.id
    assert CourseCompletionSummary.objects.count() == 1
    assert second.complete_count == 3
    assert second.incomplete_count == 1
    assert second.locked_count == 2
    assert second.percent_complete == Decimal('0.75000')


@pytest.mark.django_db
def test_mark_completion_summary_dirty_upserts_queue_row():
    """
    Dirty marking is idempotent for one learner/course pair.
    """
    user = get_user_model().objects.create_user(username='learner')

    services.mark_completion_summary_dirty('course-v1:edX+DemoX+Demo_Course', user, reason='first')
    dirty = services.mark_completion_summary_dirty('course-v1:edX+DemoX+Demo_Course', user, reason='second')

    assert CourseCompletionSummaryDirty.objects.count() == 1
    assert dirty.reason == 'second'
