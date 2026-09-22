#!/usr/bin/env python3
"""Build uracquet.com V2: static site from templates/ + inline page content → site/.
Usage: BASE_URL=https://www.uracquet.com python3 build.py
"""
import os, re, json, shutil, html, sys
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
SRC  = ROOT / "assets" / "source"
OUT  = ROOT / "site"
BASE = os.environ.get("BASE_URL", "https://www.uracquet.com").rstrip("/")
from urllib.parse import urlparse
PREFIX = urlparse(BASE).path.rstrip("/")  # "" for a root domain, "/repo" for a GitHub project page

BIZ = dict(
    name="URacquet Shop", street="4711 Pine Street", city="Philadelphia", state="PA", zip="19143",
    phone="(215) 586-3649", tel="+12155863649", email="uracquet@gmail.com",
    instagram="https://www.instagram.com/uracquetshop/",
    ucd="https://www.universitycity.org/place/uracquet-shop/",
    maps_dir="https://www.google.com/maps/dir/?api=1&destination=4711+Pine+Street,+Philadelphia,+PA+19143",
    maps_embed="https://www.google.com/maps?q=4711+Pine+Street+Philadelphia+PA+19143&output=embed",
    maps_place="https://www.google.com/maps/search/?api=1&query=URacquet+Shop+4711+Pine+Street+Philadelphia+PA+19143",
    press_url="https://court-theory.beehiiv.com/p/thank-the-stringer-mark-kuczynski-uracquet-philadelphia",
)
# CANONICAL HOURS — pending the keeper's ruling (PLAN.md 7.4); current website version.
HOURS = [("Monday","Closed",None,None),("Tuesday","12:00 – 6:30 pm","12:00","18:30"),("Wednesday","12:00 – 6:30 pm","12:00","18:30"),
         ("Thursday","1:00 – 6:30 pm","13:00","18:30"),("Friday","12:30 – 6:30 pm","12:30","18:30"),
         ("Saturday","11:00 am – 6:00 pm","11:00","18:00"),("Sunday","12:00 – 5:00 pm","12:00","17:00")]

ALT = {
 "wix_08.jpg":"A stack of freshly strung tennis racquets on the bench at URacquet Shop",
 "wix_06.jpg":"Mark Kuczynski stringing a racquet on the Wilson stringing machine at URacquet Shop",
 "wix_13.jpg":"Mark Kuczynski measuring a racquet's balance and swing weight on a diagnostic machine",
 "wix_14.jpg":"The racquet wall at URacquet Shop: Babolat, Head, Wilson and Tecnifibre racquets and bags",
 "wix_07.jpg":"Racquets hanging on the display wall at URacquet Shop",
 "wix_05.jpg":"Reels of Wilson, Head and Yonex tennis string",
 "wix_11.jpg":"Tennis accessories: a Head bag, dampeners, overgrips, Penn balls and tennis shoes",
 "wix_10.jpg":"A customer swinging a demo racquet inside URacquet Shop",
 "wix_09.jpg":"A customer browsing the racquet wall at URacquet Shop",
 "wix_12.jpg":"The outdoor courts at Penn Tennis Center in Penn Park",
 "wix_04.jpg":"Snow-covered tennis courts with the Philadelphia skyline behind",
 "wix_02.jpeg":"Arthur Ashe Stadium during the US Open",
 "wix_03.jpg":"A USTA National Championships banner on a court fence",
}

# ---------- images ----------
def build_images():
    (OUT/"img").mkdir(parents=True, exist_ok=True)
    for name in ALT:
        src = SRC/name
        if not src.exists(): continue
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        stem = name.rsplit(".",1)[0]
        for w in (1600, 800):
            t = im.copy(); t.thumbnail((w, w*3), Image.LANCZOS)
            t.save(OUT/"img"/f"{stem}-{w}.webp", "WEBP", quality=80, method=6)
    # OG image 1200x630 from wix_08
    og = ImageOps.exif_transpose(Image.open(SRC/"wix_08.jpg")).convert("RGB")
    og = ImageOps.fit(og, (1200,630), Image.LANCZOS)
    og.save(OUT/"img"/"og.jpg", "JPEG", quality=85)
    # logo mark from brand_logo.png (top square), favicons
    logo = Image.open(SRC/"brand_logo.png").convert("RGBA")
    w,h = logo.size; mark = logo.crop((0,0,w,w))
    for s,fn in ((512,"icon-512.png"),(192,"icon-192.png"),(180,"apple-touch-icon.png"),(64,"logo-mark.png"),(32,"favicon-32.png")):
        m = mark.resize((s,s), Image.LANCZOS); m.save(OUT/"img"/fn, "PNG", optimize=True)
    mark.resize((160,160), Image.LANCZOS).save(OUT/"img"/"logo-mark@2x.png","PNG",optimize=True)
    mark.resize((48,48), Image.LANCZOS).save(OUT/"favicon.ico", "ICO", sizes=[(16,16),(32,32),(48,48)])
    # full logo lockups (webp, 800px)
    for src_name, out_name in (("brand_logo.png","logo-full.webp"),("brand_logo_black_white.png","logo-bw.webp")):
        l = Image.open(SRC/src_name).convert("RGBA"); l.thumbnail((800,1600), Image.LANCZOS)
        bg = Image.new("RGBA", l.size, (255,255,255,0)); bg.alpha_composite(l); bg.save(OUT/"img"/out_name, "WEBP", quality=85)

def pic(name, cls="", sizes="(max-width: 800px) 100vw, 800px", loading="lazy", w=None, h=None):
    stem = name.rsplit(".",1)[0]
    alt = html.escape(ALT.get(name,""))
    dims = f' width="{w}" height="{h}"' if w and h else ""
    return (f'<img src="/img/{stem}-800.webp" srcset="/img/{stem}-800.webp 800w, /img/{stem}-1600.webp 1600w" '
            f'sizes="{sizes}" alt="{alt}" loading="{loading}" decoding="async"{dims} class="{cls}">')

def hero_img(name, pos=None):
    stem = name.rsplit(".",1)[0]
    style = f' style="object-position:{pos}"' if pos else ""
    return f'<img src="/img/{stem}-1600.webp" alt="" fetchpriority="high" decoding="async"{style}>'

# ---------- schema ----------
def biz_schema():
    spec = []
    for day, label, o, c in HOURS:
        if o: spec.append({"@type":"OpeningHoursSpecification","dayOfWeek":day,"opens":o,"closes":c})
    return {
      "@context":"https://schema.org","@type":"SportingGoodsStore","@id":BASE+"/#store",
      "name":BIZ["name"],"url":BASE+"/","telephone":BIZ["tel"],"email":BIZ["email"],
      "image":BASE+"/img/og.jpg","logo":BASE+"/img/icon-512.png","priceRange":"$$",
      "description":"Master Racquet Technician stringing, racquet customization, racquet demos and tennis and squash equipment in West Philadelphia, one mile from the University of Pennsylvania and Drexel University.",
      "address":{"@type":"PostalAddress","streetAddress":BIZ["street"],"addressLocality":BIZ["city"],"addressRegion":BIZ["state"],"postalCode":BIZ["zip"],"addressCountry":"US"},
      "areaServed":"Philadelphia, PA","openingHoursSpecification":spec,
      "sameAs":[BIZ["instagram"],BIZ["ucd"]],
      "founder":{"@type":"Person","name":"Mark Kuczynski","jobTitle":"USRSA Master Racquet Technician"},
      "hasOfferCatalog":{"@type":"OfferCatalog","name":"Racquet services","itemListElement":[
        {"@type":"Offer","itemOffered":{"@type":"Service","name":"Racquet stringing"},"price":"26.50","priceCurrency":"USD","description":"String installation labor per racquet; string priced separately"},
        {"@type":"Offer","itemOffered":{"@type":"Service","name":"Base grip replacement"},"price":"5.00","priceCurrency":"USD","description":"Labor; plus the cost of the grip"},
        {"@type":"Offer","itemOffered":{"@type":"Service","name":"Bumper guard and grommet replacement"},"price":"15.00","priceCurrency":"USD","description":"Labor; materials $15 for current models"},
        {"@type":"Offer","itemOffered":{"@type":"Service","name":"Grip size build-up (heat-shrink sleeve)"},"price":"15.00","priceCurrency":"USD"},
        {"@type":"Offer","itemOffered":{"@type":"Service","name":"Racquet demo program"},"price":"40.00","priceCurrency":"USD","description":"Three racquets for seven days, $35 credit toward purchase"},
        {"@type":"Offer","itemOffered":{"@type":"Service","name":"Single-racquet demo"},"price":"20.00","priceCurrency":"USD","description":"One racquet for seven days, $15 credit toward purchase"}]}
    }

def faq_schema(pairs):
    return {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in pairs]}

def crumbs_schema(items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":n,"item":BASE+u} for i,(n,u) in enumerate(items)]}

def faq_html(pairs):
    return '<div class="faq">' + "".join(f"<details><summary>{html.escape(q)}</summary><p>{a}</p></details>" for q,a in pairs) + "</div>"

# ---------- layout ----------
NAV = [("Home","/"),("Services","/services/"),("Products","/products/"),("Demo","/demo/"),("About","/about/"),("Visit","/visit/")]
HOURS_TABLE = "<table><thead><tr><th>Day</th><th>Hours</th></tr></thead><tbody>" + "".join(f"<tr><td>{d}</td><td>{l}</td></tr>" for d,l,_,_ in HOURS) + "</tbody></table>"

GSC_FILE = ROOT/"gsc-token.txt"
GSC_META = f'<meta name="google-site-verification" content="{GSC_FILE.read_text().strip()}">' if GSC_FILE.exists() else ""

def layout(p):
    url = p["url"]; canon = BASE + url
    schemas = [biz_schema()] + p.get("schemas", [])
    if url != "/": schemas.append(crumbs_schema([("Home","/"),(p["nav"],url)]))
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>' for s in schemas)
    nav_items = []
    for n,u in NAV:
        cur = ' aria-current="page"' if u == url else ''
        nav_items.append(f'<li><a href="{u}"{cur}>{n}</a></li>')
    nav_items.append(f'<li class="nav-ig"><a href="{BIZ["instagram"]}" rel="noopener">Instagram @uracquetshop</a></li>')
    nav = "".join(nav_items)
    crumbs = "" if url=="/" else f'<nav class="crumbs wrap" aria-label="Breadcrumb"><a href="/">Home</a> › {html.escape(p["nav"])}</nav>'
    hero_cls = "hero" if url=="/" else "hero small"
    hero = f'''<section class="{hero_cls}">{hero_img(p["hero"], p.get("hero_pos"))}<div class="wrap"><h1>{p["h1"]}</h1>{p.get("lead","")}{p.get("cta","")}</div></section>'''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(p["title"])}</title>
<meta name="description" content="{html.escape(p["description"])}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website">
<meta property="og:site_name" content="URacquet Shop">
<meta property="og:title" content="{html.escape(p["title"])}">
<meta property="og:description" content="{html.escape(p["description"])}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{BASE}/img/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#20a048">
{GSC_META}
<link rel="icon" href="/img/favicon-32.png" sizes="32x32">
<link rel="icon" href="/img/icon-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
<link rel="preload" as="image" href="/img/{p["hero"].rsplit(".",1)[0]}-1600.webp">
<link rel="stylesheet" href="/style.css">
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/" aria-label="URacquet Shop home"><img src="/img/logo-mark@2x.png" width="44" height="44" alt=""><span>URACQUET<small>SHOP · PHILADELPHIA</small></span></a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav class="nav" id="nav" aria-label="Main"><ul>{nav}</ul></nav>
    <a class="ig" href="{BIZ["instagram"]}" rel="noopener" aria-label="URacquet Shop on Instagram" title="@uracquetshop"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></a>
    <a class="call header-call" href="tel:{BIZ["tel"]}">📞 {BIZ["phone"]}</a>
  </div>
</header>
<main id="main">
{hero}
{crumbs}
{p["body"]}
</main>
<footer class="site-footer">
  <div class="wrap">
    <div><h3>Visit</h3><p>{BIZ["street"]}<br>{BIZ["city"]}, {BIZ["state"]} {BIZ["zip"]}<br>West Philadelphia — one mile from Penn &amp; Drexel</p><p><a href="{BIZ["maps_dir"]}" rel="noopener">Get directions</a></p></div>
    <div><h3>Hours (typical)</h3><ul>{"".join(f"<li>{d[:3]}: {l}</li>" for d,l,_,_ in HOURS)}</ul><p><a href="{BIZ["maps_place"]}" rel="noopener">Today’s hours on Google →</a></p></div>
    <div><h3>Contact</h3><ul><li><a href="tel:{BIZ["tel"]}">{BIZ["phone"]}</a></li><li><a href="mailto:{BIZ["email"]}">{BIZ["email"]}</a></li><li><a href="{BIZ["instagram"]}" rel="noopener">Instagram @uracquetshop</a></li></ul></div>
    <div><h3>Pages</h3><ul><li><a href="/services/">Services &amp; prices</a></li><li><a href="/products/">Products</a></li><li><a href="/demo/">Demo program</a></li><li><a href="/about/">About Mark</a></li><li><a href="/local/">Tennis in Philadelphia</a></li><li><a href="/press/">Press</a></li></ul></div>
  </div>
  <div class="legal wrap">© 2026 URacquet Shop · Master Racquet Technician services · Philadelphia, PA</div>
</footer>
<div class="callbar" aria-label="Quick actions"><a class="c1" href="tel:{BIZ["tel"]}">Call the shop</a><a class="c2" href="{BIZ["maps_dir"]}" rel="noopener">Directions</a></div>
<script>
(function(){{var b=document.querySelector('.menu-btn'),n=document.getElementById('nav');if(!b)return;b.addEventListener('click',function(){{var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');}});}})();
</script>
</body>
</html>'''

# ---------- pages ----------
P = BIZ
services_faq = [
 ("How much does it cost to string a racquet?","$26.50 labor per racquet, plus the string you choose. Bring your own string and pay labor only."),
 ("How long does stringing take?","Turnaround depends on the queue — many racquets are ready the same or next day. Rush and appointment stringing are available on request; please call ahead."),
 ("Do I need an appointment?","No — drop-offs are welcome during shop hours. Call ahead for rush or appointment stringing."),
 ("What string should I use?","We talk it through before every job. We carry polyester and co-poly monofilaments, multifilaments, synthetic gut, natural gut, kevlar and zyex from Luxilon, Wilson, Babolat, Head, Tecnifibre, Solinco, Ashaway, Signum Pro, Gosen and MSV."),
 ("Do you string squash racquets?","Yes — we string tennis and squash racquets. Call ahead if you have a specific string in mind."),
]
demo_faq = [
 ("How much does the demo program cost?","$40 for three racquets for seven days. If you buy a racquet afterward, $35 of that comes back as a credit. A single racquet is $20 for seven days with a $15 credit."),
 ("Can I swap racquets during the week?","Yes — swap in person for a different demo any time during your seven-day period."),
 ("Which racquets can I demo?","Current models from Wilson, Head, Babolat, Tecnifibre, Dunlop and Diadem. Ask about specific models and grip sizes."),
]

PAGES = [
 dict(url="/", nav="Home", hero="wix_08.jpg",
  title="Racquet Stringing & Tennis Shop in West Philadelphia | URacquet Shop",
  description="Master Racquet Technician stringing, customization, racquet demos and tennis gear in West Philadelphia — one mile from Penn and Drexel. 4711 Pine St. Call (215) 586-3649.",
  h1="Master Racquet Stringing &amp; Tennis Shop in West Philadelphia",
  lead='<p class="lead">Strung by a USRSA Master Racquet Technician who strings for the ATP and WTA Tours, NCAA Division I programs and the University of Pennsylvania. One mile from Penn and Drexel.</p>',
  cta=f'<div class="btns"><a class="btn primary" href="tel:{P["tel"]}">Call {P["phone"]}</a><a class="btn ghost" href="{P["maps_dir"]}" rel="noopener">Get directions</a><a class="btn ghost" href="/services/">Services &amp; prices</a></div>',
  body=f'''
<section class="trust"><div class="wrap"><ul><li>USRSA Master Racquet Technician</li><li>Penn varsity's stringer since 2022</li><li>ATP 250 Winston-Salem Open</li><li>WTA 125 Philadelphia Open</li><li>Eddie Herr International</li></ul></div></section>
<section class="band"><div class="wrap prose">
<h2>Welcome to URacquet Shop</h2>
<p>Located in West Philadelphia, less than a mile from the University of Pennsylvania and Drexel University campuses, we are your destination for tennis and squash equipment and Master Racquet Technician stringing and customization in the Philadelphia area. Learn about <a href="/about/">our background</a>, the <a href="/services/">services we offer</a>, our <a href="/demo/">racquet demo program</a>, and our <a href="/products/">in-store products</a> for every level of play.</p>
</div></section>
<section class="band alt"><div class="wrap">
<h2>Services &amp; prices</h2>
<div class="grid">
 <div class="card"><h3>Stringing</h3><p class="price">$26.50 labor</p><p>Plus the string you choose — or bring your own. Strung by a Master Racquet Technician, every time. Rush and appointment stringing on request.</p><a href="/services/#stringing">Stringing details →</a></div>
 <div class="card"><h3>Customization</h3><p class="price">Quoted after measurement</p><p>Static weight, swing weight, twist weight and balance matched to your specs on digital equipment.</p><a href="/services/#customization">Customization details →</a></div>
 <div class="card"><h3>Grips &amp; grommets</h3><p class="price">From $5</p><p>Base grip $5 + grip · overgrip installed free with purchase · bumper guard and grommet replacement $15 labor + materials.</p><a href="/services/#grips">Grip &amp; grommet details →</a></div>
</div></div></section>
<section class="band"><div class="wrap split">
 <div><h2>Racquet demo program</h2><p>Don’t just take the advice of YouTubers, friends — or even us. Try racquets yourself: <strong>three racquets, seven days, $40</strong>, with a $35 credit toward the one you buy. Want to try just one racquet? No problem. Pay just $20 for a seven-day demo with a $15 credit toward your new racquet purchase. Start with a free in-shop consultation.</p><a class="btn green" href="/demo/">How the demo program works</a></div>
 {pic("wix_10.jpg")}
</div></section>
<section class="band alt"><div class="wrap split">
 {pic("wix_06.jpg")}
 <div><h2>Meet Mark Kuczynski</h2><p>Owner of URacquet Shop and USRSA-certified Master Racquet Technician. Mark has strung for the world’s top professionals on the ATP and WTA Tours, at international junior championships, and for leading NCAA Division I programs — and has been the University of Pennsylvania’s dedicated stringer since 2022.</p><a class="btn outline" href="/about/">About Mark</a> &nbsp; <a href="/press/">In the press →</a></div>
</div></section>
<section class="band"><div class="wrap">
<h2>In stock now</h2>
<div class="grid">
 <div class="card"><h3>Wilson Defyer</h3><p>98 Pro, 100 and 100L</p></div><div class="card"><h3>Head Extreme</h3><p>MP and Pro with Hy-bor technology</p></div><div class="card"><h3>Dunlop FX 500</h3><p>FX 500 and FX 500 Tour</p></div><div class="card"><h3>Babolat Pure Aero</h3><p>98, 100 and Team</p></div><div class="card"><h3>Wilson Blade V10</h3><p>98 and 100</p></div><div class="card"><h3>Tecnifibre Fire</h3><p>98 and 100</p></div><div class="card"><h3>Yonex Ezone</h3><p>98 and 100</p></div><div class="card"><h3>Diadem Axis</h3><p>98, 100 and Project Bublik</p></div>
</div>
<p class="note" style="margin-top:1em">Plus string from Luxilon, Solinco, Babolat, Tecnifibre, Head, Wilson, Gosen and more; shoes from K-Swiss, Wilson, Adidas and Asics. <a href="/products/">All products →</a></p>
<p style="margin-top:1em"><a class="btn outline" href="{P["instagram"]}" rel="noopener">New arrivals are posted on Instagram first — @uracquetshop</a></p>
</div></section>
<section class="band alt"><div class="wrap split">
 <div><h2>Visit the shop</h2><p><strong>{P["street"]}, {P["city"]}, {P["state"]} {P["zip"]}</strong><br>West Philadelphia — free, no-time-limit parking on Pine Street.</p><p class="note">Typical hours below — <a href="{P["maps_place"]}" rel="noopener">check Google Maps for today’s</a>, since they change when Mark is out on a pickup.</p>{HOURS_TABLE}<div class="btns"><a class="btn green" href="{P["maps_dir"]}" rel="noopener">Get directions</a><a class="btn outline" href="/visit/">Hours, parking &amp; contact</a></div></div>
 {pic("wix_14.jpg")}
</div></section>'''),

 dict(url="/services/", nav="Services", hero="wix_05.jpg",
  title="Tennis Racquet Stringing & Customization in Philadelphia — from $26.50 | URacquet Shop",
  description="USRSA Master Racquet Technician stringing ($26.50 labor), racquet customization, grip replacement, grommets and grip build-up in West Philadelphia. Rush service available. Prices listed.",
  h1="Tennis &amp; Squash Racquet Stringing and Customization in Philadelphia",
  lead='<p class="lead">Every racquet strung by USRSA Master Racquet Technician Mark Kuczynski, with the same attention he gives a professional at a major tournament. Prices below — no surprises.</p>',
  cta=f'<div class="btns"><a class="btn primary" href="tel:{P["tel"]}">Call {P["phone"]}</a><a class="btn ghost" href="#prices">See all prices</a></div>',
  schemas=[faq_schema(services_faq)],
  body=f'''
<section class="band"><div class="wrap prose">
<h2 id="stringing">Stringing</h2>
<p>At URacquet Shop, your racquet is strung by Mark Kuczynski, USRSA Certified Master Racquet Technician. A free in-person consultation is available at the shop. Every racquet gets the same attention to detail Mark gives a professional at a major tournament — a steady, consistent string bed every time you step on the court. Eliminate the “what ifs” that follow a racquet strung by a friend or neighbor: string with the professional who has become the go-to racquet stringer in Philadelphia.</p>
<ul class="price-list"><li><span>String installation labor</span><b>$26.50 per racquet</b></li><li><span>String</span><b>varies by selection</b></li><li><span>Bring your own string</span><b>labor only</b></li></ul>
<p class="note">Rush and appointment stringing are provided on an as-available basis at the shop’s discretion. Please call ahead to schedule rush requests before dropping off your racquet.</p>
<h2 id="customization">Customization</h2>
<p>Racquet customization alters a racquet’s existing specifications — static weight, swing weight, twist weight and balance — to a custom set requested by the player. Mark has years of experience matching and customizing racquets for the region’s most skilled and advanced players. Because every project is different, an exact price is quoted after the racquet’s current specifications are measured; contact the shop with a description of your project for a rough estimate. We use modern digital equipment for every customization.</p>
<figure class="figure">{pic("wix_13.jpg")}<figcaption>Measuring racquet twist weight before a customization.</figcaption></figure>
<h2 id="grips">Grip replacement</h2>
<p>A fresh grip is one of the most important — and most neglected — ways to prevent arm injury. A slippery, deteriorated grip makes your hand work harder to hold the racquet, building tension up the kinetic chain into your wrist and elbow. We install base grips professionally, and we’ll install your overgrip while teaching you how to do it yourself.</p>
<ul class="price-list"><li><span>Replacement base grip installation</span><b>$5 + grip</b></li><li><span>Overgrip installation</span><b>free + grip</b></li></ul>
<h2 id="grommets">Bumper guard and grommet replacement</h2>
<p>Over time a racquet’s bumper guard and grommets deteriorate, which can cause premature string breakage and irreparable damage to the graphite beam. We replace bumper guards and grommets professionally to protect your biggest tennis investment.</p>
<ul class="price-list"><li><span>Labor</span><b>$15</b></li><li><span>Materials, current-generation models</span><b>$15</b></li><li><span>Materials, prior-generation models</span><b>call for estimate</b></li></ul>
<h2 id="grip-size">Grip size build-up and alterations</h2>
<p>A racquet handle can be built up to a more comfortable grip size — most commonly with a heat-shrink sleeve under the base grip, or with specialty base grips that add width. Grip size can also be decreased with thinner base grips; shaving the plastic pallet is possible but costly and only worth attempting when a thinner grip isn’t acceptable. The last option — removing and replacing the pallet — isn’t possible on every model. Call the shop to discuss the best option for your racquet.</p>
<ul class="price-list"><li><span>Grip build-up with heat-shrink sleeve (sleeve and labor)</span><b>$15*</b></li><li><span>Base grip replacement</span><b>see above</b></li><li><span>Pallet alteration, removal and replacement</span><b>call the shop</b></li></ul>
<p class="note">*When a heat-shrink sleeve increases the grip size, the current base grip may no longer fit — expect to purchase a new base grip with this option.</p>
<h2 id="prices">All prices at a glance</h2>
<table><thead><tr><th>Service</th><th>Price</th></tr></thead><tbody>
<tr><td>String installation labor</td><td>$26.50 / racquet (+ string)</td></tr><tr><td>Customization</td><td>quoted after measurement</td></tr><tr><td>Base grip installation</td><td>$5 + grip</td></tr><tr><td>Overgrip installation</td><td>free + grip</td></tr><tr><td>Bumper guard &amp; grommets</td><td>$15 labor + $15 materials (current models)</td></tr><tr><td>Grip build-up (heat-shrink)</td><td>$15</td></tr><tr><td>Demo program</td><td>$40 / 3 racquets / 7 days</td></tr></tbody></table>
<h2>Frequently asked</h2>{faq_html(services_faq)}
<p style="margin-top:1.5em"><a class="btn green" href="tel:{P["tel"]}">Call {P["phone"]}</a> &nbsp; <a class="btn outline" href="/visit/">Hours &amp; directions</a></p>
</div></section>'''),

 dict(url="/products/", nav="Products", hero="wix_14.jpg",
  title="Tennis & Squash Racquets, String, Shoes & Accessories — West Philadelphia | URacquet Shop",
  description="Wilson, Head, Babolat, Tecnifibre, Dunlop, Diadem and Yonex racquets; Luxilon, Solinco, Gosen and more string; tennis shoes from K-Swiss, Wilson, Adidas and Asics; grips, dampeners and balls — in stock at 4711 Pine St.",
  h1="Tennis &amp; Squash Racquets, String, Shoes &amp; Accessories",
  lead='<p class="lead">The latest racquets from Wilson, Head, Babolat, Tecnifibre, Dunlop, Diadem and Yonex; every type of string from the brands used on tour; shoes and accessories — chosen by people who play.</p>',
  body=f'''
<section class="band"><div class="wrap prose">
<p>Our knowledgeable staff aren’t just passionate about tennis — we’re experienced players ourselves. We use our years of experience with players from the professional circuit, advanced juniors, club players and beginners to help you find the equipment that lets you play your best and enjoy the game.</p>
<h2>Racquets</h2>
<p>We carry the latest generation of racquets from <strong>Wilson, Head, Babolat, Tecnifibre, Dunlop, Diadem and Yonex</strong>. Our <a href="/demo/">racquet demo program</a> makes upgrading easy and helps new players choose the racquet that suits them. Looking for a specific model and grip size? Call to confirm availability.</p>
<figure class="figure">{pic("wix_07.jpg")}</figure>
<h2>String</h2>
<p>Stringing is our specialty. Your racquet is strung exclusively by certified Master Racquet Technician Mark Kuczynski, with experience on the ATP Tour. Before every job, we talk through the string that suits your swing and style of play. We carry every type of string — monofilament polyester and co-polymer, multifilament, synthetic, natural gut, and specialty strings such as kevlar and zyex — from the brands used on tour:</p>
<ul class="brands"><li>Luxilon</li><li>Wilson</li><li>Babolat</li><li>Head</li><li>Tecnifibre</li><li>Solinco</li><li>Ashaway</li><li>Signum Pro</li><li>Gosen</li><li>MSV</li></ul>
<p>You can also bring your own string and pay only the <a href="/services/#stringing">installation labor fee</a>.</p>
<figure class="figure">{pic("wix_05.jpg")}</figure>
<h2>Accessories and shoes</h2>
<p>Keep your racquet in top condition with our base grips, overgrips and dampeners. Caps, visors and wristbands for all weather conditions. Premium and championship tennis balls from Wilson, Dunlop, Tecnifibre and Diadem. And try on the latest tennis shoes from <strong>K-Swiss, Wilson, Adidas and Asics</strong>.</p>
<figure class="figure">{pic("wix_11.jpg")}</figure>
<h2>In stock now</h2>
<div class="grid"><div class="card"><h3>Wilson Defyer</h3><p>98 Pro, 100 and 100L</p></div><div class="card"><h3>Head Extreme</h3><p>MP and Pro with Hy-bor technology</p></div><div class="card"><h3>Dunlop FX 500</h3><p>FX 500 and FX 500 Tour</p></div><div class="card"><h3>Babolat Pure Aero</h3><p>98, 100 and Team</p></div><div class="card"><h3>Wilson Blade V10</h3><p>98 and 100</p></div><div class="card"><h3>Tecnifibre Fire</h3><p>98 and 100</p></div><div class="card"><h3>Yonex Ezone</h3><p>98 and 100</p></div><div class="card"><h3>Diadem Axis</h3><p>98, 100 and Project Bublik</p></div></div>
<p style="margin-top:1.2em"><a class="btn outline" href="{P["instagram"]}" rel="noopener">See what just came in — @uracquetshop on Instagram</a></p>
</div></section>'''),

 dict(url="/demo/", nav="Demo", hero="wix_12.jpg",
  title="Racquet Demo Program in Philadelphia — Try 3 Racquets for 7 Days | URacquet Shop",
  description="Demo three tennis or squash racquets for seven days for $40, with a $35 credit toward your purchase. Free in-shop consultation at URacquet Shop, West Philadelphia.",
  h1="Racquet Demo Program — Try 3 Racquets for 7 Days",
  lead='<p class="lead">Many players prefer to test a racquet before buying. Start with a free in-shop consultation; take three racquets home for a week.</p>',
  schemas=[faq_schema(demo_faq)],
  body=f'''
<section class="band"><div class="wrap prose">
<h2>How it works</h2>
<p>Our racquet experts walk you through the options based on your swing speed, skill level, style of play and experience. Then:</p>
<ol><li>After your free consultation, pay <strong>$40</strong> to take <strong>three demo racquets</strong> home for <strong>7 days</strong>.</li>
<li>Want to try more than three during your week? Swap a racquet in person for a different demo — during your demo period only.</li>
<li>When the 7 days end and all racquets are returned, choose one of three options:
 <ul><li><strong>Ready to buy:</strong> receive a <strong>$35 credit</strong> toward your new racquet.</li>
 <li><strong>Keep demoing:</strong> pay another $40 for a second 7-day period. If you buy after two periods, a single $35 credit applies. Demos are limited to 14 consecutive days (two periods).</li>
 <li><strong>Not buying yet:</strong> your demo account closes; the $35 credit stays available on a new racquet purchase for <strong>60 days</strong>.</li></ul></li></ol>
<p>Just want to try one racquet? Pay just $20 for a seven-day demo with a $15 credit toward your new racquet purchase.</p>
<h2>Other things to know</h2>
<ul><li>Racquets not returned after 7 days incur a late fee of <strong>$8 plus tax per day</strong>.</li><li>Racquets not returned after 10 days are charged at full retail — typically <strong>$250–305 per racquet</strong>.</li></ul>
<h2>Get the most out of your demo</h2>
<p>Plan specific court time before you pick up demos — account for weather, vacations and court availability. We don’t recommend playing serious matches with demo racquets; the best test is a hitting session with a coach or a more experienced partner, where you can evaluate in a more controlled hitting environment. Can’t decide? Ask your coach or hitting partner for feedback first, then come back for a consultation.</p>
<figure class="figure">{pic("wix_10.jpg")}<figcaption>Trying a demo racquet in the shop.</figcaption></figure>
<h2>Frequently asked</h2>{faq_html(demo_faq)}
<p style="margin-top:1.5em"><a class="btn green" href="tel:{P["tel"]}">Call to book a consultation</a></p>
</div></section>'''),

 dict(url="/about/", nav="About", hero="wix_02.jpeg",
  title="Mark Kuczynski, USRSA Master Racquet Technician — Penn's Stringer | URacquet Shop",
  description="Meet Mark Kuczynski: USRSA Master Racquet Technician, stringer for the ATP and WTA Tours, Eddie Herr, NCAA Division I programs, and the University of Pennsylvania since 2022. Owner of URacquet Shop, West Philadelphia.",
  h1="Mark Kuczynski, USRSA Master Racquet Technician",
  lead='<p class="lead">Owner of URacquet Shop. Stringer to tour professionals, international juniors, NCAA Division I programs — and the University of Pennsylvania since 2022.</p>',
  body=f'''
<section class="band"><div class="wrap prose">
<p>URacquet Shop owner Mark Kuczynski, a United States Racquet Stringing Association (USRSA) Master Racquet Technician, brings extensive experience stringing at the highest levels of tennis. As a multi-year member of the ATP 250 Winston-Salem Open stringing team, he coordinated racquet logistics and delivered precision stringing for the world’s top-ranked professionals. His tournament experience includes the 2023 and 2024 stringing teams at the Eddie Herr International Junior Championships at IMG Academy, where he strung for leading juniors and for multiple top-50 professionals conducting training blocks at IMG.</p>
<p>Based in Philadelphia, Mark has been the dedicated full-time stringer for the University of Pennsylvania’s varsity tennis programs since 2022, and has worked for numerous NCAA and Ivy League programs including Wake Forest, Ohio State, the University of Georgia, Princeton, Harvard and Columbia. He has been the primary stringer and team leader for multiple ITA Northeast Regional Championships and for the ECAC Championships three years running. His commitment to professional service is underscored by training from multiple Master Racquet Technicians and Grand Slam–experienced stringers.</p>
<figure class="figure">{pic("wix_06.jpg")}</figure>
<p>In March 2026, Mark opened URacquet Shop in West Philadelphia, blocks from the University of Pennsylvania and Drexel University, to give Philadelphia’s club players and NCAA athletes alike access to Master Racquet Technician services — and the chance to pick his brain on the latest racquet and string technology.</p>
<p>When not in the shop or on court, Mark is at home with his wife and their cats.</p>
<h2>Credentials</h2>
<ul><li>USRSA Master Racquet Technician</li><li>University of Pennsylvania varsity tennis — full-time stringer since 2022</li><li>WTA 125 Philadelphia Open (2026) — team leader, manager and head stringer</li><li>ATP 250 Winston-Salem Open — multi-year stringing team member</li><li>Eddie Herr International Junior Championships, IMG Academy — 2023, 2024</li><li>ITA Northeast Regional Championships; ECAC Championships (three years) — primary stringer and team lead</li><li>NCAA and Ivy League programs served: Wake Forest, Ohio State, Georgia, Princeton, Harvard, Columbia</li></ul>
<figure class="figure">{pic("wix_13.jpg")}<figcaption>Measuring racquet twist weight before a customization.</figcaption></figure>
<p><a class="btn outline" href="/press/">Read the press →</a></p>
</div></section>'''),

 dict(url="/visit/", nav="Visit", hero="wix_14.jpg",
  title="Visit URacquet Shop — 4711 Pine St, West Philadelphia — Hours & Parking",
  description="URacquet Shop, 4711 Pine Street, Philadelphia, PA 19143. Hours, free parking on Pine Street, directions from Penn and Drexel, phone (215) 586-3649.",
  h1="Visit URacquet Shop — 4711 Pine St, West Philadelphia",
  lead=f'<p class="lead">{P["street"]}, {P["city"]}, {P["state"]} {P["zip"]} · one mile from the University of Pennsylvania and Drexel University.</p>',
  cta=f'<div class="btns"><a class="btn primary" href="{P["maps_dir"]}" rel="noopener">Get directions</a><a class="btn ghost" href="tel:{P["tel"]}">Call {P["phone"]}</a></div>',
  body=f'''
<section class="band"><div class="wrap split">
<div><h2>Hours</h2><p><a class="btn green" href="{P["maps_place"]}" rel="noopener">Today’s hours on Google Maps</a></p><p class="note">Hours change when Mark is out on a pickup or drop-off — <strong>Google always has today’s hours.</strong> Typical schedule:</p>{HOURS_TABLE}
<h2>Contact</h2><ul><li>Phone: <a href="tel:{P["tel"]}">{P["phone"]}</a></li><li>Email: <a href="mailto:{P["email"]}">{P["email"]}</a></li><li>Instagram: <a href="{P["instagram"]}" rel="noopener">@uracquetshop</a></li></ul></div>
<div><iframe class="map" src="{P["maps_embed"]}" title="Map: URacquet Shop, 4711 Pine Street, Philadelphia" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>
</div></section>
<section class="band alt"><div class="wrap prose">
<h2>Parking</h2>
<p>Ample free, no-time-limit parking is available on Pine Street. Two-hour free parking is available on the surrounding streets — 47th St, Osage Ave, Spruce St and 48th St. Please check the posted signs where you park; URacquet Shop is not responsible for parking violations received during your visit.</p>
<h2>Getting here from campus</h2>
<p>We’re about a mile from Penn and Drexel — a 15-minute walk or a short bike ride. SEPTA trolley and Market–Frankford Line stops are within walking distance of the shop.</p>
</div></section>'''),

 dict(url="/local/", nav="Tennis in Philadelphia", hero="wix_04.jpg",
  title="Tennis in Philadelphia: Leagues, Courts & Events | URacquet Shop",
  description="Where to play and watch tennis in Philadelphia — Penn varsity at Penn Tennis Center, USTA and Tennis Philly Flex leagues, pro events, and public courts near University City. From URacquet Shop.",
  h1="Tennis in Philadelphia: Leagues, Courts &amp; Events",
  lead='<p class="lead">Where to play, where to watch, and how to get into a league — the local tennis resource from the shop on Pine Street.</p>',
  body=f'''
<section class="band"><div class="wrap prose">
<h2>Varsity tennis</h2>
<p>Watch NCAA Division I tennis at Penn Tennis Center in Penn Park, University of Pennsylvania — home of the Quakers, whose racquets are strung at URacquet Shop.</p>
<h2>Professional tournaments</h2>
<p>Stay up to date with the ATP and WTA Tours — and Philadelphia’s own WTA 125 event, where Mark ran the stringing operation in 2026. <a href="/press/">Read about it →</a></p>
<h2>USTA &amp; Flex leagues</h2>
<p>Recreational league tennis for every level — USTA Middle States leagues and Tennis Philly Flex Leagues. Achieve your competitive goals and make friends for life.</p>
<figure class="figure">{pic("wix_12.jpg")}<figcaption>Penn Tennis Center, Penn Park.</figcaption></figure>
<h2>Need a racquet strung before your match?</h2>
<p><a href="/services/">Stringing is $26.50 labor</a>; rush service is available on request. <a href="tel:{P["tel"]}">Call the shop</a>.</p>
</div></section>'''),

 dict(url="/press/", nav="Press", hero="wix_03.jpg",
  title="In the Press — Mark Kuczynski & URacquet Shop",
  description="Court Theory's profile of URacquet Shop's Mark Kuczynski, stringer for the inaugural WTA 125 Philadelphia Open, plus tour and collegiate stringing credits.",
  h1="In the Press",
  lead='<p class="lead">Coverage of Mark’s stringing work on tour and in Philadelphia.</p>',
  body=f'''
<section class="band"><div class="wrap prose">
<h2>Court Theory — “Thank The Stringer”</h2>
<p><em>Court Theory, September 2026 · by Allen McDuffee.</em> A profile of Mark’s stringing operation at the inaugural WTA 125 Ennoble Care Philadelphia Open — a trophy ceremony that acknowledged the work of the stringer, and Mark’s observations on stringing for the top players in the world.</p>
<p><a class="btn outline" href="{P["press_url"]}" rel="noopener">Read the article at Court Theory →</a></p>
<h2>Professional summary</h2>
<ul><li>WTA 125 Philadelphia Open (2026) — team leader, manager and head stringer</li><li>ATP 250 Winston-Salem Open — stringing team (multi-year)</li><li>Eddie Herr International Junior Championships — 2023, 2024</li><li>University of Pennsylvania varsity tennis — stringer since 2022</li><li>ITA Northeast Regional Championships · ECAC Championships</li></ul>
<figure class="figure">{pic("wix_02.jpeg")}</figure>
</div></section>'''),
]

_EXT_A = re.compile(r'<a\b([^>]*?)href="(https?://[^"]+)"([^>]*)>', re.I)
def externalize(text):
    """Links that leave uracquet.com open in a new tab (Mark, 9/21); same-site links stay in the tab."""
    def fix(m):
        pre, href, post = m.group(1), m.group(2), m.group(3)
        host = urlparse(href).netloc.lower()
        if host == "uracquet.com" or host.endswith(".uracquet.com") or "target=" in (pre + post):
            return m.group(0)
        tag = f'<a{pre}href="{href}"{post}'
        if "rel=" not in tag: tag += ' rel="noopener"'
        return tag + ' target="_blank">'
    return _EXT_A.sub(fix, text)

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".html":
        text = externalize(text)
    if PREFIX and path.suffix == ".html":
        text = text.replace('href="/', f'href="{PREFIX}/').replace('src="/', f'src="{PREFIX}/').replace('srcset="/', f'srcset="{PREFIX}/').replace(', /img/', f', {PREFIX}/img/')
    path.write_text(text, encoding="utf-8")

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    build_images()
    shutil.copy(ROOT/"templates"/"style.css", OUT/"style.css")
    for p in PAGES:
        rel = "index.html" if p["url"]=="/" else p["url"].strip("/")+"/index.html"
        write(OUT/rel, layout(p))
    # 404
    write(OUT/"404.html", layout(dict(url="/404.html", nav="Not found", hero="wix_14.jpg", title="Page not found | URacquet Shop",
        description="That page doesn't exist. Find stringing, products, the demo program and directions at URacquet Shop.", h1="Page not found",
        lead='<p class="lead">That page doesn’t exist — try the menu, or call the shop.</p>',
        body='<section class="band"><div class="wrap prose"><p><a class="btn green" href="/">Back to the home page</a></p></div></section>')))
    urls = [p["url"] for p in PAGES]
    write(OUT/"sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"  <url><loc>{BASE}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(OUT/"robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    write(OUT/".nojekyll", "")
    host = urlparse(BASE).netloc
    if host.endswith("uracquet.com"):  # custom-domain build: GitHub Pages CNAME file
        write(OUT/"CNAME", host + "\n")
    for g in ROOT.glob("google*.html"):  # Search Console HTML-file verification, persisted at project root
        shutil.copy(g, OUT/g.name)
    kf = ROOT/"indexnow-key.txt"
    if kf.exists():
        k = kf.read_text().strip(); write(OUT/f"{k}.txt", k)  # GitHub Pages: skip Jekyll so _headers etc. are served as-is
    write(OUT/"_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/img/*\n  Cache-Control: public, max-age=31536000, immutable\n")
    # AWS Amplify Hosting reads customHttp.yml from the artifact root (same headers as _headers)
    write(OUT/"customHttp.yml", "customHeaders:\n  - pattern: '**/*'\n    headers:\n      - key: X-Content-Type-Options\n        value: nosniff\n      - key: Referrer-Policy\n        value: strict-origin-when-cross-origin\n  - pattern: '/img/*'\n    headers:\n      - key: Cache-Control\n        value: public, max-age=31536000, immutable\n")
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"built {len(PAGES)} pages → {OUT} ({total/1e6:.1f} MB incl. images); BASE_URL={BASE}")

if __name__ == "__main__":
    main()
