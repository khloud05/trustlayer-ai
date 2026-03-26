/* =====================================================================
   TrustLayer AI — app.js
   All client-side logic: survey timer, validation, review, dashboard
   ===================================================================== */

"use strict";

// -----------------------------------------------------------------------
// Utility helpers
// -----------------------------------------------------------------------
function $(selector, ctx) {
    return (ctx || document).querySelector(selector);
}
function $$(selector, ctx) {
    return Array.from((ctx || document).querySelectorAll(selector));
}

function showSpinner(text) {
    var overlay = $("#spinnerOverlay");
    if (overlay) {
        var label = overlay.querySelector(".spinner-text");
        if (label && text) label.textContent = text;
        overlay.classList.add("visible");
    }
}

function hideSpinner() {
    var overlay = $("#spinnerOverlay");
    if (overlay) overlay.classList.remove("visible");
}

function navigateTo(path) {
    window.location.href = path;
}

// -----------------------------------------------------------------------
// Survey Page
// -----------------------------------------------------------------------
var surveyStartTime = null;

function initSurveyPage() {
    if (!document.getElementById("surveyForm")) return;

    // Load questions from API
    fetch("/api/questions")
        .then(function(r) { return r.json(); })
        .then(function(config) {
            renderQuestions(config);

            // Set domain label
            var domainLabel = document.getElementById("domainLabel");
            if (domainLabel && config.domain_label) {
                domainLabel.textContent = config.domain_label;
            }

            // Show submit button after questions loaded
            var reviewBtn = document.getElementById("reviewBtn");
            if (reviewBtn) reviewBtn.style.display = "";

            surveyStartTime = Date.now();

            // Pre-fill if returning from review
            try {
                var raw = sessionStorage.getItem("currentAnswers");
                if (raw) prefillForm(JSON.parse(raw));
            } catch (e) {}

            if (reviewBtn) {
                reviewBtn.addEventListener("click", handleReviewClick);
            }
        })
        .catch(function(err) {
            var container = document.getElementById("questionsContainer");
            if (container) {
                container.innerHTML = '<p style="color:var(--danger);text-align:center;">تعذّر تحميل الأسئلة. يرجى تحديث الصفحة.</p>';
            }
        });
}

function renderQuestions(config) {
    var container = document.getElementById("questionsContainer");
    if (!container) return;

    var html = config.questions.map(function(q, index) {
        var optionsHtml = q.options.map(function(opt) {
            return '<label class="radio-option">' +
                '<input type="radio" name="' + q.id + '" value="' + opt.value + '" />' +
                '<span class="radio-label">' + opt.label + '</span>' +
                '</label>';
        }).join("");

        return '<div class="question-card" data-field="' + q.id + '">' +
            '<label class="question-label">' +
            '<span class="question-number">' + (index + 1) + '</span>' +
            q.text +
            '</label>' +
            '<div class="radio-group">' + optionsHtml + '</div>' +
            '</div>';
    }).join("");

    container.innerHTML = html;
}

function prefillForm(answers) {
    Object.entries(answers).forEach(function(entry) {
        var fieldName = entry[0];
        var value = entry[1];
        var inputs = $$("input[name='" + fieldName + "']");
        inputs.forEach(function(input) {
            if (input.value === value) {
                input.checked = true;
            }
        });
    });
}

function getFormValues() {
    var fields = Array.from(document.querySelectorAll(".question-card"))
        .map(function(card) { return card.dataset.field; })
        .filter(Boolean);

    var answers = {};
    var missing = [];

    fields.forEach(function(field) {
        var selected = document.querySelector("input[name='" + field + "']:checked");
        if (selected) {
            answers[field] = selected.value;
        } else {
            missing.push(field);
        }
    });

    return { answers: answers, missing: missing };
}

function highlightMissingFields(missingFields) {
    // Reset all question cards
    $$(".question-card").forEach(function(card) {
        card.classList.remove("error");
    });

    missingFields.forEach(function(field) {
        var card = $(".question-card[data-field='" + field + "']");
        if (card) {
            card.classList.add("error");
            card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    });
}

function showSurveyError(message) {
    var errorDiv = document.getElementById("surveyError");
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add("visible");
        errorDiv.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function hideSurveyError() {
    var errorDiv = document.getElementById("surveyError");
    if (errorDiv) {
        errorDiv.classList.remove("visible");
    }
}

async function handleReviewClick() {
    hideSurveyError();

    var result = getFormValues();

    if (result.missing.length > 0) {
        highlightMissingFields(result.missing);
        showSurveyError("يرجى إكمال جميع الحقول المطلوبة قبل المتابعة.");
        return;
    }

    // Clear error highlights
    $$(".question-card").forEach(function(card) {
        card.classList.remove("error");
    });

    var responseTimeSec = Math.max(1, Math.round((Date.now() - surveyStartTime) / 1000));
    var responseId = "RESP-" + Date.now();

    // Check if we already had a previous originalAnswers; if not, this is the first validation
    var hadPreviousValidation = sessionStorage.getItem("validationShown") === "true";
    if (!hadPreviousValidation) {
        sessionStorage.setItem("originalAnswers", JSON.stringify(result.answers));
    }

    var requestBody = {
        response_id: responseId,
        source: "web_survey",
        answers: result.answers,
        response_time_seconds: responseTimeSec
    };

    showSpinner("جارٍ التحقق من الإجابات...");

    try {
        var response = await fetch("/validate-response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        var validationResult = await response.json();

        // Store in sessionStorage
        sessionStorage.setItem("validationResult", JSON.stringify(validationResult));
        sessionStorage.setItem("currentAnswers", JSON.stringify(result.answers));
        sessionStorage.setItem("responseId", responseId);
        sessionStorage.setItem("responseTimeSeconds", String(responseTimeSec));
        sessionStorage.setItem("validationShown", "true");

        hideSpinner();
        navigateTo("/review");

    } catch (err) {
        hideSpinner();
        showSurveyError("حدث خطأ أثناء التحقق من الإجابات. يرجى المحاولة مرة أخرى.");
        console.error("Validation error:", err);
    }
}

// -----------------------------------------------------------------------
// Review Page
// -----------------------------------------------------------------------
function initReviewPage() {
    if (!document.getElementById("reviewContent")) return;

    var validationResult = null;
    var currentAnswers = null;

    try {
        var vr = sessionStorage.getItem("validationResult");
        var ca = sessionStorage.getItem("currentAnswers");
        if (vr) validationResult = JSON.parse(vr);
        if (ca) currentAnswers = JSON.parse(ca);
    } catch (e) {}

    if (!validationResult) {
        navigateTo("/survey");
        return;
    }

    renderReview(validationResult);

    // Button: Edit answers
    var editBtn = document.getElementById("editBtn");
    if (editBtn) {
        editBtn.addEventListener("click", function() {
            navigateTo("/survey");
        });
    }

    // Button: Re-validate
    var revalidateBtn = document.getElementById("revalidateBtn");
    if (revalidateBtn) {
        revalidateBtn.addEventListener("click", handleRevalidate);
    }

    // Button: Confirm submit
    var confirmBtn = document.getElementById("confirmBtn");
    if (confirmBtn) {
        confirmBtn.addEventListener("click", handleConfirmSubmit);
    }
}

function renderReview(validationResult) {
    var score = validationResult.confidence_score;
    var quality = validationResult.quality_level;
    var issues = validationResult.issues || [];

    // Score circle
    var scoreEl = document.getElementById("scoreNumber");
    var scoreCircle = document.getElementById("scoreCircle");
    if (scoreEl) scoreEl.textContent = score;
    if (scoreCircle) {
        scoreCircle.className = "score-circle " + quality.toLowerCase();
    }

    // Quality badge
    var qualityBadge = document.getElementById("qualityBadge");
    if (qualityBadge) {
        qualityBadge.className = "quality-badge " + quality.toLowerCase();
        var labelMap = { "High": "جودة عالية", "Medium": "جودة متوسطة", "Low": "جودة منخفضة" };
        qualityBadge.textContent = labelMap[quality] || quality;
    }

    // Score description
    var scoreDesc = document.getElementById("scoreDescription");
    if (scoreDesc) {
        var descMap = {
            "High": "إجاباتك متسقة ومنطقية. الجودة عالية.",
            "Medium": "تم اكتشاف بعض التناقضات. يُنصح بمراجعتها.",
            "Low": "تم اكتشاف تناقضات متعددة. يرجى مراجعة الإجابات."
        };
        scoreDesc.textContent = descMap[quality] || "";
    }

    // Issues list
    var issuesList = document.getElementById("issuesList");
    if (issuesList) {
        if (issues.length === 0) {
            issuesList.innerHTML = '<div class="no-issues-card">' +
                '<h3>✓ لا توجد تناقضات</h3>' +
                '<p>لم يتم اكتشاف أي تناقضات في الإجابات.</p>' +
                '</div>';
        } else {
            var issuesTitle = document.getElementById("issuesTitle");
            if (issuesTitle) {
                issuesTitle.textContent = "المشكلات المكتشفة (" + issues.length + ")";
            }

            issuesList.innerHTML = issues.map(function(issue) {
                var severityLabel = { "High": "خطورة عالية", "Medium": "خطورة متوسطة", "Low": "خطورة منخفضة" };
                var fieldNameMap = {
                    "monthly_income": "الدخل الشهري",
                    "luxury_purchase_frequency": "تكرار شراء السلع الفاخرة",
                    "internet_usage": "استخدام الإنترنت",
                    "app_evaluation": "تقييم التطبيقات",
                    "tv_usage": "مشاهدة التلفاز",
                    "favorite_tv_channels": "القنوات التلفزيونية المفضلة",
                    "purchase_frequency": "تكرار الشراء الشهري",
                    "monthly_spending": "الإنفاق الشهري",
                    "brand_preference": "العلامة التجارية المفضلة",
                    "last_purchase": "آخر عملية شراء",
                    "purchase_reason": "سبب الشراء"
                };
                var fieldTags = issue.field_names.map(function(f) {
                    return '<span class="field-tag">' + (fieldNameMap[f] || f) + '</span>';
                }).join("");

                return '<div class="issue-card ' + issue.severity + '">' +
                    '<div class="issue-header">' +
                    '<span class="severity-badge ' + issue.severity + '">' + (severityLabel[issue.severity] || issue.severity) + '</span>' +
                    '<span class="deduction-badge">- ' + issue.deduction + ' نقطة</span>' +
                    '</div>' +
                    '<div class="issue-message">' + escapeHtml(issue.ar_message) + '</div>' +
                    '<div class="issue-explanation">' + escapeHtml(issue.ar_explanation) + '</div>' +
                    '<div class="issue-action">← ' + escapeHtml(issue.ar_action_suggested) + '</div>' +
                    (fieldTags ? '<div class="issue-fields">' + fieldTags + '</div>' : '') +
                    '</div>';
            }).join("");
        }
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function handleRevalidate() {
    var currentAnswers = null;
    var responseTimeSec = 0;

    try {
        var ca = sessionStorage.getItem("currentAnswers");
        var rt = sessionStorage.getItem("responseTimeSeconds");
        if (ca) currentAnswers = JSON.parse(ca);
        if (rt) responseTimeSec = parseInt(rt, 10);
    } catch (e) {}

    if (!currentAnswers) {
        navigateTo("/survey");
        return;
    }

    var responseId = "RESP-" + Date.now();
    sessionStorage.setItem("responseId", responseId);

    var requestBody = {
        response_id: responseId,
        source: "web_survey",
        answers: currentAnswers,
        response_time_seconds: responseTimeSec
    };

    showSpinner("جارٍ إعادة التحقق...");

    try {
        var response = await fetch("/validate-response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) throw new Error("Server error");

        var validationResult = await response.json();
        sessionStorage.setItem("validationResult", JSON.stringify(validationResult));

        hideSpinner();
        renderReview(validationResult);

    } catch (err) {
        hideSpinner();
        alert("حدث خطأ أثناء إعادة التحقق. يرجى المحاولة مرة أخرى.");
        console.error(err);
    }
}

async function handleConfirmSubmit() {
    var validationResult = null;
    var currentAnswers = null;
    var originalAnswers = null;
    var responseId = null;
    var responseTimeSec = 0;

    try {
        var vr = sessionStorage.getItem("validationResult");
        var ca = sessionStorage.getItem("currentAnswers");
        var oa = sessionStorage.getItem("originalAnswers");
        var rid = sessionStorage.getItem("responseId");
        var rt = sessionStorage.getItem("responseTimeSeconds");
        if (vr) validationResult = JSON.parse(vr);
        if (ca) currentAnswers = JSON.parse(ca);
        if (oa) originalAnswers = JSON.parse(oa);
        if (rid) responseId = rid;
        if (rt) responseTimeSec = parseInt(rt, 10);
    } catch (e) {}

    if (!validationResult || !currentAnswers || !responseId) {
        navigateTo("/survey");
        return;
    }

    // Build correction_actions by comparing originalAnswers vs currentAnswers
    var correctionActions = [];
    if (originalAnswers) {
        Object.keys(currentAnswers).forEach(function(field) {
            if (originalAnswers[field] !== undefined && originalAnswers[field] !== currentAnswers[field]) {
                correctionActions.push({
                    field_name: field,
                    previous_value: originalAnswers[field],
                    updated_value: currentAnswers[field]
                });
            }
        });
    }

    var submitBody = {
        response_id: responseId,
        source: "web_survey",
        answers: currentAnswers,
        response_time_seconds: responseTimeSec,
        confidence_score: validationResult.confidence_score,
        quality_level: validationResult.quality_level,
        issues: validationResult.issues,
        correction_actions: correctionActions,
        final_confirmed: true
    };

    showSpinner("جارٍ حفظ الإجابات...");

    try {
        var response = await fetch("/submit-response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(submitBody)
        });

        if (!response.ok) throw new Error("Server error");

        var result = await response.json();

        // Store final result for success page
        sessionStorage.setItem("finalScore", String(validationResult.confidence_score));
        sessionStorage.setItem("finalQuality", validationResult.quality_level);
        sessionStorage.setItem("finalResponseId", responseId);

        hideSpinner();
        navigateTo("/success");

    } catch (err) {
        hideSpinner();
        console.error(err);
        navigateTo("/error");
    }
}

// -----------------------------------------------------------------------
// Success Page
// -----------------------------------------------------------------------
function initSuccessPage() {
    if (!document.getElementById("successContent")) return;

    var score = sessionStorage.getItem("finalScore");
    var quality = sessionStorage.getItem("finalQuality");
    var responseId = sessionStorage.getItem("finalResponseId");

    var scoreEl = document.getElementById("finalScoreDisplay");
    if (scoreEl && score) scoreEl.textContent = score;

    var qualityEl = document.getElementById("finalQualityDisplay");
    if (qualityEl && quality) {
        var qualityAr = { "High": "عالية", "Medium": "متوسطة", "Low": "منخفضة" };
        qualityEl.textContent = qualityAr[quality] || quality;
        qualityEl.className = "result-row-value quality-badge " + (quality || "").toLowerCase();
    }

    var responseIdEl = document.getElementById("finalResponseIdDisplay");
    if (responseIdEl && responseId) responseIdEl.textContent = responseId;

    // Clear session after displaying
    sessionStorage.removeItem("validationResult");
    sessionStorage.removeItem("currentAnswers");
    sessionStorage.removeItem("originalAnswers");
    sessionStorage.removeItem("responseId");
    sessionStorage.removeItem("responseTimeSeconds");
    sessionStorage.removeItem("validationShown");
}

// -----------------------------------------------------------------------
// Error Page
// -----------------------------------------------------------------------
function initErrorPage() {
    if (!document.getElementById("errorContent")) return;

    var retryBtn = document.getElementById("retryBtn");
    if (retryBtn) {
        retryBtn.addEventListener("click", function() {
            navigateTo("/survey");
        });
    }
}

// -----------------------------------------------------------------------
// Dashboard Page
// -----------------------------------------------------------------------
function initDashboardPage() {
    if (!document.getElementById("dashboardContent")) return;
    loadDashboardStats();
}

async function loadDashboardStats() {
    try {
        var response = await fetch("/api/dashboard-stats");
        if (!response.ok) throw new Error("Failed to fetch stats");
        var stats = await response.json();
        renderDashboard(stats);
    } catch (err) {
        console.error("Dashboard error:", err);
    }
}

function setTextById(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
}

function renderDashboard(stats) {
    setTextById("statTotalResponses", stats.total_responses || 0);
    setTextById("statAvgScore", (stats.avg_confidence_score || 0) + "%");
    setTextById("statHighQuality", stats.high_quality_count || 0);
    setTextById("statMediumQuality", stats.medium_quality_count || 0);
    setTextById("statLowQuality", stats.low_quality_count || 0);
    setTextById("statFlagged", stats.flagged_count || 0);
    setTextById("statValid", stats.valid_count || 0);
    setTextById("statPrecision", (stats.precision || 0) + "%");
    setTextById("statRecall", (stats.recall || 0) + "%");
    setTextById("statCorrectionRate", (stats.correction_rate || 0) + "%");
    setTextById("statCompletionRate", (stats.completion_rate || 0) + "%");
    setTextById("statTimeSaved", stats.time_saved || "0%");
    setTextById("statOverallQuality", stats.overall_data_quality || "—");
}

// -----------------------------------------------------------------------
// Boot: detect current page and initialize
// -----------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function() {
    var path = window.location.pathname;

    if (path === "/survey") {
        initSurveyPage();
    } else if (path === "/review") {
        initReviewPage();
    } else if (path === "/success") {
        initSuccessPage();
    } else if (path === "/error") {
        initErrorPage();
    } else if (path === "/dashboard") {
        initDashboardPage();
    }
});
