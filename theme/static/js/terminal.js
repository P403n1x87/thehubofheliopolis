// Progressive enhancements for the terminal theme. The pages work without it.
(function () {
  "use strict";

  // Highlight the table of contents entry for the section being read.
  var toc = document.getElementById("toc");
  if (toc) {
    var links = Array.prototype.slice.call(toc.querySelectorAll("a[href^='#']"));
    var targets = links.map(function (a) {
      return document.getElementById(decodeURIComponent(a.hash.slice(1)));
    });
    var current = null;
    var pending = false;

    var update = function () {
      pending = false;
      var active = null;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i] && targets[i].getBoundingClientRect().top < 120) active = links[i];
      }
      if (active === current) return;
      if (current) current.classList.remove("current");
      if (active) active.classList.add("current");
      current = active;
    };

    window.addEventListener("scroll", function () {
      if (!pending) {
        pending = true;
        requestAnimationFrame(update);
      }
    }, { passive: true });
    update();
  }

  // Copy buttons on code blocks.
  if (navigator.clipboard) {
    document.querySelectorAll(".entry-content .highlight").forEach(function (block) {
      // Blocks with line numbers keep the code in the second table cell.
      var pre = block.querySelector("td.code pre") || block.querySelector("pre");
      if (!pre) return;
      var button = document.createElement("button");
      button.className = "copy";
      button.type = "button";
      button.textContent = "copy";
      button.addEventListener("click", function () {
        navigator.clipboard.writeText(pre.innerText.replace(/\n$/, "")).then(function () {
          button.textContent = "copied";
          setTimeout(function () { button.textContent = "copy"; }, 1500);
        });
      });
      block.appendChild(button);
    });
  }

  // less(1)-style paging: n for the next page, p for the previous one.
  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey || e.target.isContentEditable) return;
    if (/^(input|textarea|select)$/i.test(e.target.tagName)) return;
    var rel = { n: "next", p: "prev" }[e.key];
    var link = rel && document.querySelector(".pager a[rel='" + rel + "']");
    if (link) location.href = link.href;
  });

  // Visit counts from GoatCounter's public counter API. Elements stay hidden
  // if the counter is disabled, blocked or unreachable.
  var gc = document.querySelector("meta[name='goatcounter']");
  var counters = document.querySelectorAll("[data-views]");
  if (gc && counters.length && window.fetch) {
    var base = gc.content + "/counter/";
    var posts = parseInt(gc.getAttribute("data-posts"), 10) || 0;

    // Resolves to a number; 0 for paths with no recorded visits (HTTP 404).
    var count = function (path, week) {
      var url = base + encodeURIComponent(path) + ".json" + (week ? "?start=week" : "");
      return fetch(url).then(function (r) {
        if (r.status === 404) return 0;
        if (!r.ok) throw new Error(r.status);
        return r.json().then(function (data) {
          return parseInt(String(data.count).replace(/\D/g, ""), 10) || 0;
        });
      });
    };

    var plural = function (n, word) {
      return n.toLocaleString("en") + " " + word + (n === 1 ? "" : "s");
    };

    // How this week's views compare to an even split of the site's traffic.
    var heat = function (weekly, siteWeekly) {
      return posts && siteWeekly ? weekly * posts / siteWeekly : 0;
    };

    count("TOTAL", true).then(function (siteWeekly) {
      Array.prototype.forEach.call(counters, function (el) {
        var path = decodeURI(el.getAttribute("data-views"));
        var full = el.hasAttribute("data-views-total");
        Promise.all([count(path, true), full ? count(path, false) : null]).then(function (r) {
          var weekly = r[0];
          var total = r[1];
          var h = heat(weekly, siteWeekly);
          var level = h >= 3 ? "hot" : h >= 1.5 ? "warm" : "";

          var trend = document.createElement("span");
          trend.className = "views-week" + (level ? " " + level : "");
          trend.textContent = "+" + weekly.toLocaleString("en") + (full ? " this week" : "");
          var describe = function (total) {
            trend.title = (total ? plural(total, "view") + " in total, " : "") +
              plural(weekly, "view") + " in the last 7 days" +
              (h ? ", " + h.toFixed(1) + "× an even share of the site's traffic" : "");
          };
          describe(null);

          if (full) {
            if (!total) return;
            el.appendChild(document.createTextNode(plural(total, "view") + " "));
          } else if (!weekly) {
            return;
          } else {
            // Lists only show the weekly delta; fetch the total for the
            // tooltip on first hover of the row, ahead of the tooltip delay.
            var row = el.closest(".post") || el;
            var more = function () {
              row.removeEventListener("mouseenter", more);
              count(path, false).then(describe).catch(function () {});
            };
            row.addEventListener("mouseenter", more);
          }
          el.appendChild(trend);
          el.hidden = false;
        }).catch(function () {});
      });
    }).catch(function () {});
  }
})();
