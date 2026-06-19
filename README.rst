openedx-progress
################

.. note::

  This README was auto-generated. Maintainer: please review its contents and
  update all relevant sections. Instructions to you are marked with
  "PLACEHOLDER" or "TODO". Update or remove those sections, and remove this
  note when you are done.

|pypi-badge| |ci-badge| |codecov-badge| |doc-badge| |pyversions-badge|
|license-badge| |status-badge|

Purpose
*******

Progress tracking for Open edX students.

This Django plugin materializes learner course completion summaries for Open edX analytics.  It stores one row per
learner/course pair with the counts returned by
``lms.djangoapps.courseware.courses.get_course_blocks_completion_summary`` and a timestamp for when the values were
computed.

Course Completion Summaries
***************************

``CourseCompletionSummary`` stores:

* ``user_id``
* ``course_id``
* ``complete_count``
* ``incomplete_count``
* ``locked_count``
* ``percent_complete``
* ``computed_at``
* ``created`` and ``modified``

``percent_complete`` is calculated as::

  complete_count / (complete_count + incomplete_count)

``locked_count`` is intentionally excluded from the denominator to match LMS courseware behavior.  If the denominator is
zero, ``percent_complete`` is stored as ``NULL``.

Backfill Command
================

Run the backfill command inside an LMS environment where edx-platform apps are installed::

  ./manage.py lms backfill_course_completion_summaries --course-id course-v1:edX+DemoX+Demo_Course

Useful options:

* ``--user-id 123`` can be repeated to process specific learners.
* ``--batch-size 500`` controls database iteration batches.
* ``--sleep 0.5`` pauses between batches.
* ``--dry-run`` selects learners without writing rows.
* ``--force`` recomputes rows that already exist.

Dirty Queue
===========

When ``completion.models.BlockCompletion`` is importable, the plugin registers ``post_save`` and ``post_delete`` signal
handlers that enqueue learner/course pairs in ``CourseCompletionSummaryDirty`` after transaction commit.  Process queued
rows with::

  ./manage.py lms process_dirty_course_completion_summaries

Getting Started with Development
********************************

Please see the Open edX documentation for `guidance on Python development`_ in this repo.

.. _guidance on Python development: https://docs.openedx.org/en/latest/developers/how-tos/get-ready-for-python-dev.html

Deploying
*********

TODO: How can a new user go about deploying this component? Is it just a few
commands? Is there a larger how-to that should be linked here?

PLACEHOLDER: For details on how to deploy this component, see the `deployment how-to`_.

.. _deployment how-to: https://docs.openedx.org/projects/openedx-progress/how-tos/how-to-deploy-this-component.html

Getting Help
************

Documentation
=============

PLACEHOLDER: Start by going through `the documentation`_.  If you need more help see below.

.. _the documentation: https://docs.openedx.org/projects/openedx-progress

(TODO: `Set up documentation <https://openedx.atlassian.net/wiki/spaces/DOC/pages/21627535/Publish+Documentation+on+Read+the+Docs>`_)

More Help
=========

If you're having trouble, we have discussion forums at
https://discuss.openedx.org where you can connect with others in the
community.

Our real-time conversations are on Slack. You can request a `Slack
invitation`_, then join our `community Slack workspace`_.

For anything non-trivial, the best path is to open an issue in this
repository with as many details about the issue you are facing as you
can provide.

https://github.com/aulasneo/openedx-progress/issues

For more information about these options, see the `Getting Help <https://openedx.org/getting-help>`__ page.

.. _Slack invitation: https://openedx.org/slack
.. _community Slack workspace: https://openedx.slack.com/

License
*******

The code in this repository is licensed under the AGPL 3.0 unless
otherwise noted.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.

Contributing
************

Contributions are very welcome.
Please read `How To Contribute <https://openedx.org/r/how-to-contribute>`_ for details.

This project is currently accepting all types of contributions, bug fixes,
security fixes, maintenance work, or new features.  However, please make sure
to discuss your new feature idea with the maintainers before beginning development
to maximize the chances of your change being accepted.
You can start a conversation by creating a new issue on this repo summarizing
your idea.

The Open edX Code of Conduct
****************************

All community members are expected to follow the `Open edX Code of Conduct`_.

.. _Open edX Code of Conduct: https://openedx.org/code-of-conduct/

People
******

The assigned maintainers for this component and other project details may be
found in `Backstage`_. Backstage pulls this data from the ``catalog-info.yaml``
file in this repo.

.. _Backstage: https://backstage.openedx.org/catalog/default/component/openedx-progress

Reporting Security Issues
*************************

Please do not report security issues in public. Please email security@openedx.org.

.. |pypi-badge| image:: https://img.shields.io/pypi/v/openedx-progress.svg
    :target: https://pypi.python.org/pypi/openedx-progress/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/aulasneo/openedx-progress/actions/workflows/ci.yml/badge.svg?branch=main
    :target: https://github.com/aulasneo/openedx-progress/actions/workflows/ci.yml
    :alt: CI

.. |codecov-badge| image:: https://codecov.io/github/aulasneo/openedx-progress/coverage.svg?branch=main
    :target: https://codecov.io/github/aulasneo/openedx-progress?branch=main
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/openedx-progress/badge/?version=latest
    :target: https://docs.openedx.org/projects/openedx-progress
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/openedx-progress.svg
    :target: https://pypi.python.org/pypi/openedx-progress/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/aulasneo/openedx-progress.svg
    :target: https://github.com/aulasneo/openedx-progress/blob/main/LICENSE.txt
    :alt: License

.. TODO: Choose one of the statuses below and remove the other status-badge lines.
.. |status-badge| image:: https://img.shields.io/badge/Status-Experimental-yellow
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Maintained-brightgreen
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Deprecated-orange
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Unsupported-red
