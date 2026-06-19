"""
Optional signal handlers for keeping completion summaries fresh.
"""
# pylint: disable=import-outside-toplevel
from django.db import transaction
from django.db.models.signals import post_delete, post_save

from openedx_progress import services


def _block_completion_model():
    """
    Return the Open edX BlockCompletion model when it is installed.
    """
    try:
        from completion.models import BlockCompletion
    except (ImportError, RuntimeError):
        return None
    return BlockCompletion


def _course_key_from_completion(instance):
    """
    Extract a course key from a BlockCompletion instance.
    """
    context_key = getattr(instance, 'context_key', None)
    if context_key is not None:
        return context_key

    block_key = getattr(instance, 'block_key', None)
    return getattr(block_key, 'course_key', None)


def _user_id_from_completion(instance):
    """
    Extract a user id from a BlockCompletion instance.
    """
    return getattr(instance, 'user_id', None) or getattr(getattr(instance, 'user', None), 'id', None)


def _mark_dirty_from_completion(instance, reason):
    """
    Queue a summary recomputation for a BlockCompletion change.
    """
    course_key = _course_key_from_completion(instance)
    user_id = _user_id_from_completion(instance)
    if course_key is None or user_id is None:
        return

    transaction.on_commit(
        lambda: services.mark_completion_summary_dirty(course_key, user_id, reason=reason)
    )


def block_completion_saved(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Mark a learner/course summary dirty after a completion save.
    """
    _mark_dirty_from_completion(instance, 'block_completion_saved')


def block_completion_deleted(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Mark a learner/course summary dirty after a completion delete.
    """
    _mark_dirty_from_completion(instance, 'block_completion_deleted')


def register_signal_handlers():
    """
    Connect optional completion signals.
    """
    block_completion = _block_completion_model()
    if block_completion is None:
        return

    post_save.connect(
        block_completion_saved,
        sender=block_completion,
        dispatch_uid='openedx_progress.block_completion_saved',
    )
    post_delete.connect(
        block_completion_deleted,
        sender=block_completion,
        dispatch_uid='openedx_progress.block_completion_deleted',
    )
