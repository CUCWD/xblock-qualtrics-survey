/* Javascript for Qualtrics Survey XBlock */

/* exported QualtricsSurveyView */
/**
 * Initialize the QualtricsSurvey student view
 * @param {Object} runtime - The XBlock JS Runtime
 * @param {Object} element - The containing DOM element for this instance of the XBlock
 * @returns {void} nothing
 */
function QualtricsSurveyView(runtime, element) {
    'use strict';

    var $ = window.jQuery;
    var $element = $(element);

    var gradePointsHtml = $element.find('.qualtrics_message .grade .grade_points');
    var earnedScoreHtml = $element.find('.qualtrics_message .grade .earned_score');
    var possibleScoreHtml = $element.find('.qualtrics_message .grade .possible_score');
    var statusHtml = $element.find('.qualtrics_message .grade .status');
    var gradedHtml = $element.find('.qualtrics_message .grade .is_graded');
    var iframeHtml = $element.find('iframe.qualtrics-survey-iframe');

    var handlerUrl = runtime.handlerUrl(element, 'get_survey_status');
    var pollIntervalMs = 3000;
    var defaultIframeHeight = 900;
    var minIframeHeight = 300;
    var maxIframeHeight = 1000;
    var iframeHeightBufferPx = 24;

    var isGraded = false;

    /**
     * Apply the height limits and buffer to an iframe resize message.
     * @param {number|string} height - Requested content height
     * @returns {void} nothing
     */
    function setIframeHeight(height) {
        var parsedHeight = parseInt(height, 10);
        if (!Number.isFinite(parsedHeight) || parsedHeight <= 0) {
            return;
        }

        // Add a small buffer so embedded content doesn't clip at the bottom.
        parsedHeight += iframeHeightBufferPx;

        // Keep the iframe height within a sane range.
        var boundedHeight = Math.min(Math.max(parsedHeight, minIframeHeight), maxIframeHeight);
        iframeHtml.height(boundedHeight);
    }

    /**
     * Listen for resize messages from the configured Qualtrics origin.
     * @returns {void} nothing
     */
    function initializeIframeAutoResize() {
        if (!iframeHtml.length) {
            return;
        }

        iframeHtml.height(defaultIframeHeight);

        var iframeSrc = iframeHtml.attr('src');
        if (!iframeSrc) {
            return;
        }

        var qualtricsOrigin = new URL(iframeSrc, window.location.href).origin;
        window.addEventListener('message', function(event) {
            if (event.origin !== qualtricsOrigin) {
                return;
            }

            var payload = event.data;
            if (payload && payload.type === 'qualtrics-survey-height') {
                setIframeHeight(payload.height);
                return;
            }

            if (payload && typeof payload.height !== 'undefined') {
                setIframeHeight(payload.height);
            }
        });
    }

    /**
     * Poll for survey completion and update the displayed score.
     * @returns {void} nothing
     */
    function updateView() {
        $.ajax({
            method: 'POST',
            url: handlerUrl,
            data: JSON.stringify({}),
            success(data) {
                if (data.is_answered === true) {
                    earnedScoreHtml.text(data.earned_score.toFixed(1));
                    possibleScoreHtml.text(data.possible_score.toFixed(1));

                    /* If the survey is graded, show a green checkmark for completed */
                    /* If the survey is ungraded, show a gray checkmark for completed. */
                    if (isGraded) {
                        statusHtml.removeClass('ungraded').addClass('fa fa-check-circle graded');
                    } else {
                        statusHtml.removeClass('graded').addClass('fa fa-check-circle ungraded');
                    }
                }
            },
            complete() {
                setTimeout(updateView, pollIntervalMs);
            },
        });
    }

    /**
     * Set the graded status for the XBlock.
     * @returns {void} nothing
     */
    function updateGradedStatus() {
        $.ajax({
            type: 'POST',
            url: runtime.handlerUrl(element, 'is_graded'),
            data: '{}',
            success(data) {
                isGraded = data.graded;
                if (isGraded) {
                    gradedHtml.text('(Graded) ');
                    gradePointsHtml.show();
                } else {

                    // For ungraded subsections, show only the ungraded label.
                    gradedHtml.text('(Ungraded) ');
                    gradePointsHtml.hide();
                }
            },
            complete() {
                updateView();
            },
            dataType: 'json',
        });
    }

    initializeIframeAutoResize();
    updateGradedStatus();
}
