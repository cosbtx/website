#!/usr/bin/env python3
"""Email a notice to the Mailgun list for each post/meeting ADDED in this push.
Only added files trigger email (edits, redeploys, and documents never do).
A post/meeting with `notify: false` in its frontmatter is skipped."""
import os, re, sys, subprocess, base64, html as H, urllib.request, urllib.parse
from datetime import datetime

API_KEY = os.environ.get('MAILGUN_API_KEY')
DOMAIN  = os.environ.get('MAILGUN_DOMAIN') or 'announcements.cityofspringbranch.org'
LIST    = os.environ.get('MAILGUN_LIST') or 'test@announcements.cityofspringbranch.org'
FROM    = os.environ.get('MAILGUN_FROM') or f'City of Spring Branch <announcements@{DOMAIN}>'
SITE    = (os.environ.get('SITE') or 'https://demo.cityofspringbranch.org').rstrip('/')
BASE    = os.environ.get('MAILGUN_BASE') or 'https://api.mailgun.net'

if not API_KEY:
    print('No MAILGUN_API_KEY; skipping.'); sys.exit(0)

before = os.environ.get('GITHUB_EVENT_BEFORE', '')
after  = os.environ.get('GITHUB_SHA', 'HEAD')
if not before or set(before) == {'0'}:
    print('No usable before-SHA (initial/forced push); skipping to avoid a blast.'); sys.exit(0)

try:
    out = subprocess.check_output(
        ['git', 'diff', '--diff-filter=A', '--name-only', before, after, '--', 'content/posts', 'content/meetings'],
        text=True)
except subprocess.CalledProcessError as e:
    print('git diff failed:', e); sys.exit(0)

added = [l for l in out.splitlines() if l.endswith('.md') and not l.endswith('_index.md')]
print('added notice files:', added or '(none)')

CAT = {'notice': 'Notice', 'emergency': 'Emergency', 'community': 'Community'}

def parse(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', t, re.S)
    fm, body = (m.group(1), m.group(2)) if m else ('', t)
    d = {}
    for line in fm.splitlines():
        mm = re.match(r'^(\w+):\s*(.*)$', line)
        if mm:
            k, v = mm.group(1), mm.group(2).strip()
            if len(v) >= 2 and v[0] in '"\'' and v[-1] == v[0]:
                v = v[1:-1]
            d[k] = v
    return d, body

def fmt_date(s):
    try: return datetime.strptime(s[:10], '%Y-%m-%d').strftime('%A, %B %-d, %Y')
    except Exception: return s[:10]

def button(href, label):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:4px 0;">'
            f'<tr><td bgcolor="#7A2E36" style="border-radius:8px;">'
            f'<a href="{href}" style="display:inline-block;padding:11px 22px;font:bold 14px Arial,Helvetica,sans-serif;color:#ffffff;text-decoration:none;">{label}</a>'
            f'</td></tr></table>')

def shell(kicker, inner):
    return f'''<!doctype html><html><body style="margin:0;padding:0;background:#ECEAE5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ECEAE5;"><tr><td align="center" style="padding:28px 12px;">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #E4E2DC;border-radius:12px;">
    <tr><td style="height:3px;background:#7A2E36;border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td></tr>
    <tr><td style="padding:18px 26px 14px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td width="42" valign="middle"><img src="{SITE}/img/city-seal.png" width="38" height="38" alt="" style="display:block;border-radius:7px;"></td>
        <td valign="middle" style="padding-left:11px;">
          <div style="font:600 9.5px/1 Arial,Helvetica,sans-serif;letter-spacing:.14em;color:#7A2E36;text-transform:uppercase;">Official Municipal Website</div>
          <div style="font:700 16px/1.2 Georgia,'Times New Roman',serif;color:#22252A;padding-top:2px;">City of Spring Branch, Texas</div>
        </td>
      </tr></table>
    </td></tr>
    <tr><td style="border-top:1px solid #ECEAE5;font-size:0;line-height:0;">&nbsp;</td></tr>
    <tr><td style="padding:20px 26px 8px;">
      <div style="font:600 10px/1 Arial,Helvetica,sans-serif;letter-spacing:.12em;color:#7A2E36;text-transform:uppercase;margin:0 0 8px;">{kicker}</div>
      {inner}
    </td></tr>
    <tr><td style="padding:16px 26px 20px;border-top:1px solid #ECEAE5;color:#8a8f96;font:12px/1.6 Arial,Helvetica,sans-serif;">
      You are receiving this because you subscribed to City of Spring Branch notices.<br>
      <a href="{SITE}/subscription-management/?e=%recipient.e%&t=%recipient.h%" style="color:#7A2E36;">Unsubscribe</a> &middot; <a href="{SITE}/" style="color:#7A2E36;">cityofspringbranch.org</a>
    </td></tr>
  </table>
</td></tr></table>
</body></html>'''

def build(path):
    d, body = parse(path)
    if str(d.get('notify', '')).lower() == 'false':
        print('skip (notify:false):', path); return None
    title = d.get('title', 'City notice')
    if '/meetings/' in path:
        fname = os.path.basename(path)[:-3]
        url = f'{SITE}/meetings/{fname}/'
        dt = fmt_date(d.get('date', ''))
        parts = [d.get('body', 'City Commission'), dt]
        if d.get('time'): parts.append(d['time'])
        if d.get('location'): parts.append(d['location'])
        meta = ' &middot; '.join(H.escape(p) for p in parts if p)
        subject = f'{title}, {dt}'
        inner = (f'<h1 style="font:700 20px/1.3 Georgia,\'Times New Roman\',serif;color:#22252A;margin:0 0 8px;">{H.escape(title)}</h1>'
                 f'<p style="font:15px/1.55 Georgia,\'Times New Roman\',serif;color:#3a3f47;margin:0 0 16px;">{meta}</p>{button(url, "View the full notice")}')
        return subject, shell('Public Meeting Notice', inner)
    else:
        slug = d.get('slug') or re.sub(r'^\d{4}-\d{2}-\d{2}-', '', os.path.basename(path)[:-3])
        url = f'{SITE}/posts/{slug}/'
        text = H.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body))).strip()
        lead = (text[:220].rstrip() + '…') if len(text) > 220 else text
        inner = (f'<h1 style="font:700 20px/1.3 Georgia,\'Times New Roman\',serif;color:#22252A;margin:0 0 10px;">{H.escape(title)}</h1>'
                 f'<p style="font:15px/1.55 Georgia,\'Times New Roman\',serif;color:#3a3f47;margin:0 0 16px;">{H.escape(lead)}</p>{button(url, "Read the full notice")}')
        return title, shell(CAT.get(d.get('category', 'notice'), 'Notice'), inner)

sent = 0
for path in added:
    if not os.path.exists(path): continue
    r = build(path)
    if not r: continue
    subject, html = r
    data = urllib.parse.urlencode({'from': FROM, 'to': LIST, 'subject': subject, 'html': html}).encode()
    req = urllib.request.Request(f'{BASE}/v3/{DOMAIN}/messages', data=data)
    req.add_header('Authorization', 'Basic ' + base64.b64encode(f'api:{API_KEY}'.encode()).decode())
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        print('SENT:', subject, resp.status); sent += 1
    except Exception as e:
        print('SEND FAILED:', subject, e)

print(f'done; {sent} email(s) sent to {LIST}')
