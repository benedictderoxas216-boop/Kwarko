"""
listings.py
-----------
Public pages that every visitor can see:
  * home_page()     - hero, search bar, quick filters, featured dorms, locations
  * search_page()   - filters + sorted results
  * details_page()  - full information, reviews, inquiry and application forms
"""

from datetime import date

import streamlit as st

import database as db
import ui

PRICE_LIMIT = 20000          # highest value of the price slider
RATING_OPTIONS = {"Any rating": 0.0, "3.0 and up": 3.0, "3.5 and up": 3.5, "4.0 and up": 4.0, "4.5 and up": 4.5}
ANY_TYPE = "Any room type"


# ---------------------------------------------------------------------------
# Filters are stored in st.session_state.filters (a normal dictionary).
# Widget keys include a "version" number: when the homepage sets new filters
# we increase the version so the search widgets start from the new values.
# ---------------------------------------------------------------------------
def default_filters():
    return {"location": "", "price": (0, PRICE_LIMIT), "room_types": [], "amenities": [],
            "rating": "Any rating", "availability": "Any", "sort": "Most recently added"}


def go_search(**changes):
    """Open the search page with some filters already applied."""
    filters = default_filters()
    filters.update(changes)
    st.session_state.filters = filters
    st.session_state.filter_version += 1
    ui.navigate("search")


# ---------------------------------------------------------------------------
# Listing card (used on home, search and the saved-dorms tab)
# ---------------------------------------------------------------------------
def handle_save(property_id):
    """Save / unsave a dorm. Visitors who are not tenants are asked to log in."""
    if not ui.is_tenant():
        st.session_state.after_login = property_id
        ui.flash("Please log in with a tenant account to save dormitories.", "info")
        ui.navigate("login")
    saved = db.toggle_saved(ui.current_user()["id"], property_id)
    ui.flash("Added to your saved dorms." if saved else "Removed from your saved dorms.",
             "success" if saved else "info")
    st.rerun()


def render_listing_card(prop, key_prefix, saved_ids=frozenset()):
    with st.container(border=True):
        ui.html_block(ui.listing_card_html(prop))
        c1, c2 = st.columns([1.6, 1])
        if c1.button("View Details", key=f"{key_prefix}_view_{prop['id']}", type="primary",
                     icon=":material/visibility:"):
            ui.navigate("details", prop["id"])
        is_saved = prop["id"] in saved_ids
        if c2.button("Saved" if is_saved else "Save", key=f"{key_prefix}_save_{prop['id']}",
                     icon=":material/favorite:" if is_saved else ":material/heart_plus:"):
            handle_save(prop["id"])


def render_grid(properties, key_prefix, columns=3):
    saved_ids = db.get_saved_ids(ui.current_user()["id"]) if ui.is_tenant() else set()
    for start in range(0, len(properties), columns):
        cols = st.columns(columns, gap="medium")
        for col, prop in zip(cols, properties[start:start + columns]):
            with col:
                render_listing_card(prop, key_prefix, saved_ids)


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
LOCATION_COLORS = ["linear-gradient(135deg,#0B2447,#2B5A9E)", "linear-gradient(135deg,#F28C28,#E0612A)",
                   "linear-gradient(135deg,#19376D,#5B8BD0)", "linear-gradient(135deg,#7A4B1E,#F28C28)"]


def home_page():
    stats = db.get_site_stats()
    ui.html_block(
        '<div class="k-hero"><div class="shape"></div>'
        f'<span class="pill">{ui.icon("shield", 13)}&nbsp; Verified listings &middot; Real tenant reviews</span>'
        '<h1>Find Your Space.<br><span>Feel at Home.</span></h1>'
        '<p>Discover affordable and comfortable dormitories that fit your lifestyle and budget with KWARKO.</p>'
        '</div>')

    # ---- Search bar ----
    with st.container(border=True):
        ui.html_block(f'<div class="k-search-title">{ui.icon("search", 16)} Where do you want to stay?</div>')
        c1, c2, c3, c4 = st.columns([2.2, 1.3, 1.3, 1], vertical_alignment="bottom")
        location = c1.text_input("Location", placeholder="City, barangay or dorm name (e.g. Alangilan)",
                                 key="home_location")
        room_type = c2.selectbox("Room type", [ANY_TYPE] + db.ROOM_TYPES, key="home_room_type")
        budget = c3.number_input("Max monthly budget (₱)", min_value=500, max_value=PRICE_LIMIT,
                                 value=10000, step=500, key="home_budget")
        if c4.button("Search", type="primary", icon=":material/search:", key="home_search"):
            go_search(location=location, price=(0, int(budget)),
                      room_types=[] if room_type == ANY_TYPE else [room_type])

        ui.html_block('<div class="k-muted" style="margin-top:6px">Quick filters</div>')
        quick = st.columns(6)
        if quick[0].button("Under ₱3,000", key="q_budget"):
            go_search(price=(0, 3000))
        if quick[1].button("Bedspace", key="q_bedspace"):
            go_search(room_types=["Bedspace"])
        if quick[2].button("Solo rooms", key="q_solo"):
            go_search(room_types=["Solo"])
        if quick[3].button("Air-conditioned", key="q_aircon"):
            go_search(amenities=["Air Conditioning"])
        if quick[4].button("Top rated 4.5+", key="q_rating"):
            go_search(rating="4.5 and up")
        if quick[5].button("Available now", key="q_available"):
            go_search(availability="Available")

    st.write("")
    ui.stat_row([("Dormitories listed", stats["dorms"], "home", False),
                 ("Cities covered", stats["cities"], "pin", True),
                 ("Rooms available now", stats["rooms"], "bed", False),
                 ("Tenant reviews", stats["reviews"], "star", True)])

    # ---- Featured listings ----
    ui.section_header("Featured dormitories", "Top-rated places with rooms available right now.",
                      "Handpicked for you")
    featured = db.get_featured_properties(6)
    if featured:
        render_grid(featured, "feat")
    else:
        ui.empty_state("No listings yet", "Landlords haven't posted any dormitories.")
    _, mid, _ = st.columns([1.3, 1, 1.3])
    if mid.button("Browse all dormitories", key="browse_all", icon=":material/arrow_forward:"):
        go_search()

    # ---- Popular locations ----
    ui.section_header("Popular locations", "Explore dorms near the schools and workplaces you need.",
                      "Where students stay")
    locations = db.get_popular_locations(4)
    if locations:
        cols = st.columns(len(locations), gap="medium")
        for i, (col, loc) in enumerate(zip(cols, locations)):
            with col:
                ui.html_block(f'<div class="k-loc-tile" style="background:{LOCATION_COLORS[i % 4]}">'
                              f'<div class="c">{ui.esc(loc["city"])}</div>'
                              f'<div class="n">{loc["total"]} dorm{"s" if loc["total"] != 1 else ""} &middot; '
                              f'from {ui.money(loc["from_price"])}/mo</div></div>')
                if st.button(f"Explore {loc['city']}", key=f"loc_{i}"):
                    go_search(location=loc["city"])

    # ---- How it works ----
    ui.section_header("How KWARKO works", "Three simple steps from searching to moving in.", "Simple process")
    steps = [("1", "Search & filter", "Look up dorms by location, budget, room type, amenities and ratings."),
             ("2", "Compare & ask", "Check photos, room specs, house rules and reviews. Send the landlord a question."),
             ("3", "Apply & move in", "Submit a rental application and track its status from your dashboard.")]
    cols = st.columns(3, gap="medium")
    for col, (num, title, text) in zip(cols, steps):
        col.markdown(f'<div class="k-step"><div class="num">{num}</div><h4>{title}</h4><p>{text}</p></div>',
                     unsafe_allow_html=True)

    st.write("")
    with st.container():
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.markdown('<div class="k-cta"><h3>Are you a landlord?</h3><p>List your dormitory or boarding house for '
                    'free, manage rooms and availability, and receive applications from verified tenants.</p></div>',
                    unsafe_allow_html=True)
        if ui.is_landlord():
            if c2.button("Go to my dashboard", type="primary", key="cta_dash"):
                ui.navigate("landlord_dashboard")
        elif c2.button("List your property", type="primary", key="cta_list", icon=":material/add_home:"):
            st.session_state.register_as = "Landlord"
            ui.navigate("register")


# ---------------------------------------------------------------------------
# SEARCH PAGE
# ---------------------------------------------------------------------------
def search_page():
    filters = st.session_state.filters
    v = st.session_state.filter_version

    ui.page_banner("Find your next dorm", "Filter by location, budget, room type, amenities and ratings.")

    # ---- Filter bar (two rows) ----
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 1.6], gap="medium")
        filters["location"] = c1.text_input("Location", value=filters["location"], key=f"f_loc_{v}",
                                            placeholder="City, barangay or dorm name")
        filters["price"] = c2.slider("Monthly budget (₱)", 0, PRICE_LIMIT, value=tuple(filters["price"]),
                                     step=500, key=f"f_price_{v}")
        filters["room_types"] = c3.multiselect("Room type", db.ROOM_TYPES, default=filters["room_types"],
                                               key=f"f_types_{v}", placeholder="Any type")
        filters["amenities"] = c4.multiselect("Amenities", db.AMENITIES, default=filters["amenities"],
                                              key=f"f_amen_{v}", placeholder="Any amenities")
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 1.6], gap="medium", vertical_alignment="bottom")
        ratings = list(RATING_OPTIONS)
        filters["rating"] = c1.selectbox("Rating", ratings, index=ratings.index(filters["rating"]),
                                         key=f"f_rating_{v}")
        avail = ["Any", "Available", "Occupied"]
        filters["availability"] = c2.radio("Availability", avail, index=avail.index(filters["availability"]),
                                           key=f"f_avail_{v}", horizontal=True)
        sorts = list(db.SORT_OPTIONS)
        filters["sort"] = c3.selectbox("Sort by", sorts, index=sorts.index(filters["sort"]), key=f"f_sort_{v}")
        if c4.button("Reset filters", key="reset_filters", icon=":material/restart_alt:"):
            go_search()

    # ---- Results ----
    results = db.search_properties(
        location=filters["location"], min_price=filters["price"][0], max_price=filters["price"][1],
        room_types=filters["room_types"], amenities=filters["amenities"],
        min_rating=RATING_OPTIONS[filters["rating"]], availability=filters["availability"],
        sort=filters["sort"])
    ui.html_block(f'<div style="margin:18px 0 10px"><span class="k-item-title" style="font-size:1.2rem">'
                  f'{len(results)} dormitor{"y" if len(results) == 1 else "ies"} found</span>'
                  f'<span class="k-muted"> &nbsp;&middot;&nbsp; sorted by {ui.esc(filters["sort"].lower())}. '
                  f'Prices shown are the lowest monthly rate that matches your filters.</span></div>')
    if results:
        render_grid(results, "res", columns=3)
    else:
        ui.empty_state("No dormitories match your filters",
                       "Try a bigger budget, another location, or fewer amenities.")


# ---------------------------------------------------------------------------
# DETAILS PAGE
# ---------------------------------------------------------------------------
def _lines_to_list(text):
    items = [line.strip("-• ").strip() for line in (text or "").splitlines() if line.strip()]
    if not items:
        return '<div class="k-muted">Not specified.</div>'
    return '<ul class="k-list">' + "".join(f'<li>{ui.icon("check", 15)}<span>{ui.esc(i)}</span></li>'
                                           for i in items) + "</ul>"


def _gallery(images, name):
    paths = [img["image_path"] for img in images]
    if not paths:
        ui.html_block(f'<div class="k-gallery single" style="grid-template-rows:300px">{ui.img_tag(None)}</div>')
        return
    if len(paths) == 1:
        ui.html_block(f'<div class="k-gallery single" style="grid-template-rows:400px">'
                      f'{ui.img_tag(paths[0], max_width=1200, alt=name)}</div>')
    else:
        side = "".join(f'<div class="side">{ui.img_tag(p, max_width=640, alt=name)}</div>' for p in paths[1:3])
        ui.html_block(f'<div class="k-gallery"><div class="main">{ui.img_tag(paths[0], max_width=1200, alt=name)}'
                      f'</div>{side}</div>')
    if len(paths) > 3:
        with st.expander(f"View all {len(paths)} photos"):
            cols = st.columns(3)
            for i, p in enumerate(paths):
                cols[i % 3].markdown(ui.img_tag(p, "k-thumb", 480, name), unsafe_allow_html=True)


def details_page():
    prop = db.get_property(st.session_state.get("selected_property"))
    if not prop:
        ui.empty_state("Dormitory not found", "It may have been removed by the landlord.")
        if st.button("Back to search", key="notfound_back"):
            ui.navigate("search")
        return

    user = ui.current_user()
    rooms = db.get_rooms(prop["id"])
    available_rooms = [r for r in rooms if r["availability"] == "Available"]

    c1, c2 = st.columns([1, 5])
    if c1.button("Back", key="details_back", icon=":material/arrow_back:"):
        ui.navigate("search")

    # ---- Title ----
    gender = ui.badge(prop["gender_policy"], "info") if prop["gender_policy"] != "Mixed" else ui.badge("Mixed", "neutral")
    avail = ui.badge(f"{len(available_rooms)} room(s) available", "success") if available_rooms \
        else ui.badge("Fully occupied", "danger")
    ui.html_block(
        f'<div class="k-title"><h1>{ui.esc(prop["name"])}</h1></div>'
        f'<div class="k-meta" style="font-size:.92rem;margin:6px 0 16px">'
        f'<span>{ui.rating_pill(prop["avg_rating"], prop["review_count"])}</span>'
        f'<span>{ui.icon("pin", 15)} {ui.esc(prop["address"])}, {ui.esc(prop["city"])}</span>'
        f'<span>{gender}</span><span>{avail}</span></div>')
    _gallery(db.get_images(prop["id"]), prop["name"])
    st.write("")

    left, right = st.columns([1.75, 1], gap="large")

    # ================= LEFT: information =================
    with left:
        ui.html_block('<h3>About this place</h3>'
                      f'<p style="color:#334155">{ui.esc(prop["description"])}</p>')

        ui.html_block('<h3>Rooms &amp; specifications</h3>')
        for r in rooms:
            ui.html_block(
                f'<div class="k-room"><div><h5>{ui.esc(r["room_name"])}</h5>'
                f'<div class="k-chips" style="margin-bottom:6px"><span class="k-chip">{ui.esc(r["room_type"])}</span>'
                f'{ui.status_badge(r["availability"])}</div>'
                f'<div class="k-meta" style="margin-top:4px"><span>{ui.icon("users", 14)} {r["capacity"]} occupant(s)</span>'
                + (f'<span>{ui.icon("ruler", 14)} {ui.esc(r["dimensions"])}</span>' if r["dimensions"] else "")
                + '</div>'
                + (f'<div class="k-muted" style="margin-top:6px">{ui.esc(r["specs"])}</div>' if r["specs"] else "")
                + f'</div><div class="price">{ui.money(r["price"])}<br><small>per month</small></div></div>')

        ui.html_block('<h3>Amenities &amp; facilities</h3><div class="k-chips">'
                      + "".join(f'<span class="k-chip" style="font-size:.85rem;padding:7px 14px">'
                                f'{ui.icon("check", 14)} {ui.esc(a)}</span>' for a in prop["amenities"])
                      + "</div>")
        c1, c2 = st.columns(2, gap="medium")
        c1.markdown('<h3>House rules</h3>' + _lines_to_list(prop["house_rules"]), unsafe_allow_html=True)
        c2.markdown('<h3>Rental requirements</h3>' + _lines_to_list(prop["requirements"]), unsafe_allow_html=True)

        _reviews_section(prop, user)

    # ================= RIGHT: price, contact, actions =================
    with right:
        with st.container(border=True):
            low = min((r["price"] for r in available_rooms), default=prop["min_price"])
            ui.html_block(f'<div class="k-pricebox"><div class="from">Starting at</div>'
                          f'<div class="amt">{ui.money(low)} <small>/ month</small></div>'
                          f'<div class="k-muted" style="margin-top:4px">{len(available_rooms)} of {len(rooms)} '
                          f'rooms available</div></div>')
            if ui.is_tenant():
                is_saved = prop["id"] in db.get_saved_ids(user["id"])
                if st.button("Saved to favorites" if is_saved else "Save this dorm", key="detail_save",
                             icon=":material/favorite:" if is_saved else ":material/heart_plus:"):
                    handle_save(prop["id"])

        with st.container(border=True):
            ui.html_block(
                '<div class="k-item-title" style="margin-bottom:10px">Landlord contact</div>'
                f'<div class="k-contact"><div class="k-avatar">{ui.initials(prop["landlord_name"])}</div>'
                f'<div><b style="color:#0B2447">{ui.esc(prop["landlord_name"])}</b>'
                '<div class="k-muted">Property owner</div></div></div>'
                f'<div class="k-meta" style="flex-direction:column;gap:6px;margin-top:12px">'
                f'<span>{ui.icon("phone", 14)} {ui.esc(prop["contact_phone"] or prop["landlord_phone"])}</span>'
                f'<span>{ui.icon("mail", 14)} {ui.esc(prop["contact_email"] or prop["landlord_email"])}</span></div>')

        with st.container(border=True):
            _action_panel(prop, user, available_rooms)


def _action_panel(prop, user, available_rooms):
    """Send Inquiry / Apply for Room - only for logged-in tenants."""
    if not user:
        ui.html_block('<div class="k-item-title">Interested in this dorm?</div>'
                      '<p class="k-muted">Log in or create a tenant account to send an inquiry or apply for a room.</p>')
        c1, c2 = st.columns(2)
        if c1.button("Log in", type="primary", key="act_login"):
            st.session_state.after_login = prop["id"]
            ui.navigate("login")
        if c2.button("Sign up", key="act_signup"):
            st.session_state.after_login = prop["id"]
            st.session_state.register_as = "Tenant"
            ui.navigate("register")
        return
    if user["role"] == "landlord":
        ui.html_block('<div class="k-item-title">Landlord view</div>'
                      '<p class="k-muted">Inquiries and applications can only be sent from tenant accounts.</p>')
        if prop["landlord_id"] == user["id"] and st.button("Manage this listing", type="primary", key="act_manage"):
            st.session_state.manage_property = prop["id"]
            st.session_state.pending_menu = "Property Management"
            ui.navigate("landlord_dashboard")
        return

    tab_inquiry, tab_apply = st.tabs(["Send Inquiry", "Apply for Room"])
    with tab_inquiry:
        with st.form("inquiry_form", clear_on_submit=True):
            subject = st.text_input("Subject", placeholder="e.g. Is Wi-Fi included?")
            message = st.text_area("Your message", height=120,
                                   placeholder="Ask the landlord about rates, visits, rules...")
            sent = st.form_submit_button("Send Inquiry", type="primary", icon=":material/send:")
        if sent:
            if not subject.strip() or not message.strip():
                st.error("Please fill in both the subject and the message.")
            else:
                db.create_inquiry(prop["id"], user["id"], subject, message)
                ui.flash("Your inquiry was sent! You'll see the landlord's reply in your dashboard.")
                st.rerun()

    with tab_apply:
        if not available_rooms:
            ui.html_block('<div class="k-flash warning">All rooms are currently occupied. '
                          'Save this dorm or send an inquiry to ask about future openings.</div>')
            return
        room_labels = {r["id"]: f'{r["room_name"]} - {r["room_type"]} - {ui.money(r["price"])}/mo'
                       for r in available_rooms}
        with st.form("apply_form"):
            room_id = st.selectbox("Room", list(room_labels), format_func=room_labels.get)
            c1, c2 = st.columns(2)
            move_in = c1.date_input("Move-in date", value=date.today(), min_value=date.today())
            months = c2.number_input("Length of stay (months)", min_value=1, max_value=24, value=6)
            occupation = st.selectbox("Occupation", ["Student", "Working Professional", "Other"])
            school = st.text_input("School / Workplace", placeholder="e.g. Batangas State University")
            phone = st.text_input("Contact number", value=user.get("phone") or "")
            message = st.text_area("Message to the landlord (optional)", height=80)
            agree = st.checkbox("I have read the house rules and rental requirements.")
            applied = st.form_submit_button("Submit Application", type="primary", icon=":material/assignment:")
        if applied:
            if not school.strip() or not phone.strip():
                st.error("Please enter your school/workplace and contact number.")
            elif not agree:
                st.error("Please confirm that you have read the house rules and requirements.")
            elif db.has_active_application(user["id"], room_id):
                st.warning("You already have an active application for this room. Check your dashboard.")
            else:
                db.create_application(prop["id"], room_id, user["id"], move_in, months, occupation,
                                      school, phone, message)
                ui.flash("Application submitted! Track its status under 'My Applications' in your dashboard.")
                st.rerun()


def _reviews_section(prop, user):
    summary = db.get_review_summary(prop["id"])
    reviews = db.get_reviews(prop["id"])
    ui.html_block('<h3>Reviews &amp; ratings</h3>')
    if summary["total"]:
        c1, c2 = st.columns([1, 2], gap="medium")
        c1.markdown(f'<div class="k-bigrating">{summary["rating"]:.1f}</div>{ui.stars(summary["rating"], "1.2rem")}'
                    f'<div class="k-muted">{summary["total"]} review{"s" if summary["total"] != 1 else ""}</div>',
                    unsafe_allow_html=True)
        bars = ""
        for label in ("cleanliness", "security", "location", "affordability"):
            value = summary[label] or 0
            bars += (f'<div class="k-bar"><span style="width:100px">{label.title()}</span>'
                     f'<div class="track"><div class="fill" style="width:{value / 5 * 100:.0f}%"></div></div>'
                     f'<b>{value:.1f}</b></div>')
        c2.markdown(bars, unsafe_allow_html=True)
        ui.html_block("".join(
            f'<div class="k-review"><div class="who"><div class="k-avatar">{ui.initials(r["tenant_name"])}</div>'
            f'<div><b style="color:#0B2447">{ui.esc(r["tenant_name"])}</b><div class="k-muted">'
            f'{ui.stars(r["rating"])} &middot; {ui.fmt_date(r["created_at"])}</div></div></div>'
            f'<p>{ui.esc(r["comment"])}</p></div>' for r in reviews))
    else:
        ui.html_block('<p class="k-muted">No reviews yet. Tenants who stayed here can be the first to review.</p>')

    # ---- Review form (only tenants with an accepted application) ----
    if not ui.is_tenant():
        return
    if db.has_reviewed(user["id"], prop["id"]):
        ui.html_block('<div class="k-flash success" style="margin-top:12px">Thanks! You have already reviewed '
                      'this dormitory.</div>')
        return
    if not db.can_review(user["id"], prop["id"]):
        ui.html_block('<p class="k-muted" style="margin-top:12px">Only tenants with an accepted application at this '
                      'dorm can leave a review.</p>')
        return
    st.write("")
    with st.container(border=True):
        ui.html_block('<div class="k-item-title">Write a review</div>'
                      '<div class="k-muted">You stayed here - share your experience with other tenants.</div>')
        score_labels = {5: "★★★★★  Excellent", 4: "★★★★  Very good", 3: "★★★  Average", 2: "★★  Poor",
                        1: "★  Terrible"}
        optional = ["Not rated", 5, 4, 3, 2, 1]
        with st.form("review_form"):
            rating = st.radio("Overall rating", [5, 4, 3, 2, 1], format_func=score_labels.get, horizontal=True)
            st.caption("Optional: rate specific areas")
            cols = st.columns(4)
            parts = {}
            for col, label in zip(cols, ("Cleanliness", "Security", "Location", "Affordability")):
                parts[label.lower()] = col.selectbox(label, optional, key=f"rv_{label}")
            comment = st.text_area("Your review", height=100, placeholder="What was it like to live here?")
            posted = st.form_submit_button("Post Review", type="primary", icon=":material/rate_review:")
        if posted:
            if len(comment.strip()) < 10:
                st.error("Please write at least a short sentence (10+ characters).")
            else:
                values = {k: (None if v == "Not rated" else int(v)) for k, v in parts.items()}
                if db.add_review(prop["id"], user["id"], rating, comment, **values):
                    ui.flash("Thank you! Your review has been posted.")
                else:
                    ui.flash("You have already reviewed this dormitory.", "warning")
                st.rerun()
