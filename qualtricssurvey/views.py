"""
Handle view logic for the XBlock
"""
try:
    from xblock.utils.resources import ResourceLoader
    from xblock.utils.studio_editable import StudioEditableXBlockMixin
except ModuleNotFoundError:
    # For backward compatibility with releases older than Quince.
    from xblockutils.resources import ResourceLoader
    from xblockutils.studio_editable import StudioEditableXBlockMixin

from .mixins.fragment import XBlockFragmentBuilderMixin
from web_fragments.fragment import Fragment
import logging
LOGGER = logging.getLogger(__name__)
#xmodule.course_module import CourseFields
class QualtricsSurveyViewMixin(
        XBlockFragmentBuilderMixin,
        StudioEditableXBlockMixin,
):
    """
    Handle view logic for the XBlock
    """

    loader = ResourceLoader(__name__)
    show_in_read_only_mode = True

    def provide_context(self, context=None):
        """
        Build a context dictionary to render the student view
        """

        context = context or {}
        context = dict(context)

        anon_user_id = self.get_anon_id()
        anon_user_id_string = ("platform_anonymous_user_id={anon_user_id}").format(
            anon_user_id=anon_user_id,
        )
        param_course_id = self.get_course_id()
        course_id_string = ("course_id={param_course_id}").format(
            param_course_id=param_course_id,
        )
        param_course_name = self.get_course_name()
        course_name_string = ("course_name={param_course_name}").format(
            param_course_name=param_course_name,
        )
        param_course_org = self.get_course_org()
        course_org_string = ("course_org={param_course_org}").format(
            param_course_org=param_course_org,
        )
        param_course_number = self.get_course_number()
        course_number_string = ("course_number={param_course_number}").format(
            param_course_number=param_course_number,
        )
        param_course_run = self.get_course_run() 
        course_run_string = ("course_run={param_course_run}").format(
            param_course_run=param_course_run,
        )
        param_course_term = self.get_course_term()
        course_term_string = ("course_term={param_course_term}").format(
            param_course_term=param_course_term,
        )
        param_course_start_date = self.get_course_start_date()
        course_start_date_string = ("course_start_date={param_course_start_date}").format(
            param_course_start_date=param_course_start_date,
        )
        param_course_end_date = self.get_course_end_date()
        course_end_date_string = ("course_end_date={param_course_end_date}").format(
            param_course_end_date=param_course_end_date,
        )
        param_course_institution = self.get_course_institution()
        course_institution_string = ("course_institution={param_course_institution}").format(
            param_course_institution=param_course_institution,
        )
        param_course_instructors = self.get_course_instructors()
        course_instructor_string = ("course_instructor={param_course_instructors}").format(
            param_course_instructors=param_course_instructors,
        )
        param_course_module_name = self.get_course_module_name()
        course_module_name_string = ("module_name={param_course_module_name}").format(
            param_course_module_name=param_course_module_name,
        )
        
        forward_platform_user_pii_string = ""
        if self.should_forward_platform_user_pii():
            forward_platform_user_pii_string = (
                "platform_username={param_platform_username}&platform_fullname={param_platform_fullname}&platform_email={param_platform_email}&platform_user_is_staff={param_platform_user_is_staff}").format(
                    param_platform_username=self.get_username,
                    param_platform_fullname=self.get_fullname,
                    param_platform_email=self.get_email,
                    param_platform_user_is_staff = self.get_user_is_staff
            )

        forward_platform_user_demographic_data_string = ""
        if self.should_forward_platform_user_demographic_data():
            forward_platform_user_demographic_data_string = (
                "demographic_year_of_birth={param_demographic_year_of_birth}&demographic_gender={param_demographic_gender}&demographic_level_of_education_completed={param_demographic_level_of_education_completed}&demographic_country={param_demographic_country}&demographic_ethnicity={param_demographic_ethnicity}&demographic_employment_status={param_demographic_employment_status}&demographic_zipcode={param_demographic_zipcode}&demographic_enrolled_in_school={param_demographic_enrolled_in_school}&demographic_enrolled_in_school_type={param_demographic_enrolled_in_school_type}&demographic_local_community_living={param_demographic_local_community_living}").format(
                    param_demographic_year_of_birth=self.get_user_year_of_birth,
                    param_demographic_gender=self.get_user_gender, param_demographic_level_of_education_completed=self.get_user_level_of_education, 
                    param_demographic_country=self.get_user_country,
                    param_demographic_ethnicity=self.get_user_ethnicity,
                    param_demographic_employment_status=self.get_user_employment_status,
                    param_demographic_zipcode=self.get_user_zipcode,
                    param_demographic_enrolled_in_school=self.get_user_enrolled_in_school,
                    param_demographic_enrolled_in_school_type=self.get_user_enrolled_in_school_type,
                    param_demographic_local_community_living=self.get_user_local_community_living
            )

        param_display_simulation_exists = '1' if self.should_show_simulation_exists() else '0'
        show_simulation_exists_string = ("simulation_exists={param_display_simulation_exists}").format(
            param_display_simulation_exists=param_display_simulation_exists,
        )
        param_display_meta = '1' if self.should_show_meta_information() else '0'
        show_meta_information_string = ("display_meta={param_display_meta}").format(
            param_display_meta=param_display_meta,
        )
        param_survey_completed = 'The survey is done' if self.survey_completed else 'Please continue to finish the survey'

        context.update({
            'survey_id': self.survey_id.strip(),
            'your_university': self.your_university.strip(),
            # 'link_text': self.link_text.strip(),
            # 'user_id_string': user_id_string.strip(),
            'course_id_string': course_id_string.strip(),
            'course_name_string': course_name_string.strip(),
            'course_org_string': course_org_string.strip(),
            'course_number_string': course_number_string.strip(),
            'course_run_string': course_run_string.strip(),
            'course_term_string': course_term_string.strip(),
            'course_start_date_string': course_start_date_string.strip(),
            'course_end_date_string': course_end_date_string.strip(),
            'course_institution_string': course_institution_string.strip(),
            'course_instructor_string': course_instructor_string.strip(),
            'course_module_name_string': course_module_name_string.strip(),
            #'course_module_id_string': self.module_id.strip(),
            'forward_platform_user_pii': forward_platform_user_pii_string.strip(),
            'forward_platform_user_demographic_data':
            forward_platform_user_demographic_data_string.strip(),
            'show_simulation_exists_string': show_simulation_exists_string.strip(),
            'show_meta_information_string': show_meta_information_string.strip(),
            'message': self.message,
            'survey_completed': param_survey_completed,
            'anon_user_id_string': anon_user_id_string,
            'earned_score': self.score.raw_earned if self.score is not None else 0.0,
            'possible_score': self.max_score(),
        })
        
        return context
