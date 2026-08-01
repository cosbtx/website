// POST /subscribe  (from the /signup/ form: fields name, email)
// Double opt-in: emails a confirmation link; the member is only added on confirm.

async function hmac(msg, secret) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret || ''), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
function back(path, request) { return Response.redirect(new URL(path, request.url).toString(), 303); }

export async function onRequestPost({ request, env }) {
  let email = '', name = '';
  try {
    const f = await request.formData();
    email = String(f.get('email') || '').trim().toLowerCase();
    name = String(f.get('name') || '').trim();
  } catch (e) { return back('/signup/?error=bad', request); }

  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return back('/signup/?error=email', request);

  const base = env.MAILGUN_BASE || 'https://api.mailgun.net';
  const domain = env.MAILGUN_DOMAIN;
  const from = env.MAILGUN_FROM || `City of Spring Branch <announcements@${domain}>`;
  const token = await hmac(email, env.SUBSCRIBE_SECRET);
  const confirmUrl = `${new URL(request.url).origin}/confirm?e=${encodeURIComponent(email)}&t=${token}`;

  const html = `<div style="font-family:Georgia,serif;color:#22252A;max-width:520px;margin:0 auto;padding:24px">
    <p style="font:600 12px ui-monospace,monospace;letter-spacing:.08em;color:#7A2E36;text-transform:uppercase;margin:0 0 6px">City of Spring Branch, Texas</p>
    <h1 style="font-size:22px;margin:0 0 14px">Confirm your subscription</h1>
    <p${name ? '' : ''}>Please confirm you want to receive notices and news from the City of Spring Branch.</p>
    <p style="margin:22px 0"><a href="${confirmUrl}" style="background:#7A2E36;color:#fff;text-decoration:none;padding:11px 20px;border-radius:8px;font-weight:600">Confirm subscription</a></p>
    <p style="color:#575D64;font-size:13px">If you did not request this, you can ignore this email and nothing will happen.</p>
  </div>`;

  const body = new URLSearchParams({ from, to: email, subject: 'Confirm your City of Spring Branch subscription', html });
  const auth = 'Basic ' + btoa('api:' + env.MAILGUN_API_KEY);
  const r = await fetch(`${base}/v3/${domain}/messages`, { method: 'POST', headers: { Authorization: auth }, body });
  if (!r.ok) return back('/signup/?error=send', request);
  return back('/signup/?pending=1', request);
}
