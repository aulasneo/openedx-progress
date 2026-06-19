"""
openedx_progress Django application initialization.
"""

from django.apps import AppConfig
from edx_django_utils.plugins.constants import PluginSettings, PluginURLs


class OpenedxProgressConfig(AppConfig):
    """
    Configuration for the openedx_progress Django application.
    """

    name = 'openedx_progress'
    verbose_name = 'Open edX Progress'
    default_auto_field = 'django.db.models.AutoField'

    plugin_app = {
        PluginURLs.CONFIG: {
            'cms.djangoapp': {
                PluginURLs.NAMESPACE: 'openedx_progress',
                PluginURLs.REGEX: r'^api/progress/',
                PluginURLs.RELATIVE_PATH: 'urls',
            },
            'lms.djangoapp': {
                PluginURLs.NAMESPACE: 'openedx_progress',
                PluginURLs.REGEX: r'^api/progress/',
                PluginURLs.RELATIVE_PATH: 'urls',
            },
        },
        PluginSettings.CONFIG: {
            'cms.djangoapp': {
                'common': {
                    PluginSettings.RELATIVE_PATH: 'settings.common',
                },
            },
            'lms.djangoapp': {
                'common': {
                    PluginSettings.RELATIVE_PATH: 'settings.common',
                },
            },
        },
    }

    def ready(self):
        """
        Register optional Open edX signal handlers when their apps are installed.
        """
        from openedx_progress.signals import register_signal_handlers  # pylint: disable=import-outside-toplevel

        register_signal_handlers()
