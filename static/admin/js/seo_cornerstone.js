(function () {
  "use strict";

  var DEBOUNCE_MS = 600;

  function scoreClass(score) {
    if (score >= 70) return "seo-analyzer__score--good";
    if (score >= 40) return "seo-analyzer__score--ok";
    return "seo-analyzer__score--bad";
  }

  function fieldValue(form, suffix) {
    var input = form.querySelector('[name$="-' + suffix + '"]');
    return input ? input.value.trim() : "";
  }

  function checkboxValue(form, suffix) {
    var input = form.querySelector('[name$="-' + suffix + '"]');
    return input ? input.checked : false;
  }

  function parentFieldValue(form, name) {
    var input = form.querySelector("#id_" + name);
    return input ? input.value.trim() : "";
  }

  function getCsrfToken(form) {
    var tokenInput = form.querySelector('[name="csrfmiddlewaretoken"]');
    return tokenInput ? tokenInput.value : "";
  }

  function liveBodyPlaintext() {
    var field = document.getElementById("id_body_plaintext");
    return field ? field.value.trim() : null;
  }

  function getConfig(root) {
    if (root.nextElementSibling && root.nextElementSibling.classList.contains("seo-analyzer-config")) {
      return root.nextElementSibling;
    }
    return null;
  }

  function collectPayload(form, config) {
    return {
      content_type_id: config ? config.dataset.contentTypeId || null : null,
      object_id: config ? config.dataset.objectId || null : null,
      article_title: parentFieldValue(form, "title"),
      url_slug: parentFieldValue(form, "slug"),
      excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
      seo_title: fieldValue(form, "seo_title"),
      meta_description: fieldValue(form, "meta_description"),
      focus_keyword: fieldValue(form, "focus_keyword"),
      is_cornerstone: checkboxValue(form, "is_cornerstone"),
      body_plaintext: liveBodyPlaintext(),
    };
  }

  function updateScoreRing(ring, score) {
    ring.classList.remove(
      "seo-analyzer__score--good",
      "seo-analyzer__score--ok",
      "seo-analyzer__score--bad",
      "seo-analyzer__score--neutral"
    );
    ring.classList.add(scoreClass(score));
  }

  function renderChecks(container, checks) {
    container.innerHTML = checks
      .map(function (check) {
        return (
          '<li class="seo-analyzer__check seo-analyzer__check--' +
          check.status +
          '">' +
          '<span class="seo-analyzer__dot" aria-hidden="true"></span>' +
          '<span class="seo-analyzer__check-body">' +
          "<strong>" +
          check.label +
          "</strong>" +
          '<span class="seo-analyzer__message">' +
          check.message +
          "</span></span></li>"
        );
      })
      .join("");
  }

  function renderList(container, items, className) {
    container.innerHTML = items
      .map(function (item) {
        return '<li class="' + className + '">' + item + "</li>";
      })
      .join("");
  }

  function renderWarnings(container, warnings) {
    if (!warnings || !warnings.length) {
      container.innerHTML =
        '<li class="seo-analyzer__warning seo-analyzer__warning--none">No warnings.</li>';
      return;
    }
    renderList(container, warnings, "seo-analyzer__warning");
  }

  function renderParent(container, parent, isCornerstone) {
    if (isCornerstone) {
      container.innerHTML = "";
      return;
    }
    if (!parent) {
      container.innerHTML =
        '<p class="seo-cornerstone__parent seo-cornerstone__parent--none">' +
        "No cornerstone cluster assigned for this topic." +
        "</p>";
      return;
    }

    var status = parent.links_to_cornerstone ? "Linked" : "Not linked";
    container.innerHTML =
      '<p class="seo-cornerstone__parent">' +
      "<strong>Cornerstone cluster:</strong> " +
      '<a href="' +
      parent.url +
      '" target="_blank" rel="noopener">' +
      parent.title +
      "</a> · " +
      parent.reason +
      " · " +
      '<span class="seo-cornerstone__parent-status">' +
      status +
      "</span></p>";
  }

  function renderSupporting(container, items) {
    if (!items || !items.length) {
      container.innerHTML =
        '<tr><td colspan="4" class="seo-cornerstone__empty">' +
        "No supporting articles identified — publish related topics." +
        "</td></tr>";
      return;
    }

    container.innerHTML = items
      .map(function (item) {
        var rowClass = item.links_to_cornerstone ? "linked" : "missing";
        var status = item.links_to_cornerstone ? "Linked" : "Missing link";
        return (
          '<tr class="seo-cornerstone__row seo-cornerstone__row--' +
          rowClass +
          '">' +
          "<td><strong>" +
          item.title +
          "</strong></td>" +
          "<td><code>" +
          item.url +
          "</code></td>" +
          "<td>" +
          item.reason +
          "</td>" +
          "<td>" +
          status +
          "</td></tr>"
        );
      })
      .join("");
  }

  function renderClusters(container, clusters) {
    if (!clusters || !clusters.length) {
      container.innerHTML =
        '<li class="seo-cornerstone__cluster seo-cornerstone__cluster--none">' +
        "Mark cornerstone articles to see cluster recommendations." +
        "</li>";
      return;
    }

    container.innerHTML = clusters
      .map(function (cluster) {
        return (
          '<li class="seo-cornerstone__cluster"><strong>' +
          cluster.cornerstone_title +
          "</strong> — " +
          cluster.recommendation +
          "</li>"
        );
      })
      .join("");
  }

  function initCornerstoneAnalyzer(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getConfig(root);
    var apiUrl = config ? config.dataset.seoAnalyzerApi : null;
    if (!apiUrl) return;

    var timer = null;
    var inflight = null;
    var requestId = 0;

    function runAnalysis() {
      if (inflight) inflight.abort();
      var thisRequestId = ++requestId;
      inflight = new AbortController();
      root.classList.add("is-loading");

      fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(form),
        },
        body: JSON.stringify(collectPayload(form, config)),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Analysis failed");
          return response.json();
        })
        .then(function (data) {
          if (thisRequestId !== requestId) {
            return;
          }
          if (data.message && !data.checks) {
            root.innerHTML = "<p>" + data.message + "</p>";
            return;
          }

          var scoreValue = root.querySelector("[data-seo-score-value]");
          var scoreRing = root.querySelector("[data-seo-score-ring]");
          var role = root.querySelector("[data-seo-cornerstone-role]");
          var incomingCount = root.querySelector("[data-seo-incoming-count]");
          var warningsList = root.querySelector("[data-seo-cornerstone-warnings]");
          var parentWrap = root.querySelector("[data-seo-parent-cornerstone]");
          var checksList = root.querySelector("[data-seo-checks-list]");
          var supportingList = root.querySelector("[data-seo-supporting-articles]");
          var clusterList = root.querySelector("[data-seo-cluster-recommendations]");
          var recommendationsList = root.querySelector("[data-seo-recommendations-list]");

          if (scoreValue) scoreValue.textContent = String(data.score);
          if (scoreRing) updateScoreRing(scoreRing, data.score);
          if (role) {
            role.textContent = data.is_cornerstone ? "Cornerstone article" : "Supporting article";
          }
          if (incomingCount) incomingCount.textContent = String(data.incoming_link_count || 0);
          if (warningsList) renderWarnings(warningsList, data.warnings);
          if (parentWrap) renderParent(parentWrap, data.parent_cornerstone, data.is_cornerstone);
          if (checksList && data.checks) renderChecks(checksList, data.checks);
          if (supportingList) renderSupporting(supportingList, data.supporting_articles);
          if (clusterList) renderClusters(clusterList, data.cluster_recommendations);
          if (recommendationsList && data.recommendations) {
            renderList(recommendationsList, data.recommendations, "seo-analyzer__recommendation");
          }
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO cornerstone analysis error:", error);
          }
        })
        .finally(function () {
          if (thisRequestId === requestId) {
            root.classList.remove("is-loading");
            inflight = null;
          }
        });
    }

    function scheduleAnalysis() {
      window.clearTimeout(timer);
      timer = window.setTimeout(runAnalysis, DEBOUNCE_MS);
    }

    var cornerstoneInput = form.querySelector('[name$="-is_cornerstone"]');
    if (cornerstoneInput) {
      cornerstoneInput.addEventListener("change", scheduleAnalysis);
    }

    ["focus_keyword", "secondary_keywords", "seo_title", "meta_description"].forEach(function (suffix) {
      var input = form.querySelector('[name$="-' + suffix + '"]');
      if (input) {
        input.addEventListener("input", scheduleAnalysis);
        input.addEventListener("change", scheduleAnalysis);
      }
    });

    ["title", "slug", "excerpt"].forEach(function (name) {
      var input = form.querySelector("#id_" + name);
      if (input) {
        input.addEventListener("input", scheduleAnalysis);
        input.addEventListener("change", scheduleAnalysis);
      }
    });

    var bodyPlaintextInput = form.querySelector("#id_body_plaintext");
    if (bodyPlaintextInput) {
      bodyPlaintextInput.addEventListener("input", scheduleAnalysis);
      bodyPlaintextInput.addEventListener("change", scheduleAnalysis);
    }
  }

  function boot() {
    document.querySelectorAll("[data-seo-cornerstone-analyzer]").forEach(initCornerstoneAnalyzer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("seo-analyzer-hydrated", function (event) {
    var root = event.detail && event.detail.root;
    if (root && root.matches("[data-seo-cornerstone-analyzer]")) {
      initCornerstoneAnalyzer(root);
    }
  });
})();
