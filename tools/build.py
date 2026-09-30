#!/usr/bin/env python3
"""Render the extracted Thrive content (content.json) with the refreshed, performance-first design."""
import html
import os
import json
import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

HERE = Path(__file__).parent
SRC = Path(os.environ.get("THRIVE_SRC", Path.home() / "Sites/thrive-site-main"))  # checkout of the main branch (original site)
OUT = HERE.parent / "site"
ORIGIN = "https://www.thrivenaturallywellness.com"
PAGES = json.loads((HERE / "content.json").read_text(encoding="utf-8"))

CALENDLY_BADGE_URL = "https://calendly.com/thrivenaturallywellness/30min?text_color=2c3a47&primary_color=2b87da"
GTAG_ID, FB_PIXEL, HOTJAR_ID = "GT-PHP7QXZ", "406827137785254", "2677271"

NAV = [("/", "Home"), ("/start-here/", "Start here"), ("/about/", "About Nadene"), ("/services/", "Services"),
       ("/faq/", "FAQ"), ("/blog/", "Blog"),
       ("/resources/", "Resources", [("/shape-reclaimed/", "SHAPE Reclaimed"), ("/resources/", "All Resources")]),
       ("/work-with-me/", "Work with me")]

# ------------------------------------------------------------------ icons (replace Divi/FA icon fonts)
ICONS = {
    "icon_phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "icon_mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
    "icon_pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "icon_check_alt2": '<circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/>',
    "icon_like": '<path d="M7 10v12"/><path d="M15 5.9 14 10h5.8a2 2 0 0 1 2 2.3l-1.4 8a2 2 0 0 1-2 1.7H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.8a2 2 0 0 0 1.8-1.1L12 2a3.1 3.1 0 0 1 3 3.9z"/>',
    "icon_like_alt": '<path d="M7 10v12"/><path d="M15 5.9 14 10h5.8a2 2 0 0 1 2 2.3l-1.4 8a2 2 0 0 1-2 1.7H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.8a2 2 0 0 0 1.8-1.1L12 2a3.1 3.1 0 0 1 3 3.9z"/>',
    "user-md": '<circle cx="12" cy="7" r="4"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/><path d="M12 14v4"/><path d="M10 16h4"/>',
    "plus-circle": '<circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="M8 12h8"/>',
    "handshake-o": '<path d="m11 17 2 2a1 1 0 1 0 3-3"/><path d="m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.9-3.9a3 3 0 0 0-4.2 0l-.9.9a1 1 0 1 1-3-3l2.8-2.8a5.8 5.8 0 0 1 7.1-.9l.5.3a4 4 0 0 0 2.8.6L21 4"/><path d="m21 3 1 11h-2"/><path d="M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3"/><path d="M3 4h8"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "chev": '<path d="m6 9 6 6 6-6"/>',
    "menu": '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
}


def svg(name, cls="i"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def divi_icon(code):
    if not code:
        return None
    name = code.split("~|")[1] if "~|" in code else None
    return svg(name) if name in ICONS else None


# ------------------------------------------------------------------ images
IMG_OUT = OUT / "img"
WIDTHS = [480, 800, 1200, 1600]
_img_cache = {}


def local(src):
    return SRC / src.split("?")[0].lstrip("/")


def image_variants(src):
    """Create responsive WebP variants; return dict(src, srcset, w, h) or None for SVG/unknown."""
    if src in _img_cache:
        return _img_cache[src]
    p = local(src)
    info = None
    if p.suffix.lower() == ".svg":
        dest = IMG_OUT / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        vb = re.search(r'viewBox="([\d.\s-]+)"', p.read_text(errors="ignore"))
        w, h = (float(x) for x in vb.group(1).split()[2:4]) if vb else (100, 100)
        info = {"src": f"/img/{p.name}", "srcset": None, "w": round(w), "h": round(h)}
    elif p.exists():
        with Image.open(p) as im:
            im = im.convert("RGBA") if im.mode in ("P", "LA") else im
            has_alpha = im.mode == "RGBA" and im.getextrema()[3][0] < 255
            if not has_alpha and im.mode != "RGB":
                im = im.convert("RGB")
            W, H = im.size
            stem = re.sub(r"[^a-z0-9-]+", "-", p.stem.lower()).strip("-")[:60]
            widths = [w for w in WIDTHS if w < W] + [min(W, WIDTHS[-1])]
            srcset = []
            for w in sorted(set(widths)):
                name = f"{stem}-{w}.webp"
                dest = IMG_OUT / name
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    im.resize((w, round(H * w / W)), Image.LANCZOS).save(dest, "WEBP", quality=78, method=6)
                srcset.append(f"/img/{name} {w}w")
            default = [s for s in srcset if int(s.split()[-1][:-1]) <= 1200][-1].split()[0]
            info = {"src": default, "srcset": ", ".join(srcset), "w": W, "h": H}
    _img_cache[src] = info
    return info


class Ctx:
    """Per-page render state (tracks the first/LCP image)."""
    def __init__(self):
        self.first_img = True
        self.preload = None


def picture(ctx, src, alt="", sizes="(max-width: 780px) 100vw, 50vw", cls=""):
    info = image_variants(src)
    if not info:
        return ""
    eager = ctx.first_img and info["srcset"] is not None
    if eager:
        ctx.first_img = False
        ctx.preload = info
    attrs = [f'src="{info["src"]}"', f'alt="{html.escape(alt or "")}"', f'width="{info["w"]}"', f'height="{info["h"]}"']
    if info["srcset"]:
        attrs.append(f'srcset="{info["srcset"]}" sizes="{sizes}"')
    attrs.append('fetchpriority="high"' if eager else 'loading="lazy"')
    attrs.append('decoding="async"')
    if cls:
        attrs.append(f'class="{cls}"')
    return f"<img {' '.join(attrs)}>"


def fix_inline_images(ctx, h):
    """Rewrite <img> tags inside rich text to optimized, lazy, sized images."""
    def rep(m):
        src = re.search(r'src="([^"]+)"', m.group(0))
        alt = re.search(r'alt="([^"]*)"', m.group(0))
        if not src or src.group(1).startswith("http"):
            return m.group(0)
        return picture(ctx, src.group(1), alt.group(1) if alt else "", "(max-width: 780px) 100vw, 720px")
    return re.sub(r"<img[^>]*>", rep, h)


# ------------------------------------------------------------------ modules
def vis(mod_or_sec):
    hide = set(mod_or_sec.get("hide") or [])
    out = []
    if "desktop" in hide:
        out.append("hide-lg")
    if {"tablet", "phone"} <= hide:
        out.append("hide-sm")
    return (" " + " ".join(out)) if out else ""


def link_attrs(href):
    ext = href and href.startswith("http") and "thrivenaturallywellness.com" not in href
    return ' target="_blank" rel="noopener"' if ext else ""


def clean_href(href):
    if not href:
        return href
    return re.sub(r"^https?://(www\.)?thrivenaturallywellness\.com", "", href) or "/"


def btn(text, href, cls="btn"):
    href = clean_href(href) or "#"
    return f'<a class="{cls}" href="{html.escape(href)}"{link_attrs(href)}>{html.escape(text)}</a>'


def render_module(ctx, m, col_count):
    t = m["type"]
    v = vis(m)
    if t == "text":
        body = fix_inline_images(ctx, m["html"])
        body = re.sub(r'href="https?://(?:www\.)?thrivenaturallywellness\.com', 'href="', body)
        align = f" ta-{m['align']}" if m.get("align") in ("center", "right") else ""
        return f'<div class="prose{align}{v}">{body}</div>'
    if t == "image":
        img = picture(ctx, m["src"], m.get("alt"), "(max-width: 780px) 100vw, " + ("50vw" if col_count > 1 else "1100px"),
                      "media" if not m["src"].endswith(".svg") else "icon-img")
        if m.get("href"):
            img = f'<a href="{html.escape(clean_href(m["href"]))}"{link_attrs(m["href"])}>{img}</a>'
        return f'<figure class="fig{v}">{img}</figure>'
    if t == "blurb":
        icon = divi_icon(m.get("icon"))
        media = (f'<span class="blurb-icon">{icon}</span>' if icon
                 else picture(ctx, m["img"]["src"], m["img"].get("alt"), "120px", "blurb-img") if m.get("img") else "")
        title = html.escape(m["title"])
        if m.get("href") and title:
            title = f'<a href="{html.escape(clean_href(m["href"]))}"{link_attrs(m["href"])}>{title}</a>'
        head = f"<h3>{title}</h3>" if m["title"] else ""
        align = " ta-center" if m.get("align") == "center" else ""
        return f'<div class="blurb{align}{v}">{media}<div>{head}{m["html"]}</div></div>'
    if t == "cta":
        b = btn(m["button"]["text"], m["button"]["href"], "btn btn-sm") if m.get("button") and m["button"]["text"] else ""
        h = f"<h3>{html.escape(m['title'])}</h3>" if m["title"] else ""
        return f'<div class="cta-card{v}">{h}<div class="prose">{m["html"]}</div>{b}</div>'
    if t == "button":
        return f'<p class="btn-row ta-{m.get("align", "left")}{v}">{btn(m["text"], m["href"])}</p>'
    if t == "divider":
        return f'<hr class="rule{v}">'
    if t == "slider":
        slides = "".join(
            f'<figure class="slide"><blockquote class="prose">{s["html"]}</blockquote>'
            + (f'<figcaption>{html.escape(s["title"])}</figcaption>' if s["title"] else "")
            + (btn(s["button"]["text"], s["button"]["href"], "btn btn-sm") if s.get("button") else "")
            + "</figure>" for s in m["slides"])
        dots = "".join(f'<button type="button" aria-label="Show testimonial {i + 1}"></button>' for i in range(len(m["slides"])))
        return (f'<div class="slider{v}" data-slider><div class="slides" tabindex="0" aria-label="Testimonials">{slides}</div>'
                f'<div class="dots">{dots}</div></div>')
    if t == "accordion":
        items = "".join(f'<details><summary>{html.escape(i["title"])}{svg("chev", "i chev")}</summary><div class="prose">{i["html"]}</div></details>'
                        for i in m["items"])
        return f'<div class="accordion{v}">{items}</div>'
    if t == "calendly":
        return (f'<div class="calendly-embed{v}" data-calendly="{html.escape(m["url"])}">'
                f'<a class="btn" href="{html.escape(m["url"].split("?")[0])}" target="_blank" rel="noopener">{svg("calendar")} Open the scheduler</a></div>')
    if t == "form":
        name = m["name"]
        fields = []
        for f in m["fields"]:
            ftype = "email" if f["name"] == "email" else "tel" if f["name"] == "phone" else "text"
            pat = f' pattern="{html.escape(f["pattern"])}" title="{html.escape(f["title"] or "")}"' if f.get("pattern") else ""
            fid = f"{name}-{f['name']}"
            auto = {"name": "name", "email": "email", "phone": "tel"}.get(f["name"], "on")
            fields.append(f'<p class="field{" half" if f["half"] else ""}"><label for="{fid}">{html.escape(f["label"])}</label>'
                          f'<input id="{fid}" name="{f["name"]}" type="{ftype}" autocomplete="{auto}" required{pat}></p>')
        title = f"<h3>{html.escape(m['title'])}</h3>" if m.get("title") else ""
        return (f'<form class="form-card{v}" name="{name}" method="POST" action="/thank-you/" data-netlify="true" netlify-honeypot="bot-field">'
                f'{title}<input type="hidden" name="form-name" value="{name}">'
                f'<p class="hp"><label>Leave empty <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>'
                f'<div class="fields">{"".join(fields)}</div><button class="btn" type="submit">{html.escape(m["button"])}</button></form>')
    if t == "posts":
        cards = []
        for p in m["posts"]:
            href = clean_href(p["href"])
            img = picture(ctx, p["img"]["src"], p["img"].get("alt") or p["title"], "(max-width: 780px) 100vw, 360px", "post-img") if p.get("img") else ""
            cards.append(f'<article class="post-card"><a href="{href}">{img}<div class="post-body">'
                         f'<p class="meta">{html.escape(p["date"])}</p><h3>{html.escape(p["title"])}</h3>'
                         f'<p>{html.escape(p["excerpt"])}</p><span class="more">Read more {svg("arrow")}</span></div></a></article>')
        return f'<div class="post-grid{v}">{"".join(cards)}</div>'
    if t == "post_title":
        meta = f'<p class="meta">{html.escape(m["meta"])}</p>' if m.get("meta") else ""
        return f'<header class="post-head">{meta}<h1>{html.escape(m["title"])}</h1></header>'
    if t == "post_content":
        body = fix_inline_images(ctx, m["html"])
        return f'<div class="prose article">{body}</div>'
    return ""


# ------------------------------------------------------------------ sections
def section_words(s):
    t = re.sub(r"<[^>]+>", " ", json.dumps([m for r in s["rows"] for c in r["cols"] for m in c["modules"]]))
    return {w.lower() for w in re.findall(r"[A-Za-z]{4,}", t)}


def collapse_duplicates(sections):
    """Divi kept separate desktop/mobile copies of some sections. Keep one responsive copy."""
    desk = [s for s in sections if set(s["hide"]) >= {"phone", "tablet"}]
    drop = set()
    for m in [s for s in sections if s["hide"] == ["desktop"]]:
        wm = section_words(m)
        best = max(desk, key=lambda d: len(wm & section_words(d)), default=None)
        if best and wm and len(wm & section_words(best)) / len(wm) >= 0.9:
            drop.add(m["index"])
            best["hide"] = []
    return [s for s in sections if s["index"] not in drop]


def tone(s):
    c = (s.get("color") or "").replace(" ", "").lower()
    if c in ("#43c6c4", "#29c4a9"):
        return "tone-teal"
    if c == "#2f8cff":
        return "tone-blue"
    if c in ("#f1f5f7", "rgba(0,155,216,0.07)"):
        return "tone-mist"
    if c.startswith("rgba(212,244,244"):
        return "tone-aqua"
    return ""


def frac_to_fr(frac):
    a, b = (int(x) for x in frac.split("/"))
    return a * 60 // b


def render_section(ctx, s, i, is_post):
    rows = []
    for r in s["rows"]:
        cols = [c for c in r["cols"]]
        n = len(cols)
        inner = []
        for c in cols:
            mods = "".join(render_module(ctx, m, n) for m in c["modules"])
            inner.append(f'<div class="col">{mods}</div>')
        if n == 1:
            rows.append(f'<div class="row">{inner[0]}</div>')
        else:
            tmpl = " ".join(f"{frac_to_fr(c['frac'])}fr" for c in cols)
            kind = "row-quad" if n >= 4 else "row-tri" if n == 3 else "row-duo"
            rows.append(f'<div class="row grid {kind}" style="--cols:{tmpl}">{"".join(inner)}</div>')
    classes = ["sec", tone(s), "sec-hero" if i == 0 and not is_post else ""]
    return f'<section class="{" ".join(c for c in classes if c)}{vis(s)}"><div class="wrap">{"".join(rows)}</div></section>'


# ------------------------------------------------------------------ page shell
def head_tags(slug):
    """Copy SEO tags (title, metas, canonical, JSON-LD) from the current page unchanged."""
    path = SRC / slug / "index.html" if slug else SRC / "index.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    keep = [str(soup.title)]
    for m in soup.head.find_all("meta"):
        if m.get("charset") or m.get("name") in ("viewport", "generator") or m.get("http-equiv"):
            continue
        keep.append(str(m))
    can = soup.head.find("link", rel="canonical")
    if can:
        keep.append(str(can))
    for s in soup.find_all("script", type="application/ld+json"):
        keep.append(str(s))
    return "\n  ".join(keep)


CSS = (HERE / "site.css").read_text(encoding="utf-8")
JS = (HERE / "site.js").read_text(encoding="utf-8")


def nav_html(active):
    items = []
    current = ' aria-current="page"'
    for item in NAV:
        href, label = item[0], item[1]
        cur = current if href == active else ""
        if len(item) == 3:
            sub = "".join(f'<li><a href="{h}"{current if h == active and h != href else ""}>{l}</a></li>' for h, l in item[2])
            items.append(f'<li class="has-sub"><a href="{href}"{cur}>{label}{svg("chev", "i chev")}</a><ul class="sub">{sub}</ul></li>')
        else:
            items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return "".join(items)


def shell(page, body, ctx, active):
    preload = ""
    if ctx.preload and ctx.preload["srcset"]:
        preload = (f'\n  <link rel="preload" as="image" href="{ctx.preload["src"]}" imagesrcset="{ctx.preload["srcset"]}" '
                   f'imagesizes="(max-width: 780px) 100vw, 50vw" fetchpriority="high">')
    return f'''<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {head_tags(page["slug"])}
  <link rel="icon" href="/img/TNW-icon.svg" type="image/svg+xml">
  <link rel="preload" href="/fonts/montserrat-latin.woff2" as="font" type="font/woff2" crossorigin>{preload}
  <style>{CSS}</style>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-head">
    <div class="wrap head-inner">
      <a class="logo" href="/" aria-label="Thrive Naturally Wellness home"><img src="/img/Thrive-Naturally-Wellness-logo-landscape-color.svg" alt="Thrive Naturally Wellness" width="220" height="56"></a>
      <button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav" aria-label="Menu">{svg("menu")}</button>
      <nav id="nav" class="nav" aria-label="Main"><ul>{nav_html(active)}</ul></nav>
    </div>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="site-foot">
    <div class="wrap foot-inner">
      <img src="/img/Thrive-Naturally-Wellness-logo-center-white.svg" alt="Thrive Naturally Wellness" width="150" height="90" loading="lazy">
      <p>Designed by <a href="https://www.smartyeti.co" target="_blank" rel="noopener">Smart Yeti</a></p>
    </div>
  </footer>
  <button class="book-badge" type="button" data-calendly-popup="{html.escape(CALENDLY_BADGE_URL)}">{svg("calendar")}<span>Schedule time with me</span></button>
  <script>window.TNW={{gtag:"{GTAG_ID}",fb:"{FB_PIXEL}",hj:{HOTJAR_ID}}};{JS}</script>
</body>
</html>
'''


# ------------------------------------------------------------------ build
if OUT.exists():
    shutil.rmtree(OUT)
(OUT / "fonts").mkdir(parents=True)
shutil.copy2(HERE / "fonts/montserrat-latin.woff2", OUT / "fonts/montserrat-latin.woff2")
for f in ["Thrive-Naturally-Wellness-logo-landscape-color.svg", "Thrive-Naturally-Wellness-logo-center-white.svg"]:
    image_variants(f"/wp-content/uploads/2019/11/{f}")
image_variants("/wp-content/uploads/2021/09/TNW-icon.svg")

posts_for_archive = None
for page in PAGES:
    slug = page["slug"]
    is_post = any(m["type"] == "post_title" for s in page["sections"] for r in s["rows"] for c in r["cols"] for m in c["modules"])
    sections = collapse_duplicates(page["sections"])
    ctx = Ctx()
    body = "\n".join(render_section(ctx, s, i, is_post) for i, s in enumerate(sections))
    if is_post:
        body = body.replace('<section class="sec', '<section class="sec sec-article', 1)
    active = "/blog/" if is_post else ("/" + slug + "/" if slug else "/")
    dest = OUT / slug / "index.html" if slug else OUT / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(shell(page, body, ctx, active), encoding="utf-8")
    for s in page["sections"]:
        for r in s["rows"]:
            for c in r["cols"]:
                for m in c["modules"]:
                    if m["type"] == "posts" and posts_for_archive is None:
                        posts_for_archive = m

# Category archive: same post list as the blog page.
if posts_for_archive:
    ctx = Ctx()
    arch = {"slug": "category/uncategorized", "sections": []}
    body = (f'<section class="sec sec-hero tone-mist"><div class="wrap"><div class="row"><div class="col">'
            f'<div class="prose"><h1>Uncategorized</h1></div>{render_module(ctx, posts_for_archive, 1)}</div></div></div></section>')
    dest = OUT / "category/uncategorized/index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(shell(arch, body, ctx, "/blog/"), encoding="utf-8")

# Keep the original upload files that social cards / search results point to.
for f in OUT.rglob("index.html"):
    for u in re.findall(r'content="https://www\.thrivenaturallywellness\.com(/wp-content/uploads/[^"]+)"', f.read_text(encoding="utf-8")):
        p = local(u)
        if p.exists():
            d = OUT / u.lstrip("/")
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, d)

(OUT / "404.html").write_text(shell({"slug": "thank-you"}, '<section class="sec sec-hero"><div class="wrap"><div class="row"><div class="col"><div class="prose ta-center"><h1>Page not found</h1><p>The page you&rsquo;re looking for may have moved.</p></div><p class="btn-row ta-center"><a class="btn" href="/">Back to home</a></p></div></div></div></section>', Ctx(), "")
    .replace("<title>Thank you - Thrive Naturally Wellness</title>", "<title>Page not found - Thrive Naturally Wellness</title>"), encoding="utf-8")

(HERE.parent / "netlify.toml").write_text('''[build]
  publish = "site"

[[headers]]
  for = "/img/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/fonts/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[redirects]]
  from = "/wp-admin/*"
  to = "/"
  status = 301

[[redirects]]
  from = "/wp-login.php"
  to = "/"
  status = 301
''', encoding="utf-8")

size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
print(f"built {len(list(OUT.rglob('index.html')))} pages, {len(list(IMG_OUT.glob('*')))} images, {size / 1024:.0f} KiB total")
