"""
ui.py
-----
Shared look-and-feel for KWARKO:
  * the custom CSS (colors, cards, buttons, typography)
  * small HTML building blocks (listing cards, badges, stars, banners, footer)
  * navigation helpers (go to another page, flash messages)

Every page imports this file so the whole website looks consistent.
"""

import base64
import html
import io
from datetime import datetime

import streamlit as st
from PIL import Image

from database import BASE_DIR

# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------
NAVY = "#0B2447"
ORANGE = "#F28C28"

# ---------------------------------------------------------------------------
# Custom CSS - replaces the default Streamlit look
# ---------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
:root{--navy:#0B2447;--navy2:#19376D;--orange:#F28C28;--orange-d:#D9741A;--soft-blue:#E8F0FB;
--muted-orange:#FDEEDC;--bg:#F6F8FB;--text:#1B2639;--muted:#64748B;--line:#E3E9F2;}
html, body, .stApp{font-family:'Poppins','Segoe UI',system-ui,sans-serif;color:var(--text);}
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp h5, .stApp button p, [data-baseweb="tab"] p{font-family:'Poppins','Segoe UI',system-ui,sans-serif;}
[data-testid="stIconMaterial"]{font-family:'Material Symbols Rounded' !important;}
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarCollapsedControl"], [data-testid="stHeaderActionElements"],
.stMarkdown h1 > a, .stMarkdown h2 > a, .stMarkdown h3 > a, .stMarkdown h4 > a{display:none !important;}
.block-container{padding-top:1rem !important;padding-bottom:0 !important;max-width:1240px;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4{color:var(--navy);letter-spacing:-.01em;}
/* ---------- buttons ---------- */
.stButton > button, .stFormSubmitButton > button{width:100%;border-radius:10px;font-weight:600;
padding:.5rem 1rem;transition:all .18s ease;}
.stButton > button p, .stFormSubmitButton > button p{font-weight:600;}
button[kind="primary"], button[kind="primaryFormSubmit"], [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--orange) !important;border:1px solid var(--orange) !important;color:#fff !important;}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover, [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:var(--orange-d) !important;border-color:var(--orange-d) !important;
transform:translateY(-1px);box-shadow:0 6px 16px rgba(242,140,40,.28);}
button[kind="secondary"], button[kind="secondaryFormSubmit"], [data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryFormSubmit"]{background:#fff;border:1px solid #D5DEEA;color:var(--navy);}
button[kind="secondary"]:hover, button[kind="secondaryFormSubmit"]:hover, [data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover{border-color:var(--navy);color:var(--navy);background:var(--soft-blue);}
/* navigation bar buttons look like links */
[class*="st-key-nav_"] button{background:transparent !important;border:none !important;box-shadow:none !important;color:var(--navy) !important;}
[class*="st-key-nav_"] button:hover{background:var(--soft-blue) !important;transform:none;}
[class*="st-key-nav_"] button[kind="primary"], [class*="st-key-nav_"] [data-testid="stBaseButton-primary"]{background:var(--muted-orange) !important;color:var(--orange-d) !important;}
[class*="st-key-nav_signup"] button{background:var(--navy) !important;color:#fff !important;}
[class*="st-key-nav_signup"] button:hover{background:var(--navy2) !important;}
/* ---------- inputs ---------- */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-baseweb="base-input"]{border-radius:10px !important;}
[data-testid="stWidgetLabel"] p{font-weight:600;color:var(--navy);font-size:.88rem;}
/* ---------- tabs and pill menus ---------- */
.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{padding:10px 16px;border-radius:10px 10px 0 0;}
.stTabs [data-baseweb="tab"] p{font-weight:600;}
[class*="st-key-menu_"] [role="radiogroup"]{gap:8px;flex-wrap:wrap;}
[class*="st-key-menu_"] [role="radiogroup"] > label{background:#fff;border:1px solid var(--line);border-radius:999px;
padding:8px 18px;margin:0;transition:all .18s;}
[class*="st-key-menu_"] [role="radiogroup"] > label:hover{border-color:var(--navy);}
[class*="st-key-menu_"] [role="radiogroup"] > label > div:first-child{display:none;}
[class*="st-key-menu_"] [role="radiogroup"] > label:has(input:checked){background:var(--navy);border-color:var(--navy);}
[class*="st-key-menu_"] [role="radiogroup"] > label:has(input:checked) p{color:#fff;}
[class*="st-key-menu_"] [role="radiogroup"] p{font-weight:600;font-size:.9rem;}
/* ---------- bordered containers ---------- */
[data-testid="stExpander"] details{border-radius:12px;border-color:var(--line);}
/* ---------- KWARKO components ---------- */
.k-brand{display:flex;align-items:center;gap:10px;}
.k-brand img{width:42px;height:42px;border-radius:11px;}
.k-brand .t{font-weight:800;font-size:1.45rem;color:var(--navy);letter-spacing:.04em;line-height:1;}
.k-brand .s{font-size:.7rem;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;}
.k-hero{position:relative;overflow:hidden;border-radius:24px;padding:64px 56px 64px;margin-top:6px;
background:radial-gradient(circle at 85% 20%,rgba(242,140,40,.35),transparent 40%),linear-gradient(135deg,#0B2447 0%,#19376D 60%,#2B5A9E 100%);color:#fff;}
.k-hero h1{color:#fff !important;font-size:3.1rem;font-weight:800;line-height:1.1;margin:0 0 14px;}
.k-hero h1 span{color:var(--orange);}
.k-hero p{color:#DCE6F5;font-size:1.12rem;max-width:620px;margin:0;}
.k-hero .pill{display:inline-block;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);color:#fff;
padding:6px 14px;border-radius:999px;font-size:.8rem;margin-bottom:18px;}
.k-hero .shape{position:absolute;right:-60px;bottom:-80px;width:340px;height:340px;border-radius:50%;
background:rgba(255,255,255,.06);}
.k-searchwrap{margin-top:-62px;position:relative;z-index:5;}
.k-search-title{font-weight:700;color:var(--navy);font-size:1rem;margin-bottom:2px;}
.k-section{margin:46px 0 18px;}
.k-section .eyebrow{color:var(--orange);font-weight:700;font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;}
.k-section h2{margin:4px 0 6px !important;font-size:1.85rem;font-weight:800;padding:0 !important;}
.k-section p{color:var(--muted);margin:0;}
.k-card{background:#fff;border-radius:14px;overflow:hidden;}
.k-card .img{position:relative;height:190px;overflow:hidden;border-radius:12px;}
.k-card .img img{width:100%;height:100%;object-fit:cover;transition:transform .4s ease;}
.k-card:hover .img img{transform:scale(1.05);}
.k-card .img .badge-pos{position:absolute;top:12px;left:12px;}
.k-card .img .price-tag{position:absolute;bottom:12px;right:12px;background:#fff;color:var(--navy);font-weight:800;
padding:6px 12px;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,.15);font-size:1rem;}
.k-card .img .price-tag small{font-weight:500;color:var(--muted);font-size:.72rem;}
.k-card .body{padding:12px 2px 4px;}
.k-card .top{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;}
.k-card h4{margin:0 !important;padding:0 !important;font-size:1.04rem;font-weight:700;color:var(--navy);line-height:1.3;}
.k-loc{color:var(--muted);font-size:.84rem;margin:4px 0 8px;display:flex;align-items:center;gap:4px;}
.k-desc{color:#475569;font-size:.85rem;margin:8px 0 0;line-height:1.45;min-height:2.5em;}
.k-rating{display:inline-flex;align-items:center;gap:3px;background:var(--muted-orange);color:#B45C0E;font-weight:700;
font-size:.82rem;padding:3px 8px;border-radius:8px;white-space:nowrap;}
.k-rating.none{background:#F1F5F9;color:var(--muted);font-weight:600;}
.k-rating small{font-weight:500;color:#9a6a3c;}
.k-chips{display:flex;flex-wrap:wrap;gap:6px;}
.k-chip{background:var(--soft-blue);color:var(--navy2);font-size:.74rem;font-weight:600;padding:4px 10px;border-radius:999px;
display:inline-flex;align-items:center;gap:4px;}
.k-chip.light{background:#F3F5F8;color:#475569;font-weight:500;}
.k-meta{display:flex;gap:14px;color:#475569;font-size:.8rem;margin-top:8px;flex-wrap:wrap;}
.k-meta span{display:inline-flex;align-items:center;gap:4px;}
.k-badge{display:inline-flex;align-items:center;gap:4px;font-size:.74rem;font-weight:700;padding:4px 10px;border-radius:999px;}
.k-badge.success{background:#E3F7EC;color:#157A45;}
.k-badge.danger{background:#FDE7E7;color:#B42318;}
.k-badge.warning{background:#FEF3D7;color:#9A6B00;}
.k-badge.info{background:#E3EEFD;color:#1D4E9E;}
.k-badge.orange{background:var(--muted-orange);color:#B45C0E;}
.k-badge.neutral{background:#EEF1F5;color:#475569;}
.k-stars{color:var(--orange);letter-spacing:1px;}
.k-stars .off{color:#D9DEE7;}
.k-banner{background:linear-gradient(135deg,#0B2447,#19376D);border-radius:20px;padding:30px 36px;color:#fff;margin:6px 0 22px;
position:relative;overflow:hidden;}
.k-banner:after{content:"";position:absolute;right:-40px;top:-60px;width:220px;height:220px;border-radius:50%;background:rgba(242,140,40,.25);}
.k-banner h1{color:#fff !important;font-size:2rem;font-weight:800;margin:0 !important;padding:0 !important;}
.k-banner p{color:#D3DEEE;margin:6px 0 0;}
.k-stat{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px 20px;display:flex;gap:14px;align-items:center;}
.k-stat .ic{width:46px;height:46px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:var(--soft-blue);color:var(--navy);}
.k-stat .ic.o{background:var(--muted-orange);color:var(--orange-d);}
.k-stat .v{font-size:1.6rem;font-weight:800;color:var(--navy);line-height:1;}
.k-stat .l{color:var(--muted);font-size:.82rem;margin-top:4px;}
.k-loc-tile{border-radius:16px;padding:22px;color:#fff;min-height:132px;display:flex;flex-direction:column;justify-content:flex-end;
transition:transform .2s, box-shadow .2s;}
.k-loc-tile:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(11,36,71,.18);}
.k-loc-tile .c{font-size:1.25rem;font-weight:800;}
.k-loc-tile .n{font-size:.85rem;opacity:.9;}
.k-step{background:#fff;border:1px solid var(--line);border-radius:18px;padding:26px;height:100%;}
.k-step .num{width:44px;height:44px;border-radius:12px;background:var(--navy);color:#fff;display:flex;align-items:center;
justify-content:center;font-weight:800;margin-bottom:14px;}
.k-step h4{margin:0 0 6px !important;padding:0 !important;color:var(--navy);font-weight:700;}
.k-step p{color:var(--muted);font-size:.9rem;margin:0;}
.k-cta{background:linear-gradient(120deg,#FDEEDC,#FFF7EE);border:1px solid #F8D9B5;border-radius:20px;padding:28px 32px;}
.k-cta h3{margin:0 0 6px !important;padding:0 !important;font-weight:800;}
.k-cta p{color:#6B5A48;margin:0;}
.k-gallery{display:grid;grid-template-columns:2fr 1fr;grid-template-rows:200px 200px;gap:10px;border-radius:20px;overflow:hidden;}
.k-gallery img{width:100%;height:100%;object-fit:cover;display:block;}
.k-gallery .main{grid-row:1 / span 2;}
.k-gallery.single{grid-template-columns:1fr;}
.k-title h1{font-size:2.1rem;font-weight:800;margin:0 !important;padding:0 !important;}
.k-room{border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:10px;background:#fff;
display:flex;justify-content:space-between;gap:16px;align-items:center;}
.k-room h5{margin:0 0 4px !important;padding:0 !important;font-weight:700;color:var(--navy);font-size:1rem;}
.k-room .price{font-weight:800;color:var(--navy);font-size:1.15rem;text-align:right;white-space:nowrap;}
.k-room .price small{font-weight:500;color:var(--muted);font-size:.75rem;}
.k-list{margin:0;padding-left:0;list-style:none;}
.k-list li{padding:6px 0;color:#334155;display:flex;gap:8px;align-items:flex-start;font-size:.92rem;}
.k-list li svg{flex-shrink:0;margin-top:3px;color:#16A34A;}
.k-pricebox .from{color:var(--muted);font-size:.85rem;}
.k-pricebox .amt{font-size:2rem;font-weight:800;color:var(--navy);line-height:1.1;}
.k-pricebox .amt small{font-size:.9rem;font-weight:500;color:var(--muted);}
.k-contact{display:flex;align-items:center;gap:12px;}
.k-avatar{width:46px;height:46px;border-radius:50%;background:var(--navy);color:#fff;display:flex;align-items:center;
justify-content:center;font-weight:700;flex-shrink:0;}
.k-review{border-bottom:1px solid var(--line);padding:14px 0;}
.k-review .who{display:flex;gap:10px;align-items:center;}
.k-review .who .k-avatar{width:36px;height:36px;font-size:.8rem;background:var(--soft-blue);color:var(--navy);}
.k-review p{margin:8px 0 0;color:#334155;font-size:.92rem;}
.k-bar{display:flex;align-items:center;gap:10px;font-size:.85rem;color:#334155;margin:6px 0;}
.k-bar .track{flex:1;height:7px;background:#EEF1F5;border-radius:99px;overflow:hidden;}
.k-bar .fill{height:100%;background:var(--navy);border-radius:99px;}
.k-bigrating{font-size:2.6rem;font-weight:800;color:var(--navy);line-height:1;}
.k-item-title{font-weight:700;color:var(--navy);font-size:1.02rem;}
.k-muted{color:var(--muted);font-size:.85rem;}
.k-bubble{background:#F3F6FB;border-radius:12px;padding:12px 14px;margin-top:8px;color:#334155;font-size:.92rem;}
.k-bubble.reply{background:#FFF4E8;border-left:3px solid var(--orange);}
.k-bubble b{color:var(--navy);}
.k-empty{text-align:center;padding:40px 20px;border:2px dashed var(--line);border-radius:18px;color:var(--muted);}
.k-empty h4{color:var(--navy);margin-bottom:6px !important;}
.k-flash{border-radius:12px;padding:12px 16px;margin:4px 0 12px;font-weight:500;display:flex;gap:10px;align-items:center;}
.k-flash.success{background:#E3F7EC;color:#157A45;border:1px solid #BFE8D0;}
.k-flash.info{background:#E3EEFD;color:#1D4E9E;border:1px solid #C5D9F6;}
.k-flash.error{background:#FDE7E7;color:#B42318;border:1px solid #F6C9C9;}
.k-flash.warning{background:#FEF3D7;color:#9A6B00;border:1px solid #F5DFA0;}
.k-thumb{width:100%;height:120px;object-fit:cover;border-radius:12px;display:block;}
.k-ph{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#E8F0FB,#FDEEDC);color:var(--navy2);
width:100%;height:100%;min-height:120px;}
.k-footer{margin-top:64px;background:var(--navy);color:#C9D5E6;border-radius:24px 24px 0 0;padding:40px 44px 24px;}
.k-footer .cols{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:28px;}
.k-footer h5{color:#fff !important;margin:0 0 10px !important;padding:0 !important;font-weight:700;font-size:.95rem;}
.k-footer p, .k-footer li{color:#C9D5E6;font-size:.85rem;margin:0 0 6px;list-style:none;}
.k-footer ul{padding:0;margin:0;}
.k-footer .bottom{border-top:1px solid rgba(255,255,255,.12);margin-top:26px;padding-top:16px;font-size:.78rem;color:#93A4BD;
display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}
.k-auth-head{text-align:center;margin:18px 0 18px;}
.k-auth-head img{width:64px;height:64px;border-radius:16px;}
.k-auth-head h2{margin:10px 0 4px !important;padding:0 !important;font-weight:800;}
.k-auth-head p{color:var(--muted);margin:0;}
.k-role{border:1px solid var(--line);border-radius:14px;padding:14px;height:100%;background:#fff;}
.k-role b{color:var(--navy);}
.k-role p{color:var(--muted);font-size:.82rem;margin:4px 0 0;}
.k-demo{background:var(--soft-blue);border-radius:14px;padding:14px 16px;font-size:.85rem;color:var(--navy2);margin-top:6px;}
@media (max-width: 800px){
 .k-hero{padding:40px 24px 48px;} .k-hero h1{font-size:2.1rem;}
 .k-gallery{grid-template-columns:1fr;grid-template-rows:240px;} .k-gallery .side{display:none;}
 .k-footer .cols{grid-template-columns:1fr 1fr;}
}
</style>
"""


def load_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def esc(text):
    """Escape user-typed text before putting it inside HTML."""
    return html.escape(str(text or ""))


def money(value):
    return f"₱{(value or 0):,.0f}"


def fmt_date(value, with_time=False):
    """'2026-11-19 13:00:00' -> 'Nov 19, 2026'"""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%b %d, %Y %I:%M %p" if with_time else "%b %d, %Y")
    except ValueError:
        return str(value)


def initials(name):
    parts = [p for p in str(name).split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


# Simple line icons (inline SVG, Lucide style) -------------------------------
_ICON_PATHS = {
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "bed": '<path d="M2 4v16"/><path d="M2 8h18a2 2 0 0 1 2 2v10"/><path d="M2 17h20"/><path d="M6 8v9"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "msg": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "ruler": '<path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z"/><path d="m14.5 12.5 2-2"/><path d="m11.5 9.5 2-2"/><path d="m8.5 6.5 2-2"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "key": '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
}


def icon(name, size=16, fill="none"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="{fill}" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{_ICON_PATHS[name]}</svg>')


# Images ---------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=400)
def image_data_uri(rel_path, max_width=720):
    """Turn an image file into a small base64 'data URI' so it can be used in HTML."""
    if not rel_path:
        return ""
    path = BASE_DIR / rel_path
    if not path.exists():
        return ""
    try:
        with Image.open(path) as im:
            buf = io.BytesIO()
            if path.suffix.lower() == ".png":
                im = im.convert("RGBA")
                im.thumbnail((max_width, max_width))
                im.save(buf, "PNG")
                mime = "image/png"
            else:
                im = im.convert("RGB")
                im.thumbnail((max_width, max_width * 2))
                im.save(buf, "JPEG", quality=82)
                mime = "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def img_tag(rel_path, css_class="", max_width=720, alt="Dormitory photo"):
    uri = image_data_uri(rel_path, max_width)
    if uri:
        return f'<img class="{css_class}" src="{uri}" alt="{esc(alt)}">'
    return f'<div class="k-ph {css_class}">{icon("home", 42)}</div>'


# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------
def html_block(markup):
    st.markdown(markup, unsafe_allow_html=True)


def badge(text, kind="neutral"):
    return f'<span class="k-badge {kind}">{esc(text)}</span>'


STATUS_KIND = {"Pending": "warning", "Under Review": "info", "Accepted": "success", "Rejected": "danger",
               "Open": "orange", "Replied": "success", "Available": "success", "Occupied": "danger"}


def status_badge(status):
    return badge(status, STATUS_KIND.get(status, "neutral"))


def stars(rating, size=""):
    rating = rating or 0
    full = int(round(rating))
    return (f'<span class="k-stars" style="font-size:{size or "inherit"}">' + "★" * full
            + f'<span class="off">{"★" * (5 - full)}</span></span>')


def rating_pill(avg, count):
    if not count:
        return '<span class="k-rating none">New</span>'
    return f'<span class="k-rating">★ {avg:.1f} <small>({count})</small></span>'


def section_header(title, subtitle="", eyebrow=""):
    html_block(f'<div class="k-section">'
               + (f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else "")
               + f'<h2>{esc(title)}</h2>'
               + (f'<p>{esc(subtitle)}</p>' if subtitle else "") + '</div>')


def page_banner(title, subtitle=""):
    html_block(f'<div class="k-banner"><h1>{esc(title)}</h1>'
               + (f'<p>{esc(subtitle)}</p>' if subtitle else "") + '</div>')


def stat_card(label, value, icon_name, orange=False):
    return (f'<div class="k-stat"><div class="ic{" o" if orange else ""}">{icon(icon_name, 22)}</div>'
            f'<div><div class="v">{esc(value)}</div><div class="l">{esc(label)}</div></div></div>')


def stat_row(items):
    """items = list of (label, value, icon, orange)"""
    cols = st.columns(len(items))
    for col, (label, value, icon_name, orange) in zip(cols, items):
        with col:
            html_block(stat_card(label, value, icon_name, orange))


def empty_state(title, text):
    html_block(f'<div class="k-empty"><h4>{esc(title)}</h4><div>{esc(text)}</div></div>')


def listing_card_html(p):
    """The visual part of a dormitory card (photo, name, rating, price...)."""
    available = (p.get("available_rooms") or 0) > 0
    avail_badge = badge("Available", "success") if available else badge("Fully occupied", "danger")
    desc = p.get("description") or ""
    if len(desc) > 95:
        desc = desc[:92].rsplit(" ", 1)[0] + "..."
    types = "".join(f'<span class="k-chip">{esc(t)}</span>' for t in p.get("room_type_list", []))
    amen = p.get("amenities", [])
    amen_html = "".join(f'<span class="k-chip light">{esc(a)}</span>' for a in amen[:2])
    if len(amen) > 2:
        amen_html += f'<span class="k-chip light">+{len(amen) - 2} more</span>'
    return (
        '<div class="k-card">'
        f'<div class="img">{img_tag(p.get("main_image"), max_width=640, alt=p["name"])}'
        f'<span class="badge-pos">{avail_badge}</span>'
        f'<span class="price-tag">{money(p.get("min_price"))} <small>/ month</small></span></div>'
        '<div class="body">'
        f'<div class="top"><h4>{esc(p["name"])}</h4>{rating_pill(p.get("avg_rating"), p.get("review_count"))}</div>'
        f'<div class="k-loc">{icon("pin", 14)} {esc(p.get("barangay"))}, {esc(p.get("city"))}</div>'
        f'<div class="k-chips">{types}</div>'
        f'<div class="k-meta"><span>{icon("users", 14)} Up to {p.get("max_capacity") or 0} per room</span>'
        f'<span>{icon("bed", 14)} {p.get("available_rooms") or 0} of {p.get("room_count") or 0} rooms free</span></div>'
        f'<div class="k-chips" style="margin-top:8px">{amen_html}</div>'
        f'<p class="k-desc">{esc(desc)}</p>'
        '</div></div>')


def footer():
    html_block(
        '<div class="k-footer"><div class="cols">'
        f'<div><div class="k-brand"><img src="{image_data_uri("assets/logo.png", 96)}">'
        '<div><div class="t" style="color:#fff">KWARKO</div><div class="s" style="color:#93A4BD">Dormitory Finder</div></div></div>'
        '<p style="margin-top:12px">KWARKO connects students and workers with trusted dormitories, boarding houses '
        'and rental rooms. Compare prices, read real reviews and apply online.</p></div>'
        '<div><h5>For Tenants</h5><ul><li>Search dormitories</li><li>Compare prices</li><li>Save favorites</li>'
        '<li>Track applications</li></ul></div>'
        '<div><h5>For Landlords</h5><ul><li>List your property</li><li>Manage rooms</li><li>Answer inquiries</li>'
        '<li>Review applications</li></ul></div>'
        '<div><h5>Contact</h5><ul><li>hello@kwarko.ph</li><li>(043) 555 0123</li><li>Batangas City, Philippines</li></ul></div>'
        '</div><div class="bottom"><span>© 2026 KWARKO. A semestral business project prototype.</span>'
        '<span>Find Your Space. Feel at Home.</span></div></div>')


# ---------------------------------------------------------------------------
# Navigation and messages
# ---------------------------------------------------------------------------
def navigate(page, property_id=None):
    """Switch to another page (and optionally choose a dormitory)."""
    st.session_state.page = page
    if property_id is not None:
        st.session_state.selected_property = property_id
    st.rerun()


def flash(message, kind="success"):
    """Store a message that is shown at the top of the next page load."""
    st.session_state.flash = (message, kind)


def show_flash():
    data = st.session_state.get("flash")
    if data:
        message, kind = data
        symbol = {"success": "check", "info": "msg", "error": "shield", "warning": "shield"}.get(kind, "check")
        html_block(f'<div class="k-flash {kind}">{icon(symbol, 18)} {esc(message)}</div>')
        st.session_state.flash = None


def current_user():
    return st.session_state.get("user")


def is_tenant():
    user = current_user()
    return bool(user and user["role"] == "tenant")


def is_landlord():
    user = current_user()
    return bool(user and user["role"] == "landlord")
