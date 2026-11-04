#!/usr/bin/env python3
"""Daily email-reputation check against Mailgun stats.

Pulls accepted / delivered / failed / complained totals for the trailing 7 and
30 days, computes bounce and complaint rates, and emails an alert (and fails the
job) when either crosses its threshold. Silent when healthy.

Bounce rate is reported two ways:
  - inclusive: all permanent failures (matches Mailgun's headline number).
  - provider-facing: excludes addresses Mailgun suppressed before sending, since
    those never reach a mailbox and do not touch sender reputation.
The alert fires on the provider-facing rate, so Mailgun's own suppression blocks
after each broadcast do not cause false alarms.
"""
import os, sys, json, base64, urllib.request, urllib.parse, urllib.error

API_KEY = os.environ.get('MAILGUN_API_KEY')
DOMAIN  = os.environ.get('MAILGUN_DOMAIN') or 'announcements.cityofspringbranch.org'
BASE    = os.environ.get('MAILGUN_BASE') or 'https://api.mailgun.net'
FROM    = os.environ.get('MAILGUN_FROM') or f'City of Spring Branch <announcements@{DOMAIN}>'
ALERT   = os.environ.get('ALERT_EMAIL')
BOUNCE_MAX    = float(os.environ.get('BOUNCE_MAX', '0.02'))     # 2%
COMPLAINT_MAX = float(os.environ.get('COMPLAINT_MAX', '0.001')) # 0.1%

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
    """Best-effort numeric total out of a Mailgun stats node."""
    if isinstance(node, dict):
        if isinstance(node.get('total'), (int, float)):
            return node['total']
        return sum(leaf_total(v) for v in node.values())
    if isinstance(node, (int, float)):
        return node
    return 0

def window(duration):
    data = api_get(f'/v3/{DOMAIN}/stats/total', {
        'event': ['accepted', 'delivered', 'failed', 'complained'],
        'duration': duration,
    })
    acc = delv = permf = suppress = compl = 0
    for b in data.get('stats', []):
        acc  += leaf_total(b.get('accepted'))
        delv += leaf_total(b.get('delivered'))
        perm  = (b.get('failed') or {}).get('permanent') or {}
        permf += leaf_total(perm)
        for k in ('suppress-bounce', 'suppress-complaint', 'suppress-unsubscribe'):
            suppress += leaf_total(perm.get(k))
        compl += leaf_total(b.get('complained'))
    real_bounce = max(permf - suppress, 0)
    denom_incl = delv + permf
    denom_prov = delv + real_bounce
    return dict(
        duration=duration, accepted=acc, delivered=delv, permfail=permf,
        suppress=suppress, real_bounce=real_bounce, complaints=compl,
        bounce_incl=(permf / denom_incl if denom_incl else 0.0),
        bounce_prov=(real_bounce / denom_prov if denom_prov else 0.0),
        complaint=(compl / delv if delv else 0.0),
    )

def pct(x): return f'{x * 100:.2f}%'

def line(w):
    return (f"{w['duration']:>4}: sent {w['accepted']:>5}  delivered {w['delivered']:>5}  "
            f"bounce {pct(w['bounce_prov'])} provider-facing "
            f"({pct(w['bounce_incl'])} incl. {w['suppress']} suppressed)  "
            f"complaints {pct(w['complaint'])} ({w['complaints']})")

def main():
    windows = []
    for d in ('7d', '30d'):
        try:
            windows.append(window(d))
        except urllib.error.HTTPError as e:
            print(f'Mailgun stats error for {d}: HTTP {e.code} {e.read()[:200]!r}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f'Mailgun stats error for {d}: {e}', file=sys.stderr)
            sys.exit(1)

    for w in windows:
        print(line(w))

    breached = [w for w in windows
                if w['bounce_prov'] > BOUNCE_MAX or w['complaint'] > COMPLAINT_MAX]
    if not breached:
        print(f'OK: under thresholds (bounce {pct(BOUNCE_MAX)}, complaints {pct(COMPLAINT_MAX)}).')
        return

    body = (f"Email reputation threshold crossed for {DOMAIN}.\n\n"
            f"Thresholds: provider-facing bounce {pct(BOUNCE_MAX)}, complaints {pct(COMPLAINT_MAX)}.\n\n"
            + "\n".join(line(w) for w in windows)
            + "\n\n'provider-facing' excludes addresses Mailgun already suppressed; those never\n"
              "reach a mailbox. A sustained breach means the list needs cleaning or sending\n"
              "should pause before the domain is demoted to the shared IP pool.\n")
    print('\nALERT:\n' + body)

    if ALERT:
        try:
            data = urllib.parse.urlencode({
                'from': FROM, 'to': ALERT,
                'subject': f'[Spring Branch] Email reputation alert: bounce {pct(breached[0]["bounce_prov"])}',
                'text': body,
            }).encode()
            req = urllib.request.Request(f'{BASE}/v3/{DOMAIN}/messages', data=data)
            req.add_header('Authorization', auth_header())
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f'Alert email sent (HTTP {r.status}).')
        except Exception as e:
            print(f'Failed to send alert email: {e}', file=sys.stderr)
    else:
        print('No ALERT_EMAIL secret set; alert logged but not emailed.', file=sys.stderr)

    sys.exit(1)  # fail the run so GitHub also surfaces it

if __name__ == '__main__':
    main()
