/* "Which editor are you on?" on a tool's thank-you page, after the download (Anthony, 2026-11-04:
 * a question on the download form itself would cost downloads).
 *
 * email-check.js keeps the address the visitor sent in sessionStorage ("avp_email"); without it (an
 * update link, another tab) this shows nothing. A tap posts {email, editor} to the time-tracker,
 * which fills Kit's "Editor" field only when it is blank (time-tracker README, "Editor Field").
 * The page thanks them whatever the answer, and asks once per signup.
 * Every thank-you page loads it: <script src="/editor.js" defer></script>.
 */
(function () {
  var URL_SAVE = "https://time-tracker-production-0a32.up.railway.app/api/kit/editor";
  var CHOICES = [["resolve", "Resolve"], ["premiere", "Premiere"], ["final cut", "Final Cut"], ["capcut", "CapCut"], ["other", "Something else"]];
  var email = "";
  try {
    email = sessionStorage.getItem("avp_email") || "";
    if (sessionStorage.getItem("avp_editor_asked")) return;
  } catch (e) { return; }
  if (!email) return;

  var shell = document.querySelector("main .shell");
  if (!shell) return;
  var box = document.createElement("div");
  box.className = "contents editor-ask";
  box.innerHTML =
    '<p class="tag">One quick thing</p>' +
    '<p><b>Which editor are you on?</b> One tap. It helps me send you the right things.</p>' +
    '<div class="editor-choices"></div>';
  var row = box.querySelector(".editor-choices");
  row.style.cssText = "display:flex;flex-wrap:wrap;gap:8px;margin-top:12px";
  CHOICES.forEach(function (c) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "btn";
    b.textContent = c[1];
    b.style.cssText = "padding:9px 14px;font-size:.88rem;cursor:pointer";
    b.addEventListener("click", function () { pick(c[0]); });
    row.appendChild(b);
  });

  function pick(editor) {
    try { sessionStorage.setItem("avp_editor_asked", "1"); } catch (e) {}
    box.innerHTML = '<p class="tag">One quick thing</p><p><b>Thanks, noted.</b></p>';
    try {
      // text/plain keeps it a simple request, so the browser sends it without a preflight.
      fetch(URL_SAVE, { method: "POST", headers: { "Content-Type": "text/plain" }, body: JSON.stringify({ email: email, editor: editor }), keepalive: true });
    } catch (e) {}
  }

  var aside = shell.querySelector(".aside");
  if (aside) shell.insertBefore(box, aside.nextSibling);
  else shell.appendChild(box);
})();
