"""
landlord.py
-----------
The Landlord Dashboard:
  * My Listings          - all posted dorms (view, manage, delete)
  * Add New Listing      - post a dorm with its first room and photos
  * Inquiries            - read and reply to tenant questions
  * Applications         - review tenants and accept / reject applications
  * Property Management  - edit details, amenities, rules, rooms, prices, availability and photos
  * Profile              - contact details and password
"""

import io
import uuid

import streamlit as st
from PIL import Image

import database as db
import tenant
import ui

MENU = ["My Listings", "Add New Listing", "Inquiries", "Applications", "Property Management", "Profile"]


def dashboard():
    user = ui.current_user()
    stats = db.get_landlord_stats(user["id"])
    ui.page_banner(f"Landlord Dashboard - {user['full_name']}",
                   "Post rooms, keep availability up to date and respond to tenants.")
    ui.stat_row([("Listings posted", stats["listings"], "home", False),
                 ("Rooms available", stats["available_rooms"], "bed", True),
                 ("Open inquiries", stats["open_inquiries"], "msg", False),
                 ("Applications to review", stats["pending_apps"], "file", True)])
    st.write("")

    # Other pages / buttons can ask to open a specific section first.
    if st.session_state.get("pending_menu") in MENU:
        st.session_state.menu_landlord = st.session_state.pending_menu
    st.session_state.pending_menu = None
    section = st.radio("Dashboard menu", MENU, horizontal=True, key="menu_landlord",
                       label_visibility="collapsed")
    st.write("")

    if section == "My Listings":
        listings_tab(user)
    elif section == "Add New Listing":
        add_listing_tab(user)
    elif section == "Inquiries":
        inquiries_tab(user)
    elif section == "Applications":
        applications_tab(user)
    elif section == "Property Management":
        management_tab(user)
    else:
        profile_tab(user)


def open_section(section, property_id=None):
    """Jump to another dashboard section (used by buttons)."""
    st.session_state.pending_menu = section
    if property_id is not None:
        st.session_state.manage_property = property_id
    st.rerun()


# ---------------------------------------------------------------------------
# Image upload helper
# ---------------------------------------------------------------------------
def save_uploaded_image(uploaded_file):
    """Check that the upload is a real image, shrink it and save it to assets/uploads/.
    Returns the relative path stored in the database (or None if invalid)."""
    try:
        with Image.open(io.BytesIO(uploaded_file.getvalue())) as im:
            im = im.convert("RGB")
            im.thumbnail((1600, 1600))
            filename = f"{uuid.uuid4().hex[:12]}.jpg"
            db.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            im.save(db.UPLOAD_DIR / filename, "JPEG", quality=85)
        return f"assets/uploads/{filename}"
    except Exception:
        return None


def _save_images(property_id, files):
    saved = 0
    for f in files or []:
        path = save_uploaded_image(f)
        if path:
            db.add_image(property_id, path)
            saved += 1
    return saved


# ---------------------------------------------------------------------------
# My Listings
# ---------------------------------------------------------------------------
def listings_tab(user):
    props = db.get_landlord_properties(user["id"])
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.markdown(f'<h3>My Listings ({len(props)})</h3>', unsafe_allow_html=True)
    if c2.button("Add new listing", type="primary", key="ml_add", icon=":material/add:"):
        open_section("Add New Listing")
    if not props:
        ui.empty_state("You have no listings yet", "Click 'Add new listing' to post your first dormitory.")
        return

    for p in props:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1.1, 2.6, 1.1], vertical_alignment="center")
            c1.markdown(ui.img_tag(p["main_image"], "k-thumb", 420, p["name"]), unsafe_allow_html=True)
            avail = (ui.badge(f'{p["available_rooms"]} of {p["room_count"]} rooms available', "success")
                     if p["available_rooms"] else ui.badge("Fully occupied", "danger"))
            c2.markdown(
                f'<div class="k-item-title">{ui.esc(p["name"])}</div>'
                f'<div class="k-loc">{ui.icon("pin", 14)} {ui.esc(p["address"])}, {ui.esc(p["city"])}</div>'
                f'<div class="k-chips">{avail}{ui.rating_pill(p["avg_rating"], p["review_count"])}'
                + "".join(f'<span class="k-chip">{ui.esc(t)}</span>' for t in p["room_type_list"])
                + f'</div><div class="k-meta"><span>From {ui.money(p["min_price"])}/month</span>'
                f'<span>Posted {ui.fmt_date(p["created_at"])}</span></div>',
                unsafe_allow_html=True)
            with c3:
                if st.button("Manage", type="primary", key=f"ml_manage_{p['id']}", icon=":material/edit:"):
                    open_section("Property Management", p["id"])
                if st.button("Public page", key=f"ml_view_{p['id']}", icon=":material/visibility:"):
                    ui.navigate("details", p["id"])
                if st.button("Delete", key=f"ml_del_{p['id']}", icon=":material/delete:"):
                    st.session_state.confirm_delete = p["id"]
                    st.rerun()
            if st.session_state.get("confirm_delete") == p["id"]:
                st.warning(f"Delete **{p['name']}**? Its rooms, photos, inquiries, applications and reviews "
                           "will also be removed. This cannot be undone.")
                d1, d2, _ = st.columns([1, 1, 3])
                if d1.button("Yes, delete", type="primary", key=f"ml_yes_{p['id']}"):
                    db.delete_property(user["id"], p["id"])
                    st.session_state.confirm_delete = None
                    ui.flash(f"'{p['name']}' was deleted.", "info")
                    st.rerun()
                if d2.button("Cancel", key=f"ml_no_{p['id']}"):
                    st.session_state.confirm_delete = None
                    st.rerun()


# ---------------------------------------------------------------------------
# Add New Listing
# ---------------------------------------------------------------------------
def add_listing_tab(user):
    st.markdown('<h3>Add a new dormitory listing</h3>'
                '<p class="k-muted">Fields marked * are required. You can add more rooms and photos later '
                'in Property Management.</p>', unsafe_allow_html=True)
    with st.form("add_listing", clear_on_submit=False):
        ui.html_block('<div class="k-item-title">1. Property details</div>')
        name = st.text_input("Dormitory name *", placeholder="e.g. Sunrise Student Residences")
        c1, c2, c3 = st.columns([2, 1, 1])
        address = c1.text_input("Street address *", placeholder="House no., street, subdivision")
        barangay = c2.text_input("Barangay *", placeholder="e.g. Alangilan")
        city = c3.text_input("City / Municipality *", placeholder="e.g. Batangas City")
        c1, c2, c3 = st.columns(3)
        gender = c1.selectbox("Tenant policy", db.GENDER_POLICIES)
        phone = c2.text_input("Contact number", value=user["phone"] or "")
        email = c3.text_input("Contact email", value=user["email"])
        description = st.text_area("Description *", height=90,
                                   placeholder="Describe the place, nearby schools, transport, etc.")
        amenities = st.multiselect("Amenities", db.AMENITIES)
        c1, c2 = st.columns(2)
        rules = c1.text_area("House rules (one per line)", value=db.STANDARD_RULES, height=140)
        reqs = c2.text_area("Rental requirements (one per line)", value=db.STANDARD_REQS, height=140)

        ui.html_block('<div class="k-item-title" style="margin-top:10px">2. First room</div>')
        c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1])
        room_name = c1.text_input("Room name *", placeholder="e.g. Room 101")
        room_type = c2.selectbox("Room type", db.ROOM_TYPES)
        price = c3.number_input("Monthly rent (₱) *", min_value=0, max_value=100000, value=3000, step=100)
        capacity = c4.number_input("Max occupants", min_value=1, max_value=20, value=2)
        c1, c2, c3 = st.columns([1, 2, 1])
        dimensions = c1.text_input("Dimensions (optional)", placeholder="e.g. 3m x 4m")
        specs = c2.text_input("Room specifications", placeholder="Beds, furniture, fan/aircon, CR...")
        availability = c3.selectbox("Availability", db.AVAILABILITY)

        ui.html_block('<div class="k-item-title" style="margin-top:10px">3. Photos</div>')
        photos = st.file_uploader("Upload room / building photos (the first photo becomes the main photo)",
                                  type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        submitted = st.form_submit_button("Publish Listing", type="primary", icon=":material/publish:")

    if submitted:
        required = {"Dormitory name": name, "Street address": address, "Barangay": barangay,
                    "City": city, "Description": description, "Room name": room_name}
        missing = [label for label, value in required.items() if not value.strip()]
        if missing:
            st.error("Please fill in: " + ", ".join(missing))
            return
        if price <= 0:
            st.error("Monthly rent must be greater than zero.")
            return
        pid = db.create_property(user["id"], name, address, barangay, city, gender, description,
                                 rules, reqs, phone, email)
        db.set_amenities(pid, amenities)
        db.add_room(pid, room_name, room_type, price, capacity, dimensions, specs, availability)
        count = _save_images(pid, photos)
        ui.flash(f"'{name.strip()}' is now live with {count} photo(s)! You can add more rooms below.")
        open_section("Property Management", pid)


# ---------------------------------------------------------------------------
# Inquiries
# ---------------------------------------------------------------------------
def inquiries_tab(user):
    inquiries = db.get_landlord_inquiries(user["id"])
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.markdown('<h3>Tenant inquiries</h3>', unsafe_allow_html=True)
    show = c2.selectbox("Show", ["All", "Open", "Replied"], key="ll_inq_filter")
    if show != "All":
        inquiries = [q for q in inquiries if q["status"] == show]
    if not inquiries:
        ui.empty_state("No inquiries to show", "Questions from tenants will appear here.")
        return
    for q in inquiries:
        with st.container(border=True):
            ui.html_block(
                f'<div class="k-item-title">{ui.esc(q["subject"])} &nbsp;{ui.status_badge(q["status"])}</div>'
                f'<div class="k-muted">{ui.esc(q["property_name"])} &middot; {ui.fmt_date(q["created_at"], True)}</div>'
                f'<div class="k-meta"><span>{ui.icon("users", 14)} {ui.esc(q["tenant_name"])}</span>'
                f'<span>{ui.icon("mail", 14)} {ui.esc(q["tenant_email"])}</span>'
                f'<span>{ui.icon("phone", 14)} {ui.esc(q["tenant_phone"] or "-")}</span></div>'
                f'<div class="k-bubble"><b>{ui.esc(q["tenant_name"])}:</b> {ui.esc(q["message"])}</div>'
                + (f'<div class="k-bubble reply"><b>Your reply</b> <span class="k-muted">&middot; '
                   f'{ui.fmt_date(q["replied_at"], True)}</span><br>{ui.esc(q["reply"])}</div>' if q["reply"] else ""))
            with st.expander("Edit reply" if q["reply"] else "Reply to this inquiry", expanded=not q["reply"]):
                with st.form(f"reply_form_{q['id']}", clear_on_submit=True):
                    reply = st.text_area("Your reply", value=q["reply"] or "", height=90, key=f"reply_{q['id']}")
                    sent = st.form_submit_button("Send reply", type="primary", icon=":material/send:")
                if sent:
                    if not reply.strip():
                        st.error("The reply cannot be empty.")
                    else:
                        db.reply_to_inquiry(user["id"], q["id"], reply)
                        ui.flash(f"Reply sent to {q['tenant_name']}.")
                        st.rerun()


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
def applications_tab(user):
    apps = db.get_landlord_applications(user["id"])
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.markdown('<h3>Rental applications</h3>', unsafe_allow_html=True)
    show = c2.selectbox("Show", ["Needs action", "All"] + db.APPLICATION_STATUSES, key="ll_app_filter")
    if show == "Needs action":
        apps = [a for a in apps if a["status"] in ("Pending", "Under Review")]
    elif show != "All":
        apps = [a for a in apps if a["status"] == show]
    if not apps:
        ui.empty_state("No applications to show", "Try another filter, or wait for tenants to apply.")
        return
    for a in apps:
        with st.container(border=True):
            c1, c2 = st.columns([1.5, 1], gap="large")
            c1.markdown(
                f'<div class="k-item-title">{ui.esc(a["tenant_name"])} &nbsp;{ui.status_badge(a["status"])}</div>'
                f'<div class="k-muted">Applied for <b>{ui.esc(a["room_name"])}</b> ({ui.esc(a["room_type"])}, '
                f'{ui.money(a["price"])}/mo) at {ui.esc(a["property_name"])}</div>'
                f'<div class="k-meta"><span>{ui.icon("mail", 14)} {ui.esc(a["tenant_email"])}</span>'
                f'<span>{ui.icon("phone", 14)} {ui.esc(a["contact_phone"] or "-")}</span></div>'
                f'<div class="k-meta"><span><b>Occupation:</b> {ui.esc(a["occupation"])}</span>'
                f'<span><b>School/Work:</b> {ui.esc(a["school_or_work"])}</span></div>'
                f'<div class="k-meta"><span><b>Move-in:</b> {ui.fmt_date(a["move_in_date"])}</span>'
                f'<span><b>Stay:</b> {a["stay_months"]} month(s)</span>'
                f'<span><b>Submitted:</b> {ui.fmt_date(a["created_at"])}</span>'
                f'<span><b>Room now:</b> {ui.esc(a["room_availability"])}</span></div>'
                + (f'<div class="k-bubble"><b>Message:</b> {ui.esc(a["message"])}</div>' if a["message"] else ""),
                unsafe_allow_html=True)
            with c2:
                with st.form(f"app_form_{a['id']}"):
                    status = st.selectbox("Update status", db.APPLICATION_STATUSES,
                                          index=db.APPLICATION_STATUSES.index(a["status"]), key=f"st_{a['id']}")
                    note = st.text_area("Note to tenant", value=a["landlord_note"] or "", height=70,
                                        key=f"note_{a['id']}")
                    occupy = st.checkbox("Mark this room as Occupied when accepting", key=f"occ_{a['id']}")
                    saved = st.form_submit_button("Save decision", type="primary", icon=":material/check:")
                if saved:
                    db.update_application_status(user["id"], a["id"], status, note)
                    if status == "Accepted" and occupy:
                        db.set_room_availability(a["room_id"], "Occupied")
                    ui.flash(f"Application of {a['tenant_name']} is now '{status}'.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Property Management
# ---------------------------------------------------------------------------
def management_tab(user):
    props = db.get_landlord_properties(user["id"])
    if not props:
        ui.empty_state("No listings to manage", "Add a listing first.")
        return
    ids = [p["id"] for p in props]
    names = {p["id"]: p["name"] for p in props}
    chosen = st.session_state.get("manage_property")
    index = ids.index(chosen) if chosen in ids else 0
    pid = st.selectbox("Choose a property to manage", ids, index=index, format_func=names.get,
                       key=f"manage_select_{user['id']}_{chosen}")
    if pid not in ids:          # safety check (e.g. the listing was just deleted)
        pid = ids[0]
    st.session_state.manage_property = pid
    prop = db.get_property(pid)

    tab_details, tab_rooms, tab_photos = st.tabs(["Details, Amenities & Rules", "Rooms, Prices & Availability",
                                                  "Photos"])
    with tab_details:
        _details_form(user, prop)
    with tab_rooms:
        _rooms_editor(prop)
    with tab_photos:
        _photos_editor(prop)


def _details_form(user, prop):
    with st.form(f"details_{prop['id']}"):
        name = st.text_input("Dormitory name", value=prop["name"])
        c1, c2, c3 = st.columns([2, 1, 1])
        address = c1.text_input("Street address", value=prop["address"])
        barangay = c2.text_input("Barangay", value=prop["barangay"])
        city = c3.text_input("City / Municipality", value=prop["city"])
        c1, c2, c3 = st.columns(3)
        gender = c1.selectbox("Tenant policy", db.GENDER_POLICIES,
                              index=db.GENDER_POLICIES.index(prop["gender_policy"])
                              if prop["gender_policy"] in db.GENDER_POLICIES else 0)
        phone = c2.text_input("Contact number", value=prop["contact_phone"])
        email = c3.text_input("Contact email", value=prop["contact_email"])
        description = st.text_area("Description", value=prop["description"], height=100)
        amenities = st.multiselect("Amenities", db.AMENITIES,
                                   default=[a for a in prop["amenities"] if a in db.AMENITIES])
        c1, c2 = st.columns(2)
        rules = c1.text_area("House rules (one per line)", value=prop["house_rules"], height=150)
        reqs = c2.text_area("Rental requirements (one per line)", value=prop["requirements"], height=150)
        saved = st.form_submit_button("Save details", type="primary", icon=":material/save:")
    if saved:
        if not name.strip() or not address.strip() or not city.strip():
            st.error("Name, address and city cannot be empty.")
            return
        db.update_property(user["id"], prop["id"], name, address, barangay, city, gender, description,
                           rules, reqs, phone, email)
        db.set_amenities(prop["id"], amenities)
        ui.flash("Property details saved.")
        st.rerun()


def _room_fields(prefix, room=None):
    """Input widgets for one room (used for editing and adding)."""
    room = room or {}
    c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1])
    name = c1.text_input("Room name", value=room.get("room_name", ""), key=f"{prefix}_name")
    rtype = c2.selectbox("Room type", db.ROOM_TYPES,
                         index=db.ROOM_TYPES.index(room["room_type"]) if room.get("room_type") in db.ROOM_TYPES else 0,
                         key=f"{prefix}_type")
    price = c3.number_input("Monthly rent (₱)", min_value=0, max_value=100000,
                            value=int(room.get("price", 3000)), step=100, key=f"{prefix}_price")
    capacity = c4.number_input("Max occupants", min_value=1, max_value=20, value=int(room.get("capacity", 1)),
                               key=f"{prefix}_cap")
    c1, c2, c3 = st.columns([1, 2, 1])
    dims = c1.text_input("Dimensions", value=room.get("dimensions", ""), key=f"{prefix}_dims")
    specs = c2.text_input("Specifications", value=room.get("specs", ""), key=f"{prefix}_specs")
    avail = c3.selectbox("Availability", db.AVAILABILITY,
                         index=db.AVAILABILITY.index(room.get("availability", "Available")), key=f"{prefix}_avail")
    return name, rtype, price, capacity, dims, specs, avail


def _rooms_editor(prop):
    rooms = db.get_rooms(prop["id"])
    for r in rooms:
        title = f'{r["room_name"]}  ·  {r["room_type"]}  ·  {ui.money(r["price"])}/mo  ·  {r["availability"]}'
        with st.expander(title):
            with st.form(f"room_{r['id']}"):
                # The key changes whenever the saved room changes, so the form always shows fresh values.
                version = abs(hash(tuple(r.values())))
                values = _room_fields(f"r{r['id']}_{version}", r)
                saved = st.form_submit_button("Save room", type="primary", icon=":material/save:")
            if saved:
                if not values[0].strip() or values[2] <= 0:
                    st.error("Room name is required and the rent must be greater than zero.")
                else:
                    db.update_room(r["id"], *values)
                    ui.flash(f"'{values[0].strip()}' updated.")
                    st.rerun()
            c1, c2, _ = st.columns([1.3, 1, 2])
            other = "Occupied" if r["availability"] == "Available" else "Available"
            if c1.button(f"Mark as {other}", key=f"toggle_{r['id']}"):
                db.set_room_availability(r["id"], other)
                ui.flash(f"'{r['room_name']}' is now {other}.")
                st.rerun()
            if c2.button("Delete room", key=f"delroom_{r['id']}", icon=":material/delete:"):
                if len(rooms) == 1:
                    st.error("A listing needs at least one room. Add another room before deleting this one.")
                else:
                    db.delete_room(r["id"])
                    ui.flash(f"'{r['room_name']}' was deleted.", "info")
                    st.rerun()

    st.write("")
    with st.container(border=True):
        ui.html_block('<div class="k-item-title">Add another room</div>')
        with st.form(f"add_room_{prop['id']}", clear_on_submit=True):
            values = _room_fields(f"new{prop['id']}")
            added = st.form_submit_button("Add room", type="primary", icon=":material/add:")
        if added:
            if not values[0].strip() or values[2] <= 0:
                st.error("Room name is required and the rent must be greater than zero.")
            else:
                db.add_room(prop["id"], *values)
                ui.flash(f"Room '{values[0].strip()}' added.")
                st.rerun()


def _photos_editor(prop):
    images = db.get_images(prop["id"])
    if not images:
        ui.html_block('<p class="k-muted">No photos yet. Listings with photos get more inquiries!</p>')
    for start in range(0, len(images), 4):
        cols = st.columns(4)
        for col, img in zip(cols, images[start:start + 4]):
            with col:
                ui.html_block(ui.img_tag(img["image_path"], "k-thumb", 420)
                              + (f'<div style="margin-top:6px">{ui.badge("Main photo", "orange")}</div>'
                                 if img["is_main"] else ""))
                if not img["is_main"] and st.button("Set as main", key=f"main_{img['id']}"):
                    db.set_main_image(prop["id"], img["id"])
                    ui.flash("Main photo updated.")
                    st.rerun()
                if st.button("Remove", key=f"delimg_{img['id']}", icon=":material/delete:"):
                    db.delete_image(img["id"])
                    ui.flash("Photo removed.", "info")
                    st.rerun()
    st.write("")
    with st.form(f"upload_{prop['id']}", clear_on_submit=True):
        files = st.file_uploader("Upload more photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        uploaded = st.form_submit_button("Upload photos", type="primary", icon=":material/upload:")
    if uploaded:
        if not files:
            st.error("Please choose at least one photo.")
        else:
            count = _save_images(prop["id"], files)
            ui.flash(f"{count} photo(s) uploaded." if count else "Those files are not valid images.",
                     "success" if count else "error")
            st.rerun()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def profile_tab(user):
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            ui.html_block('<div class="k-item-title">Landlord profile</div>')
            with st.form("landlord_profile"):
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
        tenant.password_form(user, "landlord_pw")
