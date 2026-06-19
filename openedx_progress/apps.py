"""
openedx_progress Django application initialization.
"""

from django.apps import AppConfig


class OpenedxProgressConfig(AppConfig):
    """
    Configuration for the openedx_progress Django application.
    """

    default_auto_field = 'django.db.models.AutoField'
    name = 'openedx_progress'

    def ready(self):
        """
        Register optional Open edX signal handlers when their apps are installed.
        """
        from openedx_progress.signals import register_signal_handlers  # pylint: disable=import-outside-toplevel

        register_signal_handlers()
