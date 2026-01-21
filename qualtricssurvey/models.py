"""
Handle data access logic for the XBlock
"""

import six
from datetime import datetime
from xblock.scorable import ScorableXBlockMixin, Score
from django.utils.translation import gettext_lazy as _
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from xblock.core import XBlock
from xblock.fields import Scope
from xblock.fields import Boolean, List, String, Float
from opaque_keys.edx.keys import UsageKey
from xmodule.modulestore.django import modulestore
from collections import namedtuple
from .platform_dependencies import user_by_anonymous_id
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField
from opaque_keys.edx.django.models import UsageKeyField
from django.conf import settings
from lms.djangoapps.grades import tasks
from organizations.models import Organization, OrganizationCourse
# from requests.packages.urllib3.exceptions import HTTPError

from xmodule.fields import ScoreField
from common.djangoapps.student.models import get_user

import logging
LOGGER = logging.getLogger(__name__)

from .qualtrics_api import QualtricsApi


class CourseDetailsXBlockMixin(object):
    """
    Handles all course related information from the platform.
    """

    def _get_context(self, block):
        """
        Return section, subsection, and unit names for `block`.
        """
        block_names_by_type = {}
        block_iter = block
        while block_iter:
            block_iter_type = block_iter.scope_ids.block_type
            block_names_by_type[block_iter_type] = block_iter.display_name_with_default
            block_iter = block_iter.get_parent() if block_iter.parent else None
        section_name = block_names_by_type.get('chapter', '')
        subsection_name = block_names_by_type.get('sequential', '')
        unit_name = block_names_by_type.get('vertical', '')
        return section_name, subsection_name, unit_name

    def _get_context_course_advanced_settings(self, block):
        """
        Return CMS Advanced Settings
        """
        block_iter = block
        # Use empty string defaults so missing keys/attributes result in empty string instead of raising.
        qs_course_instructor = ''
        qs_course_term = ''

        qs_course_id = self.course_id

        while block_iter:
            block_iter_type = getattr(block_iter.scope_ids, 'block_type', None)
            if block_iter_type == 'course':
                # Safely access instructor_info and other_course_settings without raising KeyError
                try:
                    instructor_info = getattr(block_iter, 'instructor_info', {}) or {}
                    qs_course_instructor = instructor_info.get('instructors', '')
                except Exception:
                    qs_course_instructor = ''

                try:
                    other_settings = getattr(block_iter, 'other_course_settings', {}) or {}
                    qs_course_term = other_settings.get('qualtrics_term', '')
                except Exception:
                    qs_course_term = ''
                    LOGGER.error("QualtricsXblock - No qualtrics term found in other_course_settings")

            block_iter = block_iter.get_parent() if getattr(block_iter, 'parent', None) else None

        return qs_course_instructor, qs_course_term

    @property
    def course_id(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None)
        except AttributeError:
            return None

        return str(raw_course_id)

    @property
    def course_name(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None) 
        except AttributeError:
            return None

        return CourseOverview.get_from_id(raw_course_id).display_name

    @property
    def module_name(self):
        source_block_id_str = str(self.location)
        try:
            usage_key = UsageKey.from_string(source_block_id_str)
        except InvalidKeyError:
            raise ValueError("Could not find the specified Block ID.")
        
        src_block = modulestore().get_item(usage_key)
        section_name, subsection_name, unit_name = self._get_context(src_block)
        return section_name

    @property
    def course_org(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None)
        except AttributeError:
            return None

        return str(raw_course_id.org)

    @property
    def course_number(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None)
        except AttributeError:
            return None
            
        return str(raw_course_id.course)

    @property
    def course_run(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None)
        except AttributeError:
            return None           

        return str(raw_course_id.run)
    
    @property
    def course_start_date(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None) 
        except AttributeError:
            return ""
        # if (str(CourseOverview.get_from_id(raw_course_id).end_date) != 'None'):
        #     return  str(CourseOverview.get_from_id(raw_course_id).start_date)
        # return  str(CourseOverview.get_from_id(raw_course_id).start_date.date())

        # datetime = str(CourseOverview.get_from_id(raw_course_id).start_date)
        # if " " in datetime:
        #     date = datetime.split(' ')
        #     return date[0]
        # else:
        #     return datetime

        if CourseOverview.get_from_id(raw_course_id).start_date is None:
            return ""

        return str(CourseOverview.get_from_id(raw_course_id).start_date.date())

    @property
    def course_end_date(self):
        try:
            raw_course_id = getattr(self.runtime, 'course_id', None) 
        except AttributeError:
            return ""

        if CourseOverview.get_from_id(raw_course_id).end_date is None:
            return ""

        return str(CourseOverview.get_from_id(raw_course_id).end_date.date())
    
    @property
    def course_instructors(self):
        source_block_id_str = str(self.location)
        try:
            usage_key = UsageKey.from_string(source_block_id_str)
        except InvalidKeyError:
            raise ValueError("Could not find the specified Block ID.")
    
        src_block = modulestore().get_item(usage_key)
        instructors, term = self._get_context_course_advanced_settings(src_block)
        
        return instructors

    @property
    def course_term(self):
        source_block_id_str = str(self.location)
        try:
            usage_key = UsageKey.from_string(source_block_id_str)
        except InvalidKeyError:
            raise ValueError("Could not find the specified Block ID.")
            
        src_block = modulestore().get_item(usage_key)
        instructors, term = self._get_context_course_advanced_settings(src_block)
        return term

class OrganizationDetailsXBlockMixin(object):
    """
    Handles all organization related information from the platform.
    """

    @property
    def organization_name(self):
        try:
            # Only return name if forwarding course organization info is enabled
            if self.should_forward_course_organization_info() is False:
                return ''

            org = Organization.objects.get(short_name=self.course_org)
            return getattr(org, 'name', '')
        except Organization.DoesNotExist:
            return ''

    @property
    def organization_short_name(self):
        try:
            # Only return short name if forwarding course organization info is enabled
            if self.should_forward_course_organization_info() is False:
                return ''

            org = Organization.objects.get(short_name=self.course_org)
            return getattr(org, 'short_name', '')
        except Organization.DoesNotExist:
            return ''

    @property
    def organization_city(self):
        try:
            # Only return city if forwarding course organization info is enabled
            if self.should_forward_course_organization_info() is False:
                return ''
            
            org = Organization.objects.get(short_name=self.course_org)
            return getattr(org, 'city', '')
        except Organization.DoesNotExist:
            return ''

    @property
    def organization_state(self):
        try:
            # Only return state if forwarding course organization info is enabled
            if self.should_forward_course_organization_info() is False:
                return ''

            org = Organization.objects.get(short_name=self.course_org)
            return getattr(org, 'state', '')
        except Organization.DoesNotExist:
            return ''

    @property
    def organization_zipcode(self):
        try:
            # Only return zipcode if forwarding course organization info is enabled
            if self.should_forward_course_organization_info() is False:
                return ''

            org = Organization.objects.get(short_name=self.course_org)
            return getattr(org, 'zipcode', '')
        except Organization.DoesNotExist:
            return ''

class UserDetailsXBlockMixin(object):
    """
    Handles all course related information from the platform.
    """

    @property
    def get_anon_id(self):
        """
        Return an anonymous user id
        """
        try:
            user_id = self.xmodule_runtime.anonymous_student_id
        except AttributeError:
            user_id = -1
        return user_id

    @property
    def get_username(self):
        """
        Return the real user's username
        """
        try:
            username = self.xmodule_runtime._services.get('user').get_current_user().opt_attrs['edx-platform.username']
        except AttributeError:
            username = ""
        return username

    @property
    def get_fullname(self):
        """
        Return the real user's fullname
        """
        try:
            user_fullname = self.xmodule_runtime._services.get('user').get_current_user().full_name
        except AttributeError:
            user_fullname = ""
        return user_fullname

    @property
    def get_email(self):
        """
        Return the real user's email
        """
        try:
            user_email = self.xmodule_runtime._services.get('user').get_current_user().emails[0]
        except AttributeError:
            user_email = ""
        return user_email

    @property
    def get_user_is_staff(self):
        """
        Return whether the real user is staff member or not.
        """
        try:
            user_is_staff = self.xmodule_runtime.user_is_staff
        except AttributeError:
            user_is_staff = False
        return user_is_staff


class UserDemographicsXBlockMixin(object):
    """
    Handles all user demographic related information from the platform.
    """

    def get_user_profile(self):
        """
        Return user profile
        """
        user, user_profile = get_user(self.xmodule_runtime._services.get('user').get_current_user().emails[0])
        return user_profile

    def get_user_extra_info(self):
        user_id = self.get_user_profile().user_id
        # Import ExtraInfo locally because the optional app providing it may not be installed.
        try:
            from custom_reg_form.models import ExtraInfo
        except Exception:
            # ExtraInfo model is not available; return None to indicate absence.
            return None

        try:
            extra_info = ExtraInfo.objects.get(user_id=user_id)
        except ExtraInfo.DoesNotExist:
            extra_info = None
        except Exception:
            extra_info = None
        return extra_info

    @property
    def get_user_year_of_birth(self):
        """
        Return user year of birth information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled
        if self.should_forward_platform_user_demographic_data() is False:
            return ''

        try:
            user_year_of_birth = self.get_user_profile().year_of_birth
        except (AttributeError, KeyError):
            user_year_of_birth = ''
        return user_year_of_birth

    @property
    def get_user_gender(self):
        """
        Return user gender information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled
        if self.should_forward_platform_user_demographic_data() is False:
            return ''
        
        try:
            user_gender = self.get_user_profile().gender_display
        except (AttributeError, KeyError):
            user_gender = ''
        return user_gender

    @property
    def get_user_level_of_education(self):
        """
        Return user level of education information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled
        if self.should_forward_platform_user_demographic_data() is False:
            return ''

        try:
            user_level_of_education = self.get_user_profile().level_of_education_display
        except (AttributeError, KeyError):
            user_level_of_education = ''
        return user_level_of_education

    @property
    def get_user_country(self):
        """
        Return user level of education information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled
        if self.should_forward_platform_user_demographic_data() is False:
            return ''

        try:
            user_country = self.get_user_profile().country
        except (AttributeError, KeyError):
            user_country = ''
        return user_country

    @property
    def get_user_ethnicity(self):
        """
        Return user ethnicity information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled or extra info is not available.
        if self.should_forward_platform_user_demographic_data() is False or self.get_user_extra_info() is None:
            return ''

        try:
            user_ethnicity = self.get_user_extra_info().ethnicity_display
        except (AttributeError, KeyError):
            user_ethnicity = ''
        return user_ethnicity

    @property
    def get_user_employment_status(self):
        """
        Return user ethnicity information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled or extra info is not available.
        if self.should_forward_platform_user_demographic_data() is False or self.get_user_extra_info() is None:
            return ''
        
        try:
            user_employment_status = self.get_user_extra_info().employment_status_display
        except (AttributeError, KeyError):
            user_employment_status = ''
        return user_employment_status

    @property
    def get_user_zipcode(self):
        """
        Return user ethnicity information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled or extra info is not available.
        if self.should_forward_platform_user_demographic_data() is False or self.get_user_extra_info() is None:
            return ''

        try:
            user_zipcode = self.get_user_extra_info().zipcode
        except (AttributeError, KeyError):
            user_zipcode = ''
        return user_zipcode

    @property
    def get_user_enrolled_in_school(self):
        """
        Return user ethnicity information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled or extra info is not available.
        if self.should_forward_platform_user_demographic_data() is False or self.get_user_extra_info() is None:
            return ''

        try:
            user_enrolled_in_school = self.get_user_extra_info().enrolled_in_school_display
        except (AttributeError, KeyError):
            user_enrolled_in_school = ''
        return user_enrolled_in_school

    @property
    def get_user_enrolled_in_school_type(self):
        """
        Return user ethnicity information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled or extra info is not available.
        if self.should_forward_platform_user_demographic_data() is False or self.get_user_extra_info() is None:
            return ''

        try:
            user_enrolled_in_school_type = self.get_user_extra_info().enrolled_in_school_type_display
        except (AttributeError, KeyError):
            user_enrolled_in_school_type = ''
        return user_enrolled_in_school_type

    @property
    def get_user_local_community_living(self):
        """
        Return user ethnicity information
        """
        # Only return year of birth if forwarding platform user demographic data is enabled or extra info is not available.
        if self.should_forward_platform_user_demographic_data() is False or self.get_user_extra_info() is None:
            return ''

        try:
            user_local_community_living = self.get_user_extra_info().local_community_living_display
        except (AttributeError, KeyError):
            user_local_community_living = ''
        return user_local_community_living

class QualtricsSurveyModelMixin(ScorableXBlockMixin, CourseDetailsXBlockMixin, OrganizationDetailsXBlockMixin, UserDetailsXBlockMixin, UserDemographicsXBlockMixin):
    """
    Handle data access for XBlock instances
    """
    survey_completed = False

    editable_fields = [
        'display_name',
        'survey_id',
        'your_university',
        # 'link_text',
        # 'param_name',
        'message',
        'course_id_override',
        'course_name_override',
        'course_org_override',
        'course_number_override',
        'course_run_override',
        'course_term_override',
        'course_start_date_override',
        'course_end_date_override',
        'course_instructors_override',
        'forward_platform_user_pii',
        'forward_platform_user_demographic_data',
        'forward_course_organization_info',
        'send_qualtrics_score_to_platform',
        'show_simulation_exists',
        'show_meta_information',
        'weight'
    ]
    course_id_override = String(
        display_name=_('Course Identifier:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course identifier override with '
            'following format: {key type}:{org}+{course}+{run} (e.g. course-v1:edX+DemoX+2014) or {org}/{course}/{run} (e.g. edX/DemoX/2014).'
        ),
    )
    course_name_override = String(
        display_name=_('Course Name:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course name override.'
        ),
    )
    course_number_override = String(
        display_name=_('Course Number:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course number override.'
        ),
    )
    course_org_override = String(
        display_name=_('Course Organization:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course organization override.'
        ),
    )
    course_run_override = String(
        display_name=_('Course Run:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course run override.'
        ),
    )
    course_term_override = String(
        display_name=_('Course Term:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course term override (e.g. "2015_Fall" or "2021_Spring").'
        ),
    )
    course_start_date_override = String(
        display_name=_('Course Start Date:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course start date override (e.g. "2019-08-20").'
        ),
    )
    course_end_date_override = String(
        display_name=_('Course End Date:'),
        default='',
        scope=Scope.settings,
        help=_(
            'Enter in the course start date override (e.g. "2019-08-20").'
        ),
    )
    course_instructors_override = List(
        display_name=_('Course Instructor(s):'),
        default=[],
        scope=Scope.settings,
        help=_(
            'Enter in the course instructor(s) override. If there are multiple instructors use a comma to seperate values. (e.g. ["John Smith", "Sally Smith"])'
        ),
    )
    display_name = String(
        display_name=_('Display Name:'),
        default='Qualtrics Survey',
        scope=Scope.settings,
        help=_(
            'This name appears in the horizontal navigation at the top '
            'of the page.'
        ),
    )
    # link_text = String(
    #     display_name=_('Link Text:'),
    #     default='Begin Survey',
    #     scope=Scope.settings,
    #     help=_('This is the text that will link to your survey.'),
    # )
    message = String(
        display_name=_('Message:'),
        default='We need your help! Please take time now to complete this survey; your feedback '
            'will help us improve this curriculum for other learners. Once you have completed '
            'the survey please continue the course by clicking the next button. Thanks! ',
        scope=Scope.settings,
        help=_(
            'This is the text that will be displayed '
            'above the link to your survey.'
        ),
    )
    # param_name = String(
    #     display_name=_('Param Name:'),
    #     default='a',
    #     scope=Scope.settings,
    #     help=_(
    #         'This is the name for the User ID parameter in the url. '
    #         'If blank, User ID is ommitted from the url.'
    #     ),
    # )
    forward_platform_user_pii = Boolean(
        display_name=_("Forward Platform User PII to Qualtrics"),
        help=_("Sends personal information (username, full name, email) about the platform user account to Qualtrics. "
               "This is disabled by default."),
        scope=Scope.settings,
        default=False
    )
    forward_platform_user_demographic_data = Boolean(
        display_name=_("Forward Platform User Demographic Data to Qualtrics"),
        help=_("Sends personal demographic information (gender, level of education, etc) about the platform user account to Qualtrics. "
               "This is disabled by default."),
        scope=Scope.settings,
        default=False
    )
    forward_course_organization_info = Boolean(
        display_name=_("Forward Course Organization Details to Qualtrics"),
        help=_("Sends course organization details (institution name, short name, city, state, zipcode) to Qualtrics. "
               "This is disabled by default."),
        scope=Scope.settings,
        default=False
    )
    send_qualtrics_score_to_platform = Boolean(
        display_name=_("Send Qualtrics Score to Platform"),
        help=_("When enabled this sends the qualtrics score value from learner's response."
               "This is disabled by default. Only enable this when scoring is setup in the survey"),
        scope=Scope.settings,
        default=False
    )
    show_simulation_exists = Boolean(
        display_name=_("Simulation Exists"),
        help=_("Displays simulation questions from the survey when the query parameters is passed. "
               "This is disabled by default."),
        scope=Scope.settings,
        default=False
    )
    show_meta_information = Boolean(
        display_name=_("Show Qualtrics Survey Meta Information"),
        help=_("Displays 'meta' information about the survey to show query parameters passed. "
               "A default value can be set in Advanced Settings."),
        scope=Scope.settings,
        default=False
    )
    survey_id = String(
        display_name=_('Survey ID:'),
        default='Enter your survey ID here.',
        scope=Scope.settings,
        help=_(
            'This is the ID that Qualtrics uses for the survey, which can '
            'include numbers and letters, and should be entered in the '
            'following format: SV_###############'
        ),
    )
    your_university = String(
        display_name=_('Your University:'),
        default='clemson',
        scope=Scope.settings,
        help=_('This is the name of your university.'),
    )

    weight = Float(
        display_name=_("Problem Weight"),
        help=_("Defines the number of points each problem is worth. "
               "If the value is not set, each response field in the problem is worth zero points. "
               "Whenever 'Send Qualtrics Score to Platform' is set this weight is not used but rather Qualtrics defines the weight based on score settings."
        ),
        values={"min": 0, "step": .1},
        scope=Scope.settings
    )
    score = ScoreField(
        help=_("Dictionary with the current student score"), 
        scope=Scope.user_state, 
        enforce_type=False
    )
    is_answered = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if successfully answered'
    )
    
    has_score = True
          
    @property
    def descriptor(self):
        """
        Returns this XBlock object.
        This is for backwards compatibility with the XModule API.
        Some LMS code still assumes a descriptor attribute on the XBlock object.
        See courseware.module_render.rebind_noauth_module_to_user.
        """
        return self

    # pylint: disable=no-member
    def get_anon_id(self):
    #     """
    #     Return an anonymous user id
    #     """
         try:
            user_id = self.xmodule_runtime.anonymous_student_id
         except AttributeError:
             user_id = -1
         return user_id

    # pylint: disable=no-member
    def get_lms_root_url(self):
        """
        Return the lms root url of where the XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        url = configuration_helpers.get_value(
            "LMS_ROOT_URL", settings.LMS_ROOT_URL
        )
            
        return six.text_type(six.moves.urllib.parse.quote(url))

    # pylint: disable=no-member
    def get_course_block_location_id(self):
        """
        Return the course block location id of the course component XBlock.
        Encode return value for Qualtrics query parameter usage.
        """
        return six.text_type(six.moves.urllib.parse.quote(str(self.location)))

    # pylint: disable=no-member
    def get_course_id(self):
        """
        Return the course_id of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_id_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_id_override))
            
        return six.text_type(six.moves.urllib.parse.quote(self.course_id))

    # pylint: disable=no-member
    def get_course_name(self):
        """
        Return the course_name of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_name_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_name_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_name))
        
    # pylint: disable=no-member
    def get_course_org(self):
        """
        Return the course_org of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_org_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_org_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_org))

    # pylint: disable=no-member
    def get_course_number(self):
        """
        Return the course_number of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_number_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_number_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_number))

    # pylint: disable=no-member
    def get_course_run(self):
        """
        Return the course_run of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_run_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_run_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_run))

    # pylint: disable=no-member
    def get_course_term(self):
        """
        Return the course_term of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_term_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_term_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_term))

    def get_course_start_date(self):
        """
        Return the course_start_date of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_start_date_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_start_date_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_start_date))

    def get_course_end_date(self):
        """
        Return the course_start_date of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_end_date_override:
            return six.text_type(six.moves.urllib.parse.quote(self.course_end_date_override))

        return six.text_type(six.moves.urllib.parse.quote(self.course_end_date))
        

    def get_course_instructors(self):
        """
        Return the course_instructor of the course where this XBlock is used.
        Encode return value for Qualtrics query parameter usage.
        """
        if self.course_instructors_override:
            return six.text_type(six.moves.urllib.parse.quote(', '.join(self.course_instructors_override)))

        return six.text_type(six.moves.urllib.parse.quote(', '.join(self.course_instructors)))
    
    def get_course_module_name(self):
        """
        Return the module_name of the course where this XBlock is used.
        """
        return self.module_name

    def should_forward_platform_user_demographic_data(self):
        """
        Return True/False to indicate whether to forward the "Forward Platform User Demographic Data to Qualtrics" information.
        """
        return self.forward_platform_user_demographic_data

    def should_forward_platform_user_pii(self):
        """
        Return True/False to indicate whether to forward the "Forward Platform User PII to Qualtrics" information.
        """
        return self.forward_platform_user_pii
    
    def should_forward_course_organization_info(self):
        """
        Return True/False to indicate whether to forward the "Forward Course Organization Info to Qualtrics" information.
        """
        return self.forward_course_organization_info

    def should_send_qualtrics_score_to_platform(self):
        """
        Return True/False to indicate whether to "Send Qualtrics Score to Platform" information.
        """
        return self.send_qualtrics_score_to_platform

    def should_show_simulation_exists(self):
        """
        Return True/False to indicate whether to show the "Simulation Exists" questions.
        """
        return self.show_simulation_exists

    # pylint: disable=no-member
    def should_show_meta_information(self):
        """
        Return True/False to indicate whether to show the "Show Qualtrics Survey Meta Information" information.
        """
        return self.show_meta_information

    def get_survey_id(self) :
        return self.survey_id

    def get_survey_score_id(self):
        """
        Locate the Qualtrics `Score Id` in site configuration or general settings.
        """
        # score_id = configuration_helpers.get_value(
        #         "QUALTRICS_SCORE_ID", settings.QUALTRICS_SCORE_ID
        #     )
        return QualtricsApi(self.your_university).get_survey_score_id()
    
    def max_score(self):
        """
        Return the weight of the problem. This method is in the staff debug information
        """

        # Exit early because we already have a score and we don't want to pull from the
        # defaults set in the rest of this method. If we don't do this check and the max score 
        # changes either through weight or Qualtrics score (adding/removing new problems) then
        # the previous user experience could change with `raw_possible`.
        if self.score is not None:
            return self.score.raw_possible

        raw_possible = 0.0

        # Locate all questions included in the survey Trash block and use these ids to 
        # exclude them from the max_score value.
        exclude_question_ids = []

        response_survey_definition = QualtricsApi(self.your_university).get_survey_definition(self.get_survey_id())
        if response_survey_definition.ok:    
            data_response_survey_definition = response_survey_definition.json()
            result = data_response_survey_definition["result"]
            
            # Loop through all survey blocks looking for items in the Trash and add the
            # question QIDs to the exclude list for max_score.
            for block in result["Blocks"].values():
                if block["Type"] == "Trash":
                    for block_element in block["BlockElements"]:
                        if block_element["QuestionID"] not in exclude_question_ids:
                            exclude_question_ids.append(block_element["QuestionID"])

        if self.should_send_qualtrics_score_to_platform():
            # Find score values from Qualtrics

            # Get the number of questions from the Qualtrics Survey Definition Questions
            # endpoint and find all questions with score value set.
            response_survey_questions = QualtricsApi(self.your_university).get_survey_definition_questions(self.get_survey_id())

            if response_survey_questions.ok:
                data_response_survey_questions = response_survey_questions.json()
                result = data_response_survey_questions["result"]
                elements = result["elements"]

                for question in elements:
                    if question["GradingData"] and question["QuestionID"] not in exclude_question_ids:
                        for grade_data in question["GradingData"]:
                            try:
                                raw_possible += float(grade_data["Grades"][self.get_survey_score_id()])
                            except ValueError as err:
                                # Sometimes we may forget to set a score grading value and `#` will get passed from Qualtrics.
                                LOGGER.warning(u"Qualtrics - max_score() - Issue with getting raw_possible for – Survey ID ({}) QID ({}) GradingData({}) – {}".format(self.get_survey_id(), question["QuestionID"], grade_data["Grades"][self.get_survey_score_id()], err))
                                continue
                            except KeyError as err:
                                # Sometimes we may forget to set a score grading value and `#` will get passed from Qualtrics.
                                LOGGER.warning(u"Qualtrics - max_score() - Issue with getting raw_possible for – Survey ID ({}) QID ({}) – {}".format(self.get_survey_id(), question["QuestionID"], err))
                                continue
                            except KeyError as err:
                                # Sometimes we may forget to set a score grading value and `#` will get passed from Qualtrics.
                                LOGGER.warning(u"Qualtrics – max_score() – Issue with getting raw_possible for – Survey ID ({}) QID ({}) – {}".format(self.get_survey_id(), question["QuestionID"], err))
                                continue
        else:
            # Awards full points for completing a survey (default)
            raw_possible = (self.weight if self.weight is not None and self.weight > 0 else 0.0)

        # Round to nearest tenth.
        return round(raw_possible, 1)

    @XBlock.json_handler
    def is_graded(self, data, suffix=''):
        # Returns if the survey is graded or not. Used on the Javscript file to loaded graded status.
        return {'graded': self.graded}

    @XBlock.json_handler
    def get_survey_status(self, data, suffix=''):
        # Prevents dividing by zero when computing weighted score for unweighted survey

        if self.score:
            raw_earned = self.score.raw_earned
            raw_possible = self.score.raw_possible
        else:
            raw_earned = raw_possible = 0
        
        return {'is_answered': self.is_answered, 'possible_score': raw_possible, 'earned_score': raw_earned}
        
    @XBlock.json_handler
    def end_survey(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Called upon completion of the survey
        """
    
        status = data.get("Status")

        if status == 200:
            # data_response_survey = response_survey.json()
            # result = data_response_survey["result"]
            results = data.get("Results")
            values = results["values"]

            if not user_by_anonymous_id:
                import_error_anonymous_id = "Could not import `user_by_anonymous_id` from edx-platform student app."
                raise ImportError(import_error_anonymous_id)
                response = {
                    import_error_anonymous_id
                }
            else:
                # Only update learner's score if we have an `anonymous_user_id`` to
                # map to a `real` user. This `anonymous_user_id` was passed to the
                # Qualtrics survey as query parameter and was meant to prevent 
                # external system (e.g. Qualtrics) from keeping PII information for
                # a platform user account. Since then we have created an component
                # option to `Forward Platform User PII to Qualtrics` which does send
                # PII information over to Qualtrics which was a request from the
                # research team.
                if 'platform_anonymous_user_id' in values:
                    real_user = user_by_anonymous_id(values["platform_anonymous_user_id"])
                    if (real_user is None):
                        real_user_error = u"Cannot find `real_user` from the `platform_anonymous_user_id`."
                        LOGGER.error(real_user_error)
                        raise ValueError(real_user_error)

                    # rebinds the user to the xblock so that a grade can be published for the correct user
                    self.system.rebind_noauth_module_to_user(self, real_user)

                    score = self.calculate_score(values)
                    self.set_score(score)
                    self.publish_grade()
                
                    # Updates database survey status to complete
                    self.is_answered = True
                else:
                    LOGGER.warning(
                        "Could not update the learner's score because the"
                        "`platform_anonymous_user_id` value was not found in the"
                        "Qualtrics survey response."
                    )

        response = {
            "Message": "Data processed from the Qualtrics Event Subscription API postback `surveyengine.completedResponse` event."
        }
        return response

    def publish_grade(self):
        """
        Update the learner's course score for this Qualtrics component so the
        grade is reflected on the gradebook.
        """

        if self.score:
            grade_dict = {
                'value': self.score.raw_earned,
                'max_value': self.score.raw_possible,
            }
            self.runtime.publish(self, "grade", grade_dict)

    def has_submitted_answer(self):
        return self.is_answered

    def set_score(self, score):
        """
        Sets the internal score for the problem. This is not derived directly
        from the internal LCP in keeping with the ScorableXBlock spec.
        """
        self.score = score

    def get_score(self):
        """
        Returns the score currently set on the block.
        """
        return (self.score if self.score else None)

    def calculate_score(self, values):
        """
        Returns the score calculated from the current problem state.
        This varies based on the XBlock setting for `Send Qualtrics Score to Platform`.
        """
        raw_earned = 0.0
        raw_possible = self.max_score()

        if self.should_send_qualtrics_score_to_platform():
            # Find score values from Qualtrics
            if values is not None:
                raw_earned = float(values[self.get_survey_score_id()])
        else:
            # Awards full points for completing a survey (default)
            raw_earned = (self.weight if self.weight is not None and self.weight > 0 else 1.0)

        return Score(raw_earned=raw_earned, raw_possible=raw_possible)
