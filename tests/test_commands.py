"""
Tests for completion summary management commands.
"""
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from openedx_progress import services
from openedx_progress.management.commands import backfill_course_completion_summaries as backfill_command
from openedx_progress.models import CourseCompletionSummary


def _mock_summary(monkeypatch, complete_count=1, incomplete_count=1, locked_count=0):
    """
    Mock the edx-platform completion summary function.
    """
    monkeypatch.setattr(
        services,
        '_get_course_blocks_completion_summary',
        lambda course_key, user: {
            'complete_count': complete_count,
            'incomplete_count': incomplete_count,
            'locked_count': locked_count,
        },
    )


@pytest.mark.django_db
def test_backfill_processes_active_enrollments(monkeypatch):
    """
    Without explicit users, the command processes enrolled learners for the course.
    """
    user_model = get_user_model()
    learner_1 = user_model.objects.create_user(username='learner-1')
    learner_2 = user_model.objects.create_user(username='learner-2')
    _mock_summary(monkeypatch, complete_count=2, incomplete_count=2, locked_count=1)

    monkeypatch.setattr(
        backfill_command,
        'enrolled_users_for_course',
        lambda course_key: user_model.objects.filter(id__in=[learner_1.id, learner_2.id]).order_by('id'),
    )

    call_command(
        'backfill_course_completion_summaries',
        '--course-id',
        'course-v1:edX+DemoX+Demo_Course',
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert CourseCompletionSummary.objects.count() == 2
    assert set(CourseCompletionSummary.objects.values_list('user_id', flat=True)) == {learner_1.id, learner_2.id}


@pytest.mark.django_db
def test_backfill_dry_run_does_not_write(monkeypatch):
    """
    Dry-run evaluates the selected learners without writing summary rows.
    """
    learner = get_user_model().objects.create_user(username='learner')
    _mock_summary(monkeypatch)

    call_command(
        'backfill_course_completion_summaries',
        '--course-id',
        'course-v1:edX+DemoX+Demo_Course',
        '--user-id',
        str(learner.id),
        '--dry-run',
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert CourseCompletionSummary.objects.count() == 0


@pytest.mark.django_db
def test_backfill_failures_are_logged_and_processing_continues(monkeypatch):
    """
    One bad learner does not prevent later learners from being processed.
    """
    user_model = get_user_model()
    failing = user_model.objects.create_user(username='failing')
    succeeding = user_model.objects.create_user(username='succeeding')
    stderr = StringIO()

    def fake_upsert(course_key, user):
        if user.id == failing.id:
            raise RuntimeError('summary failed')

        return CourseCompletionSummary.objects.create(
            course_id=str(course_key),
            user_id=user.id,
            complete_count=1,
            incomplete_count=0,
            locked_count=0,
            percent_complete=1,
            computed_at=timezone.now(),
        )

    monkeypatch.setattr(backfill_command.services, 'upsert_completion_summary', fake_upsert)

    with pytest.raises(CommandError):
        call_command(
            'backfill_course_completion_summaries',
            '--course-id',
            'course-v1:edX+DemoX+Demo_Course',
            '--user-id',
            str(failing.id),
            '--user-id',
            str(succeeding.id),
            stdout=StringIO(),
            stderr=stderr,
        )

    assert 'Failed user {}'.format(failing.id) in stderr.getvalue()
    assert CourseCompletionSummary.objects.filter(user_id=succeeding.id).exists()
