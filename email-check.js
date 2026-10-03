/* Catches the common typos in an email address before the Kit form posts it.
 *
 * Kit cannot reach a mistyped address, so the download email never arrives and the person thinks the
 * page is broken (2026-09-29: an address ending ".comrm" bounced). This only suggests: the first submit
 * of a likely typo shows "Did you mean ...?", one click fixes and sends it, and submitting again sends
 * the address as typed. Every page with a Kit form loads it: <script src="/email-check.js" defer>.
 */
(function () {
  // Real domains, never "corrected". Montreal-heavy list, so the .ca and .fr providers are here too.
  var KNOWN = [
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.ca", "hotmail.fr", "hotmail.co.uk",
    "outlook.com", "outlook.fr", "live.com", "live.ca", "live.fr", "msn.com",
    "yahoo.com", "yahoo.ca", "yahoo.fr", "yahoo.co.uk", "ymail.com", "rocketmail.com",
    "icloud.com", "me.com", "mac.com", "aol.com", "mail.com", "gmx.com", "gmx.de",
    "protonmail.com", "proton.me", "videotron.ca", "sympatico.ca", "bell.net", "rogers.com",
    "shaw.ca", "telus.net", "orange.fr", "free.fr", "laposte.net", "sfr.fr", "qq.com", "163.com"
  ];
  // Only these are offered as corrections: the big free providers, where a near miss is almost certainly a slip.
  var TARGETS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com", "live.com", "aol.com"];
  var BAD_COM = /\.(con|cmo|comm|coom|vom|xom|ocm|cpm|cim|comrm|comr|come|cm|om|co|c)$/;

  function distance(a, b) {
    var row = [], i, j, prev, tmp;
    for (j = 0; j <= b.length; j++) row[j] = j;
    for (i = 1; i <= a.length; i++) {
      prev = row[0]; row[0] = i;
      for (j = 1; j <= b.length; j++) {
        tmp = row[j];
        row[j] = Math.min(row[j] + 1, row[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
        prev = tmp;
      }
    }
    return row[b.length];
  }

  /* The corrected address, or "" when there is nothing to suggest. */
  function suggest(email) {
    var at = email.lastIndexOf("@");
    if (at < 1) return "";
    var user = email.slice(0, at), domain = email.slice(at + 1).toLowerCase().replace(/\.+$/, "");
    if (!domain || KNOWN.indexOf(domain) >= 0) return "";
    var base = domain.split(".")[0];
    // gmail.con, hotmail.comrm: a provider name with a broken ending.
    for (var i = 0; i < TARGETS.length; i++) {
      var name = TARGETS[i].split(".")[0];
      if ((base === name || distance(base, name) <= 1) && BAD_COM.test(domain)) return user + "@" + TARGETS[i];
    }
    // gmial.com, hotmial.com: a near miss on the whole domain.
    var best = "", bestD = 3;
    for (var k = 0; k < TARGETS.length; k++) {
      var d = distance(domain, TARGETS[k]);
      if (d > 0 && d < bestD) { best = TARGETS[k]; bestD = d; }
    }
    return best && bestD <= 2 ? user + "@" + best : "";
  }
  window.avpEmailSuggest = suggest;

  function linkButton(text) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    b.style.cssText = "background:none;border:0;padding:0;font:inherit;color:inherit;text-decoration:underline;cursor:pointer";
    return b;
  }

  var forms = document.querySelectorAll('form[action*="app.kit.com/forms/"]');
  for (var f = 0; f < forms.length; f++) (function (form) {
    var input = form.querySelector('input[name="email_address"]');
    if (!input) return;
    var hint = null, accepted = "";
    function clear() { if (hint) { hint.parentNode.removeChild(hint); hint = null; } }
    input.addEventListener("input", clear);
    form.addEventListener("submit", function (e) {
      var typed = input.value.trim(), fix = suggest(typed);
      if (!fix || typed === accepted) return;
      e.preventDefault();
      clear();
      hint = document.createElement("p");
      hint.className = "email-hint";
      hint.setAttribute("role", "alert");
      hint.style.cssText = "margin:10px 0 0;font-size:0.95em";
      var yes = linkButton(fix), no = linkButton("no, send it as typed");
      hint.appendChild(document.createTextNode("Did you mean "));
      hint.appendChild(yes);
      hint.appendChild(document.createTextNode("? Or "));
      hint.appendChild(no);
      hint.appendChild(document.createTextNode("."));
      yes.addEventListener("click", function () { input.value = fix; clear(); form.submit(); });
      no.addEventListener("click", function () { accepted = typed; clear(); form.submit(); });
      form.parentNode.insertBefore(hint, form.nextSibling);
    });
  })(forms[f]);
})();
