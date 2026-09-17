"""
Tests for completion signals and transaction boundaries.
"""
from types import SimpleNamespace

import pytest

from openedx_progress import signals
from openedx_progress.models import CourseCompletionSummaryDirty


class LearningContext:
    """Represent the course/library distinction exposed by opaque learning keys."""

    def __init__(self, is_course):
        self.is_course = is_course

    def __str__(self):
        return 'course-v1:Org+Course+Run' if self.is_course else 'lib:Org:Library'


@pytest.mark.django_db
@pytest.mark.parametrize('handler', [signals.block_completion_saved, signals.block_completion_deleted])
def test_course_completion_enqueued_after_commit(handler, django_capture_on_commit_callbacks):
    """Both completion signals enqueue a course only after the transaction commits."""
    instance = SimpleNamespace(context_key=LearningContext(True), user_id=7)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        handler(sender=None, instance=instance)
        assert not CourseCompletionSummaryDirty.objects.exists()
    assert len(callbacks) == 1
    dirty = CourseCompletionSummaryDirty.objects.get()
    assert dirty.course_id == str(instance.context_key)
    assert dirty.user_id == 7
    assert dirty.reason == handler.__name__


@pytest.mark.django_db
@pytest.mark.parametrize('handler', [signals.block_completion_saved, signals.block_completion_deleted])
def test_library_completion_not_enqueued(handler, django_capture_on_commit_callbacks):
    """Library learning contexts cannot be processed by the course summary API."""
    instance = SimpleNamespace(context_key=LearningContext(False), user_id=7)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        handler(sender=None, instance=instance)
    assert callbacks == []
    assert not CourseCompletionSummaryDirty.objects.exists()
