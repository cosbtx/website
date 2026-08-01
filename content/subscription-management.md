---
title: "Manage Your Subscription"
---
<div id="manage-msg" class="form-note" hidden></div>

<div id="unsub-block">
  <p>To stop receiving City of Spring Branch emails, confirm below.</p>
  <form method="POST" action="/unsubscribe" class="subscribe-form">
    <input type="hidden" name="e" id="unsub-e">
    <input type="hidden" name="t" id="unsub-t">
    <button type="submit" class="btn btn-brass">Unsubscribe <span id="unsub-email"></span></button>
  </form>
</div>

<script>
  (function () {
    var p = new URLSearchParams(location.search);
    var msg = document.getElementById('manage-msg');
    var block = document.getElementById('unsub-block');
    if (p.get('done')) { msg.textContent = 'You have been unsubscribed. We are sorry to see you go.'; msg.hidden = false; block.hidden = true; }
    else if (p.get('error')) { msg.textContent = 'That unsubscribe link is invalid or expired. Please use the link in a recent email.'; msg.hidden = false; msg.classList.add('is-error'); block.hidden = true; }
    else {
      var e = p.get('e'), t = p.get('t');
      if (e && t) { document.getElementById('unsub-e').value = e; document.getElementById('unsub-t').value = t; document.getElementById('unsub-email').textContent = '(' + e + ')'; }
      else { block.hidden = true; msg.textContent = 'To unsubscribe, use the link at the bottom of any City of Spring Branch email.'; msg.hidden = false; }
    }
  })();
</script>
