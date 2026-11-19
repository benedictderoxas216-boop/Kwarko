"""
app.py  -  KWARKO: Dormitory Finder and Rental Platform
=======================================================
Start the website with:   streamlit run app.py

This file is the "main door" of the app. It:
  1. configures the page and loads the custom design (CSS)
  2. creates the database (with sample data) on the first run
  3. shows the navigation bar
  4. decides which page to display, based on st.session_state.page

Pages:
  home, search, details           -> listings.py   (everyone)
  login, register                 -> auth.py       (visitors)
  tenant_dashboard                -> tenant.py     (tenants only)
  landlord_dashboard              -> landlord.py   (landlords only)
"""

import streamlit as st
from PIL import Image

import auth
import database as db
import landlord
import listings
import tenant
import ui
from make_sample_images import ensure_sample_images

ensure_sample_images()          # draws the logo/sample photos if they are missing
st.set_page_config(page_title="KWARKO - Find Your Space", page_icon=Image.open(db.BASE_DIR / "assets" / "logo.png"),
                   layout="wide", initial_sidebar_state="collapsed")


def init_state():
    """Default values that every visitor's session starts with."""
    defaults = {"page": "home", "user": None, "selected_property": None, "flash": None,
                "filters": listings.default_filters(), "filter_version": 0, "after_login": None,
                "register_as": None, "pending_menu": None, "manage_property": None, "confirm_delete": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # Refresh the logged-in user from the database (e.g. after a profile update).
    if st.session_state.user:
        st.session_state.user = db.get_user(st.session_state.user["id"])


def navbar():
    user = ui.current_user()
    page = st.session_state.page
    items = [("Home", "home", ":material/home:"), ("Find Dorms", "search", ":material/search:")]
    if user:
        dash = "tenant_dashboard" if user["role"] == "tenant" else "landlord_dashboard"
        items.append(("My Dashboard", dash, ":material/dashboard:"))

    widths = [3.2] + [1.05] * len(items) + ([1.6, 0.95] if user else [0.9, 1.0])
    cols = st.columns(widths, vertical_alignment="center")
    cols[0].markdown(
        f'<div class="k-brand"><img src="{ui.image_data_uri("assets/logo.png", 96)}" alt="KWARKO logo">'
        '<div><div class="t">KWARKO</div><div class="s">Dormitory Finder &amp; Rentals</div></div></div>',
        unsafe_allow_html=True)
    for col, (label, target, icon) in zip(cols[1:], items):
        active = page == target or (target == "search" and page == "details")
        if col.button(label, key=f"nav_{target}", icon=icon, type="primary" if active else "secondary"):
            ui.navigate(target)

    if user:
        role = "Tenant" if user["role"] == "tenant" else "Landlord"
        cols[-2].markdown(f'<div class="k-contact" style="justify-content:flex-end">'
                          f'<div style="text-align:right"><b style="color:#0B2447;font-size:.9rem">'
                          f'{ui.esc(user["full_name"])}</b><div class="k-muted" style="font-size:.75rem">{role}</div></div>'
                          f'<div class="k-avatar" style="width:38px;height:38px;font-size:.8rem">'
                          f'{ui.initials(user["full_name"])}</div></div>', unsafe_allow_html=True)
        if cols[-1].button("Log out", key="nav_logout", icon=":material/logout:"):
            auth.logout()
    else:
        if cols[-2].button("Log in", key="nav_login", type="primary" if page == "login" else "secondary"):
            ui.navigate("login")
        if cols[-1].button("Sign up", key="nav_signup"):
            st.session_state.register_as = None
            ui.navigate("register")


def main():
    db.init_db()                # creates kwarko.db with sample data the first time
    init_state()
    ui.load_css()
    navbar()
    ui.show_flash()

    page = st.session_state.page
    user = ui.current_user()

    if page == "home":
        listings.home_page()
    elif page == "search":
        listings.search_page()
    elif page == "details":
        listings.details_page()
    elif page == "login":
        auth.login_page()
    elif page == "register":
        auth.register_page()
    elif page == "tenant_dashboard":
        if user and user["role"] == "tenant":
            tenant.dashboard()
        else:
            auth.login_page("Please log in with a tenant account to open the Tenant Dashboard.")
    elif page == "landlord_dashboard":
        if user and user["role"] == "landlord":
            landlord.dashboard()
        else:
            auth.login_page("Please log in with a landlord account to open the Landlord Dashboard.")
    else:
        listings.home_page()

    ui.footer()


main()
