"""
Common settings for openedx_progress.
"""


def plugin_settings(settings):  # pylint: disable=unused-argument
    """
    Apply common Open edX settings for openedx_progress.

    The plugin currently does not require runtime settings, but the hook is
    registered so LMS and CMS can load the Django plugin consistently.
    """
