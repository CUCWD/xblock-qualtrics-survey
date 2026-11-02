"""Access the Qualtrics survey and authentication APIs."""
import logging

import requests
from django.conf import settings
from django.core.cache import caches
from lazy import lazy
from requests.exceptions import HTTPError

LOGGER = logging.getLogger(__name__)


class QualtricsApi():
    """
    Backend class for communicating with Qualtrics API (https://api.qualtrics.com/)
    """

    def __init__(self, university):
        try:
            # Set this `api_org_config` base on Django settings and `university` set in XBlock.
            self.api_org = university.split('.')[0]
            self.api_org_config = {}
            for config in settings.QUALTRICS_ORGANIZATION_API_CONFIGS:
                # Strip `organization` name from the Qualtrics zone location in case a survey includes it.
                # Example: `clemson.ca1`, `utsa.az1` where `ca1` and `az1` represent the zones.
                # The result would be `clemson` or `utsa` after the `.split('.')[0]` is called.
                # We're doing this because the key values in QUALTRICS_ORGANIZATION_API_CONFIGS
                # are organization specific and don't include any zone information.
                if config['NAME'] == self.api_org:
                    self.api_org_config = config
        except KeyError:
            LOGGER.error(
                f"Cannot locate Qualtrics API configuration for {university}. "
                f"Please configure QUALTRICS_ORGANIZATION_API_CONFIGS in Django settings.\n"
            )

        self.api_ver = settings.QUALTRICS_API_VERSION
        if self.api_ver != 'v1':
            # initialize backend token cache
            self.token_cache = caches[settings.QUALTRICS_API_TOKEN_CACHE]

    def _log_if_raised(self, response, data):
        """
        Log server response if there was an error.
        """

        try:
            response.raise_for_status()
        except HTTPError:
            LOGGER.error(
                "Encountered an error when retrieving data from Qualtrics. Response sent from "
                "%r with headers %r.\n"
                "and data values %r\n"
                "Response status was %s.\n%s",
                response.request.url, response.request.headers,
                data,
                response.status_code, response.content
            )
            raise

    def _get_api_config_setting(self, name):
        """
        Returns an api_config setting if available.
        """
        try:
            return self.api_org_config[name]
        except KeyError:
            LOGGER.error(
                f"Cannot locate Qualtrics API configuration value for {name}. "
                f"Please configure QUALTRICS_ORGANIZATION_API_CONFIGS in Django settings.\n"
            )
        return None

    @lazy
    def _api_auth_url(self):
        """
        Auth URL for all API requests.
        """

        return "{}/oauth2/token".format(self._get_api_config_setting('QUALTRICS_API_BASE_URL'))

    @lazy
    def _api_base_url(self):
        """
        Base URL for all API requests.
        """

        return (
            '{}/API/{}'
        ).format(self._get_api_config_setting((
            'QUALTRICS_API_BASE_URL'
        )), settings.QUALTRICS_API_VERSION)

    @lazy
    def _api_eventsubscriptions_base_url(self):
        """
        Base URL for eventsubscriptions-specific requests.
        """

        return "{}/{}".format(self._api_base_url, "eventsubscriptions")

    @lazy
    def _api_surveys_base_url(self):
        """
        Base URL for surveys-specific requests.
        """

        return "{}/{}".format(self._api_base_url, "surveys")

    @lazy
    def _api_survey_definitions_base_url(self):
        """
        Base URL for surveys-definitions requests.
        """

        return "{}/{}".format(self._api_base_url, "survey-definitions")

    def get_headers(self):
        """
        Headers to send along with the request-- used for authentication
        """

        # v1 is deprecated and will result in 404 error
        if settings.QUALTRICS_API_VERSION == 'v1':
            headers = {
                'X-API-TOKEN': self._get_api_config_setting('QUALTRICS_API_TOKEN'),
                'Content-Type': 'application/json'
            }
            return headers
        else:
            headers = {
                "authorization": "bearer " + self.get_oauth_token(),
                'Content-Type': 'application/json'
            }
            return headers

    def get_survey_definition(self, survey_id):
        """
        Retrieve survey definition
        https://api.qualtrics.com/9d0928392673d-get-survey
        """

        url = "{}/{}".format(self._api_survey_definitions_base_url, survey_id)

        payload = {}
        headers = self.get_headers()

        # Preserve existing request timeout behavior; transport failures propagate.
        response_survey_definition = requests.request(  # pylint: disable=missing-timeout
            "GET", url, headers=headers, data=payload
        )
        try:
            self._log_if_raised(response_survey_definition, payload)
        except HTTPError:
            LOGGER.error("QualtricsApi - get_survey_definition failed for survey %s", survey_id)

        return response_survey_definition

    def get_survey_definition_questions(self, survey_id):
        """
        Retrieve survey definition questions
        https://api.qualtrics.com/957c5f8a4604b-get-questions
        """

        url = "{}/{}/questions".format(self._api_survey_definitions_base_url, survey_id)

        payload = {}
        headers = self.get_headers()

        # Preserve existing request timeout behavior; transport failures propagate.
        response_survey_questions = requests.request(  # pylint: disable=missing-timeout
            "GET", url, headers=headers, data=payload
        )
        try:
            self._log_if_raised(response_survey_questions, payload)
        except HTTPError:
            LOGGER.error("QualtricsApi - get_survey_definition_questions failed for survey %s", survey_id)

        return response_survey_questions

    def get_survey_score_id(self, survey_id):
        """
        Locate the Qualtrics `Score Id` in configuration settings.
        """
        score_id = None
        category_name = self._get_api_config_setting('QUALTRICS_SCORE_CATEGORY_NAME')

        response_survey_definition = self.get_survey_definition(survey_id)
        if response_survey_definition.ok:
            data_response_survey_definition = response_survey_definition.json()
            result = data_response_survey_definition["result"]
            categories = result.get("Scoring", {}).get("ScoringCategories", [])

            # Qualtrics currently returns ScoringCategories as a list.
            if isinstance(categories, list):
                category_items = categories
            elif isinstance(categories, dict):
                category_items = categories.values()
            else:
                category_items = []

            score_id = next(
                (
                    cat.get("ID")
                    for cat in category_items
                    if isinstance(cat, dict) and cat.get("Name") == category_name
                ),
                None,
            )

        if score_id is None:
            LOGGER.error(
                "QualtricsApi - get_survey_score_id() - Score category '%s' not found in survey '%s'",
                category_name, survey_id
            )

        LOGGER.info(
            "QualtricsApi - get_survey_score_id() - Located score_id '%s' for category '%s' in survey '%s'",
            score_id, category_name, survey_id
        )

        return score_id

    def get_oauth_token(self):
        """
        Checks for valid auth token in cache and returns it, otherwise a new one is generated and saved to cache
        """

        # If no api org set from passed in university setting then exit and don't set/retrieve
        # oauth token in cache.
        if not self.api_org:
            LOGGER.info('Qualtrics: No current api_org set for this component, not getting cached oauth token')
            return None

        token_cache_name = 'qualtrics_api_auth_token_' + str(self.api_org)
        token_cached = self.token_cache.get(token_cache_name)

        if token_cached is not None:
            return token_cached
        else:
            client_id = self._get_api_config_setting('QUALTRICS_API_OAUTH_CLIENT_ID')
            client_secret = self._get_api_config_setting('QUALTRICS_API_OAUTH_CLIENT_SECRET')

            payload = {
                'grant_type': 'client_credentials',
                'scope': 'write:subscriptions read:survey_responses read:surveys'
            }

            response = requests.post(  # pylint: disable=missing-timeout
                self._api_auth_url, auth=(client_id, client_secret), data=payload
            )

            if response.ok:
                token = response.json()['access_token']
                self.token_cache.set(token_cache_name, token, getattr(
                    settings, 'QUALTRICS_API_TOKEN_EXPIRATION', 3599))  # 24h
                return token
            else:
                response.raise_for_status()
                return None
