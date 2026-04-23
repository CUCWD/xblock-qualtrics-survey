/* Javascript for Qualtrics Survey XBlock */

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
  
  var grade_html = $element.find('.qualtrics_message .grade')
  var grade_points_html = $element.find('.qualtrics_message .grade .grade_points')
  var earned_score_html = $element.find('.qualtrics_message .grade .earned_score')
  var possible_score_html = $element.find('.qualtrics_message .grade .possible_score')
  var status_html = $element.find('.qualtrics_message .grade .status')
  var graded_html = $element.find('.qualtrics_message .grade .is_graded')
  var iframe_html = $element.find('iframe.qualtrics-survey-iframe')
  
  var handlerUrl = runtime.handlerUrl(element, 'get_survey_status');
  var pollIntervalMs = 3000
  var defaultIframeHeight = 900
  var minIframeHeight = 300
  var maxIframeHeight = 1000
  var iframeHeightBufferPx = 24

  var isGraded = false

  function setIframeHeight(height) {
    var parsedHeight = parseInt(height, 10)
    if (!Number.isFinite(parsedHeight) || parsedHeight <= 0) {
      return
    }

    // Add a small buffer so embedded content doesn't clip at the bottom.
    parsedHeight += iframeHeightBufferPx

    // Keep the iframe height within a sane range.
    var boundedHeight = Math.min(Math.max(parsedHeight, minIframeHeight), maxIframeHeight)
    iframe_html.height(boundedHeight)
  }

  function initializeIframeAutoResize() {
    if (!iframe_html.length) {
      return
    }

    iframe_html.height(defaultIframeHeight)

    var iframeSrc = iframe_html.attr('src')
    if (!iframeSrc) {
      return
    }

    var qualtricsOrigin = new URL(iframeSrc, window.location.href).origin
    window.addEventListener('message', function (event) {
      if (event.origin !== qualtricsOrigin) {
        return
      }

      var payload = event.data
      if (payload && payload.type === 'qualtrics-survey-height') {
        setIframeHeight(payload.height)
        return
      }

      if (payload && typeof payload.height !== 'undefined') {
        setIframeHeight(payload.height)
      }
    })
  }

  /* Set the graded status for the xblock */
  function updateGradedStatus() {
    $.ajax({
        type: 'POST',
        url: runtime.handlerUrl(element, 'is_graded'),
        data: '{}',
        success: function (data) {
          isGraded = data.graded
          if (isGraded) {
            graded_html.text('(Graded) ')
            grade_points_html.show()
          }
          else {
            // For ungraded subsections, show only the ungraded label.
            graded_html.text('(Ungraded) ')
            grade_points_html.hide()
          }
        },
        complete: function () {
          updateView()
        },
        dataType: 'json'
    });
  }

  /* Regularly check to see if score was received and display to the learner */
  function updateView() {
    $.ajax({
      method: "POST",
      url: handlerUrl,
      data: JSON.stringify({}),
      success: function (data) {
        if (data.is_answered == true) {
          earned_score_html.text(data.earned_score.toFixed(1))
          possible_score_html.text(data.possible_score.toFixed(1))

          /* If the survey is graded, show a green checkmark for completed */
          /* If the survey is ungraded, show a gray checkmark for completed. */
          if (isGraded) {
            status_html.removeClass('ungraded').addClass('fa fa-check-circle graded')
          } else {
            status_html.removeClass('graded').addClass('fa fa-check-circle ungraded')
          }
        }
      },
      complete: function () {
        setTimeout(updateView, pollIntervalMs)
      }
    });
  }

  initializeIframeAutoResize()
  updateGradedStatus();
}
