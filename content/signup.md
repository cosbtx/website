---
title: "Sign Up for Announcements"
---
Get city notices and news delivered to your inbox: meeting notices, elections, tax-rate hearings, and community announcements. We will never share your email, and you can unsubscribe at any time.

<div id="signup-msg" class="form-note" hidden></div>

<form method="POST" action="/subscribe" class="subscribe-form">
  <input type="text" name="name" placeholder="Name (optional)" autocomplete="name">
  <input type="email" name="email" placeholder="you@example.com" required autocomplete="email">
  <button type="submit" class="btn btn-brass">Subscribe</button>
</form>

<script>
  (function () {
    var p = new URLSearchParams(location.search);
    var el = document.getElementById('signup-msg');
    if (p.get('pending')) { el.textContent = 'Almost there. Check your email and click the confirmation link to finish subscribing.'; el.hidden = false; }
    else if (p.get('error')) { el.textContent = 'Sorry, something went wrong. Please check your email address and try again.'; el.hidden = false; el.classList.add('is-error'); }
  })();
</script>
