"""
tenant.py
---------
The Tenant Dashboard:
  * My Applications  - status of every rental application (and cancel while Pending)
  * My Inquiries     - questions sent to landlords and their replies
  * Saved Dorms      - bookmarked dormitories
  * Rental History   - accepted stays and the reviews written
  * Profile          - update name / phone and change password
"""

import streamlit as st

import database as db
import listings
import ui

MENU = ["My Applications", "My Inquiries", "Saved Dorms", "Rental History & Reviews", "Profile"]


def dashboard():
    user = ui.current_user()
    stats = db.get_tenant_stats(user["id"])
    ui.page_banner(f"Hi, {user['full_name'].split()[0]}!",
                   "Track your applications, read landlord replies and manage your saved dorms.")
    ui.stat_row([("Applications sent", stats["applications"], "file", False),
                 ("In progress", stats["in_progress"], "search", True),
                 ("Saved dorms", stats["saved"], "heart", False),
                 ("Landlord replies", stats["replies"], "msg", True)])
    st.write("")

    if st.session_state.get("pending_menu") in MENU:      # e.g. sent here from another page
        st.session_state.menu_tenant = st.session_state.pending_menu
    st.session_state.pending_menu = None
    section = st.radio("Dashboard menu", MENU, horizontal=True, key="menu_tenant",
                       label_visibility="collapsed")
    st.write("")

    if section == "My Applications":
        applications_tab(user)
    elif section == "My Inquiries":
        inquiries_tab(user)
    elif section == "Saved Dorms":
        saved_tab(user)
    elif section == "Rental History & Reviews":
        history_tab(user)
    else:
        profile_tab(user)


def applications_tab(user):
    apps = db.get_tenant_applications(user["id"])
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.markdown('<h3>My Applications</h3>', unsafe_allow_html=True)
    status = c2.selectbox("Show", ["All"] + db.APPLICATION_STATUSES, key="tenant_app_filter")
    if status != "All":
        apps = [a for a in apps if a["status"] == status]
    if not apps:
        ui.empty_state("No applications here", "Find a dorm you like and click 'Apply for Room'.")
        if st.button("Find a dorm", type="primary", key="apps_find"):
            listings.go_search()
        return
    for a in apps:
        with st.container(border=True):
            c1, c2 = st.columns([3.2, 1], vertical_alignment="center")
            note = (f'<div class="k-bubble reply"><b>Landlord note:</b> {ui.esc(a["landlord_note"])}</div>'
                    if a["landlord_note"] else "")
            c1.markdown(
                f'<div class="k-item-title">{ui.esc(a["property_name"])} &nbsp;{ui.status_badge(a["status"])}</div>'
                f'<div class="k-muted">{ui.esc(a["room_name"])} &middot; {ui.esc(a["room_type"])} &middot; '
                f'{ui.money(a["price"])}/month &middot; {ui.esc(a["city"])}</div>'
                f'<div class="k-meta"><span>Submitted {ui.fmt_date(a["created_at"])}</span>'
                f'<span>Move-in {ui.fmt_date(a["move_in_date"])}</span><span>{a["stay_months"]} month(s)</span>'
                f'<span>Last update {ui.fmt_date(a["updated_at"])}</span></div>{note}',
                unsafe_allow_html=True)
            with c2:
                if st.button("View dorm", key=f"app_view_{a['id']}"):
                    ui.navigate("details", a["property_id"])
                if a["status"] == "Pending" and st.button("Cancel application", key=f"app_cancel_{a['id']}"):
                    db.cancel_application(user["id"], a["id"])
                    ui.flash("Your application was cancelled.", "info")
                    st.rerun()


def inquiries_tab(user):
    st.markdown('<h3>My Inquiries</h3>', unsafe_allow_html=True)
    inquiries = db.get_tenant_inquiries(user["id"])
    if not inquiries:
        ui.empty_state("No inquiries yet", "Open a dorm's page and use 'Send Inquiry' to ask the landlord.")
        return
    for q in inquiries:
        with st.container(border=True):
            c1, c2 = st.columns([3.2, 1], vertical_alignment="top")
            reply = (f'<div class="k-bubble reply"><b>{ui.esc(q["landlord_name"])} replied</b> '
                     f'<span class="k-muted">&middot; {ui.fmt_date(q["replied_at"], True)}</span><br>'
                     f'{ui.esc(q["reply"])}</div>' if q["reply"]
                     else '<div class="k-muted" style="margin-top:8px">Waiting for the landlord to reply...</div>')
            c1.markdown(
                f'<div class="k-item-title">{ui.esc(q["subject"])} &nbsp;{ui.status_badge(q["status"])}</div>'
                f'<div class="k-muted">To {ui.esc(q["property_name"])} &middot; {ui.fmt_date(q["created_at"], True)}</div>'
                f'<div class="k-bubble"><b>You:</b> {ui.esc(q["message"])}</div>{reply}',
                unsafe_allow_html=True)
            if c2.button("View dorm", key=f"inq_view_{q['id']}"):
                ui.navigate("details", q["property_id"])


def saved_tab(user):
    st.markdown('<h3>Saved Dorms</h3>', unsafe_allow_html=True)
    saved = db.get_saved_properties(user["id"])
    if not saved:
        ui.empty_state("No saved dorms yet", "Tap 'Save' on any listing to keep it here for later.")
        if st.button("Browse dormitories", type="primary", key="saved_browse"):
            listings.go_search()
        return
    listings.render_grid(saved, "saved", columns=3)


def history_tab(user):
    st.markdown('<h3>Rental History</h3>', unsafe_allow_html=True)
    stays = [a for a in db.get_tenant_applications(user["id"]) if a["status"] == "Accepted"]
    if not stays:
        ui.empty_state("No rental history yet", "Accepted applications will appear here.")
    for a in stays:
        reviewed = db.has_reviewed(user["id"], a["property_id"])
        with st.container(border=True):
            c1, c2 = st.columns([3.2, 1], vertical_alignment="center")
            c1.markdown(f'<div class="k-item-title">{ui.esc(a["property_name"])}</div>'
                        f'<div class="k-muted">{ui.esc(a["room_name"])} &middot; {ui.money(a["price"])}/month &middot; '
                        f'moved in {ui.fmt_date(a["move_in_date"])} &middot; {a["stay_months"]} month(s)</div>'
                        + (f'<div style="margin-top:6px">{ui.badge("Reviewed", "success")}</div>' if reviewed else ""),
                        unsafe_allow_html=True)
            label = "View dorm" if reviewed else "Write a review"
            if c2.button(label, key=f"hist_{a['id']}", type="secondary" if reviewed else "primary"):
                ui.navigate("details", a["property_id"])

    st.markdown('<h3 style="margin-top:24px">My Reviews</h3>', unsafe_allow_html=True)
    reviews = db.get_tenant_reviews(user["id"])
    if not reviews:
        ui.html_block('<p class="k-muted">You have not written any reviews yet.</p>')
    for r in reviews:
        ui.html_block(f'<div class="k-review"><div class="k-item-title">{ui.esc(r["property_name"])}</div>'
                      f'<div class="k-muted">{ui.stars(r["rating"])} &middot; {ui.fmt_date(r["created_at"])}</div>'
                      f'<p>{ui.esc(r["comment"])}</p></div>')


def profile_tab(user):
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            ui.html_block('<div class="k-item-title">Profile information</div>')
            with st.form("tenant_profile"):
                name = st.text_input("Full name", value=user["full_name"])
                st.text_input("Email address", value=user["email"], disabled=True)
                phone = st.text_input("Mobile number", value=user["phone"] or "")
                saved = st.form_submit_button("Save changes", type="primary", icon=":material/save:")
            if saved:
                if len(name.strip()) < 2:
                    st.error("Please enter your full name.")
                else:
                    db.update_user_profile(user["id"], name, phone)
                    st.session_state.user = db.get_user(user["id"])
                    ui.flash("Your profile was updated.")
                    st.rerun()
    with c2:
        password_form(user, "tenant_pw")


def password_form(user, form_key):
    """Shared by tenant and landlord dashboards."""
    with st.container(border=True):
        ui.html_block('<div class="k-item-title">Change password</div>')
        with st.form(form_key, clear_on_submit=True):
            current = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            confirm = st.text_input("Confirm new password", type="password")
            changed = st.form_submit_button("Update password", icon=":material/lock_reset:")
        if changed:
            if len(new) < 6:
                st.error("New password must be at least 6 characters.")
            elif new != confirm:
                st.error("New passwords do not match.")
            elif not db.change_password(user["id"], current, new):
                st.error("Your current password is incorrect.")
            else:
                st.success("Password updated successfully.")
