

/* eslint-disable no-unused-vars */
/**
 * Initialize the QualtricsSurvey student view
 * @param {Object} runtime - The XBlock JS Runtime
 * @param {Object} element - The containing DOM element for this instance of the XBlock
 * @returns {undefined} nothing
 */
 
function QualtricsSurveyView(runtime, element) {
  'use strict';

  var $ = window.jQuery;
  var $element = $(element);
  
  /* eslint-enable no-unused-vars */
   
    
  // TODO: Put your logic here
  // To find elements inside your XBlock, try:
  // var myElement = $element.find('.myElement');
  
  var earned_score_html = $('.qualtricssurvey_block .qualtrics_message .grade .earned_score')
  var possible_score_html = $('.qualtricssurvey_block .qualtrics_message .grade .possible_score')
  var status_html = $('.qualtricssurvey_block .qualtrics_message .grade .status')
  var graded_html = $('.qualtricssurvey_block .qualtrics_message .grade .is_graded')
  
  var handlerUrl = runtime.handlerUrl(element, 'get_survey_status');

  /* Set the graded status for the xblock */
  function updateGradedStatus() {
    $.ajax({
        type: 'POST',
        url: runtime.handlerUrl(element, 'is_graded'),
        data: '{}',
        success: function (data) {
          $element.find(graded_html).text(
            data.graded ? '(Graded) ' : '(Ungraded) ' 
          );
        },
        dataType: 'json'
    });
  }

  /* Regularly check to see if score was received and display to the learner */
  function updateView(event) {
    setTimeout(function() { 
      $.ajax({
        method: "POST",
        url: handlerUrl,
        data: JSON.stringify({}),
        success: function (data) {
          if (data.is_answered == true) {
            $element.find(earned_score_html).text(data.earned_score.toFixed(1))
            $element.find(possible_score_html).text(data.possible_score.toFixed(1))
            $element.find(status_html).addClass("fa fa-check-circle graded")
          }
          else {
            updateView()
          }
        }
      });
    }, 3000)
  }

  updateGradedStatus();
  updateView();
}
