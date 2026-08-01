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
  let email = '', t = '';
  if (request.method === 'POST') {
    try { const f = await request.formData(); email = String(f.get('e') || '').toLowerCase(); t = String(f.get('t') || ''); } catch (e) {}
  } else {
    const u = new URL(request.url); email = String(u.searchParams.get('e') || '').toLowerCase(); t = String(u.searchParams.get('t') || '');
  }
  const expected = await hmac(email, env.SUBSCRIBE_SECRET);
  if (!email || t !== expected) return back('/subscription-management/?error=token', request);

  const base = env.MAILGUN_BASE || 'https://api.mailgun.net';
  const list = env.MAILGUN_LIST;
  const auth = 'Basic ' + btoa('api:' + env.MAILGUN_API_KEY);
  await fetch(`${base}/v3/lists/${encodeURIComponent(list)}/members/${encodeURIComponent(email)}`, { method: 'DELETE', headers: { Authorization: auth } });
  return back('/subscription-management/?done=1', request);
}

export const onRequestGet = ({ request, env }) => handle(request, env);
export const onRequestPost = ({ request, env }) => handle(request, env);
