// POST /subscribe  (from the /signup/ form: fields name, email)
// Double opt-in: emails a confirmation link; the member is only added on confirm.

async function hmac(msg, secret) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret || ''), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
function back(path, request) { return Response.redirect(new URL(path, request.url).toString(), 303); }

// Branded, email-client-safe shell (table layout, inline styles). Reused for notice emails.
function emailShell(origin, bodyHtml, footerExtra) {
  return `<!doctype html><html><body style="margin:0;padding:0;background:#ECEAE5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ECEAE5;"><tr><td align="center" style="padding:28px 12px;">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #E4E2DC;border-radius:12px;">
    <tr><td style="height:3px;background:#7A2E36;border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td></tr>
    <tr><td style="padding:18px 26px 14px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td width="42" valign="middle"><img src="${origin}/img/city-seal.png" width="38" height="38" alt="" style="display:block;border-radius:7px;"></td>
        <td valign="middle" style="padding-left:11px;">
          <div style="font:600 9.5px/1 Arial,Helvetica,sans-serif;letter-spacing:.14em;color:#7A2E36;text-transform:uppercase;">Official Municipal Website</div>
          <div style="font:700 16px/1.2 Georgia,'Times New Roman',serif;color:#22252A;padding-top:2px;">City of Spring Branch, Texas</div>
        </td>
      </tr></table>
    </td></tr>
    <tr><td style="border-top:1px solid #ECEAE5;font-size:0;line-height:0;">&nbsp;</td></tr>
    <tr><td style="padding:22px 26px 6px;">${bodyHtml}</td></tr>
    <tr><td style="padding:16px 26px 20px;border-top:1px solid #ECEAE5;color:#8a8f96;font:12px/1.6 Arial,Helvetica,sans-serif;">
      City of Spring Branch &middot; P.O. Box 1143, Spring Branch, TX 78070<br>
      <a href="${origin}/" style="color:#7A2E36;">cityofspringbranch.org</a>${footerExtra || ''}
    </td></tr>
  </table>
</td></tr></table>
</body></html>`;
}

function button(href, label) {
  return `<table role="presentation" cellpadding="0" cellspacing="0" style="margin:2px 0;"><tr><td bgcolor="#7A2E36" style="border-radius:8px;">
    <a href="${href}" style="display:inline-block;padding:11px 22px;font:bold 14px Arial,Helvetica,sans-serif;color:#ffffff;text-decoration:none;">${label}</a>
  </td></tr></table>`;
}

export async function onRequestPost({ request, env }) {
  let email = '';
  try {
    const f = await request.formData();
    email = String(f.get('email') || '').trim().toLowerCase();
  } catch (e) { return back('/signup/?error=bad', request); }

  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return back('/signup/?error=email', request);

  const base = env.MAILGUN_BASE || 'https://api.mailgun.net';
  const domain = env.MAILGUN_DOMAIN;
  const from = env.MAILGUN_FROM || `City of Spring Branch <announcements@${domain}>`;
  const origin = new URL(request.url).origin;
  const token = await hmac(email, env.SUBSCRIBE_SECRET);
  const confirmUrl = `${origin}/confirm?e=${encodeURIComponent(email)}&t=${token}`;

  const body = `
    <h1 style="font:700 20px/1.3 Georgia,'Times New Roman',serif;color:#22252A;margin:0 0 10px;">Confirm your subscription</h1>
    <p style="font:15px/1.55 Georgia,'Times New Roman',serif;color:#3a3f47;margin:0 0 18px;">Please confirm you want to receive notices and news from the City of Spring Branch, Texas.</p>
    ${button(confirmUrl, 'Confirm subscription')}
    <p style="font:13px/1.5 Arial,Helvetica,sans-serif;color:#8a8f96;margin:18px 0 0;">If you did not request this, you can ignore this email and nothing will happen.</p>`;
  const html = emailShell(origin, body, '');

  const params = new URLSearchParams({ from, to: email, subject: 'Confirm your City of Spring Branch subscription', html });
  const auth = 'Basic ' + btoa('api:' + env.MAILGUN_API_KEY);
  const r = await fetch(`${base}/v3/${domain}/messages`, { method: 'POST', headers: { Authorization: auth }, body: params });
  if (!r.ok) return back('/signup/?error=send', request);
  return back('/signup/?pending=1', request);
}
