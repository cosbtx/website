#!/usr/bin/env python3
"""Daily email-reputation check against Mailgun stats.

Alerts only when reputation is WORSENING, so a steady, known-elevated bounce rate
does not nag every day. It compares the most recent 7 days (the latest batch of
mail) against the trailing 30-day norm, and emails ALERT_EMAIL only when:

  - the recent bounce rate runs meaningfully above the 30-day norm (BOUNCE_RISE),
  - the recent bounce rate crosses a hard ceiling (BOUNCE_CEIL), or
  - the recent complaint rate crosses COMPLAINT_MAX.

It stays silent on days with no recent sends, and on days where the latest batch
is in line with history. Bounce counts only true hard bounces (addresses that
reached a mailbox and were rejected), not Mailgun's own suppression blocks.

Exit code reflects whether the CHECK ran, not the reputation verdict: 0 on a
successful check (whether or not it alerted), 1 only when the check itself failed
(Mailgun unreachable, or an alert email could not be sent).
"""
import os, sys, json, base64, urllib.request, urllib.parse, urllib.error

API_KEY = os.environ.get('MAILGUN_API_KEY')
DOMAIN  = os.environ.get('MAILGUN_DOMAIN') or 'announcements.cityofspringbranch.org'
BASE    = os.environ.get('MAILGUN_BASE') or 'https://api.mailgun.net'
FROM    = os.environ.get('MAILGUN_FROM') or f'City of Spring Branch <announcements@{DOMAIN}>'
ALERT   = os.environ.get('ALERT_EMAIL')
BOUNCE_RISE   = float(os.environ.get('BOUNCE_RISE', '0.01'))    # recent bounce 1.0 pp above 30-day norm
BOUNCE_CEIL   = float(os.environ.get('BOUNCE_CEIL', '0.08'))    # 8% hard ceiling (catastrophe)
COMPLAINT_MAX = float(os.environ.get('COMPLAINT_MAX', '0.003')) # 0.3% (Gmail's danger line)
MIN_SAMPLE    = int(os.environ.get('MIN_SAMPLE', '25'))         # only judge when a real batch sent recently

if not API_KEY:
    print('No MAILGUN_API_KEY; skipping.'); sys.exit(0)

def auth_header():
    return 'Basic ' + base64.b64encode(f'api:{API_KEY}'.encode()).decode()

def api_get(path, params):
    url = f'{BASE}{path}?' + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url)
    req.add_header('Authorization', auth_header())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def leaf_total(node):
    if isinstance(node, dict):
        if isinstance(node.get('total'), (int, float)):
            return node['total']
        return sum(leaf_total(v) for v in node.values())
    if isinstance(node, (int, float)):
        return node
    return 0

def counts(duration):
    data = api_get(f'/v3/{DOMAIN}/stats/total', {
        'event': ['accepted', 'delivered', 'failed', 'complained'],
        'duration': duration,
    })
    acc = delv = new_bounce = sup_bounce = compl = 0
    for b in data.get('stats', []):
        acc  += leaf_total(b.get('accepted'))
        delv += leaf_total(b.get('delivered'))
        perm  = (b.get('failed') or {}).get('permanent') or {}
        new_bounce += leaf_total(perm.get('bounce'))           # true hard bounce
        sup_bounce += leaf_total(perm.get('suppress-bounce'))  # Mailgun blocked a previously-bounced address
        compl += leaf_total(b.get('complained'))
    return dict(accepted=acc, delivered=delv, new_bounce=new_bounce,
                sup_bounce=sup_bounce, complaints=compl)

def brate(c):
    d = c['delivered'] + c['new_bounce']
    return c['new_bounce'] / d if d else 0.0

def crate(c):
    return c['complaints'] / c['delivered'] if c['delivered'] else 0.0

def pct(x): return f'{x * 100:.2f}%'

def summary(label, c):
    return (f"{label}: sent {c['accepted']:>5}  delivered {c['delivered']:>5}  "
            f"bounce {pct(brate(c))} ({c['new_bounce']} hard, {c['sup_bounce']} suppressed)  "
            f"complaints {pct(crate(c))} ({c['complaints']})")

def send_alert(reasons, recent, base):
    body = (f"Email reputation is worsening for {DOMAIN}.\n\n"
            + "\n".join(f"  - {r}" for r in reasons) + "\n\n"
            + summary('last 7d ', recent) + "\n"
            + summary('last 30d', base) + "\n\n"
            "Bounce counts only true hard bounces, not Mailgun's suppression blocks.\n"
            "The list likely needs attention or sending should pause before the domain\n"
            "is demoted to the shared IP pool.\n")
    print('\nALERT:\n' + body)
    if not ALERT:
        print('No ALERT_EMAIL secret set; alert logged but not emailed.', file=sys.stderr)
        return False
    data = urllib.parse.urlencode({
        'from': FROM, 'to': ALERT,
        'subject': f'[Spring Branch] Email reputation worsening: bounce {pct(brate(recent))}',
        'text': body,
    }).encode()
    req = urllib.request.Request(f'{BASE}/v3/{DOMAIN}/messages', data=data)
    req.add_header('Authorization', auth_header())
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f'Alert email sent (HTTP {r.status}).')
    return True

def main():
    try:
        recent = counts('7d')
        base   = counts('30d')
    except urllib.error.HTTPError as e:
        print(f'Mailgun stats error: HTTP {e.code} {e.read()[:200]!r}', file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f'Mailgun stats error: {e}', file=sys.stderr); sys.exit(1)

    print(summary('last 7d ', recent))
    print(summary('last 30d', base))

    if recent['delivered'] < MIN_SAMPLE:
        print(f'OK: only {recent["delivered"]} delivered in 7d (< {MIN_SAMPLE}); no recent batch to judge.')
        return

    rb, bb, rc = brate(recent), brate(base), crate(recent)
    reasons = []
    if rb > bb + BOUNCE_RISE:
        reasons.append(f"recent bounce {pct(rb)} is {pct(rb - bb)} above the 30-day norm {pct(bb)}")
    if rb > BOUNCE_CEIL:
        reasons.append(f"recent bounce {pct(rb)} exceeds hard ceiling {pct(BOUNCE_CEIL)}")
    if rc > COMPLAINT_MAX:
        reasons.append(f"recent complaint rate {pct(rc)} exceeds {pct(COMPLAINT_MAX)}")

    if not reasons:
        print('OK: recent batch is in line with the 30-day norm; no worsening.')
        return

    try:
        send_alert(reasons, recent, base)
    except Exception as e:
        print(f'Alert email failed to send: {e}', file=sys.stderr); sys.exit(1)

if __name__ == '__main__':
    main()
