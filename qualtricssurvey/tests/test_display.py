"""Exercise real iframe rendering with explicit course and runtime fixtures."""
import re
import unittest
from html import unescape
from unittest import mock
from urllib.parse import parse_qs, urlparse

from opaque_keys.edx.keys import CourseKey
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds
from xblock.runtime import NullI18nService
from xblock.scorable import Score

from qualtricssurvey.xblocks import QualtricsSurvey


def mock_an_xblock(**kwargs):
    """Build an XBlock with a saved score and deterministic course metadata."""
    course_id = CourseKey.from_string('course-v1:example+course+run')
    usage_id = course_id.make_usage_key('qualtricssurvey', 'survey')
    runtime = mock.Mock(course_id=course_id, anonymous_student_id='anonymous-learner')
    runtime.service.return_value = NullI18nService()
    values = {
        'survey_id': 'SV_test',
        'your_university': 'example',
        'course_name_override': 'Test Course',
        'course_term_override': 'Fall',
        'course_start_date_override': '2026-01-01',
        'course_end_date_override': '2026-12-31',
        'course_instructors_override': ['Test Instructor'],
    }
    values.update(kwargs)
    block = QualtricsSurvey(runtime, DictFieldData(values), ScopeIds('learner', 'qualtricssurvey', usage_id, usage_id))
    block.xmodule_runtime = runtime
    block.location = usage_id
    block.score = Score(0, 5)
    return block


class TestRender(unittest.TestCase):
    """Validate iframe markup, query parameters, and bundled resources."""

    def setUp(self):
        self.xblock = mock_an_xblock()
        section = mock.patch.object(
            QualtricsSurvey, 'module_name', new_callable=mock.PropertyMock, return_value='Section'
        )
        section.start()
        self.addCleanup(section.stop)
        network = mock.patch(
            'requests.sessions.Session.request', side_effect=AssertionError('Unexpected network call')
        )
        network.start()
        self.addCleanup(network.stop)

    def test_render(self):
        fragment = self.xblock.student_view()
        self.assertIn('qualtricssurvey_block', fragment.content)
        self.assertEqual(fragment.js_init_fn, 'QualtricsSurveyView')
        self.assertTrue(any('QualtricsSurveyView' in resource.data for resource in fragment.resources))
        self.assertTrue(any('.qualtricssurvey_block' in resource.data for resource in fragment.resources))

    def test_student_view(self):
        content = self.xblock.student_view().content
        source = re.search(r'<iframe[^>]+src="([^"]+)"', content).group(1)
        url = urlparse(unescape(source))
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.netloc, 'example.qualtrics.com')
        self.assertEqual(url.path, '/jfe/form/SV_test')
        params = parse_qs(url.query)
        self.assertEqual(params['platform_anonymous_user_id'], ['anonymous-learner'])
        self.assertEqual(params['course_id'], ['course-v1:example+course+run'])
        self.assertEqual(params['course_name'], ['Test Course'])
        self.assertEqual(params['lms_root_url'], ['https://lms.example.org'])
        self.assertNotIn('platform_email', params)
        self.assertNotIn('platform_username', params)
        self.assertIn(self.xblock.message, content)

    def test_custom_message(self):
        self.xblock.message = 'Custom <script>message</script>'
        content = self.xblock.student_view().content
        self.assertIn('Custom &lt;script&gt;message&lt;/script&gt;', content)
        self.assertNotIn('<script>message</script>', content)

    def test_course_name_override_is_url_encoded(self):
        self.xblock.course_name_override = 'Research & Development'
        content = self.xblock.student_view().content
        source = re.search(r'<iframe[^>]+src="([^"]+)"', content).group(1)
        self.assertEqual(parse_qs(urlparse(unescape(source)).query)['course_name'], ['Research & Development'])

    def test_score_round_trip(self):
        score = Score(3, 5)
        self.xblock.set_score(score)
        self.assertEqual(self.xblock.get_score(), score)
        self.assertEqual(self.xblock.max_score(), 5)
        self.xblock.publish_grade()
        self.xblock.runtime.publish.assert_called_once_with(self.xblock, 'grade', {'value': 3, 'max_value': 5})
