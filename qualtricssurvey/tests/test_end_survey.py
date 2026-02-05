"""
Test the end_survey method of the Qualtrics Survey XBlock
"""

import unittest
import json
from unittest import mock
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xblock.field_data import DictFieldData
from qualtricssurvey.xblocks import QualtricsSurvey


def mock_an_xblock(**kwargs):
    """
    Create and return an instance of the XBlock with mocked runtime and dependencies
    """
    course_id = SlashSeparatedCourseKey('foo', 'bar', 'baz')
    runtime = mock.Mock(course_id=course_id)
    runtime.publish = mock.Mock()
    scope_ids = mock.Mock()
    field_data = DictFieldData(kwargs)
    xblock = QualtricsSurvey(runtime, field_data, scope_ids)
    return xblock


class TestEndSurveyHandler(unittest.TestCase):
    """
    Test the end_survey method of the XBlock
    """

    def setUp(self):
        self.xblock = mock_an_xblock()

        # Mock system and runtime methods needed by end_survey
        self.xblock.system = mock.Mock()
        self.xblock.runtime = mock.Mock()
        self.xblock.runtime.publish = mock.Mock()
        self.xblock.system.rebind_noauth_module_to_user = mock.Mock()

    def _create_mock_request(self, data, method="POST"):
        """
        Create a properly mocked request object for XBlock handler testing
        """
        mock_request = mock.Mock()
        mock_request.method = method
        mock_request.body = json.dumps(data).encode('utf-8')
        mock_request.META = {'CONTENT_TYPE': 'application/json'}
        return mock_request

    @mock.patch('qualtricssurvey.models.user_by_anonymous_id')
    def test_end_survey_with_status_200_and_anonymous_id(self, mock_user_by_id):
        """
        Test that end_survey processes data successfully when Status=200 and 
        platform_anonymous_user_id is provided
        """
        xblock = self.xblock
        
        # Mock the user lookup
        mock_user = mock.Mock()
        mock_user_by_id.return_value = mock_user
        
        # Mock calculate_score and set_score methods
        xblock.calculate_score = mock.Mock(return_value=0.8)
        xblock.set_score = mock.Mock()
        xblock.publish_grade = mock.Mock()
        xblock.save = mock.Mock()
        
        # Simulate data received from Qualtrics with successful status
        data = {
            "Status": 200,
            "Results": {
                "values": {
                    "platform_anonymous_user_id": "test_anon_id_123",
                    "Q1": "Very Satisfied"
                }
            }
        }

        mock_request = self._create_mock_request(data)

        # Call the handler with the mock request
        response = xblock.end_survey(mock_request, data)

        # Verify the response is a Response object with success status
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.text)
        self.assertIn("Message", response_data)
        
        # Verify that the user was looked up
        mock_user_by_id.assert_called_once_with("test_anon_id_123")
        
        # Verify that system was rebound to the user
        xblock.system.rebind_noauth_module_to_user.assert_called_once_with(xblock, mock_user)
        
        # Verify that score was calculated and set
        xblock.calculate_score.assert_called_once()
        xblock.set_score.assert_called_once_with(0.8)
        
        # Verify that grade was published
        xblock.publish_grade.assert_called_once()
        
        # Verify completion was published
        xblock.runtime.publish.assert_called_once_with(xblock, "completion", {"completion": 1.0})
        
        # Verify survey completion status was updated
        self.assertTrue(xblock.survey_completed)
        self.assertTrue(xblock.is_answered)
        xblock.save.assert_called_once()

    @mock.patch('qualtricssurvey.models.user_by_anonymous_id')
    def test_end_survey_with_missing_anonymous_id(self, mock_user_by_id):
        """
        Test that end_survey logs warning when platform_anonymous_user_id is missing
        """
        xblock = self.xblock
        
        data = {
            "Status": 200,
            "Results": {
                "values": {
                    "Q1": "Very Satisfied"
                }
            }
        }

        mock_request = self._create_mock_request(data)

        # Call the handler with the mock request
        response = xblock.end_survey(mock_request, data)

        # Verify the response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.text)
        self.assertIn("Message", response_data)
        
        # Verify that user lookup wasn't called
        mock_user_by_id.assert_not_called()
        
        # Verify that publish wasn't called
        xblock.runtime.publish.assert_not_called()

    @mock.patch('qualtricssurvey.models.user_by_anonymous_id')
    def test_end_survey_with_invalid_anonymous_id(self, mock_user_by_id):
        """
        Test that end_survey raises ValueError when user cannot be found for anonymous_id
        """
        xblock = self.xblock
        
        # Mock the user lookup to return None
        mock_user_by_id.return_value = None
        
        # Simulate data received from Qualtrics
        data = {
            "Status": 200,
            "Results": {
                "values": {
                    "platform_anonymous_user_id": "invalid_anon_id",
                    "Q1": "Very Satisfied"
                }
            }
        }

        mock_request = self._create_mock_request(data)

        # Call the handler - it should raise ValueError because user_by_anonymous_id returns None
        with self.assertRaises(ValueError) as context:
            xblock.end_survey(mock_request, data)
        
        # Verify the error message
        self.assertIn("Cannot find `real_user`", str(context.exception))

    def test_end_survey_with_status_not_200(self):
        """
        Test that end_survey returns success response even when Status != 200
        """
        xblock = self.xblock
        
        # Simulate data received from Qualtrics
        data = {
            "Status": 400
        }

        mock_request = self._create_mock_request(data)

        # Call the handler with the mock request
        response = xblock.end_survey(mock_request, data)

        # Verify the response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.text)
        self.assertIn("Message", response_data)
        
        # Verify that publish wasn't called
        xblock.runtime.publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
