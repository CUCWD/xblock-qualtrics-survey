"""Regression coverage for invalid course keys and Qualtrics request failures."""
import unittest
from unittest import mock

from django.test import SimpleTestCase, override_settings
from opaque_keys import InvalidKeyError
from requests import Request, Response
from requests.exceptions import ConnectionError as RequestsConnectionError
from xblock.scorable import Score

from qualtricssurvey.qualtrics_api import QualtricsApi
from qualtricssurvey.tests.test_display import mock_an_xblock


class TestCourseKeys(unittest.TestCase):
    """Invalid platform identifiers produce the public validation error."""

    def test_invalid_usage_keys(self):
        block = mock_an_xblock()
        block.location = 'invalid-usage-key'
        for name in ('module_name', 'course_instructors', 'course_term'):
            with self.subTest(property=name):
                with self.assertRaisesRegex(ValueError, 'Could not find the specified Block ID') as raised:
                    getattr(block, name)
                self.assertIsInstance(raised.exception.__cause__, InvalidKeyError)

    def test_calculate_score_accepts_scorable_interface(self):
        block = mock_an_xblock(weight=2)
        with mock.patch.object(block, 'should_send_qualtrics_score_to_platform', return_value=False):
            self.assertEqual(block.calculate_score(), Score(2, 5))


@override_settings(
    QUALTRICS_ORGANIZATION_API_CONFIGS=[{
        'NAME': 'example',
        'QUALTRICS_API_BASE_URL': 'https://example.qualtrics.com',
    }],
    QUALTRICS_API_VERSION='v3',
    QUALTRICS_API_TOKEN_CACHE='default',
)
class TestQualtricsRequests(SimpleTestCase):
    """Keep failed HTTP responses inspectable and preserve transport exceptions."""

    def setUp(self):
        self.api = QualtricsApi('example')
        headers = mock.patch.object(self.api, 'get_headers', return_value={'Authorization': 'Bearer test'})
        headers.start()
        self.addCleanup(headers.stop)

    def test_successful_responses(self):
        for method in ('get_survey_definition', 'get_survey_definition_questions'):
            with self.subTest(method=method):
                response = Response()
                response.status_code = 200
                with mock.patch('qualtricssurvey.qualtrics_api.requests.request', return_value=response):
                    self.assertIs(getattr(self.api, method)('SV_test'), response)

    def test_http_errors_are_logged_and_returned(self):
        for method in ('get_survey_definition', 'get_survey_definition_questions'):
            with self.subTest(method=method):
                response = Response()
                response.status_code = 503
                response.request = Request('GET', 'https://example.qualtrics.com/API/v3/surveys/SV_test').prepare()
                with mock.patch('qualtricssurvey.qualtrics_api.requests.request', return_value=response):
                    with self.assertLogs('qualtricssurvey.qualtrics_api', level='ERROR') as logs:
                        self.assertIs(getattr(self.api, method)('SV_test'), response)
                self.assertTrue(any('Response status was 503' in entry for entry in logs.output))
                self.assertFalse(response.ok)

    def test_connection_failures_propagate(self):
        for method in ('get_survey_definition', 'get_survey_definition_questions'):
            with self.subTest(method=method):
                with mock.patch(
                    'qualtricssurvey.qualtrics_api.requests.request',
                    side_effect=RequestsConnectionError('connection unavailable'),
                ):
                    with self.assertRaisesRegex(RequestsConnectionError, 'connection unavailable'):
                        getattr(self.api, method)('SV_test')
