#!/usr/bin/env python3
"""VoxTerrae Hub static generator -> dist/worker.mjs (Cloudflare Worker, pages embedded, R2 for binaries)."""
import json, os, re, html, datetime, hashlib, sys
import markdown
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.join(HERE, "site"); DIST = os.path.join(HERE, "dist"); os.makedirs(DIST, exist_ok=True)
ORIGIN = os.environ.get("PUBLIC_ORIGIN", "https://voxterrae.app")
REL = json.load(open(os.path.join(SITE, "releases.json")))
LATEST = next(r for r in REL["releases"] if r["version"] == REL["latest"])
TODAY = datetime.date.today().isoformat()
P = dict(bg="#0a0f0d", panel="#10171a", line="#1d2a2e", text="#d7e0dc", muted="#8a9a92", ph="#37f28f", amber="#f2b137", red="#ff5c5c", blue="#5cc8ff")
# ---- contrast (WCAG) -------------------------------------------------------------------------
def lum(h):
    r, g, b = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
def contrast(a, b):
    la, lb = lum(a), lum(b); return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
CONTRAST = {k: round(contrast(P[k], P["bg"]), 2) for k in ("text", "muted", "ph", "amber", "red", "blue")}
CONTRAST["muted_on_panel"] = round(contrast(P["muted"], P["panel"]), 2)
# ---- css -------------------------------------------------------------------------------------
CSS = f"""
:root{{--bg:{P['bg']};--panel:{P['panel']};--line:{P['line']};--text:{P['text']};--muted:{P['muted']};--ph:{P['ph']};--amber:{P['amber']};--red:{P['red']};--blue:{P['blue']}}}
*{{box-sizing:border-box}}html{{color-scheme:dark}}body{{margin:0;background:var(--bg);color:var(--text);font:17px/1.6 system-ui,"Segoe UI",Inter,Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
.skip{{position:absolute;left:-999px;top:8px;background:var(--ph);color:#000;padding:8px 12px;border-radius:6px;z-index:9}}.skip:focus{{left:8px}}
a{{color:var(--ph);text-decoration:underline;text-underline-offset:3px}}a:hover{{color:#fff}}a:focus-visible,button:focus-visible{{outline:3px solid var(--amber);outline-offset:2px}}
code,pre,kbd,.mono{{font-family:"Cascadia Code","Cascadia Mono",Consolas,"JetBrains Mono",ui-monospace,monospace}}
pre{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;overflow:auto;font-size:15px;line-height:1.5}}code{{background:var(--panel);padding:1px 6px;border-radius:4px;font-size:.93em}}pre code{{background:none;padding:0}}
header{{border-bottom:1px solid var(--line);background:rgba(10,15,13,.92);backdrop-filter:blur(6px);position:sticky;top:0;z-index:5}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 20px}}nav{{display:flex;align-items:center;gap:6px;height:60px}}nav .brand{{display:flex;align-items:center;gap:10px;color:var(--text);text-decoration:none;font-weight:700;letter-spacing:.06em;font-family:"Cascadia Code",Consolas,ui-monospace,monospace;margin-right:auto}}
nav a.l{{color:var(--muted);text-decoration:none;padding:8px 12px;border-radius:6px;font-size:15px}}nav a.l:hover,nav a.l[aria-current]{{color:var(--text);background:var(--panel)}}nav a.cta{{background:var(--ph);color:#04120a;font-weight:700;text-decoration:none;padding:9px 16px;border-radius:8px;margin-left:8px}}
main{{padding:40px 0 60px}}h1{{font-size:44px;line-height:1.1;margin:0 0 16px;letter-spacing:-.01em}}h2{{font-size:26px;margin:44px 0 12px}}h3{{font-size:19px;margin:28px 0 8px}}p{{margin:0 0 14px}}.lead{{font-size:21px;color:var(--muted);max-width:60ch}}
.hero{{display:grid;grid-template-columns:1.05fr 1fr;gap:36px;align-items:center;padding:26px 0 10px}}@media(max-width:820px){{.hero{{grid-template-columns:1fr}}h1{{font-size:34px}}}}
.eyebrow{{font-family:"Cascadia Code",Consolas,ui-monospace,monospace;color:var(--ph);letter-spacing:.14em;font-size:13px;text-transform:uppercase}}
.btn{{display:inline-flex;align-items:center;gap:10px;background:var(--ph);color:#04120a;font-weight:700;text-decoration:none;padding:14px 22px;border-radius:10px;font-size:17px}}.btn.sec{{background:var(--panel);color:var(--text);border:1px solid var(--line)}}.btnrow{{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0 10px}}
.fine{{color:var(--muted);font-size:14px}}.shot{{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--panel);box-shadow:0 30px 80px rgba(0,0,0,.5)}}.shot img{{display:block;width:100%;height:auto}}
.tiles{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:30px}}@media(max-width:820px){{.tiles{{grid-template-columns:1fr}}}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 18px 14px}}.tile h3{{margin:0 0 6px;font-size:17px}}.tile p{{margin:0;color:var(--muted);font-size:15px}}
table{{border-collapse:collapse;width:100%;margin:12px 0 20px;font-size:15px}}th,td{{text-align:left;padding:10px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-weight:600;font-size:13px;letter-spacing:.06em;text-transform:uppercase}}td .mono{{font-size:13px;word-break:break-all}}
.notice{{border-left:4px solid var(--amber);background:var(--panel);padding:14px 16px;border-radius:0 10px 10px 0;margin:18px 0}}.notice.ok{{border-color:var(--ph)}}.notice.red{{border-color:var(--red)}}
.pill{{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:12px;color:var(--muted);font-family:Consolas,ui-monospace,monospace}}.pill.on{{color:var(--ph);border-color:var(--ph)}}
.docs{{display:grid;grid-template-columns:240px 1fr;gap:36px}}@media(max-width:820px){{.docs{{grid-template-columns:1fr}}}}.toc{{position:sticky;top:76px;align-self:start}}.toc a{{display:block;color:var(--muted);text-decoration:none;padding:6px 10px;border-left:2px solid var(--line);font-size:15px}}.toc a[aria-current]{{color:var(--text);border-color:var(--ph)}}
footer{{border-top:1px solid var(--line);padding:26px 0 40px;color:var(--muted);font-size:14px}}footer .cols{{display:flex;gap:30px;flex-wrap:wrap;justify-content:space-between}}footer a{{color:var(--muted)}}
.rel{{border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0;background:var(--panel)}}.rel h3{{margin:0}}.rel ul{{margin:10px 0 0;padding-left:20px}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
"""
def layout(title, body, path, desc="", extra_head=""):
    nav = [("/", "Home"), ("/download", "Download"), ("/releases", "Releases"), ("/docs", "Docs"), ("/security", "Security"), ("/about", "About")]
    CUR = ' aria-current="page"'
    links = "".join(f'<a class="l" href="{h}"{CUR if (path == h or (h != "/" and path.startswith(h))) else ""}>{t}</a>' for h, t in nav)
    desc = desc or "VoxTerrae is the WarHeatMap.app IRC client: one click into #warheatmap on our IRCv3 home network and the classic EFnet rooms, with history, reactions, replies and notifications. Open source, no accounts, no telemetry."
    canon = ORIGIN + (path if path != "/" else "/")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc)}"><link rel="canonical" href="{canon}"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="website"><meta property="og:site_name" content="VoxTerrae"><meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}"><meta property="og:url" content="{canon}"><meta property="og:image" content="{ORIGIN}/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="{P['bg']}"><style>{CSS}</style>{extra_head}</head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap"><nav aria-label="Primary"><a class="brand" href="/"><svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true"><rect x="4" y="4" width="56" height="56" rx="12" fill="{P['bg']}" stroke="{P['ph']}" stroke-width="4"/><rect x="18" y="18" width="28" height="28" fill="{P['ph']}"/></svg>VOXTERRAE</a>{links}<a class="cta" href="/download">Download</a></nav></div></header>
<main id="main"><div class="wrap">{body}</div></main>
<footer><div class="wrap"><div class="cols"><div>VoxTerrae is open source (MIT). A <a href="https://warheatmap.app">WarHeatMap.app</a> project.<br>No cookies, no trackers, no accounts. <a href="/docs/privacy">Privacy</a> · <a href="/security">Security</a> · <a href="/.well-known/security.txt">security.txt</a></div><div>Networks: <span class="mono">irc.warheatmap.app:6697</span> (HOME) · EFnet<br>Feeds: <a href="/api/latest.json">latest.json</a> · <a href="/api/releases.json">releases.json</a> · <a href="/llms.txt">llms.txt</a></div></div></div></footer></body></html>"""
def md(text):
    return markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])
def fm(raw):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S); meta = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":"); meta[k.strip()] = v.strip()
        return meta, m.group(2)
    return meta, raw
def asset_rows(rel):
    rows = []
    for a in rel["assets"]:
        size = f"{a['size']/1024/1024:.2f} MB" if a["size"] > 1024 * 1024 else f"{a['size']/1024:.0f} KB"
        rows.append(f"<tr><td><a href=\"/dl/{rel['version']}/{a['file']}\" download>{a['file']}</a><div class=\"fine\">{html.escape(a.get('note',''))}</div></td><td>{a['platform']}</td><td>{size}</td><td><span class=\"mono\">{a['sha256']}</span></td></tr>")
    for a in rel.get("planned", []):
        rows.append(f"<tr><td>{a['file']} <span class=\"pill\">planned</span><div class=\"fine\">{html.escape(a.get('note',''))}</div></td><td>{a['platform']}</td><td>–</td><td><span class=\"fine\">published with the file</span></td></tr>")
    return "".join(rows)
PAGES = {}   # path -> (content-type, body)
def add(path, ctype, body): PAGES[path] = (ctype, body)
# ---- home ------------------------------------------------------------------------------------
src = LATEST["assets"][0]
home = f"""<section class="hero"><div><div class="eyebrow">WarHeatMap.app · IRC 2026</div><h1>The door from the map to the room.</h1>
<p class="lead">VoxTerrae is the WarHeatMap IRC client. One click puts you in <span class="mono">#warheatmap</span> on our home network and in the classic EFnet rooms at the same time, with history, reactions, replies and notifications. No accounts. No telemetry.</p>
<div class="btnrow"><a class="btn" href="/download">Download <span class="mono" style="font-weight:500;opacity:.8">v{REL['latest']}</span></a><a class="btn sec" href="/docs">Read the docs</a></div>
<p class="fine">Windows portable exe is built from this source and listed as soon as it exists. Today's asset is the source bundle ({src['size']/1024:.0f} KB, SHA-256 published). <a href="/docs/install">Run from source</a> works now.</p></div>
<figure class="shot" style="margin:0"><img src="/img/replymode.png" width="1280" height="720" alt="VoxTerrae dark-ops window: room list grouped by HOME and EFnet on the left, the #warheatmap timeline with reactions and a reply strip in the middle, the live-map rail and member list on the right" loading="eager" fetchpriority="high"></figure></section>
<section class="tiles"><div class="tile"><h3>Two networks, one window</h3><p>HOME (<span class="mono">irc.warheatmap.app</span>, IRCv3) for history, reactions and replies; EFnet for the old rooms. Both connect on launch and reconnect on their own.</p></div>
<div class="tile"><h3>History that catches you up</h3><p>Everything you saw is stored locally and searchable. On launch the client replays your history, then asks HOME only for what you missed. Never a duplicated line.</p></div>
<div class="tile"><h3>Private by construction</h3><p>Data stays in <span class="mono">%LOCALAPPDATA%\\VoxTerrae</span>. The only network traffic is IRC and one update check. This site sets no cookies and runs no trackers.</p></div></section>
<h2>How it works</h2>
<ol><li><strong>Download and run.</strong> One file. Windows may show a SmartScreen notice for a new program; <a href="/docs/verify">verify the checksum</a> and continue.</li><li><strong>Pick a handle, press ENTER.</strong> Both networks connect. You start in #warheatmap.</li><li><strong>Talk.</strong> Right-click a message to reply or react on HOME. <span class="mono">/search</span> your history. <span class="mono">/ask</span> Axiom a question.</li></ol>
<h2>Trust, in the open</h2><p>Every file carries a published SHA-256 and a verify command. Certificates on EFnet are pinned on first use and the client refuses a changed one. Source is MIT-licensed; GitHub publishing is in progress. Code signing and Sigstore provenance are on the <a href="/releases">roadmap</a>, and this page says so rather than hiding the SmartScreen prompt.</p>"""
jsonld = json.dumps({"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "VoxTerrae", "applicationCategory": "CommunicationApplication", "operatingSystem": "Windows 11, Windows 10", "softwareVersion": REL["latest"], "downloadUrl": f"{ORIGIN}/download", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "license": "https://opensource.org/licenses/MIT", "publisher": {"@type": "Organization", "name": "WarHeatMap.app", "url": "https://warheatmap.app"}, "description": "IRC client for the WarHeatMap.app community: IRCv3 home network plus EFnet, history, reactions, replies, notifications."})
add("/", "text/html; charset=utf-8", layout("VoxTerrae: the WarHeatMap IRC client", home, "/", extra_head=f'<script type="application/ld+json">{jsonld}</script>'))
# ---- download --------------------------------------------------------------------------------
dl = f"""<div class="eyebrow">Download</div><h1>VoxTerrae {REL['latest']}</h1><p class="lead">Released {LATEST['date']}. {LATEST['title']}.</p>
<h2>Files</h2><table><thead><tr><th>File</th><th>Platform</th><th>Size</th><th>SHA-256</th></tr></thead><tbody>{asset_rows(LATEST)}</tbody></table>
<p><a href="/dl/{REL['latest']}/SHA256SUMS">SHA256SUMS</a> for this release.</p>
<div class="notice"><strong>About the Windows SmartScreen notice.</strong> A brand-new, not-yet-signed program triggers "Windows protected your PC" the first time it runs. That is a reputation check, not a scan result. Verify the SHA-256 below, then choose <em>More info → Run anyway</em>. Code signing (SignPath Foundation for open source, or Azure Artifact Signing) is on the roadmap and this notice will be updated when a signed build ships.</div>
<h2>Verify</h2><pre><code># PowerShell
Get-FileHash .\\{src['file']} -Algorithm SHA256
# expected
{src['sha256']}</code></pre><p>Details and what a checksum does and does not prove: <a href="/docs/verify">Verify a download</a>.</p>
<h2>Other channels</h2><table><thead><tr><th>Channel</th><th>State</th><th>Notes</th></tr></thead><tbody>
<tr><td>GitHub Releases</td><td><span class="pill">in progress</span></td><td>Mirror of every asset with Sigstore provenance from the build workflow.</td></tr>
<tr><td>winget</td><td><span class="pill">planned</span></td><td><span class="mono">winget install VoxTerrae</span> once a signed portable build is published.</td></tr>
<tr><td>Run from source</td><td><span class="pill on">available</span></td><td>Python 3.11+, see <a href="/docs/install">Install</a>.</td></tr></tbody></table>
<h2>Requirements</h2><p>Windows 10 1809+ (Windows 11 recommended). Outbound TCP 6697 to <span class="mono">irc.warheatmap.app</span> and the EFnet servers; 6667 only as a last resort on EFnet.</p>"""
add("/download", "text/html; charset=utf-8", layout("Download VoxTerrae", dl, "/download", "Download VoxTerrae with published SHA-256 checksums, verify instructions and an honest note about SmartScreen."))
# ---- releases --------------------------------------------------------------------------------
def rel_block(r, link=True):
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in r["notes"])
    files = ", ".join(f"<a href=\"/dl/{r['version']}/{a['file']}\">{a['file']}</a>" for a in r["assets"])
    h = f"<a href=\"/releases/{r['version']}\">{r['version']}</a>" if link else r["version"]
    return f"<article class=\"rel\"><h3>{h} <span class=\"fine\">· {r['date']}</span></h3><p style=\"margin:6px 0 0\">{html.escape(r['title'])}</p><ul>{notes}</ul><p class=\"fine\" style=\"margin-top:10px\">Files: {files}</p></article>"
roadmap = """<h2>Roadmap</h2><ul><li><strong>0.1.x</strong>: Windows portable exe published with SHA256SUMS; in-app update check against <span class="mono">/api/latest.json</span>.</li><li><strong>0.2</strong>: GitHub Releases mirror with Sigstore provenance; SignPath Foundation code signing application; winget manifest (portable).</li><li><strong>0.3</strong>: <span class="mono">voxterrae://join/</span> deep links from warheatmap.app event cards; live-map rail fed by the event stream.</li><li><strong>Later</strong>: MSI installer, macOS/Linux packages.</li></ul>"""
add("/releases", "text/html; charset=utf-8", layout("VoxTerrae releases", f"<div class=\"eyebrow\">Releases</div><h1>Changelog</h1>{''.join(rel_block(r) for r in REL['releases'])}{roadmap}", "/releases", "VoxTerrae changelog and roadmap."))
for r in REL["releases"]:
    add(f"/releases/{r['version']}", "text/html; charset=utf-8", layout(f"VoxTerrae {r['version']}", f"<div class=\"eyebrow\">Release</div><h1>VoxTerrae {r['version']}</h1>{rel_block(r, link=False)}<h2>Files</h2><table><thead><tr><th>File</th><th>Platform</th><th>Size</th><th>SHA-256</th></tr></thead><tbody>{asset_rows(r)}</tbody></table>", f"/releases/{r['version']}", f"VoxTerrae {r['version']}: {r['title']}"))
    sums = "".join(f"{a['sha256']}  {a['file']}\n" for a in r["assets"])
    add(f"/dl/{r['version']}/SHA256SUMS", "text/plain; charset=utf-8", sums)
# ---- docs ------------------------------------------------------------------------------------
docs = []
for fn in sorted(os.listdir(os.path.join(SITE, "docs"))):
    meta, body = fm(open(os.path.join(SITE, "docs", fn), encoding="utf-8").read())
    docs.append((int(meta.get("order", 99)), fn[:-3], meta.get("title", fn), meta.get("summary", ""), body))
docs.sort()
def toc(cur):
    CUR = ' aria-current="page"'
    return "<nav class=\"toc\" aria-label=\"Docs\">" + "".join(f"<a href=\"/docs/{s}\"{CUR if s == cur else ''}>{html.escape(t)}</a>" for _, s, t, _, _ in docs) + "</nav>"
idx = "".join(f"<div class=\"tile\"><h3><a href=\"/docs/{s}\">{html.escape(t)}</a></h3><p>{html.escape(sm)}</p></div>" for _, s, t, sm, _ in docs)
add("/docs", "text/html; charset=utf-8", layout("VoxTerrae docs", f"<div class=\"eyebrow\">Docs</div><h1>Documentation</h1><p class=\"lead\">Eight short pages. If something is missing, say so in #warheatmap.</p><section class=\"tiles\">{idx}</section>", "/docs", "VoxTerrae documentation: install, first launch, networks, commands, verify, privacy, troubleshooting, FAQ."))
for _, s, t, sm, body in docs:
    add(f"/docs/{s}", "text/html; charset=utf-8", layout(f"{t} · VoxTerrae docs", f"<div class=\"docs\">{toc(s)}<article><div class=\"eyebrow\">Docs</div><h1>{html.escape(t)}</h1><p class=\"lead\">{html.escape(sm)}</p>{md(body)}</article></div>", f"/docs/{s}", sm))
# ---- security / about ------------------------------------------------------------------------
SEC_CONTACT = os.environ.get("SECURITY_CONTACT", "mailto:security@voxterrae.app")
expires = (datetime.date.today() + datetime.timedelta(days=365)).isoformat() + "T00:00:00.000Z"
sec = f"""<div class="eyebrow">Security</div><h1>Reporting a vulnerability</h1><p class="lead">Thank you for looking. Please report privately first.</p>
<p>Email <a href="{SEC_CONTACT}">{SEC_CONTACT.replace('mailto:','')}</a> with the version, the networks involved, steps to reproduce and impact. You will get an acknowledgement within 72 hours and a fix or a timeline within 14 days for anything that affects message confidentiality, certificate handling or remote code execution. Please give us that window before publishing.</p>
<h2>Scope</h2><ul><li>The VoxTerrae client (this site's downloads and the source).</li><li>This website and its feeds.</li><li>Out of scope: the EFnet servers (not ours), and social-engineering of channel members.</li></ul>
<h2>What we already do</h2><ul><li>Strict CA verification on HOME; trust-on-first-use pinning with change refusal on EFnet.</li><li>Published SHA-256 for every file; SHA256SUMS per release.</li><li>No third-party code on this site; no telemetry in the client.</li></ul>
<h2>Machine-readable</h2><p><a href="/.well-known/security.txt">/.well-known/security.txt</a> (RFC 9116).</p>"""
add("/security", "text/html; charset=utf-8", layout("Security · VoxTerrae", sec, "/security", "How to report a security issue in VoxTerrae, and what the project already does."))
add("/.well-known/security.txt", "text/plain; charset=utf-8", f"Contact: {SEC_CONTACT}\nExpires: {expires}\nPreferred-Languages: en\nCanonical: {ORIGIN}/.well-known/security.txt\nPolicy: {ORIGIN}/security\n")
about = f"""<div class="eyebrow">About</div><h1>Why a client at all</h1>
<p class="lead">warheatmap.app has daily readers all over the world. They needed a room, not another platform.</p>
<p>IRC is open, federated, forty years old and still the fastest way to talk in text. What it lacked was the layer people expect in 2026: history you can scroll back into, reactions, threaded replies, notifications. IRCv3 provides all of that; our home network runs it. VoxTerrae is the client that makes it one click, and it keeps the classic EFnet rooms in the same window because that is where some of us have lived since the nineties.</p>
<h2>Licences</h2><table><tbody><tr><td>VoxTerrae</td><td>MIT</td></tr><tr><td>Qt via PySide6</td><td>LGPLv3. The application links Qt dynamically; you may replace the Qt libraries with your own build. Qt source: <a href="https://download.qt.io/">download.qt.io</a>.</td></tr><tr><td>qasync</td><td>BSD-2-Clause</td></tr><tr><td>Fonts</td><td>System fonts only (Cascadia, Segoe UI); nothing bundled.</td></tr></tbody></table>
<h2>Contact</h2><p>#warheatmap on <span class="mono">irc.warheatmap.app</span>. Security reports: see <a href="/security">Security</a>.</p>"""
add("/about", "text/html; charset=utf-8", layout("About · VoxTerrae", about, "/about", "Why VoxTerrae exists, and its licences."))
add("/404", "text/html; charset=utf-8", layout("Not found · VoxTerrae", "<div class=\"eyebrow\">404</div><h1>No such room.</h1><p class=\"lead\">That page is not here. Try <a href=\"/\">home</a>, <a href=\"/download\">download</a> or the <a href=\"/docs\">docs</a>.</p>", "/404"))
# ---- feeds -----------------------------------------------------------------------------------
latest = {"product": "VoxTerrae", "version": REL["latest"], "pub_date": LATEST["date"] + "T00:00:00Z", "notes": " · ".join(LATEST["notes"]), "url": f"{ORIGIN}/releases/{REL['latest']}",
          "platforms": {a["platform"]: {"url": f"{ORIGIN}/dl/{REL['latest']}/{a['file']}", "sha256": a["sha256"], "size": a["size"], "kind": a["kind"], "signature": None} for a in LATEST["assets"]}}
add("/api/latest.json", "application/json; charset=utf-8", json.dumps(latest, indent=1))
add("/api/releases.json", "application/json; charset=utf-8", json.dumps(REL, indent=1))
add("/robots.txt", "text/plain; charset=utf-8", f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n")
urls = [p for p in PAGES if PAGES[p][0].startswith("text/html") and p != "/404"]
add("/sitemap.xml", "application/xml; charset=utf-8", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" + "".join(f"<url><loc>{ORIGIN}{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in urls) + "</urlset>")
add("/llms.txt", "text/plain; charset=utf-8", f"# VoxTerrae\n\n> {latest['notes'][:300]}\n\nVoxTerrae is the open-source (MIT) IRC client for the WarHeatMap.app community. It connects to the IRCv3 home network irc.warheatmap.app and to EFnet at the same time. Latest version {REL['latest']} ({LATEST['date']}).\n\n## Docs\n" + "".join(f"- [{t}]({ORIGIN}/docs/{s}): {sm}\n" for _, s, t, sm, _ in docs) + f"\n## Downloads\n- [Download]({ORIGIN}/download): files with SHA-256\n- [Releases]({ORIGIN}/releases): changelog\n- [latest.json]({ORIGIN}/api/latest.json): machine-readable update feed\n\n## Security\n- [Security policy]({ORIGIN}/security)\n- [security.txt]({ORIGIN}/.well-known/security.txt)\n")
add("/favicon.svg", "image/svg+xml", f"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 64\"><rect x=\"4\" y=\"4\" width=\"56\" height=\"56\" rx=\"12\" fill=\"{P['bg']}\" stroke=\"{P['ph']}\" stroke-width=\"4\"/><rect x=\"18\" y=\"18\" width=\"28\" height=\"28\" fill=\"{P['ph']}\"/></svg>")
# ---- worker ----------------------------------------------------------------------------------
worker = """// VoxTerrae Hub — generated by hub/build.py %s. Pages are embedded; binaries and images stream from R2 (binding RELEASES).
const PAGES = %s;
const SEC = { "x-content-type-options": "nosniff", "referrer-policy": "strict-origin-when-cross-origin", "x-frame-options": "DENY", "permissions-policy": "camera=(), microphone=(), geolocation=()", "strict-transport-security": "max-age=31536000; includeSubDomains; preload", "content-security-policy": "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'" };
function page(path, status = 200) {
  const p = PAGES[path]; if (!p) return null;
  const h = new Headers(SEC); h.set("content-type", p[0]);
  h.set("cache-control", path.startsWith("/api/") ? "public, max-age=300" : "public, max-age=600");
  if (path.startsWith("/api/")) h.set("access-control-allow-origin", "*");
  return new Response(p[1], { status, headers: h });
}
export default {
  async fetch(req, env) {
    const u = new URL(req.url); let path = u.pathname.replace(/\\/+$/, "") || "/";
    const CANON = new URL("%s").host;
    if (u.host !== CANON) return Response.redirect("https://" + CANON + u.pathname + u.search, 301);   // www + legacy hostnames -> canonical
    if (req.method !== "GET" && req.method !== "HEAD") return new Response("method not allowed", { status: 405, headers: SEC });
    if (path === "/health") return new Response(JSON.stringify({ ok: true, v: "%s", latest: "%s", pages: Object.keys(PAGES).length }), { headers: { "content-type": "application/json", ...SEC } });
    if (path === "/og.png" || path === "/og.jpg") path = "/img/og.png";
    if (path.startsWith("/dl/") || path.startsWith("/img/")) {
      const key = path.startsWith("/dl/") ? "releases/" + path.slice(4) : "site/" + path.slice(5);
      if (key.includes("..")) return page("/404", 404);
      if (path.startsWith("/dl/") && PAGES[path]) return page(path);               // SHA256SUMS is embedded
      const obj = await env.RELEASES.get(key);
      if (!obj) return page("/404", 404);
      const h = new Headers(SEC); obj.writeHttpMetadata(h); h.set("etag", obj.httpEtag);
      h.set("cache-control", "public, max-age=31536000, immutable");
      if (path.startsWith("/dl/")) { h.set("content-disposition", `attachment; filename="${path.split("/").pop()}"`); if (!h.get("content-type")) h.set("content-type", "application/octet-stream"); }
      return new Response(req.method === "HEAD" ? null : obj.body, { headers: h });
    }
    if (PAGES[path] && path !== "/404") return page(path);
    if (path === "/index.html") return Response.redirect(u.origin + "/", 301);
    return page("/404", 404);
  }
};
""" % (TODAY, json.dumps(PAGES, ensure_ascii=False), ORIGIN, hashlib.md5(json.dumps(PAGES, sort_keys=True).encode()).hexdigest()[:8], REL["latest"])
out = os.path.join(DIST, "worker.mjs"); open(out, "w", encoding="utf-8").write(worker)
print(f"built {out}: {len(worker.encode()):,} bytes, {len(PAGES)} routes")
print("contrast vs bg:", CONTRAST)
# gate: latest release must have an asset with a 64-hex sha
assert all(re.fullmatch(r"[0-9a-f]{64}", a["sha256"]) for a in LATEST["assets"]) and LATEST["assets"], "latest release has no verified asset"
# link check: every internal href resolves to a route, /dl/, /img/, or an anchor
missing = set()
for path, (ct, body) in PAGES.items():
    if not ct.startswith("text/html"): continue
    for href in re.findall(r'href="(/[^"#]*)', body):
        if href in PAGES or href.startswith(("/dl/", "/img/", "/og.png", "/health")): continue
        missing.add(href)
print("broken internal links:", sorted(missing) or "none")
