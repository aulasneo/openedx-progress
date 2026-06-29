"""
Tests for completion summary management commands.
"""
import sys
import types
from io import StringIO
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
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


def test_course_keys_from_overviews_reads_course_overview_class(monkeypatch):
    """
    The all-course source is CourseOverview.get_all_courses().
    """
    module_names = [
        'openedx',
        'openedx.core',
        'openedx.core.djangoapps',
        'openedx.core.djangoapps.content',
        'openedx.core.djangoapps.content.course_overviews',
        'openedx.core.djangoapps.content.course_overviews.models',
    ]
    for module_name in module_names:
        module = types.ModuleType(module_name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, module_name, module)

    course_ids = [
        'course-v1:edX+DemoX+Demo_Course',
        'course-v1:edX+OtherX+Other_Course',
    ]
    overview_queryset = Mock()
    overview_queryset.order_by.return_value = overview_queryset
    overview_queryset.values_list.return_value = course_ids
    course_overview = Mock()
    course_overview.get_all_courses.return_value = overview_queryset
    sys.modules['openedx.core.djangoapps.content.course_overviews.models'].CourseOverview = course_overview

    assert backfill_command.course_keys_from_overviews() == course_ids
    course_overview.get_all_courses.assert_called_once_with()
    overview_queryset.order_by.assert_called_once_with('id')
    overview_queryset.values_list.assert_called_once_with('id', flat=True)


@pytest.mark.django_db
def test_backfill_without_course_id_processes_all_course_overviews(monkeypatch):
    """
    Without a course id, the command processes every course from CourseOverview.
    """
    user_model = get_user_model()
    learner_1 = user_model.objects.create_user(username='learner-1')
    learner_2 = user_model.objects.create_user(username='learner-2')
    course_ids = [
        'course-v1:edX+DemoX+Demo_Course',
        'course-v1:edX+OtherX+Other_Course',
    ]
    enrolled_course_ids = []
    _mock_summary(monkeypatch, complete_count=2, incomplete_count=2, locked_count=1)

    def fake_enrolled_users_for_course(course_key):
        enrolled_course_ids.append(str(course_key))
        if str(course_key) == course_ids[0]:
            return user_model.objects.filter(id=learner_1.id).order_by('id')
        return user_model.objects.filter(id=learner_2.id).order_by('id')

    monkeypatch.setattr(backfill_command, 'course_keys_from_overviews', lambda: course_ids)
    monkeypatch.setattr(backfill_command, 'enrolled_users_for_course', fake_enrolled_users_for_course)

    call_command(
        'backfill_course_completion_summaries',
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert enrolled_course_ids == course_ids
    assert set(CourseCompletionSummary.objects.values_list('course_id', 'user_id')) == {
        (course_ids[0], learner_1.id),
        (course_ids[1], learner_2.id),
    }


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
    assert 'RuntimeError: summary failed' in stderr.getvalue()
    assert CourseCompletionSummary.objects.filter(user_id=succeeding.id).exists()
