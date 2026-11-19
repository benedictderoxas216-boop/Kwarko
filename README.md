# KWARKO – Dormitory Finder and Rental Platform

**"Find Your Space. Feel at Home."**

KWARKO is a working website prototype that connects tenants (students, workers and anyone looking for a room) with landlords of dormitories, boarding houses and rental rooms. It is built with **Python + Streamlit + SQLite** and runs locally on Windows.

---

## 1. Quick start (Windows)

### Option A – one double-click
Double-click **`run_kwarko.bat`**. The first time, it creates a virtual environment and installs the requirements (internet needed once). Then the website opens in your browser.

### Option B – typed commands
Open **Command Prompt** inside the `KWARKO` folder and run:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The website opens at **http://localhost:8501**. Stop it with `Ctrl + C` in the Command Prompt.

Next time you only need:

```bat
venv\Scripts\activate
streamlit run app.py
```

> Requires Python 3.9 or newer (python.org). During installation tick **"Add Python to PATH"**.

### Demo accounts

| Role     | Email                | Password      |
|----------|----------------------|---------------|
| Tenant   | tenant@kwarko.ph     | tenant123     |
| Landlord | landlord@kwarko.ph   | landlord123   |

The login page also has **"Use demo tenant"** and **"Use demo landlord"** buttons. Other sample accounts (e.g. `juan.reyes@kwarko.ph`, `grace.tan@kwarko.ph`) use the password `password123`.

### Reset the sample data
Close the app, delete **`kwarko.db`**, and start the app again. The database is recreated with fresh sample data automatically.

---

## 2. Project structure

```
KWARKO/
├── app.py                  Main file: page setup, navigation bar, page router
├── database.py             SQLite tables, all queries, sample data
├── auth.py                 Login, registration, logout
├── listings.py             Homepage, search & filters, dormitory details page
├── tenant.py               Tenant dashboard
├── landlord.py             Landlord dashboard
├── ui.py                   Design: custom CSS, cards, badges, footer, navigation helpers
├── make_sample_images.py   Draws the logo and sample dorm pictures (runs automatically if missing)
├── requirements.txt        Python packages to install
├── run_kwarko.bat          Windows one-click launcher
├── .streamlit/config.toml  Theme colors (navy + orange)
├── assets/
│   ├── logo.png
│   ├── images/             Sample dorm pictures (dorm01_1.jpg ...)
│   └── uploads/            Photos uploaded by landlords
└── kwarko.db               SQLite database (created on first run)
```

---

## 3. Website architecture (Step 1 – Project Planning)

KWARKO is a **single Streamlit app** with simple page switching.

1. `app.py` runs from top to bottom every time the user clicks something (this is how Streamlit works).
2. It creates the database if needed, loads the CSS, and draws the **navigation bar**.
3. It checks `st.session_state.page` and calls the matching page function.
4. Pages never write SQL themselves – they call functions in `database.py` (e.g. `db.search_properties(...)`, `db.create_application(...)`).
5. Whoever is logged in is stored in `st.session_state.user`. Dashboards check the role before opening.

```
 Browser  ──>  app.py (router + navbar)
                  │
     ┌────────────┼──────────────┬──────────────┬──────────────┐
 listings.py   auth.py       tenant.py      landlord.py      ui.py (design)
     └────────────┴──────────────┴──────────────┘
                         │
                   database.py  ──>  kwarko.db (SQLite)
```

### Main pages and navigation flow

```
Home ──(search bar / quick filters / location tiles)──> Search results ──(View Details)──> Dormitory Details
 │                                                                                         │
 ├── Log in / Sign up (choose Tenant or Landlord)                                          ├── Save dorm
 │        ├── Tenant  ──> Tenant Dashboard                                                 ├── Send Inquiry   (tenant)
 │        └── Landlord ─> Landlord Dashboard                                               ├── Apply for Room (tenant)
 │                                                                                         └── Write Review   (tenant who stayed)
 └── "List your property" ──> Register as Landlord
```

* Visitors can browse, search and view details. To save, inquire or apply they are asked to log in, and are returned to the same dorm after logging in.
* Tenant Dashboard: My Applications, My Inquiries, Saved Dorms, Rental History & Reviews, Profile.
* Landlord Dashboard: My Listings, Add New Listing, Inquiries, Applications, Property Management, Profile.

---

## 4. Database structure

| Table | What it stores | Key relationships |
|---|---|---|
| `users` | Tenant and landlord accounts (password is salted + hashed) | `role` = tenant / landlord |
| `properties` | Dormitory listings: name, address, barangay, city, description, house rules, requirements, contact | `landlord_id` → users |
| `rooms` | Room specifications: name, type, monthly price, capacity, dimensions, specs, availability | `property_id` → properties |
| `property_images` | Photo file paths, one marked as main photo | `property_id` → properties |
| `property_amenities` | Amenities of each dorm (Wi-Fi, aircon, ...) | `property_id` → properties |
| `inquiries` | Tenant questions and landlord replies (Open / Replied) | `property_id`, `tenant_id` |
| `applications` | Rental applications (Pending / Under Review / Accepted / Rejected) | `property_id`, `room_id`, `tenant_id` |
| `reviews` | 1–5 star rating, comment, optional cleanliness / security / location / affordability | `property_id`, `tenant_id`, **UNIQUE(property, tenant)** |
| `saved_properties` | Bookmarked dorms | `tenant_id`, `property_id` |

```
users (landlord) 1───* properties 1───* rooms
                         │  1───* property_images
                         │  1───* property_amenities
                         │  1───* reviews        *───1 users (tenant)
                         │  1───* inquiries      *───1 users (tenant)
                         │  1───* applications   *───1 users (tenant), *───1 rooms
                         └  1───* saved_properties *─1 users (tenant)
```

Deleting a listing also deletes its rooms, photos, inquiries, applications and reviews (`ON DELETE CASCADE`).

---

## 5. Features checklist

**Tenant**
- Browse and search dorms by location (city, barangay or name)
- Filters: price range, room type, amenities, rating, availability
- Sort: lowest price, highest price, highest rating, most recently added
- Details page: photos, rooms & specs, dimensions, amenities, house rules, requirements, landlord contact, reviews
- Send inquiries, apply for a room, save/bookmark dorms
- Dashboard: application statuses (and cancel while Pending), landlord replies, saved dorms, rental history, profile & password
- Reviews: only tenants with an **Accepted** application may review, and only once per dorm

**Landlord**
- Add listings with the first room, amenities, rules, requirements and photos
- Edit details, amenities, house rules and requirements
- Add / edit / delete rooms, set prices, capacity, room type and availability
- Upload photos, choose the main photo, remove photos
- Reply to inquiries, review applicant information, accept / reject / mark Under Review with a note
- Optionally mark a room as Occupied when accepting
- Delete listings (with confirmation)

**Not included on purpose** (per project scope): online payments, GPS, AI recommendations, real-time chat, external APIs, document processing, complex verification.

---

## 6. Suggested demo script for the presentation

1. **Home page** – show the hero, search bar, quick filters, featured dorms and popular locations.
2. Click **"Bedspace"** quick filter → change budget and sorting on the search page.
3. Open **Alangilan Student Residences** → photos, rooms, rules, reviews.
4. In the "Interested in this dorm?" box click **Log in** → **Use demo tenant** (you return to the same dorm) → **Send Inquiry** and **Apply for Room**.
5. Open **My Dashboard** → show the application statuses, landlord reply, saved dorms.
6. In **Rental History**, click **Write a review** on Pallocan Haven and post a review.
7. **Log out** → **Use demo landlord** → **Applications**: accept Juan's application → **Inquiries**: reply.
8. **Add New Listing** with a photo → see it appear in search results.
9. **Property Management** → change a price or mark a room Occupied → show the change on the public page.

---

## 7. Customizing

* **Real photos:** upload them from the Landlord Dashboard, or replace files in `assets/images/` (keep the same names). The included pictures are simple illustrations drawn by `make_sample_images.py`.
* **Colors:** edit `.streamlit/config.toml` and the `:root` colors at the top of the CSS in `ui.py`.
* **Sample dorms:** edit `SAMPLE_PROPERTIES` and `SAMPLE_REVIEWS` in `database.py`, then delete `kwarko.db`.
* **Amenities / room types:** edit the lists at the top of `database.py`.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick "Add Python to PATH", or use `py` instead of `python`. |
| `'streamlit' is not recognized` | Activate the environment first: `venv\Scripts\activate` (or run `python -m streamlit run app.py`). |
| PowerShell blocks `activate` | Use Command Prompt instead, or run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| Port already in use | `streamlit run app.py --server.port 8502` |
| Weird data after testing | Delete `kwarko.db` and restart. |
