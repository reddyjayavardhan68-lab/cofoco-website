"""
COFOCO (Conscious Form Company) - Database Schema & Data Layer
Strictly implemented according to COFOCO Website Requirements Analysis.
Self-contained SQLite engine with WAL mode, foreign keys, and atomic transactions.
Compatible with PostgreSQL data types and Django ORM models.
"""

import os
import sqlite3
import json
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cofoco.db")
IST = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def hash_password(password: str) -> str:
    salt = "cofoco_secure_salt_2026"
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Roles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        permissions_json TEXT NOT NULL
    );
    """)

    # 2. Staff Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role_id TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        mfa_enabled INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );
    """)

    # 3. Characters
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        tagline TEXT NOT NULL,
        quality TEXT NOT NULL,
        routine_cue TEXT NOT NULL,
        story TEXT NOT NULL,
        theme_symbol TEXT NOT NULL,
        theme_colors_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('draft', 'review', 'published')),
        published_by TEXT,
        published_at TEXT,
        artwork_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (published_by) REFERENCES users(id)
    );
    """)

    # 4. Raw Components & Equipment
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS components (
        id TEXT PRIMARY KEY,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('gym_essential', 'recovery')),
        material TEXT NOT NULL,
        dimensions TEXT,
        unit_cost REAL NOT NULL,
        supplier_name TEXT,
        supplier_lead_days INTEGER DEFAULT 7,
        created_at TEXT NOT NULL
    );
    """)

    # 5. Kits
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kits (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        character_id TEXT NOT NULL,
        subtitle TEXT NOT NULL,
        description TEXT NOT NULL,
        routine_integration TEXT NOT NULL,
        base_price REAL NOT NULL,
        mrp REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('draft', 'review', 'published')),
        is_featured INTEGER DEFAULT 1,
        image_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (character_id) REFERENCES characters(id)
    );
    """)

    # 6. Product Variants
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_variants (
        id TEXT PRIMARY KEY,
        kit_id TEXT NOT NULL,
        variant_name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        price REAL NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (kit_id) REFERENCES kits(id)
    );
    """)

    # 7. BOM Versions (Bill of Materials)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bom_versions (
        id TEXT PRIMARY KEY,
        variant_id TEXT NOT NULL,
        version TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('draft', 'active', 'archived')),
        notes TEXT,
        created_by TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (variant_id) REFERENCES product_variants(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    );
    """)

    # 8. BOM Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bom_items (
        id TEXT PRIMARY KEY,
        bom_version_id TEXT NOT NULL,
        component_id TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        FOREIGN KEY (bom_version_id) REFERENCES bom_versions(id),
        FOREIGN KEY (component_id) REFERENCES components(id)
    );
    """)

    # 9. Component Inventory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id TEXT PRIMARY KEY,
        component_id TEXT UNIQUE NOT NULL,
        on_hand INTEGER NOT NULL DEFAULT 0,
        low_stock_threshold INTEGER NOT NULL DEFAULT 10,
        location TEXT DEFAULT 'Warehouse Bay A-1',
        updated_at TEXT NOT NULL,
        FOREIGN KEY (component_id) REFERENCES components(id)
    );
    """)

    # 10. Stock Movement Ledger
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_ledger (
        id TEXT PRIMARY KEY,
        component_id TEXT NOT NULL,
        change_type TEXT NOT NULL CHECK(change_type IN ('receipt', 'reservation', 'pick', 'adjustment', 'return')),
        quantity INTEGER NOT NULL,
        balance_after INTEGER NOT NULL,
        reference_type TEXT,
        reference_id TEXT,
        reason TEXT,
        created_by TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (component_id) REFERENCES components(id)
    );
    """)

    # 11. Component Reservations (Atomic checkout holds)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        order_id TEXT,
        component_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('active', 'consumed', 'released')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (component_id) REFERENCES components(id)
    );
    """)

    # 12. Carts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carts (
        id TEXT PRIMARY KEY,
        session_id TEXT UNIQUE NOT NULL,
        coupon_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 13. Cart Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        id TEXT PRIMARY KEY,
        cart_id TEXT NOT NULL,
        variant_id TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (cart_id) REFERENCES carts(id),
        FOREIGN KEY (variant_id) REFERENCES product_variants(id)
    );
    """)

    # 14. Orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        order_number TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        delivery_address TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount REAL NOT NULL DEFAULT 0.0,
        shipping_fee REAL NOT NULL DEFAULT 0.0,
        tax REAL NOT NULL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        payment_status TEXT NOT NULL CHECK(payment_status IN ('pending', 'paid', 'failed', 'refunded', 'reconciliation_required')),
        order_status TEXT NOT NULL CHECK(order_status IN ('paid', 'picking', 'packed', 'dispatched', 'delivered', 'cancelled')),
        promised_dispatch_date TEXT NOT NULL,
        assigned_staff_id TEXT,
        campaign_id TEXT,
        session_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (assigned_staff_id) REFERENCES users(id)
    );
    """)

    # 15. Order Items (Preserves Exact BOM Snapshot!)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        variant_id TEXT NOT NULL,
        kit_name TEXT NOT NULL,
        variant_name TEXT NOT NULL,
        character_name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        bom_snapshot_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (variant_id) REFERENCES product_variants(id)
    );
    """)

    # 16. Payment Events (Idempotency and Gateway Audit)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_events (
        id TEXT PRIMARY KEY,
        order_id TEXT,
        gateway TEXT NOT NULL DEFAULT 'razorpay',
        event_type TEXT NOT NULL,
        gateway_payment_id TEXT UNIQUE,
        gateway_order_id TEXT,
        gateway_signature TEXT,
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'INR',
        status TEXT NOT NULL CHECK(status IN ('verified', 'duplicate', 'late_arrival', 'failed')),
        payload_json TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 17. Shipments & Tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        id TEXT PRIMARY KEY,
        order_id TEXT UNIQUE NOT NULL,
        courier_name TEXT NOT NULL,
        tracking_number TEXT NOT NULL,
        tracking_url TEXT NOT NULL,
        dispatched_at TEXT NOT NULL,
        delivered_at TEXT,
        created_by TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    );
    """)

    # 18. Returns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS returns (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        order_item_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('requested', 'received', 'inspected', 'rejected')),
        inspection_result TEXT CHECK(inspection_result IN ('passed', 'damaged', 'pending')),
        restocked INTEGER DEFAULT 0,
        assigned_owner TEXT,
        resolution_notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (order_item_id) REFERENCES order_items(id),
        FOREIGN KEY (assigned_owner) REFERENCES users(id)
    );
    """)

    # 19. Refunds
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS refunds (
        id TEXT PRIMARY KEY,
        return_id TEXT,
        order_id TEXT NOT NULL,
        amount REAL NOT NULL,
        gateway_refund_id TEXT UNIQUE,
        status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'processed')),
        reason TEXT NOT NULL,
        approved_by TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (return_id) REFERENCES returns(id),
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (approved_by) REFERENCES users(id)
    );
    """)

    # 20. Marketing Campaigns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        source TEXT NOT NULL,
        medium TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        start_date TEXT NOT NULL,
        end_date TEXT
    );
    """)

    # 21. Analytics Events (Strictly Pseudonymous - Zero PII)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analytics_events (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        event_name TEXT NOT NULL,
        character_id TEXT,
        kit_id TEXT,
        campaign_id TEXT,
        metadata_json TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 22. Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        changes_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # 23. Indian Serviceable Pincodes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS serviceable_pincodes (
        pincode TEXT PRIMARY KEY,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        estimated_days INTEGER DEFAULT 3,
        cod_allowed INTEGER DEFAULT 0
    );
    """)

    # Performance & Lookup Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_ledger_comp ON stock_ledger(component_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status, expires_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics_events(event_name, created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_gw ON payment_events(gateway_payment_id);")

    conn.commit()
    conn.close()

def seed_db():
    conn = get_db()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) as cnt FROM roles;")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    now = datetime.now(IST)
    now_str = now.isoformat()

    # 1. Seed Roles
    roles = [
        ("role_admin", "Admin", "Unrestricted administrator access across all systems",
         json.dumps(["all", "manage_catalog", "publish", "manage_stock", "fulfill", "manage_returns", "manage_refunds", "view_analytics", "export_analytics", "manage_users"])),
        ("role_editor", "Brand Editor", "Draft and edit character stories, kits, symbolism, and artwork",
         json.dumps(["manage_catalog", "draft_character", "preview_content"])),
        ("role_publisher", "Publisher", "Review and approve character releases and kit launches",
         json.dumps(["manage_catalog", "publish", "preview_content"])),
        ("role_warehouse", "Warehouse Staff", "Pick orders, generate BOM pick lists, pack, and dispatch shipments",
         json.dumps(["fulfill", "view_orders", "print_pick_list", "update_dispatch", "receive_stock"])),
        ("role_support", "Support Staff", "Handle customer inquiries, track orders, and initiate return cases",
         json.dumps(["view_orders", "view_tracking", "create_return", "view_exceptions"])),
        ("role_finance", "Finance Staff", "Authorize refunds, reconcile payment mismatches, review contribution margins",
         json.dumps(["manage_refunds", "reconcile_payments", "view_analytics", "export_analytics"]))
    ]
    for r in roles:
        cursor.execute("INSERT INTO roles (id, name, description, permissions_json) VALUES (?, ?, ?, ?);", r)

    # 2. Seed Users
    users = [
        ("user_admin", "admin", "founder@cofoco.fit", hash_password("Admin@COFOCO2026"), "Aditya Varma", "role_admin", 1, 1, now_str),
        ("user_editor", "editor", "editor@cofoco.fit", hash_password("Editor@COFOCO2026"), "Ananya Sen", "role_editor", 1, 1, now_str),
        ("user_publisher", "publisher", "publisher@cofoco.fit", hash_password("Publish@COFOCO2026"), "Rohan Deshmukh", "role_publisher", 1, 1, now_str),
        ("user_warehouse", "warehouse", "ops@cofoco.fit", hash_password("Warehouse@COFOCO2026"), "Balram Yadav", "role_warehouse", 1, 1, now_str),
        ("user_support", "support", "care@cofoco.fit", hash_password("Support@COFOCO2026"), "Priya Nair", "role_support", 1, 1, now_str),
        ("user_finance", "finance", "finance@cofoco.fit", hash_password("Finance@COFOCO2026"), "Vikram Mehta", "role_finance", 1, 1, now_str)
    ]
    for u in users:
        cursor.execute("INSERT INTO users (id, username, email, password_hash, full_name, role_id, is_active, mfa_enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", u)

    # 3. Seed 6 Launch Characters
    characters = [
        ("char_arjun", "arjun", "Arjun", "Supremacy of Unwavering Focus", "Focus", "Preparation before training",
         "Arjun personifies the pinnacle of calibrated focus. In high-performance training, the lift is decided before the barbell is ever unhooked. Arjun's methodology centers on breathwork, sensory narrowing, muscle pre-activation, and calibrated resistance band warmup that zeroes the mind into absolute alignment with form.",
         "Moon and flowing water in cool blues",
         json.dumps({"primary": "#0F2B48", "secondary": "#1E5B94", "accent": "#6BA4D9", "light": "#D9E8F5", "badge": "Cool Blues & Moon Motif"}),
         "published", "user_publisher", now_str, "/images/characters/arjun.svg", now_str),

        ("char_bheema", "bheema", "Bheema", "Uncompromising Physical Dominance", "Strength", "The work of a training session",
         "Bheema channels raw, mountainous, unyielding physical power. His routine is the uncompromising heavy work of the session: maximal compound lifts, robust joint reinforcement, and brutal functional endurance that anchors every rep. He does not seek shortcuts; he bends iron to will.",
         "Mountain and warm earth tones",
         json.dumps({"primary": "#3B2219", "secondary": "#7D4F38", "accent": "#C08A5E", "light": "#EADCC9", "badge": "Warm Earth & Mountain Motif"}),
         "published", "user_publisher", now_str, "/images/characters/bheema.svg", now_str),

        ("char_karna", "karna", "Karna", "Resilience Under Implacable Odds", "Resolve", "Show up with resolve",
         "Karna represents unrelenting resilience and steadfast loyalty to the discipline. No matter the odds, adversity, or physical fatigue, he arrives on the platform ready to endure, train with unwavering heart, and forge unbreakable character through grit and self-discipline.",
         "Amber sun motif",
         json.dumps({"primary": "#3D2504", "secondary": "#B87314", "accent": "#E09F3E", "light": "#FCECD5", "badge": "Amber Sun Motif"}),
         "published", "user_publisher", now_str, "/images/characters/karna.svg", now_str),

        ("char_sita", "sita", "Sita", "Rooted Inner Poise & Enduring Grace", "Steadiness", "Wind-down routine",
         "Sita personifies rooted inner poise, graceful endurance, and intentional stillness. Her routine restores the nervous system after intense exertion, transitioning the body from high-threshold sympathetic output into calm, tissue-deep cellular recovery through mindful restorative movement.",
         "Ivory lotus rising from water",
         json.dumps({"primary": "#253028", "secondary": "#4A6B56", "accent": "#92B89E", "light": "#E9F0EB", "badge": "Lotus & Water Tone"}),
         "published", "user_publisher", now_str, "/images/characters/sita.svg", now_str),

        ("char_draupadi", "draupadi", "Draupadi", "Fierce Self-Possession & Sovereignty", "Self-possession", "Purposeful routine",
         "Draupadi commands sovereignty, fire, and absolute self-possession. Her training is purposeful and razor-sharp, turning intentional physical mastery into an armor of confidence and unwavering presence in every room. Every movement is done with sovereign dignity.",
         "Rose motif with rich tones",
         json.dumps({"primary": "#3A121E", "secondary": "#8B2643", "accent": "#C85A7A", "light": "#F7E5EB", "badge": "Royal Rose Motif"}),
         "published", "user_publisher", now_str, "/images/characters/draupadi.svg", now_str),

        ("char_savitri", "savitri", "Savitri", "The Inevitability of Daily Consistency", "Resolve and consistency", "Consistent daily habits",
         "Savitri demonstrates relentless daily devotion and triumph through disciplined constancy. Her routine honors the truth that lasting strength is built day after day, through seamless micro-habits, restorative mobility, and relentless dedication to the craft.",
         "Olive tones and morning vitality",
         json.dumps({"primary": "#232A1C", "secondary": "#4F5D38", "accent": "#879A63", "light": "#ECF0E7", "badge": "Olive & Habit Tone"}),
         "published", "user_publisher", now_str, "/images/characters/savitri.svg", now_str)
    ]
    for c in characters:
        cursor.execute("""
        INSERT INTO characters (id, slug, name, tagline, quality, routine_cue, story, theme_symbol, theme_colors_json, status, published_by, published_at, artwork_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, c)

    # 4. Seed Components (Gym Essentials & Recovery)
    components = [
        ("comp_band_set", "CFC-CMP-001", "Calibrated Latex Resistance Bands (Set of 4)", "gym_essential", "100% Malaysian Natural Latex", "4 Resistance Levels (10-60 lbs)", 380.0, "Apex Elastomers India", 5),
        ("comp_chalk_block", "CFC-CMP-002", "Pure Magnesium Carbonate Gym Chalk Block", "gym_essential", "High-density Magnesium Carbonate", "56g block", 85.0, "Western Minerals Gujarat", 4),
        ("comp_foam_roller", "CFC-CMP-003", "Precision Grid High-Density EPP Foam Roller", "recovery", "Eco-friendly EPP Polypropylene", "33cm x 14cm", 420.0, "Zenith Polychem Pune", 7),
        ("comp_focus_timer", "CFC-CMP-004", "Magnetic Interval & Routine Focus Timer", "gym_essential", "Matte ABS & Lithium Battery", "8cm x 8cm", 490.0, "Precision Microtech Bengaluru", 10),
        ("comp_leather_belt", "CFC-CMP-005", "Olympic Grade Top-Grain Leather Lifting Belt 10mm", "gym_essential", "Vegetable-tanned buffalo leather", "10mm thickness, 4-inch back", 1250.0, "Himalayan Leathercraft Kanpur", 12),
        ("comp_wrist_wraps", "CFC-CMP-006", "Heavy Duty Competition Wrist Wraps (Pair)", "gym_essential", "Cotton Elastic blend with thumb loop", "18-inch length", 210.0, "Vortex Textiles Ludhiana", 5),
        ("comp_liquid_chalk", "CFC-CMP-007", "Zero-Dust Liquid Grip Chalk 150ml", "gym_essential", "Pharmaceutical Magnesium + Isopropanol", "150ml bottle", 140.0, "Western Minerals Gujarat", 4),
        ("comp_massage_ball", "CFC-CMP-008", "Vibrating Percussion Recovery Lacrosse Ball", "recovery", "Silicone rubber core with 3-speed motor", "6.5cm diameter", 680.0, "Precision Microtech Bengaluru", 10),
        ("comp_duffel_bag", "CFC-CMP-009", "Water-Resistant 1000D Cordura Athlete Duffel", "gym_essential", "1000D Cordura Nylon with YKK zips", "42L volume", 1100.0, "RuggedGear Noida", 14),
        ("comp_dip_belt", "CFC-CMP-010", "Reinforced Steel Chain Weighted Dip & Pull-up Belt", "gym_essential", "Reinforced Poly-Webbing & Stainless Chain", "36-inch chain, 500kg test", 550.0, "Titan Metals Jalandhar", 6),
        ("comp_cork_mat", "CFC-CMP-011", "Organic Natural Cork & Tree Rubber Restorative Mat", "recovery", "Sustainable Cork Surface + Natural Rubber base", "183cm x 66cm x 5mm", 980.0, "Terra Eco Products Kerala", 8),
        ("comp_acupressure", "CFC-CMP-012", "Therapeutic Acupressure Spiked Mat & Neck Pillow", "recovery", "Organic Linen + Cotton + Non-toxic ABS spikes", "68cm x 42cm mat", 620.0, "Aura Wellness Coimbatore", 7),
        ("comp_recovery_mist", "CFC-CMP-013", "Botanical Magnesium Sleep & Wind-Down Mist 100ml", "recovery", "Zechstein Magnesium Chloride + Lavender Essential Oil", "100ml glass bottle", 230.0, "Vedic Botanics Dehradun", 5),
        ("comp_stretch_strap", "CFC-CMP-014", "Multi-Loop Non-Elastic Physical Therapy Stretch Strap", "recovery", "High-density woven polyester", "2-meter length, 10 loops", 160.0, "Vortex Textiles Ludhiana", 5),
        ("comp_barbell_pad", "CFC-CMP-015", "Contoured Ergonomic High-Density Squat Barbell Pad", "gym_essential", "Rubberized anti-slip foam with nylon wrap", "44cm length fits Olympic bar", 310.0, "Zenith Polychem Pune", 6),
        ("comp_ankle_cuffs", "CFC-CMP-016", "Neoprene Padded Cable Machine Ankle Cuffs (Pair)", "gym_essential", "Heavy Neoprene with dual D-ring stainless steel", "Universal fit", 280.0, "Titan Metals Jalandhar", 6),
        ("comp_steel_shaker", "CFC-CMP-017", "Double-Wall Vacuum Insulated Stainless Steel Shaker 750ml", "recovery", "18/8 Kitchen-grade stainless steel", "750ml capacity", 520.0, "Apex Steeltech Hosur", 8),
        ("comp_habit_journal", "CFC-CMP-018", "Hardbound 180-Day Daily Fitness & Routine Journal", "gym_essential", "120gsm archival FSC paper with vegan leather cover", "A5 size, 220 pages", 290.0, "Chronicle Press Mumbai", 7)
    ]
    for comp in components:
        cursor.execute("""
        INSERT INTO components (id, sku, name, category, material, dimensions, unit_cost, supplier_name, supplier_lead_days, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, comp + (now_str,))

    # 5. Seed Kits
    kits = [
        ("kit_arjun_precision", "arjun-precision-kit", "The Archer Precision Kit", "char_arjun",
         "Master your pre-training mindset and form alignment",
         "Designed for disciplined lifters who treat preparation as sacred. Calibrated resistance bands warm up kinetic chains, high-density foam releases myofascial tension, and the magnetic interval timer enforces exact rest intervals.",
         "Use 15 minutes before your main session: 5 min foam roll, 5 min band activation, zero-phone timer setup.",
         4299.0, 5499.0, "published", 1, "/images/kits/arjun_kit.svg", now_str),

        ("kit_bheema_titan", "bheema-titan-strength-kit", "The Titan Strength Kit", "char_bheema",
         "Maximal load integrity, spinal support and deep muscle recovery",
         "Built for heavy lifters who move substantial iron. Features our top-grain 10mm buffalo leather belt, competition wrist wraps, zero-dust liquid chalk, and a percussion lacrosse ball for deep tissue reset.",
         "Unwrap for heavy compound sets: cinch the belt for PR attempts, use the percussion ball between sets on hips and lats.",
         6499.0, 7999.0, "published", 1, "/images/kits/bheema_kit.svg", now_str),

        ("kit_karna_resolve", "karna-resolve-endurance-kit", "The Sol Invictus Kit", "char_karna",
         "Built to outlast grueling sessions and conquer physical fatigue",
         "Equips the dedicated athlete with a heavy-duty Cordura athlete duffel, reinforced weighted dip & pull-up chain belt, liquid grip, and the deep-tissue lacrosse ball.",
         "Load the dip belt for high-tension bodyweight work; unpack in any gym with ironclad confidence.",
         5899.0, 7299.0, "published", 1, "/images/kits/karna_kit.svg", now_str),

        ("kit_sita_lotus", "sita-lotus-restoration-kit", "The Lotus Restoration Kit", "char_sita",
         "Downregulate your nervous system and restore tissue elasticity",
         "A complete somatic recovery suite: natural organic cork & rubber mat, therapeutic acupressure spiked mat with cervical neck pillow, and organic magnesium lavender mist.",
         "Perform your 20-minute post-training wind-down: 10 minutes on the acupressure mat followed by deep hamstring and hip stretches on cork.",
         4999.0, 6299.0, "published", 1, "/images/kits/sita_kit.svg", now_str),

        ("kit_draupadi_sovereign", "draupadi-sovereign-kit", "The Sovereign Form Kit", "char_draupadi",
         "Command your physical power with calibrated precision and poise",
         "Precision accessory arsenal for leg day and functional dominance. Includes contoured Olympic barbell squat pad, neoprene cable ankle cuffs, insulated stainless shaker, and resistance band set.",
         "Integrate into hip thrusts, cable kickbacks, and heavy squats with zero slippage or bruise fatigue.",
         4799.0, 5999.0, "published", 1, "/images/kits/draupadi_kit.svg", now_str),

        ("kit_savitri_habit", "savitri-continuum-kit", "The Continuum Habit Kit", "char_savitri",
         "Unbroken daily routine consistency, micro-habits and mobility",
         "For the athlete committed to compounding small daily habits into lifetime mastery. Features the 180-Day routine tracker journal, multi-loop stretch strap, calibrated bands, and pure grip chalk.",
         "Log morning habit metrics, execute morning thoracic mobilization, and review routine cues daily.",
         3699.0, 4699.0, "published", 1, "/images/kits/savitri_kit.svg", now_str)
    ]
    for k in kits:
        cursor.execute("""
        INSERT INTO kits (id, slug, name, character_id, subtitle, description, routine_integration, base_price, mrp, status, is_featured, image_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, k)

    # 6. Seed Product Variants
    variants = [
        ("var_arjun_std", "kit_arjun_precision", "Standard Edition", "CFC-KIT-ARJ-STD", 4299.0, 1),
        ("var_arjun_pro", "kit_arjun_precision", "Pro Edition (Heavy Bands)", "CFC-KIT-ARJ-PRO", 4799.0, 1),

        ("var_bheema_m", "kit_bheema_titan", "Medium Belt (30-34 in)", "CFC-KIT-BHM-M", 6499.0, 1),
        ("var_bheema_l", "kit_bheema_titan", "Large Belt (34-38 in)", "CFC-KIT-BHM-L", 6499.0, 1),
        ("var_bheema_xl", "kit_bheema_titan", "XL Belt (38-42 in)", "CFC-KIT-BHM-XL", 6499.0, 1),

        ("var_karna_std", "kit_karna_resolve", "Standard Edition", "CFC-KIT-KRN-STD", 5899.0, 1),

        ("var_sita_std", "kit_sita_lotus", "Standard Restorative Edition", "CFC-KIT-SIT-STD", 4999.0, 1),

        ("var_draupadi_std", "kit_draupadi_sovereign", "Standard Sovereign Edition", "CFC-KIT-DRP-STD", 4799.0, 1),

        ("var_savitri_std", "kit_savitri_habit", "Standard Habit Edition", "CFC-KIT-SVT-STD", 3699.0, 1)
    ]
    for v in variants:
        cursor.execute("INSERT INTO product_variants (id, kit_id, variant_name, sku, price, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);", v + (now_str,))

    # 7. Seed BOM Versions (Active v1.0)
    bom_versions = [
        ("bom_arjun_std_v1", "var_arjun_std", "v1.0", "active", "Launch production BOM for Arjun Standard Kit", "user_admin"),
        ("bom_arjun_pro_v1", "var_arjun_pro", "v1.0", "active", "Launch production BOM for Arjun Pro Kit", "user_admin"),
        ("bom_bheema_m_v1", "var_bheema_m", "v1.0", "active", "Launch production BOM for Bheema Medium Kit", "user_admin"),
        ("bom_bheema_l_v1", "var_bheema_l", "v1.0", "active", "Launch production BOM for Bheema Large Kit", "user_admin"),
        ("bom_bheema_xl_v1", "var_bheema_xl", "v1.0", "active", "Launch production BOM for Bheema XL Kit", "user_admin"),
        ("bom_karna_std_v1", "var_karna_std", "v1.0", "active", "Launch production BOM for Karna Standard Kit", "user_admin"),
        ("bom_sita_std_v1", "var_sita_std", "v1.0", "active", "Launch production BOM for Sita Standard Kit", "user_admin"),
        ("bom_draupadi_std_v1", "var_draupadi_std", "v1.0", "active", "Launch production BOM for Draupadi Standard Kit", "user_admin"),
        ("bom_savitri_std_v1", "var_savitri_std", "v1.0", "active", "Launch production BOM for Savitri Standard Kit", "user_admin")
    ]
    for bv in bom_versions:
        cursor.execute("INSERT INTO bom_versions (id, variant_id, version, status, notes, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);", bv + (now_str,))

    # 8. Seed BOM Items (Components per variant)
    bom_items = [
        # Arjun Standard: 1x band set, 1x foam roller, 1x focus timer, 1x chalk block
        ("bi_01", "bom_arjun_std_v1", "comp_band_set", 1),
        ("bi_02", "bom_arjun_std_v1", "comp_foam_roller", 1),
        ("bi_03", "bom_arjun_std_v1", "comp_focus_timer", 1),
        ("bi_04", "bom_arjun_std_v1", "comp_chalk_block", 1),

        # Arjun Pro: 2x band set, 1x foam roller, 1x focus timer, 2x chalk block
        ("bi_05", "bom_arjun_pro_v1", "comp_band_set", 2),
        ("bi_06", "bom_arjun_pro_v1", "comp_foam_roller", 1),
        ("bi_07", "bom_arjun_pro_v1", "comp_focus_timer", 1),
        ("bi_08", "bom_arjun_pro_v1", "comp_chalk_block", 2),

        # Bheema Medium: 1x leather belt, 1x wrist wraps, 1x liquid chalk, 1x massage ball
        ("bi_09", "bom_bheema_m_v1", "comp_leather_belt", 1),
        ("bi_10", "bom_bheema_m_v1", "comp_wrist_wraps", 1),
        ("bi_11", "bom_bheema_m_v1", "comp_liquid_chalk", 1),
        ("bi_12", "bom_bheema_m_v1", "comp_massage_ball", 1),

        # Bheema Large: 1x leather belt, 1x wrist wraps, 1x liquid chalk, 1x massage ball
        ("bi_13", "bom_bheema_l_v1", "comp_leather_belt", 1),
        ("bi_14", "bom_bheema_l_v1", "comp_wrist_wraps", 1),
        ("bi_15", "bom_bheema_l_v1", "comp_liquid_chalk", 1),
        ("bi_16", "bom_bheema_l_v1", "comp_massage_ball", 1),

        # Bheema XL: 1x leather belt, 1x wrist wraps, 1x liquid chalk, 1x massage ball
        ("bi_17", "bom_bheema_xl_v1", "comp_leather_belt", 1),
        ("bi_18", "bom_bheema_xl_v1", "comp_wrist_wraps", 1),
        ("bi_19", "bom_bheema_xl_v1", "comp_liquid_chalk", 1),
        ("bi_20", "bom_bheema_xl_v1", "comp_massage_ball", 1),

        # Karna: 1x duffel bag, 1x dip belt, 1x liquid chalk, 1x massage ball
        ("bi_21", "bom_karna_std_v1", "comp_duffel_bag", 1),
        ("bi_22", "bom_karna_std_v1", "comp_dip_belt", 1),
        ("bi_23", "bom_karna_std_v1", "comp_liquid_chalk", 1),
        ("bi_24", "bom_karna_std_v1", "comp_massage_ball", 1),

        # Sita: 1x cork mat, 1x acupressure mat, 1x recovery mist, 1x stretch strap
        ("bi_25", "bom_sita_std_v1", "comp_cork_mat", 1),
        ("bi_26", "bom_sita_std_v1", "comp_acupressure", 1),
        ("bi_27", "bom_sita_std_v1", "comp_recovery_mist", 1),
        ("bi_28", "bom_sita_std_v1", "comp_stretch_strap", 1),

        # Draupadi: 1x barbell pad, 1x ankle cuffs, 1x steel shaker, 1x band set
        ("bi_29", "bom_draupadi_std_v1", "comp_barbell_pad", 1),
        ("bi_30", "bom_draupadi_std_v1", "comp_ankle_cuffs", 1),
        ("bi_31", "bom_draupadi_std_v1", "comp_steel_shaker", 1),
        ("bi_32", "bom_draupadi_std_v1", "comp_band_set", 1),

        # Savitri: 1x habit journal, 1x stretch strap, 1x band set, 1x chalk block
        ("bi_33", "bom_savitri_std_v1", "comp_habit_journal", 1),
        ("bi_34", "bom_savitri_std_v1", "comp_stretch_strap", 1),
        ("bi_35", "bom_savitri_std_v1", "comp_band_set", 1),
        ("bi_36", "bom_savitri_std_v1", "comp_chalk_block", 1)
    ]
    for bi in bom_items:
        cursor.execute("INSERT INTO bom_items (id, bom_version_id, component_id, quantity) VALUES (?, ?, ?, ?);", bi)

    # 9. Seed Inventory Stock
    # Note: Keep Savitri component stock low or one component 0 to demonstrate Out of Stock / low stock states cleanly
    inventory_data = [
        ("inv_01", "comp_band_set", 45, 12, "Bay A-01"),
        ("inv_02", "comp_chalk_block", 60, 15, "Bay A-02"),
        ("inv_03", "comp_foam_roller", 30, 8, "Bay B-01"),
        ("inv_04", "comp_focus_timer", 28, 6, "Bay B-02"),
        ("inv_05", "comp_leather_belt", 25, 8, "Bay C-01"),
        ("inv_06", "comp_wrist_wraps", 50, 10, "Bay C-02"),
        ("inv_07", "comp_liquid_chalk", 40, 10, "Bay A-03"),
        ("inv_08", "comp_massage_ball", 22, 6, "Bay B-03"),
        ("inv_09", "comp_duffel_bag", 18, 5, "Bay D-01"),
        ("inv_10", "comp_dip_belt", 20, 5, "Bay D-02"),
        ("inv_11", "comp_cork_mat", 35, 8, "Bay E-01"),
        ("inv_12", "comp_acupressure", 32, 8, "Bay E-02"),
        ("inv_13", "comp_recovery_mist", 45, 10, "Bay E-03"),
        ("inv_14", "comp_stretch_strap", 40, 10, "Bay F-01"),
        ("inv_15", "comp_barbell_pad", 24, 6, "Bay F-02"),
        ("inv_16", "comp_ankle_cuffs", 28, 6, "Bay F-03"),
        ("inv_17", "comp_steel_shaker", 36, 8, "Bay G-01"),
        ("inv_18", "comp_habit_journal", 4, 10, "Bay H-01") # Low stock (4 left) to test low-stock alert!
    ]
    for inv in inventory_data:
        cursor.execute("INSERT INTO inventory (id, component_id, on_hand, low_stock_threshold, location, updated_at) VALUES (?, ?, ?, ?, ?, ?);", inv + (now_str,))
        # Initial stock ledger entry
        cursor.execute("""
        INSERT INTO stock_ledger (id, component_id, change_type, quantity, balance_after, reference_type, reference_id, reason, created_by, created_at)
        VALUES (?, ?, 'receipt', ?, ?, 'initial_seed', 'SEED-001', 'Initial warehouse stock receipt', 'user_admin', ?);
        """, (str(uuid.uuid4()), inv[1], inv[2], inv[2], now_str))

    # 10. Seed Campaigns
    campaigns = [
        ("camp_diwali", "diwali_focus_2026", "Diwali Focus & Strength Campaign", "instagram", "influencer", 1, "2026-10-20", "2026-11-20"),
        ("camp_anthem", "launch_anthem", "COFOCO Brand Launch Video Anthem", "youtube", "preroll", 1, "2026-11-01", "2026-12-01"),
        ("camp_reels", "instagram_reels", "Organic Character Training Reels", "instagram", "social_organic", 1, "2026-11-05", "2026-12-31"),
        ("camp_founder", "founder_newsletter", "Aditya's Form & Focus Newsletter", "email", "newsletter", 1, "2026-11-08", "2026-12-31")
    ]
    for camp in campaigns:
        cursor.execute("INSERT INTO campaigns (id, code, name, source, medium, is_active, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", camp)

    # 11. Seed Indian Serviceable Pincodes
    pincodes = [
        ("110001", "New Delhi", "Delhi", 2, 0),
        ("110020", "New Delhi", "Delhi", 2, 0),
        ("400001", "Mumbai", "Maharashtra", 3, 0),
        ("400050", "Mumbai (Bandra)", "Maharashtra", 3, 0),
        ("560001", "Bengaluru", "Karnataka", 2, 0),
        ("560034", "Bengaluru (Koramangala)", "Karnataka", 2, 0),
        ("560038", "Bengaluru (Indiranagar)", "Karnataka", 2, 0),
        ("500001", "Hyderabad", "Telangana", 3, 0),
        ("500081", "Hyderabad (Hitec City)", "Telangana", 3, 0),
        ("600001", "Chennai", "Tamil Nadu", 3, 0),
        ("700001", "Kolkata", "West Bengal", 4, 0),
        ("411001", "Pune", "Maharashtra", 3, 0),
        ("380001", "Ahmedabad", "Gujarat", 3, 0),
        ("122001", "Gurugram", "Haryana", 2, 0),
        ("201301", "Noida", "Uttar Pradesh", 2, 0)
    ]
    for p in pincodes:
        cursor.execute("INSERT INTO serviceable_pincodes (pincode, city, state, estimated_days, cod_allowed) VALUES (?, ?, ?, ?, ?);", p)

    # 12. Seed Historical Orders (Paid, Picking, Packed, Dispatched, Delivered)
    # Covering single-kit, mixed-kit, refunds, and overdue dispatch scenarios for founder analytics!
    sample_orders = [
        # Order 1: Delivered (Delivered 3 days ago)
        ("ord_01", "CFC-2026-8801", "Kavita Ramachandran", "kavita.r@gmail.com", "+91 98201 12345", "Flat 4B, Silver Oak, Indiranagar", "Bengaluru", "Karnataka", "560038",
         4299.0, 0.0, 0.0, 773.82, 4299.0, "paid", "delivered", (now - timedelta(days=5)).isoformat(), "user_warehouse", "camp_diwali", "sess_001",
         (now - timedelta(days=6)).isoformat(), (now - timedelta(days=3)).isoformat()),

        # Order 2: Dispatched with tracking
        ("ord_02", "CFC-2026-8802", "Devendra Singhania", "dev.singh@outlook.com", "+91 98111 98765", "House 12, Golf Links", "New Delhi", "Delhi", "110001",
         6499.0, 0.0, 0.0, 1169.82, 6499.0, "paid", "dispatched", (now - timedelta(days=2)).isoformat(), "user_warehouse", "camp_anthem", "sess_002",
         (now - timedelta(days=3)).isoformat(), (now - timedelta(days=1)).isoformat()),

        # Order 3: Mixed-Kit Order (Arjun + Sita kits to test mixed-kit line attribution!)
        ("ord_03", "CFC-2026-8803", "Arunav Sen", "arunav.sen@tcs.com", "+91 97400 44556", "Tower 3, Penthouse 21, Hitec City", "Hyderabad", "Telangana", "500081",
         9298.0, 500.0, 0.0, 1583.64, 8798.0, "paid", "packed", (now + timedelta(days=1)).isoformat(), "user_warehouse", "camp_reels", "sess_003",
         (now - timedelta(hours=18)).isoformat(), (now - timedelta(hours=2)).isoformat()),

        # Order 4: Picking (Freshly paid, awaiting warehouse packing)
        ("ord_04", "CFC-2026-8804", "Meera Krishnan", "meera.k@gmail.com", "+91 94440 22334", "32/1 Poes Garden", "Chennai", "Tamil Nadu", "600001",
         4999.0, 0.0, 0.0, 899.82, 4999.0, "paid", "picking", (now + timedelta(days=2)).isoformat(), "user_warehouse", "camp_founder", "sess_004",
         (now - timedelta(hours=6)).isoformat(), (now - timedelta(hours=6)).isoformat()),

        # Order 5: Overdue Dispatch (Paid 3 days ago, promised dispatch was yesterday! Triggers overdue dispatch exception)
        ("ord_05", "CFC-2026-8805", "Rajeshwar Patil", "raj.patil@rediffmail.com", "+91 98220 55667", "102 Koregaon Park", "Pune", "Maharashtra", "411001",
         5899.0, 0.0, 0.0, 1061.82, 5899.0, "paid", "paid", (now - timedelta(days=1)).isoformat(), "user_warehouse", "camp_diwali", "sess_005",
         (now - timedelta(days=3)).isoformat(), (now - timedelta(days=3)).isoformat()),

        # Order 6: Return & Refund Case (Delivered, returned, inspected, and refunded)
        ("ord_06", "CFC-2026-8806", "Sneha Roy", "sneha.roy@gmail.com", "+91 98300 77889", "54 Ballygunge Circular Rd", "Kolkata", "West Bengal", "700001",
         4799.0, 0.0, 0.0, 863.82, 4799.0, "refunded", "delivered", (now - timedelta(days=7)).isoformat(), "user_warehouse", "camp_anthem", "sess_006",
         (now - timedelta(days=8)).isoformat(), (now - timedelta(days=2)).isoformat()),

        # Order 7: Reconciliation Required (Late payment arrival after reservation expired!)
        ("ord_07", "CFC-2026-8807", "Tanvi Bhatia", "tanvi.b@gmail.com", "+91 99990 11223", "C-88 Defence Colony", "New Delhi", "Delhi", "110020",
         4299.0, 0.0, 0.0, 773.82, 4299.0, "reconciliation_required", "paid", (now + timedelta(days=2)).isoformat(), None, "camp_reels", "sess_007",
         (now - timedelta(hours=1)).isoformat(), (now - timedelta(hours=1)).isoformat())
    ]

    for ord_data in sample_orders:
        cursor.execute("""
        INSERT INTO orders (id, order_number, customer_name, customer_email, customer_phone, delivery_address, city, state, pincode,
                            subtotal, discount, shipping_fee, tax, total_amount, payment_status, order_status, promised_dispatch_date,
                            assigned_staff_id, campaign_id, session_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ord_data)

    # 13. Seed Order Items with Exact BOM Snapshots!
    # Order 1: Arjun Precision Kit (Standard)
    bom_snapshot_arjun = [
        {"component_sku": "CFC-CMP-001", "name": "Calibrated Latex Resistance Bands (Set of 4)", "qty": 1, "unit_cost": 380.0},
        {"component_sku": "CFC-CMP-003", "name": "Precision Grid High-Density EPP Foam Roller", "qty": 1, "unit_cost": 420.0},
        {"component_sku": "CFC-CMP-004", "name": "Magnetic Interval & Routine Focus Timer", "qty": 1, "unit_cost": 490.0},
        {"component_sku": "CFC-CMP-002", "name": "Pure Magnesium Carbonate Gym Chalk Block", "qty": 1, "unit_cost": 85.0}
    ]
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_01", "ord_01", "var_arjun_std", "The Archer Precision Kit", "Standard Edition", "Arjun", 4299.0, 1, json.dumps(bom_snapshot_arjun), (now - timedelta(days=6)).isoformat()))

    # Order 2: Bheema Titan Strength Kit (Large)
    bom_snapshot_bheema = [
        {"component_sku": "CFC-CMP-005", "name": "Olympic Grade Top-Grain Leather Lifting Belt 10mm (Large)", "qty": 1, "unit_cost": 1250.0},
        {"component_sku": "CFC-CMP-006", "name": "Heavy Duty Competition Wrist Wraps (Pair)", "qty": 1, "unit_cost": 210.0},
        {"component_sku": "CFC-CMP-007", "name": "Zero-Dust Liquid Grip Chalk 150ml", "qty": 1, "unit_cost": 140.0},
        {"component_sku": "CFC-CMP-008", "name": "Vibrating Percussion Recovery Lacrosse Ball", "qty": 1, "unit_cost": 680.0}
    ]
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_02", "ord_02", "var_bheema_l", "The Titan Strength Kit", "Large Belt (34-38 in)", "Bheema", 6499.0, 1, json.dumps(bom_snapshot_bheema), (now - timedelta(days=3)).isoformat()))

    # Order 3: Mixed Order (Arjun + Sita)
    bom_snapshot_sita = [
        {"component_sku": "CFC-CMP-011", "name": "Organic Natural Cork & Tree Rubber Restorative Mat", "qty": 1, "unit_cost": 980.0},
        {"component_sku": "CFC-CMP-012", "name": "Therapeutic Acupressure Spiked Mat & Neck Pillow", "qty": 1, "unit_cost": 620.0},
        {"component_sku": "CFC-CMP-013", "name": "Botanical Magnesium Sleep & Wind-Down Mist 100ml", "qty": 1, "unit_cost": 230.0},
        {"component_sku": "CFC-CMP-014", "name": "Multi-Loop Non-Elastic Physical Therapy Stretch Strap", "qty": 1, "unit_cost": 160.0}
    ]
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_03_a", "ord_03", "var_arjun_std", "The Archer Precision Kit", "Standard Edition", "Arjun", 4299.0, 1, json.dumps(bom_snapshot_arjun), (now - timedelta(hours=18)).isoformat()))
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_03_b", "ord_03", "var_sita_std", "The Lotus Restoration Kit", "Standard Restorative Edition", "Sita", 4999.0, 1, json.dumps(bom_snapshot_sita), (now - timedelta(hours=18)).isoformat()))

    # Order 4: Sita Kit
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_04", "ord_04", "var_sita_std", "The Lotus Restoration Kit", "Standard Restorative Edition", "Sita", 4999.0, 1, json.dumps(bom_snapshot_sita), (now - timedelta(hours=6)).isoformat()))

    # Order 5: Karna Kit
    bom_snapshot_karna = [
        {"component_sku": "CFC-CMP-009", "name": "Water-Resistant 1000D Cordura Athlete Duffel", "qty": 1, "unit_cost": 1100.0},
        {"component_sku": "CFC-CMP-010", "name": "Reinforced Steel Chain Weighted Dip & Pull-up Belt", "qty": 1, "unit_cost": 550.0},
        {"component_sku": "CFC-CMP-007", "name": "Zero-Dust Liquid Grip Chalk 150ml", "qty": 1, "unit_cost": 140.0},
        {"component_sku": "CFC-CMP-008", "name": "Vibrating Percussion Recovery Lacrosse Ball", "qty": 1, "unit_cost": 680.0}
    ]
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_05", "ord_05", "var_karna_std", "The Sol Invictus Kit", "Standard Edition", "Karna", 5899.0, 1, json.dumps(bom_snapshot_karna), (now - timedelta(days=3)).isoformat()))

    # Order 6: Draupadi Kit (Returned)
    bom_snapshot_draupadi = [
        {"component_sku": "CFC-CMP-015", "name": "Contoured Ergonomic High-Density Squat Barbell Pad", "qty": 1, "unit_cost": 310.0},
        {"component_sku": "CFC-CMP-016", "name": "Neoprene Padded Cable Machine Ankle Cuffs (Pair)", "qty": 1, "unit_cost": 280.0},
        {"component_sku": "CFC-CMP-017", "name": "Double-Wall Vacuum Insulated Stainless Steel Shaker 750ml", "qty": 1, "unit_cost": 520.0},
        {"component_sku": "CFC-CMP-001", "name": "Calibrated Latex Resistance Bands (Set of 4)", "qty": 1, "unit_cost": 380.0}
    ]
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_06", "ord_06", "var_draupadi_std", "The Sovereign Form Kit", "Standard Sovereign Edition", "Draupadi", 4799.0, 1, json.dumps(bom_snapshot_draupadi), (now - timedelta(days=8)).isoformat()))

    # Order 7: Arjun Kit (Late arrival)
    cursor.execute("""
    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ("oi_07", "ord_07", "var_arjun_std", "The Archer Precision Kit", "Standard Edition", "Arjun", 4299.0, 1, json.dumps(bom_snapshot_arjun), (now - timedelta(hours=1)).isoformat()))

    # 14. Seed Payment Events
    payment_events = [
        ("pay_01", "ord_01", "razorpay", "payment.captured", "pay_RZP_TEST_8801", "order_RZP_ORD_8801", "sig_valid_01", 4299.0, "INR", "verified", json.dumps({"method": "upi", "vpa": "kavita@okhdfcbank"}), (now - timedelta(days=6)).isoformat()),
        ("pay_02", "ord_02", "razorpay", "payment.captured", "pay_RZP_TEST_8802", "order_RZP_ORD_8802", "sig_valid_02", 6499.0, "INR", "verified", json.dumps({"method": "card", "card_network": "MasterCard"}), (now - timedelta(days=3)).isoformat()),
        ("pay_03", "ord_03", "razorpay", "payment.captured", "pay_RZP_TEST_8803", "order_RZP_ORD_8803", "sig_valid_03", 8798.0, "INR", "verified", json.dumps({"method": "netbanking", "bank": "HDFC"}), (now - timedelta(hours=18)).isoformat()),
        ("pay_04", "ord_04", "razorpay", "payment.captured", "pay_RZP_TEST_8804", "order_RZP_ORD_8804", "sig_valid_04", 4999.0, "INR", "verified", json.dumps({"method": "upi", "vpa": "meera@icici"}), (now - timedelta(hours=6)).isoformat()),
        ("pay_05", "ord_05", "razorpay", "payment.captured", "pay_RZP_TEST_8805", "order_RZP_ORD_8805", "sig_valid_05", 5899.0, "INR", "verified", json.dumps({"method": "card", "card_network": "Visa"}), (now - timedelta(days=3)).isoformat()),
        ("pay_06", "ord_06", "razorpay", "payment.captured", "pay_RZP_TEST_8806", "order_RZP_ORD_8806", "sig_valid_06", 4799.0, "INR", "verified", json.dumps({"method": "upi", "vpa": "sneha@oksbi"}), (now - timedelta(days=8)).isoformat()),
        ("pay_07", "ord_07", "razorpay", "payment.captured", "pay_RZP_TEST_8807", "order_RZP_ORD_8807", "sig_late_07", 4299.0, "INR", "late_arrival", json.dumps({"method": "upi", "vpa": "tanvi@okaxis", "note": "Captured after reservation timeout"}), (now - timedelta(hours=1)).isoformat())
    ]
    for pe in payment_events:
        cursor.execute("""
        INSERT INTO payment_events (id, order_id, gateway, event_type, gateway_payment_id, gateway_order_id, gateway_signature, amount, currency, status, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, pe)

    # 15. Seed Shipments
    shipments = [
        ("ship_01", "ord_01", "Blue Dart Express", "BLUEDART-88291039", "https://www.bluedart.com/tracking?track=BLUEDART-88291039",
         (now - timedelta(days=5)).isoformat(), (now - timedelta(days=3)).isoformat(), "user_warehouse", (now - timedelta(days=5)).isoformat()),
        ("ship_02", "ord_02", "Delhivery Logistics", "DELH-99201948", "https://www.delhivery.com/track/package/DELH-99201948",
         (now - timedelta(days=1)).isoformat(), None, "user_warehouse", (now - timedelta(days=1)).isoformat()),
        ("ship_06", "ord_06", "Blue Dart Express", "BLUEDART-77291011", "https://www.bluedart.com/tracking?track=BLUEDART-77291011",
         (now - timedelta(days=6)).isoformat(), (now - timedelta(days=4)).isoformat(), "user_warehouse", (now - timedelta(days=6)).isoformat())
    ]
    for s in shipments:
        cursor.execute("""
        INSERT INTO shipments (id, order_id, courier_name, tracking_number, tracking_url, dispatched_at, delivered_at, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, s)

    # 16. Seed Returns & Refunds (Inspected and Approved)
    returns = [
        ("ret_01", "ord_06", "oi_06", 1, "Ordered incorrect size preference for ankle cuffs; kit unopened", "inspected", "passed", 1, "user_support",
         "Box unopened, safety seals fully intact. Passed quality inspection and restocked.", (now - timedelta(days=3)).isoformat(), (now - timedelta(days=2)).isoformat()),
        ("ret_02", "ord_02", "oi_02", 1, "Customer requested exchange for size preference; package returned to warehouse", "requested", "pending", 0, "user_support",
         None, (now - timedelta(hours=8)).isoformat(), (now - timedelta(hours=8)).isoformat())
    ]
    for r in returns:
        cursor.execute("""
        INSERT INTO returns (id, order_id, order_item_id, quantity, reason, status, inspection_result, restocked, assigned_owner, resolution_notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, r)

    refunds = [
        ("ref_01", "ret_01", "ord_06", 4799.0, "rfnd_RZP_REF_8806", "processed", "Inspected return passed quality check; full refund credited to original UPI account", "user_finance", (now - timedelta(days=2)).isoformat())
    ]
    for rf in refunds:
        cursor.execute("""
        INSERT INTO refunds (id, return_id, order_id, amount, gateway_refund_id, status, reason, approved_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rf)

    # 17. Seed Analytics Events (Storefront Sessions & Behavioral Funnel)
    # Generate realistic session events across the 6 launch characters
    char_ids = ["char_arjun", "char_bheema", "char_karna", "char_sita", "char_draupadi", "char_savitri"]
    kit_ids = ["kit_arjun_precision", "kit_bheema_titan", "kit_karna_resolve", "kit_sita_lotus", "kit_draupadi_sovereign", "kit_savitri_habit"]
    camp_ids = ["camp_diwali", "camp_anthem", "camp_reels", "camp_founder"]

    # Seed 240 simulated storefront sessions across the past 7 days
    event_rows = []
    for day in range(7, -1, -1):
        day_time = now - timedelta(days=day)
        # 30 sessions per day
        for s_idx in range(30):
            sess_id = f"sess_{day}_{s_idx:02d}"
            camp = camp_ids[s_idx % len(camp_ids)]
            char = char_ids[(s_idx + day) % len(char_ids)]
            kit = kit_ids[(s_idx + day) % len(kit_ids)]
            e_time = (day_time + timedelta(minutes=s_idx * 15)).isoformat()

            # 1. character_view
            event_rows.append((str(uuid.uuid4()), sess_id, "character_view", char, None, camp, json.dumps({"source": "campaign_entry"}), e_time))

            # 2. kit_view (70% reach kit view)
            if s_idx % 10 < 7:
                event_rows.append((str(uuid.uuid4()), sess_id, "kit_view", char, kit, camp, json.dumps({"referrer": "character_collection"}), e_time))

            # 3. compare_used (30% use compare)
            if s_idx % 10 in (1, 4, 7):
                alt_kit = kit_ids[(s_idx + day + 1) % len(kit_ids)]
                event_rows.append((str(uuid.uuid4()), sess_id, "compare_used", char, kit, camp, json.dumps({"compared_with": alt_kit}), e_time))

            # 4. add_to_cart (40% add to cart)
            if s_idx % 10 in (2, 5, 8, 9):
                event_rows.append((str(uuid.uuid4()), sess_id, "add_to_cart", char, kit, camp, json.dumps({"qty": 1}), e_time))

            # 5. checkout_started (20% start checkout)
            if s_idx % 10 in (5, 9):
                event_rows.append((str(uuid.uuid4()), sess_id, "checkout_started", char, kit, camp, json.dumps({"step": "shipping_address"}), e_time))

    cursor.executemany("""
    INSERT INTO analytics_events (id, session_id, event_name, character_id, kit_id, campaign_id, metadata_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, event_rows)

    # 18. Seed Audit Log entries
    audit_data = [
        (str(uuid.uuid4()), "user_admin", "initialize_catalog", "catalog", "system", json.dumps({"message": "Initialized 6 launch characters and 6 BOM configurations"}), (now - timedelta(days=14)).isoformat()),
        (str(uuid.uuid4()), "user_publisher", "publish_character", "character", "char_arjun", json.dumps({"status": "published", "approved": True}), (now - timedelta(days=10)).isoformat()),
        (str(uuid.uuid4()), "user_warehouse", "dispatch_order", "order", "ord_01", json.dumps({"tracking": "BLUEDART-88291039"}), (now - timedelta(days=5)).isoformat()),
        (str(uuid.uuid4()), "user_support", "inspect_return", "return", "ret_01", json.dumps({"result": "passed", "restocked": True}), (now - timedelta(days=2)).isoformat()),
        (str(uuid.uuid4()), "user_finance", "process_refund", "refund", "ref_01", json.dumps({"amount": 4799.0, "gateway_ref": "rfnd_RZP_REF_8806"}), (now - timedelta(days=2)).isoformat())
    ]
    for aud in audit_data:
        cursor.execute("INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, changes_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);", aud)

    conn.commit()
    conn.close()
    print("[COFOCO] Database schema initialized and realistic seed data inserted successfully.")

if __name__ == "__main__":
    init_db()
    seed_db()
