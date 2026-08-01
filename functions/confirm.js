// GET /confirm?e=<email>&t=<token>  — completes double opt-in, adds the member.

async function hmac(msg, secret) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret || ''), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
function back(path, request) { return Response.redirect(new URL(path, request.url).toString(), 303); }

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const email = String(url.searchParams.get('e') || '').toLowerCase();
  const t = String(url.searchParams.get('t') || '');
  const expected = await hmac(email, env.SUBSCRIBE_SECRET);
  if (!email || t !== expected) return back('/subscription-management/?error=token', request);

  const base = env.MAILGUN_BASE || 'https://api.mailgun.net';
  const list = env.MAILGUN_LIST;
  const auth = 'Basic ' + btoa('api:' + env.MAILGUN_API_KEY);
  // Store an unsubscribe token as a member var so list emails can carry a signed unsubscribe link.
  const body = new URLSearchParams({ address: email, subscribed: 'yes', upsert: 'yes', vars: JSON.stringify({ h: t }) });
  const r = await fetch(`${base}/v3/lists/${encodeURIComponent(list)}/members`, { method: 'POST', headers: { Authorization: auth }, body });
  if (!r.ok) return back('/subscription-management/?error=add', request);
  return back('/subscription-confirmed/', request);
}
