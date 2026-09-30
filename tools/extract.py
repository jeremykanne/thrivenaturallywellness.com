#!/usr/bin/env python3
"""Extract the Divi page structure (sections > rows > columns > modules) from the
static Thrive site into JSON, so a new design can re-render the same copy and structure."""
import json
import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString

SITE = Path(os.environ.get("THRIVE_SRC", Path.home() / "Sites/thrive-site-main"))
OUT = Path(__file__).parent / "content.json"

PAGES = ["", "start-here", "about", "services", "faq", "blog", "resources", "shape-reclaimed",
         "work-with-me", "thank-you",
         "natural-allergy-relief-a-naturopathic-approach-to-seasonal-wellness",
         "natural-approaches-to-managing-anxiety-and-stress-two-steps-and-a-bonus",
         "the-role-of-detoxification-in-naturopathic-medicine-myth-or-must"]

KEEP_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "a", "strong", "b", "em", "i",
             "br", "blockquote", "img", "span", "sup", "sub", "table", "thead", "tbody", "tr", "td", "th"}
KEEP_ATTRS = {"a": {"href", "target", "rel"}, "img": {"src", "alt", "width", "height"}}


def clean_html(node):
    """Return simplified inner HTML: semantic tags only, no classes/inline styles."""
    if node is None:
        return ""
    node = BeautifulSoup(str(node), "html.parser")
    for c in node.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for t in node.find_all(["script", "style", "noscript", "svg", "iframe", "form"]):
        t.decompose()
    for t in node.find_all(True):
        if t.name not in KEEP_TAGS:
            t.unwrap()
            continue
        allowed = KEEP_ATTRS.get(t.name, set())
        t.attrs = {k: v for k, v in t.attrs.items() if k in allowed}
    for t in node.find_all("span"):
        t.unwrap()
    for t in node.find_all("b"):
        t.name = "strong"
    for t in node.find_all("i"):
        t.name = "em"
    html = str(node)
    html = re.sub(r"<p>\s*(&nbsp;| )?\s*</p>", "", html)
    html = re.sub(r"\n\s*\n+", "\n", html).strip()
    return html


def text(node):
    return node.get_text(" ", strip=True) if node else ""


def img_info(img):
    if not img:
        return None
    return {"src": img.get("src"), "alt": img.get("alt", "")}


def link_of(node):
    a = node.find("a", href=True) if node else None
    return a["href"] if a else None


PAGE_CSS = ""


def css_align(key):
    """Alignment Divi applied via generated CSS (desktop rule, not inside a media query)."""
    if not key:
        return None
    base = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*\s*\}", "", PAGE_CSS)
    m = re.search(r"\." + re.escape(key) + r"(?![\w-])[^{]*\{[^}]*text-align:\s*(center|right|left)", base)
    return m.group(1) if m else None


def parse_module(m):
    cls = m.get("class", [])
    known = [("et_pb_promo", "et_pb_cta"), ("et_pb_button_module_wrapper", "et_pb_button"),
             ("et_pb_contact_form_container", "et_pb_contact_form"), ("et_pb_posts", "et_pb_posts"),
             ("et_pb_blog_grid_wrapper", "et_pb_posts")]
    kind = next((k for c, k in known if c in cls), None)
    if kind is None and any(c.startswith("et_pb_blog_") for c in cls):
        kind = "et_pb_posts"
    if kind is None:
        for k in ("et_pb_text", "et_pb_image", "et_pb_blurb", "et_pb_code", "et_pb_divider", "et_pb_slider",
                  "et_pb_accordion", "et_pb_post_title", "et_pb_post_content", "et_pb_search"):
            if k in cls:
                kind = k
                break
    align = next((c.replace("et_pb_text_align_", "") for c in cls if c.startswith("et_pb_text_align_")), None)
    align = css_align(numbered(m)) or align
    dark = "et_pb_bg_layout_dark" in cls

    if kind == "et_pb_text":
        return {"type": "text", "html": clean_html(m.select_one(".et_pb_text_inner")), "align": align, "dark": dark}
    if kind == "et_pb_image":
        img = m.find("img")
        return {"type": "image", **(img_info(img) or {}), "href": link_of(m)}
    if kind == "et_pb_blurb":
        icon_el = m.select_one(".et-pb-icon")
        return {"type": "blurb", "title": text(m.select_one(".et_pb_module_header")),
                "href": link_of(m.select_one(".et_pb_module_header")),
                "html": clean_html(m.select_one(".et_pb_blurb_description")),
                "img": img_info(m.select_one(".et_pb_main_blurb_image img")),
                "icon": text(icon_el) if icon_el else None, "align": align}
    if kind == "et_pb_cta":
        btn = m.select_one(".et_pb_promo_button")
        return {"type": "cta", "title": text(m.select_one(".et_pb_module_header")),
                "html": clean_html(m.select_one(".et_pb_promo_description > div")),
                "button": {"text": text(btn), "href": btn.get("href")} if btn else None, "align": align}
    if kind == "et_pb_button":
        a = m.find("a") or m
        align = next((c.replace("et_pb_button_alignment_", "") for c in cls
                      if re.fullmatch(r"et_pb_button_alignment_(left|center|right)", c)), "left")
        return {"type": "button", "text": text(a), "href": a.get("href"), "align": align}
    if kind == "et_pb_posts":
        posts = []
        for art in m.select("article"):
            t = art.select_one(".entry-title a") or art.find("a", href=True)
            posts.append({"title": text(t), "href": t.get("href") if t else None,
                          "date": text(art.select_one(".published")),
                          "img": img_info(art.find("img")),
                          "excerpt": text(art.select_one(".post-content-inner") or art.select_one(".post-content"))})
        return {"type": "posts", "posts": posts}
    if kind == "et_pb_code":
        inner = m.select_one(".et_pb_code_inner")
        cal = inner.select_one(".calendly-inline-widget") if inner else None
        if cal:
            return {"type": "calendly", "url": cal.get("data-url")}
        raw = inner.decode_contents().strip() if inner else ""
        return {"type": "code", "raw": raw}
    if kind == "et_pb_divider":
        return {"type": "divider"}
    if kind == "et_pb_slider":
        slides = []
        for s in m.select(".et_pb_slide"):
            btn = s.select_one(".et_pb_more_button")
            slides.append({"title": text(s.select_one(".et_pb_slide_title")),
                           "html": clean_html(s.select_one(".et_pb_slide_content")),
                           "button": {"text": text(btn), "href": btn.get("href")} if btn else None})
        return {"type": "slider", "slides": slides}
    if kind == "et_pb_accordion":
        return {"type": "accordion", "items": [
            {"title": text(t.select_one(".et_pb_toggle_title")), "html": clean_html(t.select_one(".et_pb_toggle_content"))}
            for t in m.select(".et_pb_toggle")]}
    if kind == "et_pb_contact_form":
        form = m.find("form")
        fields = []
        for p in form.select(".et_pb_contact_field"):
            inp = p.find(["input", "textarea", "select"])
            fields.append({"label": text(p.find("label")), "name": inp.get("name"),
                           "type": inp.get("type", inp.name), "half": "et_pb_contact_field_half" in p.get("class", []),
                           "pattern": inp.get("pattern"), "title": inp.get("title")})
        title = text(m.select_one(".et_pb_contact_main_title"))
        return {"type": "form", "name": form.get("name"), "title": title, "fields": fields,
                "button": text(form.select_one("button"))}
    if kind == "et_pb_post_title":
        return {"type": "post_title", "title": text(m.find(["h1", "h2"])), "meta": text(m.select_one(".et_pb_title_meta_container"))}
    if kind == "et_pb_post_content":
        return {"type": "post_content", "html": clean_html(m)}
    if kind == "et_pb_search":
        return None
    print("  ! unhandled module", kind, cls[:4], file=sys.stderr)
    return {"type": "unknown", "kind": kind, "html": clean_html(m)}


def hidden_map(css):
    """{'et_pb_section_4': {'phone','tablet'}, ...} from Divi's responsive display:none rules."""
    hidden = {}
    for mq, body in re.findall(r"@media([^{]*)\{((?:[^{}]*\{[^{}]*\})*)\s*\}", css):
        q = mq.replace(" ", "")
        dev = ("desktop" if "min-width:981px" in q else "phone" if "max-width:767px" in q
               else "tablet" if "max-width:980px" in q else None)
        if not dev:
            continue
        for sel, rule in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
            if re.search(r"display:\s*none", rule):
                for one in sel.split(","):
                    m = re.search(r"\.(et_pb_[a-z_]+_\d+)$", one.strip())
                    if m:
                        hidden.setdefault(m.group(1), set()).add(dev)
    return hidden


def numbered(el):
    return next((c for c in el.get("class", []) if re.fullmatch(r"et_pb_[a-z_]+_\d+", c)
                 and not c.endswith("_wrapper")), None)


def section_bg(css, idx):
    """Background image / color for .et_pb_section_N from Divi's generated CSS."""
    out = {}
    for m in re.finditer(r"\.et_pb_section_%d(?![0-9])[^{]*\{([^}]*)\}" % idx, css):
        body = m.group(1)
        img = re.search(r"background-image:\s*url\(([^)]+)\)", body)
        col = re.search(r"background-color:\s*([^;!]+)", body)
        if img and "bg" not in out:
            out["bg"] = img.group(1).strip("'\"")
        if col and "color" not in out:
            out["color"] = col.group(1).strip()
    return out


def column_fraction(col):
    for c in col.get("class", []):
        m = re.fullmatch(r"et_pb_column_(\d)_(\d)", c)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    return "4/4"


def extract(slug):
    path = SITE / slug / "index.html" if slug else SITE / "index.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    css = "\n".join(s.get_text() for s in soup.find_all("style"))
    global PAGE_CSS
    PAGE_CSS = css
    page = {
        "slug": slug,
        "title": text(soup.title),
        "description": (soup.find("meta", attrs={"name": "description"}) or {}).get("content", ""),
        "og_image": (soup.find("meta", attrs={"property": "og:image"}) or {}).get("content"),
        "sections": [],
    }
    hidden = hidden_map(css)
    root = soup.select_one("#et-main-area") or soup
    for sec in root.select(".et_pb_section"):
        idx = int(re.search(r"et_pb_section_(\d+)", " ".join(sec["class"])).group(1))
        s = {"index": idx, **section_bg(css, idx),
             "dark": any("et_pb_bg_layout_dark" in " ".join(r.get("class", [])) for r in sec.select(".et_pb_module")[:1]),
             "hide": sorted(hidden.get(f"et_pb_section_{idx}", [])), "rows": []}
        for row in sec.select(":scope > .et_pb_row, :scope > .et_pb_row_inner"):
            r = {"cols": []}
            for col in row.select(":scope > .et_pb_column"):
                mods = []
                for el in col.select(":scope > .et_pb_module"):
                    mod = parse_module(el)
                    if mod:
                        key = numbered(el.find(class_=re.compile(r"et_pb_button_\d+$")) or el) if "et_pb_button_module_wrapper" in el.get("class", []) else numbered(el)
                        mod["hide"] = sorted(hidden.get(key, [])) if key else []
                    mods.append(mod)
                r["cols"].append({"frac": column_fraction(col), "modules": [x for x in mods if x]})
            if any(c["modules"] for c in r["cols"]):
                s["rows"].append(r)
        if s["rows"]:
            page["sections"].append(s)
    return page


pages = []
for slug in PAGES:
    p = extract(slug)
    n = sum(len(c["modules"]) for s in p["sections"] for r in s["rows"] for c in r["cols"])
    print(f"{slug or '/':72.72} sections {len(p['sections']):2}  modules {n:3}")
    pages.append(p)
OUT.write_text(json.dumps(pages, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT)
