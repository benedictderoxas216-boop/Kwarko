"""
auth.py
-------
Login, registration and logout.

Passwords are never stored as plain text: database.py saves a salted
PBKDF2 hash. After logging in, tenants and landlords are sent to their own
dashboards (or back to the dorm they were looking at).
"""

import re

import streamlit as st

import database as db
import ui

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_user(user):
    """Remember the user in the session and send them to the right page."""
    st.session_state.user = user
    ui.flash(f"Welcome, {user['full_name'].split()[0]}! You are logged in as a {user['role']}.")
    destination = st.session_state.get("after_login")
    st.session_state.after_login = None
    if destination and user["role"] == "tenant":
        ui.navigate("details", destination)
    ui.navigate("tenant_dashboard" if user["role"] == "tenant" else "landlord_dashboard")


def logout():
    st.session_state.user = None
    for key in ("after_login", "manage_property", "confirm_delete", "pending_menu"):
        st.session_state[key] = None
    ui.flash("You have been logged out. See you again soon!", "info")
    ui.navigate("home")


def _attempt_login(email, password, role):
    if not email or not password:
        st.error("Please enter your email and password.")
        return
    user = db.authenticate(email, password)
    if not user:
        st.error("Incorrect email or password.")
    elif user["role"] != role:
        st.error(f"This account is registered as a {user['role'].title()}. "
                 f"Please select '{user['role'].title()}' above.")
    else:
        login_user(user)


def _auth_header(title, subtitle):
    ui.html_block(f'<div class="k-auth-head"><img src="{ui.image_data_uri("assets/logo.png", 128)}">'
                  f'<h2>{ui.esc(title)}</h2><p>{ui.esc(subtitle)}</p></div>')


def login_page(notice=""):
    _, middle, _ = st.columns([1, 1.35, 1])
    with middle:
        _auth_header("Welcome back", "Log in to continue finding your space.")
        if notice:
            ui.html_block(f'<div class="k-flash info">{ui.icon("key", 18)} {ui.esc(notice)}</div>')
        with st.container(border=True):
            with st.form("login_form"):
                role = st.radio("I am logging in as a", ["Tenant", "Landlord"], horizontal=True)
                email = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="Your password")
                submitted = st.form_submit_button("Log In", type="primary", icon=":material/login:")
            if submitted:
                _attempt_login(email, password, role.lower())

            ui.html_block('<div class="k-demo"><b>Demo accounts for the presentation</b><br>'
                          'Tenant: tenant@kwarko.ph / tenant123<br>'
                          'Landlord: landlord@kwarko.ph / landlord123</div>')
            c1, c2 = st.columns(2)
            if c1.button("Use demo tenant", key="demo_tenant", icon=":material/person:"):
                _attempt_login("tenant@kwarko.ph", "tenant123", "tenant")
            if c2.button("Use demo landlord", key="demo_landlord", icon=":material/apartment:"):
                _attempt_login("landlord@kwarko.ph", "landlord123", "landlord")

        st.write("")
        c1, c2 = st.columns([1.4, 1], vertical_alignment="center")
        c1.markdown("Don't have an account yet?")
        if c2.button("Create account", key="go_register"):
            ui.navigate("register")


def register_page():
    _, middle, _ = st.columns([1, 1.6, 1])
    with middle:
        _auth_header("Create your KWARKO account", "Choose how you want to use KWARKO.")
        c1, c2 = st.columns(2)
        c1.markdown('<div class="k-role"><b>' + ui.icon("search", 16) + ' Tenant</b><p>Find, compare and apply for '
                    'dormitories. Save favorites and track your applications.</p></div>', unsafe_allow_html=True)
        c2.markdown('<div class="k-role"><b>' + ui.icon("home", 16) + ' Landlord</b><p>Post your rooms, manage '
                    'availability and respond to tenant inquiries and applications.</p></div>',
                    unsafe_allow_html=True)
        st.write("")
        with st.container(border=True):
            with st.form("register_form"):
                default_index = 1 if st.session_state.get("register_as") == "Landlord" else 0
                role = st.radio("Account type", ["Tenant", "Landlord"], index=default_index, horizontal=True)
                full_name = st.text_input("Full name", placeholder="Juan Dela Cruz")
                c1, c2 = st.columns(2)
                email = c1.text_input("Email address", placeholder="you@example.com")
                phone = c2.text_input("Mobile number", placeholder="09XX XXX XXXX")
                c1, c2 = st.columns(2)
                password = c1.text_input("Password", type="password", placeholder="At least 6 characters")
                confirm = c2.text_input("Confirm password", type="password")
                agree = st.checkbox("I agree to the KWARKO terms of use and privacy policy.")
                submitted = st.form_submit_button("Create Account", type="primary",
                                                  icon=":material/person_add:")
            if submitted:
                errors = []
                if len(full_name.strip()) < 2:
                    errors.append("Please enter your full name.")
                if not EMAIL_PATTERN.match(email.strip()):
                    errors.append("Please enter a valid email address.")
                if len(password) < 6:
                    errors.append("Password must be at least 6 characters.")
                if password != confirm:
                    errors.append("Passwords do not match.")
                if not agree:
                    errors.append("Please agree to the terms of use.")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    user_id = db.create_user(full_name, email, password, role.lower(), phone)
                    if user_id is None:
                        st.error("An account with this email already exists. Please log in instead.")
                    else:
                        st.session_state.register_as = None
                        login_user(db.get_user(user_id))

        st.write("")
        c1, c2 = st.columns([1.4, 1], vertical_alignment="center")
        c1.markdown("Already have an account?")
        if c2.button("Log in", key="go_login"):
            ui.navigate("login")
