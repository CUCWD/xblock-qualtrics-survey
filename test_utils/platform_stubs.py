"""Explicit LMS service doubles for standalone tests, with the real Ulmo score field."""
import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock


def _module(name, **attributes):
    """Install a test module and its namespace parents."""
    if name not in sys.modules:
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
        if '.' in name:
            parent, child = name.rsplit('.', 1)
            setattr(_module(parent), child, module)
    module = sys.modules[name]
    module.__dict__.update(attributes)
    return module


def _unconfigured(name):
    """Fail if a test accidentally calls an LMS service without arranging a fixture."""
    return Mock(side_effect=AssertionError(f'Configure the {name} fixture before using it.'))


def install():
    """Install only the platform import boundaries needed by the XBlock."""
    platform_root = os.environ.get('QUALTRICS_TEST_PLATFORM_ROOT')
    if not platform_root:
        raise RuntimeError('Set QUALTRICS_TEST_PLATFORM_ROOT to the Ulmo edx-platform checkout.')
    fields_path = Path(platform_root) / 'xmodule' / 'fields.py'
    if not fields_path.is_file():
        raise RuntimeError(f'Ulmo score fields are missing: {fields_path}')

    _module('xmodule')
    spec = importlib.util.spec_from_file_location('xmodule.fields', fields_path)
    fields = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fields
    spec.loader.exec_module(fields)
    sys.modules['xmodule'].fields = fields

    _module('openedx.core.djangoapps.content.course_overviews.models',
            CourseOverview=Mock(get_from_id=_unconfigured('CourseOverview.get_from_id')))
    _module('openedx.core.djangoapps.site_configuration.helpers',
            get_value=lambda key, default=None: default)
    _module('xmodule.modulestore.django', modulestore=_unconfigured('modulestore'))
    _module('lms.djangoapps.grades.tasks',
            recalculate_subsection_grade_v3=_unconfigured('grade recalculation'))
    _module('common.djangoapps.student.models',
            get_user=_unconfigured('get_user'),
            user_by_anonymous_id=_unconfigured('user_by_anonymous_id'))
