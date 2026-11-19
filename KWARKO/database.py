"""
database.py
-----------
All SQLite logic for KWARKO lives here:
  * the table definitions (schema)
  * small helper functions to run queries
  * functions used by the pages (users, listings, rooms, inquiries, ...)
  * the sample data that is loaded the first time the app runs

The pages never write SQL themselves - they only call the functions below.
That keeps the user-interface code short and easy to explain.
"""

import hashlib
import secrets
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # the KWARKO folder
DB_PATH = BASE_DIR / "kwarko.db"                    # the SQLite database file
UPLOAD_DIR = BASE_DIR / "assets" / "uploads"        # photos uploaded by landlords

ROOM_TYPES = ["Solo", "Shared", "Bedspace", "Private Room"]
AVAILABILITY = ["Available", "Occupied"]
APPLICATION_STATUSES = ["Pending", "Under Review", "Accepted", "Rejected"]
GENDER_POLICIES = ["Mixed", "Female only", "Male only"]
AMENITIES = [
    "Wi-Fi", "Air Conditioning", "Laundry Area", "Kitchen", "Parking",
    "CCTV / Security", "Study Area", "Private CR", "Refrigerator",
    "Water Included", "Electricity Included", "Near Transport",
]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def get_connection():
    """Open a connection. Rows behave like dictionaries (row['name'])."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # needed for ON DELETE CASCADE
    return conn


def fetch_all(sql, params=()):
    """Run a SELECT and return a list of dictionaries."""
    with closing(get_connection()) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def fetch_one(sql, params=()):
    """Run a SELECT and return one dictionary (or None)."""
    with closing(get_connection()) as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE. Returns the new row id (for INSERT)."""
    with closing(get_connection()) as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('tenant', 'landlord')),
    phone         TEXT DEFAULT '',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS properties (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    address       TEXT NOT NULL,
    barangay      TEXT DEFAULT '',
    city          TEXT NOT NULL,
    gender_policy TEXT DEFAULT 'Mixed',
    description   TEXT DEFAULT '',
    house_rules   TEXT DEFAULT '',
    requirements  TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    contact_email TEXT DEFAULT '',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id  INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_name    TEXT NOT NULL,
    room_type    TEXT NOT NULL,
    price        REAL NOT NULL,
    capacity     INTEGER NOT NULL DEFAULT 1,
    dimensions   TEXT DEFAULT '',
    specs        TEXT DEFAULT '',
    availability TEXT NOT NULL DEFAULT 'Available'
                 CHECK (availability IN ('Available', 'Occupied'))
);

CREATE TABLE IF NOT EXISTS property_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    image_path  TEXT NOT NULL,
    is_main     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS property_amenities (
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    amenity     TEXT NOT NULL,
    PRIMARY KEY (property_id, amenity)
);

CREATE TABLE IF NOT EXISTS inquiries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    tenant_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject     TEXT NOT NULL,
    message     TEXT NOT NULL,
    reply       TEXT DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'Replied')),
    created_at  TEXT NOT NULL,
    replied_at  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS applications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id    INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id        INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    tenant_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    move_in_date   TEXT NOT NULL,
    stay_months    INTEGER NOT NULL DEFAULT 6,
    occupation     TEXT DEFAULT '',
    school_or_work TEXT DEFAULT '',
    contact_phone  TEXT DEFAULT '',
    message        TEXT DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'Pending'
                   CHECK (status IN ('Pending', 'Under Review', 'Accepted', 'Rejected')),
    landlord_note  TEXT DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id   INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    tenant_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating        INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    cleanliness   INTEGER,
    security      INTEGER,
    location      INTEGER,
    affordability INTEGER,
    comment       TEXT DEFAULT '',
    created_at    TEXT NOT NULL,
    UNIQUE (property_id, tenant_id)          -- one review per tenant per dorm
);

CREATE TABLE IF NOT EXISTS saved_properties (
    tenant_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (tenant_id, property_id)
);
"""


def init_db():
    """Create the tables (if needed) and load sample data on the first run."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        seed_sample_data()


# ---------------------------------------------------------------------------
# Users and authentication
# ---------------------------------------------------------------------------
def hash_password(password, salt=None):
    """Hash a password with a random salt (PBKDF2). Returns (hash, salt)."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 60_000)
    return digest.hex(), salt


def _public_user(row):
    """Remove the password fields before giving the user to the UI."""
    if not row:
        return None
    return {k: row[k] for k in ("id", "full_name", "email", "role", "phone", "created_at")}


def create_user(full_name, email, password, role, phone="", created_at=None):
    """Create an account. Returns the new user id, or None if the email exists."""
    email = email.strip().lower()
    if fetch_one("SELECT id FROM users WHERE email = ?", (email,)):
        return None
    pw_hash, salt = hash_password(password)
    return execute(
        "INSERT INTO users (full_name, email, password_hash, salt, role, phone, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (full_name.strip(), email, pw_hash, salt, role, phone.strip(), created_at or now_str()),
    )


def authenticate(email, password):
    """Return the user (without password) if the email/password are correct."""
    row = fetch_one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    if row and hash_password(password, row["salt"])[0] == row["password_hash"]:
        return _public_user(row)
    return None


def get_user(user_id):
    return _public_user(fetch_one("SELECT * FROM users WHERE id = ?", (user_id,)))


def update_user_profile(user_id, full_name, phone):
    execute("UPDATE users SET full_name = ?, phone = ? WHERE id = ?",
            (full_name.strip(), phone.strip(), user_id))


def change_password(user_id, current_password, new_password):
    """Returns True if the current password was correct and the change was saved."""
    row = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not row or hash_password(current_password, row["salt"])[0] != row["password_hash"]:
        return False
    pw_hash, salt = hash_password(new_password)
    execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (pw_hash, salt, user_id))
    return True


# ---------------------------------------------------------------------------
# Listings: searching and reading
# ---------------------------------------------------------------------------
# This SELECT is shared by the search page, the homepage and the dashboards.
# For every property it also calculates: lowest price, room types, rating,
# number of reviews, number of available rooms and the main photo.
_LISTING_SELECT = """
SELECT p.*,
       u.full_name AS landlord_name,
       MIN(r.price)                       AS min_price,
       MAX(r.price)                       AS max_price,
       GROUP_CONCAT(DISTINCT r.room_type) AS room_types,
       MAX(r.capacity)                    AS max_capacity,
       COUNT(r.id)                        AS room_count,
       SUM(CASE WHEN r.availability = 'Available' THEN 1 ELSE 0 END) AS available_rooms,
       (SELECT ROUND(AVG(rv.rating), 1) FROM reviews rv WHERE rv.property_id = p.id) AS avg_rating,
       (SELECT COUNT(*) FROM reviews rv WHERE rv.property_id = p.id)                 AS review_count,
       (SELECT image_path FROM property_images pi WHERE pi.property_id = p.id
         ORDER BY pi.is_main DESC, pi.id LIMIT 1)                                     AS main_image
FROM properties p
JOIN users u ON u.id = p.landlord_id
"""

SORT_OPTIONS = {
    "Most recently added": "p.created_at DESC",
    "Lowest price": "min_price ASC",
    "Highest price": "min_price DESC",
    "Highest rating": "COALESCE(avg_rating, 0) DESC, review_count DESC",
}


def _attach_amenities(listings):
    """Add an 'amenities' list and a 'room_type_list' to every listing."""
    if not listings:
        return listings
    ids = [p["id"] for p in listings]
    marks = ",".join("?" * len(ids))
    rows = fetch_all(f"SELECT property_id, amenity FROM property_amenities "
                     f"WHERE property_id IN ({marks}) ORDER BY amenity", ids)
    by_property = {}
    for row in rows:
        by_property.setdefault(row["property_id"], []).append(row["amenity"])
    for p in listings:
        p["amenities"] = by_property.get(p["id"], [])
        types = (p.get("room_types") or "").split(",")
        p["room_type_list"] = [t for t in ROOM_TYPES if t in types]
    return listings


def search_properties(location="", min_price=0, max_price=None, room_types=None,
                      amenities=None, min_rating=0, availability="Any",
                      sort="Most recently added", limit=None):
    """
    Search dormitories using the filters from the search page.
    Room filters (price, type, availability) decide which rooms are counted,
    so the "starting price" shown always matches the tenant's filters.
    """
    room_conditions = ["r.price >= ?"]
    params = [min_price]
    if max_price is not None:
        room_conditions.append("r.price <= ?")
        params.append(max_price)
    if room_types:
        room_conditions.append(f"r.room_type IN ({','.join('?' * len(room_types))})")
        params.extend(room_types)
    if availability == "Available":
        room_conditions.append("r.availability = 'Available'")

    where = ["1 = 1"]
    if location.strip():
        like = f"%{location.strip()}%"
        where.append("(p.name LIKE ? OR p.address LIKE ? OR p.barangay LIKE ? OR p.city LIKE ?)")
        params.extend([like] * 4)
    for amenity in amenities or []:
        where.append("EXISTS (SELECT 1 FROM property_amenities pa "
                     "WHERE pa.property_id = p.id AND pa.amenity = ?)")
        params.append(amenity)
    if availability == "Occupied":
        where.append("NOT EXISTS (SELECT 1 FROM rooms r2 "
                     "WHERE r2.property_id = p.id AND r2.availability = 'Available')")

    sql = (_LISTING_SELECT.replace("JOIN users u ON u.id = p.landlord_id",
                                   "JOIN users u ON u.id = p.landlord_id\n"
                                   "JOIN rooms r ON r.property_id = p.id AND "
                                   + " AND ".join(room_conditions))
           + " WHERE " + " AND ".join(where)
           + " GROUP BY p.id"
           + " HAVING COALESCE(avg_rating, 0) >= ?"
           + " ORDER BY " + SORT_OPTIONS.get(sort, SORT_OPTIONS["Most recently added"]))
    params.append(min_rating or 0)
    if limit:
        sql += f" LIMIT {int(limit)}"
    return _attach_amenities(fetch_all(sql, params))


def get_featured_properties(limit=6):
    """Top-rated dorms that still have an available room (for the homepage)."""
    return search_properties(availability="Available", sort="Highest rating", limit=limit)


def get_popular_locations(limit=4):
    return fetch_all(
        "SELECT city, COUNT(*) AS total, MIN(r.min_price) AS from_price FROM properties p "
        "JOIN (SELECT property_id, MIN(price) AS min_price FROM rooms GROUP BY property_id) r "
        "ON r.property_id = p.id GROUP BY city ORDER BY total DESC, city LIMIT ?", (limit,))


def get_site_stats():
    return fetch_one(
        "SELECT (SELECT COUNT(*) FROM properties) AS dorms,"
        " (SELECT COUNT(DISTINCT city) FROM properties) AS cities,"
        " (SELECT COUNT(*) FROM rooms WHERE availability = 'Available') AS rooms,"
        " (SELECT COUNT(*) FROM reviews) AS reviews")


def get_property(property_id):
    """One dormitory with all of its information (used by the details page)."""
    rows = fetch_all(
        _LISTING_SELECT.replace("JOIN users u ON u.id = p.landlord_id",
                                "JOIN users u ON u.id = p.landlord_id "
                                "LEFT JOIN rooms r ON r.property_id = p.id")
        + " WHERE p.id = ? GROUP BY p.id", (property_id,))
    if not rows:
        return None
    prop = _attach_amenities(rows)[0]
    landlord = fetch_one("SELECT full_name, email, phone FROM users WHERE id = ?",
                         (prop["landlord_id"],))
    prop["landlord_email"] = landlord["email"]
    prop["landlord_phone"] = landlord["phone"]
    return prop


def get_rooms(property_id, only_available=False):
    sql = "SELECT * FROM rooms WHERE property_id = ?"
    if only_available:
        sql += " AND availability = 'Available'"
    return fetch_all(sql + " ORDER BY price", (property_id,))


def get_room(room_id):
    return fetch_one("SELECT * FROM rooms WHERE id = ?", (room_id,))


def get_images(property_id):
    return fetch_all("SELECT * FROM property_images WHERE property_id = ? "
                     "ORDER BY is_main DESC, id", (property_id,))


def get_amenities(property_id):
    return [r["amenity"] for r in fetch_all(
        "SELECT amenity FROM property_amenities WHERE property_id = ? ORDER BY amenity",
        (property_id,))]


# ---------------------------------------------------------------------------
# Landlord: managing listings, rooms and photos
# ---------------------------------------------------------------------------
def get_landlord_properties(landlord_id):
    sql = (_LISTING_SELECT.replace("JOIN users u ON u.id = p.landlord_id",
                                   "JOIN users u ON u.id = p.landlord_id "
                                   "LEFT JOIN rooms r ON r.property_id = p.id")
           + " WHERE p.landlord_id = ? GROUP BY p.id ORDER BY p.created_at DESC")
    return _attach_amenities(fetch_all(sql, (landlord_id,)))


def owns_property(landlord_id, property_id):
    return fetch_one("SELECT id FROM properties WHERE id = ? AND landlord_id = ?",
                     (property_id, landlord_id)) is not None


def create_property(landlord_id, name, address, barangay, city, gender_policy, description,
                    house_rules, requirements, contact_phone, contact_email, created_at=None):
    return execute(
        "INSERT INTO properties (landlord_id, name, address, barangay, city, gender_policy,"
        " description, house_rules, requirements, contact_phone, contact_email, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (landlord_id, name.strip(), address.strip(), barangay.strip(), city.strip(),
         gender_policy, description.strip(), house_rules.strip(), requirements.strip(),
         contact_phone.strip(), contact_email.strip(), created_at or now_str()))


def update_property(landlord_id, property_id, name, address, barangay, city, gender_policy,
                    description, house_rules, requirements, contact_phone, contact_email):
    execute(
        "UPDATE properties SET name = ?, address = ?, barangay = ?, city = ?, gender_policy = ?,"
        " description = ?, house_rules = ?, requirements = ?, contact_phone = ?, contact_email = ?"
        " WHERE id = ? AND landlord_id = ?",
        (name.strip(), address.strip(), barangay.strip(), city.strip(), gender_policy,
         description.strip(), house_rules.strip(), requirements.strip(), contact_phone.strip(),
         contact_email.strip(), property_id, landlord_id))


def delete_property(landlord_id, property_id):
    """Delete a listing. Rooms, photos, inquiries, etc. are removed by CASCADE."""
    if not owns_property(landlord_id, property_id):
        return False
    for img in get_images(property_id):
        _remove_uploaded_file(img["image_path"])
    execute("DELETE FROM properties WHERE id = ? AND landlord_id = ?", (property_id, landlord_id))
    return True


def set_amenities(property_id, amenities):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM property_amenities WHERE property_id = ?", (property_id,))
        conn.executemany("INSERT INTO property_amenities (property_id, amenity) VALUES (?, ?)",
                         [(property_id, a) for a in dict.fromkeys(amenities)])
        conn.commit()


def add_room(property_id, room_name, room_type, price, capacity, dimensions="", specs="",
             availability="Available"):
    return execute(
        "INSERT INTO rooms (property_id, room_name, room_type, price, capacity, dimensions,"
        " specs, availability) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (property_id, room_name.strip(), room_type, float(price), int(capacity),
         dimensions.strip(), specs.strip(), availability))


def update_room(room_id, room_name, room_type, price, capacity, dimensions, specs, availability):
    execute(
        "UPDATE rooms SET room_name = ?, room_type = ?, price = ?, capacity = ?, dimensions = ?,"
        " specs = ?, availability = ? WHERE id = ?",
        (room_name.strip(), room_type, float(price), int(capacity), dimensions.strip(),
         specs.strip(), availability, room_id))


def set_room_availability(room_id, availability):
    execute("UPDATE rooms SET availability = ? WHERE id = ?", (availability, room_id))


def delete_room(room_id):
    execute("DELETE FROM rooms WHERE id = ?", (room_id,))


def add_image(property_id, image_path, is_main=False):
    # The first photo of a property automatically becomes the main photo.
    if not get_images(property_id):
        is_main = True
    if is_main:
        execute("UPDATE property_images SET is_main = 0 WHERE property_id = ?", (property_id,))
    return execute("INSERT INTO property_images (property_id, image_path, is_main) VALUES (?, ?, ?)",
                   (property_id, image_path, 1 if is_main else 0))


def set_main_image(property_id, image_id):
    execute("UPDATE property_images SET is_main = CASE WHEN id = ? THEN 1 ELSE 0 END "
            "WHERE property_id = ?", (image_id, property_id))


def delete_image(image_id):
    img = fetch_one("SELECT * FROM property_images WHERE id = ?", (image_id,))
    if not img:
        return
    execute("DELETE FROM property_images WHERE id = ?", (image_id,))
    _remove_uploaded_file(img["image_path"])
    # If the main photo was deleted, promote the next one.
    remaining = get_images(img["property_id"])
    if img["is_main"] and remaining:
        set_main_image(img["property_id"], remaining[0]["id"])


def _remove_uploaded_file(rel_path):
    """Only files inside assets/uploads are deleted (never the sample images)."""
    if rel_path.startswith("assets/uploads/"):
        path = BASE_DIR / rel_path
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# Inquiries
# ---------------------------------------------------------------------------
def create_inquiry(property_id, tenant_id, subject, message, created_at=None):
    return execute("INSERT INTO inquiries (property_id, tenant_id, subject, message, created_at)"
                   " VALUES (?, ?, ?, ?, ?)",
                   (property_id, tenant_id, subject.strip(), message.strip(),
                    created_at or now_str()))


def get_tenant_inquiries(tenant_id):
    return fetch_all(
        "SELECT i.*, p.name AS property_name, p.city, u.full_name AS landlord_name "
        "FROM inquiries i JOIN properties p ON p.id = i.property_id "
        "JOIN users u ON u.id = p.landlord_id "
        "WHERE i.tenant_id = ? ORDER BY i.created_at DESC", (tenant_id,))


def get_landlord_inquiries(landlord_id):
    return fetch_all(
        "SELECT i.*, p.name AS property_name, t.full_name AS tenant_name, t.email AS tenant_email,"
        " t.phone AS tenant_phone FROM inquiries i "
        "JOIN properties p ON p.id = i.property_id JOIN users t ON t.id = i.tenant_id "
        "WHERE p.landlord_id = ? ORDER BY i.status = 'Replied', i.created_at DESC",
        (landlord_id,))


def reply_to_inquiry(landlord_id, inquiry_id, reply):
    execute("UPDATE inquiries SET reply = ?, status = 'Replied', replied_at = ? "
            "WHERE id = ? AND property_id IN (SELECT id FROM properties WHERE landlord_id = ?)",
            (reply.strip(), now_str(), inquiry_id, landlord_id))


# ---------------------------------------------------------------------------
# Rental applications
# ---------------------------------------------------------------------------
def has_active_application(tenant_id, room_id):
    """True if the tenant already has a Pending / Under Review / Accepted application."""
    return fetch_one("SELECT id FROM applications WHERE tenant_id = ? AND room_id = ? "
                     "AND status IN ('Pending', 'Under Review', 'Accepted')",
                     (tenant_id, room_id)) is not None


def create_application(property_id, room_id, tenant_id, move_in_date, stay_months, occupation,
                       school_or_work, contact_phone, message, status="Pending",
                       landlord_note="", created_at=None):
    stamp = created_at or now_str()
    return execute(
        "INSERT INTO applications (property_id, room_id, tenant_id, move_in_date, stay_months,"
        " occupation, school_or_work, contact_phone, message, status, landlord_note,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (property_id, room_id, tenant_id, str(move_in_date), int(stay_months), occupation,
         school_or_work.strip(), contact_phone.strip(), message.strip(), status, landlord_note,
         stamp, stamp))


_APPLICATION_SELECT = """
SELECT a.*, p.name AS property_name, p.city, p.address,
       r.room_name, r.room_type, r.price, r.availability AS room_availability,
       t.full_name AS tenant_name, t.email AS tenant_email
FROM applications a
JOIN properties p ON p.id = a.property_id
JOIN rooms r ON r.id = a.room_id
JOIN users t ON t.id = a.tenant_id
"""


def get_tenant_applications(tenant_id):
    return fetch_all(_APPLICATION_SELECT + " WHERE a.tenant_id = ? ORDER BY a.created_at DESC",
                     (tenant_id,))


def get_landlord_applications(landlord_id):
    return fetch_all(
        _APPLICATION_SELECT + " WHERE p.landlord_id = ? ORDER BY "
        "CASE a.status WHEN 'Pending' THEN 0 WHEN 'Under Review' THEN 1 ELSE 2 END, "
        "a.created_at DESC", (landlord_id,))


def update_application_status(landlord_id, application_id, status, note):
    execute("UPDATE applications SET status = ?, landlord_note = ?, updated_at = ? "
            "WHERE id = ? AND property_id IN (SELECT id FROM properties WHERE landlord_id = ?)",
            (status, note.strip(), now_str(), application_id, landlord_id))


def cancel_application(tenant_id, application_id):
    """Tenants may withdraw an application while it is still Pending."""
    execute("DELETE FROM applications WHERE id = ? AND tenant_id = ? AND status = 'Pending'",
            (application_id, tenant_id))


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
def can_review(tenant_id, property_id):
    """Only tenants with an ACCEPTED application (they stayed there) may review."""
    return fetch_one("SELECT id FROM applications WHERE tenant_id = ? AND property_id = ? "
                     "AND status = 'Accepted'", (tenant_id, property_id)) is not None


def has_reviewed(tenant_id, property_id):
    return fetch_one("SELECT id FROM reviews WHERE tenant_id = ? AND property_id = ?",
                     (tenant_id, property_id)) is not None


def add_review(property_id, tenant_id, rating, comment, cleanliness=None, security=None,
               location=None, affordability=None, created_at=None):
    """Returns True if saved, False if this tenant already reviewed the dorm."""
    try:
        execute("INSERT INTO reviews (property_id, tenant_id, rating, cleanliness, security,"
                " location, affordability, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (property_id, tenant_id, int(rating), cleanliness, security, location,
                 affordability, comment.strip(), created_at or now_str()))
        return True
    except sqlite3.IntegrityError:
        return False


def get_reviews(property_id):
    return fetch_all("SELECT rv.*, u.full_name AS tenant_name FROM reviews rv "
                     "JOIN users u ON u.id = rv.tenant_id WHERE rv.property_id = ? "
                     "ORDER BY rv.created_at DESC", (property_id,))


def get_review_summary(property_id):
    return fetch_one("SELECT ROUND(AVG(rating), 1) AS rating, COUNT(*) AS total,"
                     " ROUND(AVG(cleanliness), 1) AS cleanliness, ROUND(AVG(security), 1) AS security,"
                     " ROUND(AVG(location), 1) AS location, ROUND(AVG(affordability), 1) AS affordability"
                     " FROM reviews WHERE property_id = ?", (property_id,))


def get_tenant_reviews(tenant_id):
    return fetch_all("SELECT rv.*, p.name AS property_name FROM reviews rv "
                     "JOIN properties p ON p.id = rv.property_id WHERE rv.tenant_id = ? "
                     "ORDER BY rv.created_at DESC", (tenant_id,))


# ---------------------------------------------------------------------------
# Saved / bookmarked dorms
# ---------------------------------------------------------------------------
def get_saved_ids(tenant_id):
    return {r["property_id"] for r in fetch_all(
        "SELECT property_id FROM saved_properties WHERE tenant_id = ?", (tenant_id,))}


def toggle_saved(tenant_id, property_id):
    """Save the dorm, or remove it if already saved. Returns True if now saved."""
    if property_id in get_saved_ids(tenant_id):
        execute("DELETE FROM saved_properties WHERE tenant_id = ? AND property_id = ?",
                (tenant_id, property_id))
        return False
    execute("INSERT INTO saved_properties (tenant_id, property_id, created_at) VALUES (?, ?, ?)",
            (tenant_id, property_id, now_str()))
    return True


def get_saved_properties(tenant_id):
    sql = (_LISTING_SELECT.replace("JOIN users u ON u.id = p.landlord_id",
                                   "JOIN users u ON u.id = p.landlord_id "
                                   "JOIN saved_properties s ON s.property_id = p.id "
                                   "LEFT JOIN rooms r ON r.property_id = p.id")
           + " WHERE s.tenant_id = ? GROUP BY p.id ORDER BY s.created_at DESC")
    return _attach_amenities(fetch_all(sql, (tenant_id,)))


# ---------------------------------------------------------------------------
# Dashboard numbers
# ---------------------------------------------------------------------------
def get_tenant_stats(tenant_id):
    return fetch_one(
        "SELECT (SELECT COUNT(*) FROM applications WHERE tenant_id = :t) AS applications,"
        " (SELECT COUNT(*) FROM applications WHERE tenant_id = :t"
        "   AND status IN ('Pending', 'Under Review')) AS in_progress,"
        " (SELECT COUNT(*) FROM saved_properties WHERE tenant_id = :t) AS saved,"
        " (SELECT COUNT(*) FROM inquiries WHERE tenant_id = :t AND status = 'Replied') AS replies",
        {"t": tenant_id})


def get_landlord_stats(landlord_id):
    return fetch_one(
        "SELECT (SELECT COUNT(*) FROM properties WHERE landlord_id = :l) AS listings,"
        " (SELECT COUNT(*) FROM rooms r JOIN properties p ON p.id = r.property_id"
        "   WHERE p.landlord_id = :l AND r.availability = 'Available') AS available_rooms,"
        " (SELECT COUNT(*) FROM inquiries i JOIN properties p ON p.id = i.property_id"
        "   WHERE p.landlord_id = :l AND i.status = 'Open') AS open_inquiries,"
        " (SELECT COUNT(*) FROM applications a JOIN properties p ON p.id = a.property_id"
        "   WHERE p.landlord_id = :l AND a.status IN ('Pending', 'Under Review')) AS pending_apps",
        {"l": landlord_id})


# ---------------------------------------------------------------------------
# Sample data (loaded automatically on the first run)
# ---------------------------------------------------------------------------
SAMPLE_LANDLORDS = [
    ("Ramon Dela Cruz", "landlord@kwarko.ph", "landlord123", "0917 555 0101"),
    ("Linda Aquino", "linda.aquino@kwarko.ph", "password123", "0918 555 0202"),
    ("Carlos Bautista", "carlos.bautista@kwarko.ph", "password123", "0920 555 0303"),
    ("Grace Tan", "grace.tan@kwarko.ph", "password123", "0921 555 0404"),
]

SAMPLE_TENANTS = [
    ("Maria Santos", "tenant@kwarko.ph", "tenant123", "0927 555 1001"),
    ("Juan Reyes", "juan.reyes@kwarko.ph", "password123", "0927 555 1002"),
    ("Angela Cruz", "angela.cruz@kwarko.ph", "password123", "0927 555 1003"),
    ("Mark Villanueva", "mark.villanueva@kwarko.ph", "password123", "0927 555 1004"),
    ("Bea Garcia", "bea.garcia@kwarko.ph", "password123", "0927 555 1005"),
    ("Paolo Mendoza", "paolo.mendoza@kwarko.ph", "password123", "0927 555 1006"),
]

STANDARD_RULES = ("Curfew at 10:00 PM (gate closes)\nNo smoking and no alcoholic drinks inside\n"
                  "Visitors allowed in the lobby only until 8:00 PM\nKeep quiet hours from 10:00 PM to 6:00 AM\n"
                  "Clean as you go in shared areas")
STANDARD_REQS = ("Valid ID (school or government ID)\n1 month advance + 1 month deposit\n"
                 "Signed boarding agreement\nParent/guardian contact details (for students)")

# Each room: (room name, type, monthly price, capacity, dimensions, specs, availability)
SAMPLE_PROPERTIES = [
    {"landlord": "landlord@kwarko.ph", "name": "Alangilan Student Residences",
     "address": "Golden Country Homes Rd., Brgy. Alangilan", "barangay": "Alangilan",
     "city": "Batangas City", "gender": "Mixed", "style": "apartment", "days_ago": 4,
     "description": "A 3-storey student dormitory a 5-minute walk from BatStateU Alangilan. "
                    "Quiet study areas on every floor, fast fiber Wi-Fi and a shared kitchen make it "
                    "a favorite among engineering students.",
     "amenities": ["Wi-Fi", "Laundry Area", "Kitchen", "CCTV / Security", "Study Area",
                   "Water Included", "Near Transport"],
     "rooms": [("Room 101 - 4-bed bedspace", "Bedspace", 2500, 4, "3.5m x 4m",
                "Double-deck beds, personal locker, study table, electric fan", "Available"),
               ("Room 204 - Twin sharing", "Shared", 3800, 2, "3m x 3.5m",
                "2 single beds, 2 study tables, wardrobe, window", "Available")]},
    {"landlord": "linda.aquino@kwarko.ph", "name": "Casa Verde Dormitory",
     "address": "Rizal Ave. Extension, Brgy. Kumintang Ibaba", "barangay": "Kumintang Ibaba",
     "city": "Batangas City", "gender": "Mixed", "style": "apartment", "days_ago": 20,
     "description": "Modern air-conditioned rooms with private bathrooms near the Capitol and "
                    "jeepney routes to downtown. Ideal for working professionals and graduate students.",
     "amenities": ["Wi-Fi", "Air Conditioning", "Parking", "CCTV / Security", "Private CR",
                   "Refrigerator", "Near Transport"],
     "rooms": [("Studio A - Private room", "Private Room", 6500, 1, "4m x 4.5m",
                "Queen bed, private CR, aircon, mini-fridge, work desk", "Available"),
               ("Unit B - Solo room", "Solo", 5200, 1, "3m x 3.5m",
                "Single bed, aircon, study table, shared CR", "Available")]},
    {"landlord": "landlord@kwarko.ph", "name": "Pallocan Haven Boarding House",
     "address": "Purok 3, Brgy. Pallocan West", "barangay": "Pallocan West",
     "city": "Batangas City", "gender": "Mixed", "style": "house", "days_ago": 45,
     "description": "A homey and budget-friendly boarding house run by a family. Free use of the "
                    "kitchen and laundry area, with home-style meals available on request.",
     "amenities": ["Wi-Fi", "Kitchen", "Laundry Area", "Water Included"],
     "rooms": [("Bedspace Room 1", "Bedspace", 2000, 6, "4m x 5m",
                "Double-deck beds, shared cabinet, ceiling fan", "Available"),
               ("Room 2 - Shared", "Shared", 3000, 3, "3.5m x 4m",
                "3 single beds, study table, cabinet", "Available")]},
    {"landlord": "linda.aquino@kwarko.ph", "name": "Poblacion Urban Suites",
     "address": "P. Burgos St., Poblacion", "barangay": "Poblacion",
     "city": "Batangas City", "gender": "Mixed", "style": "apartment", "days_ago": 12,
     "description": "Condo-style rooms in the city center, steps away from malls, banks and "
                    "the port terminal. 24/7 guard and keycard access.",
     "amenities": ["Wi-Fi", "Air Conditioning", "Private CR", "CCTV / Security", "Refrigerator",
                   "Electricity Included", "Near Transport"],
     "rooms": [("Suite 3A - Solo", "Solo", 7000, 1, "3.5m x 4m",
                "Single bed, aircon, smart TV, private CR", "Available"),
               ("Suite 5C - Private room", "Private Room", 8500, 2, "4.5m x 5m",
                "Double bed, aircon, kitchenette, private CR", "Occupied")]},
    {"landlord": "landlord@kwarko.ph", "name": "Gulod Labac Ladies' Dorm",
     "address": "National Road, Brgy. Gulod Labac", "barangay": "Gulod Labac",
     "city": "Batangas City", "gender": "Female only", "style": "house", "days_ago": 30,
     "description": "A safe, female-only dormitory with a resident house mother, CCTV and a "
                    "strict visitor policy. Clean, bright rooms and a cozy study lounge.",
     "amenities": ["Wi-Fi", "CCTV / Security", "Study Area", "Laundry Area", "Kitchen"],
     "rooms": [("Room A - Shared", "Shared", 3200, 2, "3m x 3.5m",
                "2 single beds, vanity mirror, cabinet, electric fan", "Available"),
               ("Room C - Bedspace", "Bedspace", 2300, 4, "3.5m x 4m",
                "Double-deck beds, lockers, study table", "Available")]},
    {"landlord": "carlos.bautista@kwarko.ph", "name": "Marawoy Tech Lofts",
     "address": "Marawoy Rd., Brgy. Marawoy", "barangay": "Marawoy",
     "city": "Lipa City", "gender": "Mixed", "style": "apartment", "days_ago": 8,
     "description": "Loft-style rooms built for students of the nearby universities in Lipa. "
                    "Co-working lounge, fiber internet and bike parking.",
     "amenities": ["Wi-Fi", "Air Conditioning", "Study Area", "Parking", "CCTV / Security"],
     "rooms": [("Loft 1 - Solo", "Solo", 5500, 1, "3m x 4m",
                "Loft bed, desk underneath, aircon, wardrobe", "Available"),
               ("Loft 4 - Shared", "Shared", 3900, 2, "4m x 4m",
                "2 loft beds, 2 desks, aircon", "Available")]},
    {"landlord": "carlos.bautista@kwarko.ph", "name": "Lipa Heights Bedspace",
     "address": "C.M. Recto Ave., Brgy. Sabang", "barangay": "Sabang",
     "city": "Lipa City", "gender": "Male only", "style": "house", "days_ago": 60,
     "description": "The most affordable bedspace option in Lipa City proper. Walking distance "
                    "to the cathedral, public market and jeepney terminals.",
     "amenities": ["Wi-Fi", "Laundry Area", "Water Included", "Near Transport"],
     "rooms": [("Hall A - Bedspace", "Bedspace", 1800, 8, "5m x 6m",
                "Double-deck beds, lockers, ceiling fans", "Occupied"),
               ("Hall B - Bedspace", "Bedspace", 1900, 6, "4m x 5m",
                "Double-deck beds, lockers, window", "Available")]},
    {"landlord": "carlos.bautista@kwarko.ph", "name": "Tanauan Riverside Rooms",
     "address": "J.P. Laurel Highway, Brgy. Darasa", "barangay": "Darasa",
     "city": "Tanauan City", "gender": "Mixed", "style": "house", "days_ago": 2,
     "description": "Newly built private rooms near the industrial park - perfect for factory "
                    "and BPO workers. Each room has its own bathroom and a small kitchen counter.",
     "amenities": ["Wi-Fi", "Private CR", "Parking", "Kitchen", "CCTV / Security"],
     "rooms": [("Room 1 - Private", "Private Room", 4800, 2, "3.5m x 4.5m",
                "Double bed, private CR, kitchen counter, electric fan", "Available"),
               ("Room 3 - Solo", "Solo", 4200, 1, "3m x 3m",
                "Single bed, private CR, cabinet", "Available")]},
    {"landlord": "grace.tan@kwarko.ph", "name": "España Scholars Dorm",
     "address": "España Blvd., Sampaloc", "barangay": "Sampaloc",
     "city": "Manila", "gender": "Mixed", "style": "apartment", "days_ago": 90,
     "description": "University Belt dormitory a short walk from UST and other Manila "
                    "universities. 24-hour study hall, security guard and laundry service.",
     "amenities": ["Wi-Fi", "Air Conditioning", "Study Area", "Laundry Area", "CCTV / Security",
                   "Near Transport"],
     "rooms": [("Room 5F-1 - Bedspace", "Bedspace", 3500, 4, "4m x 4m",
                "Double-deck beds, aircon, lockers", "Available"),
               ("Room 7F-2 - Shared", "Shared", 5000, 2, "3m x 4m",
                "2 single beds, aircon, 2 desks", "Available")]},
    {"landlord": "grace.tan@kwarko.ph", "name": "Taft Avenue Study Hub",
     "address": "Taft Ave. corner Vito Cruz, Malate", "barangay": "Malate",
     "city": "Manila", "gender": "Mixed", "style": "apartment", "days_ago": 25,
     "description": "High-rise student residence along Taft Avenue near LRT Vito Cruz station. "
                    "Gym, roof deck and air-conditioned rooms with study nooks.",
     "amenities": ["Wi-Fi", "Air Conditioning", "Study Area", "CCTV / Security", "Refrigerator",
                   "Electricity Included", "Near Transport"],
     "rooms": [("Unit 12B - Solo", "Solo", 9000, 1, "3.5m x 4m",
                "Single bed, aircon, study nook, private CR", "Available"),
               ("Unit 9A - Shared", "Shared", 6000, 2, "4m x 4.5m",
                "2 single beds, aircon, shared CR", "Occupied")]},
    {"landlord": "grace.tan@kwarko.ph", "name": "Diliman Commons",
     "address": "Maginhawa St., Teachers Village", "barangay": "Teachers Village",
     "city": "Quezon City", "gender": "Mixed", "style": "house", "days_ago": 15,
     "description": "A garden dormhouse in the Maginhawa food street area, a jeepney ride to UP "
                    "Diliman. Shared kitchen, garden study area and friendly community.",
     "amenities": ["Wi-Fi", "Kitchen", "Study Area", "Laundry Area", "Near Transport"],
     "rooms": [("Garden Room - Shared", "Shared", 4500, 2, "3.5m x 4m",
                "2 single beds, cabinet, garden view", "Available"),
               ("Attic Room - Private", "Private Room", 7500, 1, "4m x 5m",
                "Double bed, aircon, private CR, work desk", "Available")]},
    {"landlord": "landlord@kwarko.ph", "name": "Bolbok Family Boarding",
     "address": "Bolbok Rd., Brgy. Bolbok", "barangay": "Bolbok",
     "city": "Batangas City", "gender": "Mixed", "style": "house", "days_ago": 120,
     "description": "A long-running family boarding house with spacious rooms and a big parking "
                    "area. Currently fully occupied - save it and check back for openings.",
     "amenities": ["Parking", "Kitchen", "Laundry Area", "Water Included"],
     "rooms": [("Room 1 - Shared", "Shared", 2800, 3, "4m x 4m",
                "3 single beds, cabinet, electric fan", "Occupied"),
               ("Room 2 - Solo", "Solo", 3500, 1, "3m x 3m",
                "Single bed, cabinet, study table", "Occupied")]},
]

# (property no., tenant email, rating, cleanliness, security, location, affordability, comment, days ago)
SAMPLE_REVIEWS = [
    (1, "juan.reyes@kwarko.ph", 5, 5, 4, 5, 5, "Super near the campus, I can wake up 15 minutes before class. Wi-Fi is fast and the study area is always clean.", 40),
    (1, "angela.cruz@kwarko.ph", 4, 4, 4, 5, 4, "Great location and very helpful caretaker. The common CR can get busy in the morning.", 70),
    (1, "mark.villanueva@kwarko.ph", 5, 4, 5, 5, 5, "Best value dorm near BatStateU. Safe and quiet during exam week.", 100),
    (2, "bea.garcia@kwarko.ph", 5, 5, 5, 4, 4, "Very clean and the aircon is a lifesaver. Feels like a small condo.", 35),
    (2, "paolo.mendoza@kwarko.ph", 4, 5, 4, 4, 3, "Comfortable room and responsive landlord. A bit pricey but worth it.", 80),
    (3, "juan.reyes@kwarko.ph", 4, 4, 3, 4, 5, "Very affordable and the family is kind. Rooms are simple but clean.", 150),
    (3, "bea.garcia@kwarko.ph", 4, 3, 4, 4, 5, "Good for students on a tight budget. Kitchen access is a big plus.", 120),
    (4, "mark.villanueva@kwarko.ph", 5, 5, 5, 5, 4, "Everything you need is walking distance. Keycard access feels very secure.", 25),
    (4, "angela.cruz@kwarko.ph", 4, 5, 5, 5, 3, "Clean and modern, but monthly rent is on the higher side.", 60),
    (5, "angela.cruz@kwarko.ph", 5, 5, 5, 4, 4, "As a girl living alone for the first time, this place made my parents feel at ease.", 45),
    (5, "bea.garcia@kwarko.ph", 5, 5, 5, 4, 5, "House mother is so caring. Rooms are bright and very clean.", 90),
    (6, "paolo.mendoza@kwarko.ph", 5, 5, 4, 4, 4, "The co-working lounge is perfect for group projects. Love the loft bed!", 20),
    (6, "juan.reyes@kwarko.ph", 4, 4, 4, 4, 4, "Nice modern rooms. Parking for my bike is very convenient.", 55),
    (7, "mark.villanueva@kwarko.ph", 3, 3, 3, 5, 5, "Cheapest in Lipa and the location is perfect, but it can get noisy with many tenants.", 75),
    (7, "paolo.mendoza@kwarko.ph", 4, 3, 4, 5, 5, "Good enough for the price. Near everything.", 110),
    (9, "juan.reyes@kwarko.ph", 4, 4, 5, 5, 3, "Very near UST and the 24-hour study hall saved my finals week.", 200),
    (9, "tenant@kwarko.ph", 4, 4, 4, 5, 4, "I stayed here for one semester. Safe area, friendly guards and a clean study hall.", 180),
    (9, "angela.cruz@kwarko.ph", 5, 5, 5, 5, 4, "Clean, secure and close to school. Would stay again.", 210),
    (10, "bea.garcia@kwarko.ph", 4, 5, 5, 5, 2, "Amazing facilities and the roof deck view is great, but it is expensive.", 50),
    (11, "mark.villanueva@kwarko.ph", 5, 4, 4, 5, 4, "Maginhawa food trip every night! The garden study area is so relaxing.", 30),
    (11, "angela.cruz@kwarko.ph", 4, 4, 4, 5, 4, "Friendly housemates and a cozy vibe. Jeep to UP is easy.", 65),
    (12, "paolo.mendoza@kwarko.ph", 4, 4, 4, 3, 5, "Spacious rooms and the owners treat you like family.", 300),
]


def sample_image_paths(index):
    """Sample photos for property number `index` (1-based): exterior + 2 rooms."""
    return [f"assets/images/dorm{index:02d}_{k}.jpg" for k in (1, 2, 3)]


def seed_sample_data():
    """Fill an empty database with realistic demo accounts, dorms and activity."""
    def ago(days, hour=10):
        return (datetime.now() - timedelta(days=days)).replace(
            hour=hour, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    users = {}
    for i, (name, email, pw, phone) in enumerate(SAMPLE_LANDLORDS):
        users[email] = create_user(name, email, pw, "landlord", phone, ago(400 - i))
    for i, (name, email, pw, phone) in enumerate(SAMPLE_TENANTS):
        users[email] = create_user(name, email, pw, "tenant", phone, ago(380 - i))

    prop_ids, room_ids = {}, {}
    for idx, p in enumerate(SAMPLE_PROPERTIES, start=1):
        landlord_email = p["landlord"]
        landlord_phone = next(l[3] for l in SAMPLE_LANDLORDS if l[1] == landlord_email)
        pid = create_property(users[landlord_email], p["name"], p["address"], p["barangay"],
                              p["city"], p["gender"], p["description"], STANDARD_RULES,
                              STANDARD_REQS, landlord_phone, landlord_email, ago(p["days_ago"]))
        prop_ids[idx] = pid
        set_amenities(pid, p["amenities"])
        room_ids[idx] = [add_room(pid, *room) for room in p["rooms"]]
        for k, path in enumerate(sample_image_paths(idx)):
            add_image(pid, path, is_main=(k == 0))

    def apply(prop_no, room_no, email, status, days, note="", message="", occupation="Student",
              school="Batangas State University", months=6):
        return create_application(prop_ids[prop_no], room_ids[prop_no][room_no], users[email],
                                  (date.today() - timedelta(days=days - 14)).isoformat(), months,
                                  occupation, school, "0927 555 1000", message, status, note,
                                  ago(days))

    # Past stays (status Accepted) - these allow the sample reviews below.
    for prop_no, email, *_rest, days in SAMPLE_REVIEWS:
        if email != "tenant@kwarko.ph":
            apply(prop_no, 0, email, "Accepted", days + 30, "Welcome! See you on move-in day.")
    apply(9, 0, "tenant@kwarko.ph", "Accepted", 220, "Approved - please bring your school ID.",
          school="University of Santo Tomas")
    apply(3, 1, "tenant@kwarko.ph", "Accepted", 60, "Approved. Your room is ready.")  # not yet reviewed

    for prop_no, email, rating, c, s, l, a, comment, days in SAMPLE_REVIEWS:
        add_review(prop_ids[prop_no], users[email], rating, comment, c, s, l, a, ago(days))

    # Current applications of the demo tenant (Maria Santos)
    apply(2, 1, "tenant@kwarko.ph", "Pending", 2, message="Hi! I will start my OJT in Batangas City next month.",
          occupation="Working Professional", school="OJT - Batangas Port")
    apply(6, 0, "tenant@kwarko.ph", "Under Review", 5, "Checking your requirements. We will update you soon.",
          message="Looking for a quiet room for my thesis year.")
    apply(10, 1, "tenant@kwarko.ph", "Rejected", 12, "Sorry, this room was already reserved by another tenant.",
          school="De La Salle University")

    # Applications waiting for the demo landlord (Ramon Dela Cruz)
    apply(1, 0, "juan.reyes@kwarko.ph", "Pending", 1, message="I'm an incoming 2nd year ECE student. Is the bedspace still open?", months=10)
    apply(1, 1, "paolo.mendoza@kwarko.ph", "Pending", 3, message="Me and my classmate would like the twin room.")
    apply(5, 0, "bea.garcia@kwarko.ph", "Under Review", 4, "Please send a copy of your school ID.",
          message="Looking for a safe dorm for second semester.")

    # Inquiries
    q1 = create_inquiry(prop_ids[1], users["tenant@kwarko.ph"], "Is water and electricity included?",
                        "Good day! Is the water and electricity already included in the monthly rent of the bedspace?",
                        ago(6))
    reply_to_inquiry(users["landlord@kwarko.ph"], q1,
                     "Hello Maria! Water is included. Electricity is shared equally per room based on the sub-meter.")
    create_inquiry(prop_ids[11], users["tenant@kwarko.ph"], "Visiting the dorm",
                   "Hi, can I visit the Garden Room this Saturday afternoon?", ago(1, 15))
    create_inquiry(prop_ids[3], users["angela.cruz@kwarko.ph"], "Meals available?",
                   "Hello po! Do you offer meal plans for boarders? How much per month?", ago(2, 9))
    create_inquiry(prop_ids[5], users["mark.villanueva@kwarko.ph"], "For my sister",
                   "Good evening. My sister is a freshman - is there a slot available for June?", ago(1, 20))

    # Saved dorms of the demo tenant
    for prop_no in (1, 2, 11):
        execute("INSERT INTO saved_properties (tenant_id, property_id, created_at) VALUES (?, ?, ?)",
                (users["tenant@kwarko.ph"], prop_ids[prop_no], ago(prop_no)))
