// GET or POST /unsubscribe?e=<email>&t=<token>  — removes the member from the list.
// The token is the same HMAC stored as the member var `h`, carried in the email link.

async function hmac(msg, secret) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret || ''), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
function back(path, request) { return Response.redirect(new URL(path, request.url).toString(), 303); }

async function handle(request, env) {
  // Read from the query string (works for GET and Gmail's one-click List-Unsubscribe POST,
  // which carries e/t in the URL), falling back to the on-page form's POST body.
  const u = new URL(request.url);
  let email = String(u.searchParams.get('e') || '').toLowerCase();
  let t = String(u.searchParams.get('t') || '');
  const oneClick = request.method === 'POST' && !!email && !!t;
  if ((!email || !t) && request.method === 'POST') {
    try { const f = await request.formData(); email = email || String(f.get('e') || '').toLowerCase(); t = t || String(f.get('t') || ''); } catch (e) {}
  }
  const expected = await hmac(email, env.SUBSCRIBE_SECRET);
  if (!email || t !== expected) {
    return oneClick ? new Response('Invalid', { status: 400 }) : back('/subscription-management/?error=token', request);
  }

  const base = env.MAILGUN_BASE || 'https://api.mailgun.net';
  const list = env.MAILGUN_LIST;
  const auth = 'Basic ' + btoa('api:' + env.MAILGUN_API_KEY);
  await fetch(`${base}/v3/lists/${encodeURIComponent(list)}/members/${encodeURIComponent(email)}`, { method: 'DELETE', headers: { Authorization: auth } });
  // Gmail's one-click POST expects a 200, not a redirect to an HTML page.
  return oneClick ? new Response('Unsubscribed', { status: 200 }) : back('/subscription-management/?done=1', request);
}

export const onRequestGet = ({ request, env }) => handle(request, env);
export const onRequestPost = ({ request, env }) => handle(request, env);
