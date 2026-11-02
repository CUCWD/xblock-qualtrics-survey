Qualtrics Survey
==================

XBlock to ease linking to Qualtrics surveys.

|badge-ci|
|badge-coveralls|

The tool makes it easy for instructors to link to a Qualtrics survey
from within their course.

|image-lms-view-normal|


Installation
------------


System Administrator
~~~~~~~~~~~~~~~~~~~~

To install the XBlock on your platform,
add the following to your `requirements.txt` file:

    xblock-qualtrics-survey

You'll also need to add this to your `INSTALLED_APPS`:

    qualtricssurvey


Ulmo dependency management
~~~~~~~~~~~~~~~~~~~~~~~~~~

Provision the environment with the target edx-platform requirements first.
This XBlock declares its runtime dependencies without version pins so that
Ulmo controls the shared package versions. To install this checkout without
changing those versions, run from this repository::

    python -m pip install --no-deps .

For editable installation, use ``python -m pip install --no-deps -e .``.
These commands assume all runtime dependencies are already installed by the
platform, including its configured edx-organizations package.

``requirements/base.txt`` forwards to the unpinned ``base.in`` declarations,
and ``make upgrade`` preserves that arrangement. The other requirements files
and ``make requirements`` are for isolated development and CI environments;
do not install their pinned dependencies or constraints into edx-platform.

Course Staff
~~~~~~~~~~~~

To install the XBlock in your course,
access your `Advanced Module List`:

    Settings -> Advanced Settings -> Advanced Module List

|image-cms-settings-menu|

and add the following:

    qualtricssurvey

|image-cms-advanced-module-list|


Standalone Python tests
-----------------------

The XBlock uses LMS services that are not installed by pip. Standalone tests
use explicit service doubles from ``test_utils`` and load the real Ulmo
``ScoreField`` from an edx-platform checkout. Production imports are unchanged.

From this repository, run::

    export QUALTRICS_TEST_PLATFORM_ROOT=/path/to/ulmo/openedx-platform
    tox -e django42,django52

CI fetches ``xmodule/fields.py`` from platform commit
``46c543590c78aa1bfa846d47a4f1c5c6ec388490``. Test-only shared dependency pins
in ``requirements/test-constraints.txt`` match that Ulmo checkout; refresh them
when upgrading the target platform. Tox selects Django 4.2 for compatibility
coverage and Django 5.2.11 for Ulmo.

These tests exercise iframe rendering, resource loading, workbench scenarios,
and score handling. LMS database services, external Qualtrics requests, and
end-to-end gradebook behavior require integration tests inside edx-platform.

Run Python style and static analysis checks with ``tox -e quality``. The quality
environment uses Django 5.2.11 and the same Ulmo dependency constraints as the
tests. Its minimal Django settings do not require an edx-platform checkout.
Both pycodestyle and pylint allow 120-character lines; LMS-only imports are
excluded from pylint's import resolution. Local pylint overrides live in
``pylintrc_tweaks``; regenerate ``pylintrc`` with ``edx_lint write pylintrc``
after editing them.

Use
---


Course Staff
~~~~~~~~~~~~

To add a Qualtrics Survey link to your course:

- go to a unit in Studio
- select "Qualtrics Survey" from the Advanced Components menu

|image-cms-add|

You can now edit and preview the new component.

|image-cms-view|

Using the Studio editor, you can edit the following fields:

- display name
- survey id
- university
- link text
- message
- parameter name for userid

Note: If you plan to make use of the "Param Name" field to store User ID
data, you will need to configure your Qualtrics surveys to in turn
collect that data on Qualtrics’ end.

|image-cms-editor-1|
|image-cms-editor-2|


Qualtrics Frame Rezize
~~~~~~~~~~~~~~~~~~~~~~
Add this code to each Qualtrics survey that needs resizing in the Look and Feel > Header section.

.. code-block:: javascript

   <script>
      Qualtrics.SurveyEngine.addOnReady(function()
      {
      /* Place your JavaScript here to run when the page is fully displayed */

      // --------------------------------------------------------------------
      // Send Qualtrics survey height back to the platform for iframe resize.
      // --------------------------------------------------------------------
      (function() {
         function sendHeight() {
            var h = Math.max(
            document.body ? document.body.scrollHeight : 0,
            document.documentElement ? document.documentElement.scrollHeight : 0
            );
            window.parent.postMessage(
            { type: 'qualtrics-survey-height', height: h },
            '*'
            );
         }

         sendHeight();

         // Also send on window resize
         window.addEventListener('resize', sendHeight);

         // Resend after a brief delay in case content is still rendering
         setTimeout(sendHeight, 500);
      })();

      });
   </script>


Participants
~~~~~~~~~~~~

|image-lms-view-normal|

Students click on a link within the unit and this takes them to the survey.


.. |badge-coveralls| image:: https://coveralls.io/repos/github/Stanford-Online/xblock-qualtrics-survey/badge.svg?branch=master
   :target: https://coveralls.io/github/Stanford-Online/xblock-qualtrics-survey?branch=master
.. |badge-ci| image:: https://github.com/openedx/xblock-qualtrics-survey/workflows/Python%20CI/badge.svg?branch=master
   :target: https://github.com/openedx/xblock-qualtrics-survey/actions?query=workflow%3A%22Python+CI%22
.. |image-cms-add| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/cms-add.png
   :width: 100%
.. |image-cms-advanced-module-list| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/cms-advanced-module-list.png
   :width: 100%
.. |image-cms-editor-1| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/cms-editor-1.png
   :width: 100%
.. |image-cms-editor-2| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/cms-editor-2.png
   :width: 100%
.. |image-cms-settings-menu| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/cms-settings-menu.png
   :width: 100%
.. |image-cms-view| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/cms-view.png
   :width: 100%
.. |image-lms-view-normal| image:: https://s3-us-west-1.amazonaws.com/stanford-openedx-docs/xblocks/qualtrics-survey/static/images/lms-view-normal.png
   :width: 100%
