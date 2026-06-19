"""
Database models for openedx_progress.
"""
from django.db import models
from model_utils.models import TimeStampedModel


class CourseCompletionSummary(TimeStampedModel):
    """
    Materialized learner completion counts for a course.

    .. pii: The user_id field stores an identifier linked to a learner.
       The course_id and completion counts are educational records.
    .. pii_types: id, other
    .. pii_retirement: retained
    """

    user_id = models.PositiveIntegerField(db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)
    complete_count = models.PositiveIntegerField(default=0)
    incomplete_count = models.PositiveIntegerField(default=0)
    locked_count = models.PositiveIntegerField(default=0)
    percent_complete = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        null=True,
        blank=True,
    )
    computed_at = models.DateTimeField(db_index=True)

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        return '<CourseCompletionSummary, course_id: {}, user_id: {}>'.format(self.course_id, self.user_id)

    class Meta:
        """
        Model metadata.
        """

        constraints = [
            models.UniqueConstraint(
                fields=['course_id', 'user_id'],
                name='op_unique_course_user_summary',
            ),
        ]
        indexes = [
            models.Index(fields=['course_id', 'user_id'], name='op_course_user_idx'),
            models.Index(fields=['course_id', 'computed_at'], name='op_course_computed_idx'),
            models.Index(fields=['user_id', 'computed_at'], name='op_user_computed_idx'),
        ]


class CourseCompletionSummaryDirty(TimeStampedModel):
    """
    Queue entry for recomputing one learner's course completion summary.

    .. pii: The user_id field stores an identifier linked to a learner.
       The course_id and reason fields may reveal learning activity.
    .. pii_types: id, other
    .. pii_retirement: retained
    """

    user_id = models.PositiveIntegerField(db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        return '<CourseCompletionSummaryDirty, course_id: {}, user_id: {}>'.format(self.course_id, self.user_id)

    class Meta:
        """
        Model metadata.
        """

        constraints = [
            models.UniqueConstraint(
                fields=['course_id', 'user_id'],
                name='op_unique_dirty_course_user',
            ),
        ]
        indexes = [
            models.Index(fields=['course_id', 'user_id'], name='op_dirty_course_user_idx'),
            models.Index(fields=['modified'], name='op_dirty_modified_idx'),
        ]
