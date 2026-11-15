# COFOCO — Conscious Form Company
### Complete Character-Inspired Fitness & Recovery E-Commerce Platform

---

## 1. Executive Summary & Brand Overview

**COFOCO** (**Conscious Form Company**) brings gym essentials and somatic cellular recovery equipment together into character-inspired kits. Built directly from the authoritative *COFOCO Website Requirements Analysis Specification (v0.1, 14 Nov 2026)*, this platform connects character archetypes with disciplined daily training routines, reliable atomic inventory management, and founder business analytics.

- **Brand Personality**: Modern, Premium, Minimal, Fitness-focused, Inspirational, Character-driven
- **Target Market**: Direct-to-Consumer in India, priced in INR (₹), Indian GST 18% inclusive
- **Design Foundation**:
  - Primary: Deep Charcoal (`#121416`, `#1A1D20`)
  - Secondary: Warm Ivory (`#FDFBF7`, `#F7F4EE`)
  - Accent: Muted Gold (`#C5A880`, `#D4AF37`)
  - Background: Soft White (`#FAFAFA`)
  - Text: Dark Charcoal (`#1F2428`)
- **Accessibility**: Strict **WCAG 2.2 AA** compliance, keyboard tab navigation, visible focus indicators, skip-to-content links, color cues paired with text labels, and reduced-motion media query support.

---

## 2. Six Launch Characters & Prescribed Routines

Character artwork, symbolism, palettes, and copy are strictly configurable and approved before publication without inventing unverified claims. Every character page is labeled **"[Character Name] by COFOCO"**.

| Character | Theme & Motif | Palette Tokens | Defining Quality | Routine Cue | Curated Launch Kit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arjun** | Moon and flowing water | Cool Blues (`#0F2B48`, `#1E5B94`, `#6BA4D9`, `#D9E8F5`) | **Focus** | *Preparation before training* | **The Archer Precision Kit** (₹4,299) |
| **Bheema** | Mountain and heavy earth | Warm Earth Tones (`#3B2219`, `#7D4F38`, `#C08A5E`, `#EADCC9`) | **Strength** | *The work of a training session* | **The Titan Strength Kit** (₹6,499) |
| **Karna** | Amber sun motif | Amber Sun (`#3D2504`, `#B87314`, `#E09F3E`, `#FCECD5`) | **Resolve** | *Show up with resolve* | **The Sol Invictus Kit** (₹5,899) |
| **Sita** | Ivory lotus rising from water | Lotus & Forest Greens (`#253028`, `#4A6B56`, `#92B89E`, `#E9F0EB`) | **Steadiness** | *Wind-down routine* | **The Lotus Restoration Kit** (₹4,999) |
| **Draupadi** | Royal rose motif | Burgundy & Rose (`#3A121E`, `#8B2643`, `#C85A7A`, `#F7E5EB`) | **Self-possession** | *Purposeful routine* | **The Sovereign Form Kit** (₹4,799) |
| **Savitri** | Olive tones & habit loop | Olive & Morning Mist (`#232A1C`, `#4F5D38`, `#879A63`, `#ECF0E7`) | **Resolve and consistency** | *Consistent daily habits* | **The Continuum Habit Kit** (₹3,699) |

---

## 3. Project Structure

```
C:\Users\mvish\.gemini\antigravity\scratch\cofoco\
├── database.py                 # SQLite database schema (23 tables) & seed data
├── server.py                   # High-performance multi-threaded REST API server (Python 3.13)
├── test_inmemory.py            # Comprehensive 12-scenario automated test suite (100% pass)
├── test_cofoco.py              # Socket-based integration test runner
├── generate_assets.py          # Vector asset generator for character emblems & kit visuals
├── check_db.py                 # Diagnostic verification utility
├── cofoco.db                   # SQLite transactional database (WAL mode, foreign keys)
│
├── static/                     # Storefront & Staff Dashboard Single Page Application
│   ├── index.html              # Modern, semantic, accessible HTML5 SPA shell
│   ├── styles.css              # Design system stylesheet, WCAG 2.2 AA tokens, responsive CSS
│   ├── app.js                  # Modular client application, router, state, cart, modals
│   └── images/
│       ├── characters/         # Bespoke SVG artwork emblems (arjun, bheema, karna, sita, draupadi, savitri)
│       └── kits/               # High-res kit graphics (arjun_kit, bheema_kit, etc.)
│
└── backend_django/             # Full Django REST Framework production configuration
    ├── manage.py
    ├── requirements.txt
    ├── .env.example
    ├── cofoco/
    │   ├── settings.py         # Configured for PostgreSQL, DRF, CORS, Razorpay, IST
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    └── apps/
        ├── catalog/models.py   # Character, Component, Kit, ProductVariant, BOMVersion, BOMItem
        ├── inventory/models.py # Inventory, StockLedger, Reservation
        ├── orders/models.py    # Cart, Order, OrderItem (frozen BOM snapshot), Shipment, Return, Refund
        └── analytics/models.py # Campaign, AnalyticsEvent (Zero PII), AuditLog
```

---

## 4. Database Schema & Architecture

The system models all 23 core entities with relational integrity:

```
Character
   ↓
  Kit
   ↓
ProductVariant
   ↓
BOMVersion (active version)
   ↓
BOMItem ──→ Component ──→ Inventory & Stock Ledger
                             ↑
                        Reservations (15-min atomic holds)
```

1. **`roles`**: RBAC permissions for Admin, Brand Editor, Publisher, Warehouse Staff, Support Staff, Finance Staff.
2. **`users`**: Staff accounts with salted PBKDF2-HMAC-SHA256 password hashing.
3. **`characters`**: Quality, routine cue, story, theme colors, draft/review/published lifecycle.
4. **`components`**: Raw gym essentials & recovery items (SKUs, materials, dimensions, unit costs, supplier lead times).
5. **`kits`**: Curated product bundles linked to characters, pricing in INR.
6. **`product_variants`**: Specific sellable SKUs (Standard vs Pro editions, belt sizes).
7. **`bom_versions` & `bom_items`**: Multi-component Bill of Materials with versioning.
8. **`inventory`**: Component on-hand counts, low-stock reorder thresholds, warehouse bay locations.
9. **`stock_ledger`**: Complete audit log for receipts, reservations, picks, adjustments, and inspected returns.
10. **`reservations`**: Component-level atomic locks with 15-minute checkout expiration.
11. **`carts` & `cart_items`**: Session-persisted cart state with coupon discounts.
12. **`orders`**: Customer contact data, delivery address, subtotal, discount, shipping, GST tax, order status (`paid`, `picking`, `packed`, `dispatched`, `delivered`).
13. **`order_items`**: **Crucial Requirement**: Preserves the exact frozen BOM configuration snapshot (`bom_snapshot_json`) at purchase time. Future BOM edits do not alter historical pick lists!
14. **`payment_events`**: Idempotent event ledger for Razorpay captures, preventing duplicate order creation.
15. **`shipments`**: Courier partner, tracking number (AWB), and live carrier tracking URL.
16. **`returns` & `refunds`**: Quality inspection gate (`passed` vs `damaged`). Restocks into sellable inventory only upon verified inspection pass!
17. **`campaigns` & `analytics_events`**: Pseudonymous behavioral funnel tracking (`character_view`, `kit_view`, `compare_used`, `add_to_cart`, `checkout_started`). Strictly zero PII.
18. **`serviceable_pincodes`**: Real-time Indian postal code serviceability validation.

---

## 5. Core Business Logics & Mathematical Formats

### A. Sellable Kit Inventory Calculation (OP02)
Available component stock is computed as on-hand sellable quantity less active reservations:
$$\text{Available Stock}_c = \text{On-Hand}_c - \sum \text{Active Reservations}_c$$
The number of sellable kits for a variant is strictly limited by the lowest whole number of kits supported by its required components:
$$\text{Sellable Kits} = \min_{c \in \text{BOM}} \left\lfloor \frac{\text{Available Stock}_c}{\text{Required Qty}_c} \right\rfloor$$
If any component drops to 0 available units, the kit dynamically switches to **Out of Stock**, disables purchase buttons, keeps product specs visible, and displays in-stock alternative kits.

### B. Atomic Component Reservation (OP02, OP03)
When a customer clicks checkout, all required BOM components across all cart items are reserved atomically within a database transaction (`BEGIN IMMEDIATE`). A 15-minute window (`reserved_until`) is established. If two customers compete for the last component, only one receives the reservation; the other receives an HTTP 409 conflict and availability notice.

### C. Payment Idempotency & Reconciliation (OP03, OP05)
Duplicate webhook/callback captures from Razorpay are verified and acknowledged without creating duplicate orders or deducting stock twice. Late payments arriving after a reservation has expired are safely placed in the `reconciliation_required` queue to prevent unreserved warehouse dispatch.

### D. Return Quality Gate (OP05, US03)
Returned inventory is never blindly restocked. Units enter a physical inspection workflow. Only items marked `passed` are restocked into sellable inventory with an audit entry in the stock ledger. Damaged/opened items are scrapped.

### E. Founder Business Analytics (AN01–AN03, US04)
Calculated in **Asia/Kolkata (IST)** timezone with monetary figures in **INR (₹)**:
- **Session Conversion**: Eligible storefront sessions with at least one captured order $\div$ eligible sessions.
- **Character Engagement**: Sessions reaching a kit from a character page $\div$ sessions viewing that character.
- **Net Merchandise Revenue**: Captured merchandise value after discounts, less merchandise refunds (excludes taxes & shipping). Captures and refunds reported on their own event dates.
- **Contribution Margin**: Net merchandise revenue + net shipping charged − product cost − fulfillment & shipping costs − payment fees. Missing costs flagged.
- **Return Rate**: Returned units received $\div$ delivered units for the same delivery cohort.
- **On-Time Dispatch**: Orders dispatched by promised dispatch time $\div$ orders due in the selected period.
- **Zero-PII CSV Export**: One-click export of filtered aggregate metrics strictly excluding customer names, emails, phones, and addresses.

---

## 6. Verification & Automated Test Suite

All 12 acceptance scenarios from Section 16 were executed against `test_inmemory.py` with a **100% pass rate**:

```
=================================================================
   COFOCO E-COMMERCE SUITE: VALIDATING ALL 12 TEST SCENARIOS   
=================================================================

[Scenario 1] Customer discovers and selects a character kit...
  ✓ Passed: Arjun character loaded with cool blue theme, routine cue, and linked kit.

[Scenario 2] Customer compares two different kits (Arjun vs Bheema)...
  ✓ Passed: Side-by-side comparison returned specs, materials, prices, and stock.

[Scenario 3] Customer adds a kit to cart...
  ✓ Passed: Kit added to cart. Subtotal: ₹4299.0, Total: ₹4299.0

[Scenario 4] Customer completes guest checkout with PIN code serviceability...
  ✓ Passed: Guest order CFC-2026-5634-E0DF confirmed and paid.

[Scenario 5] Duplicate payment callback idempotency test...
  ✓ Passed: Duplicate gateway callback acknowledged without creating duplicate order or deducting stock.

[Scenario 6] Reservation cleanup / expired reservation handling...
  ✓ Passed: Late payment capture safely flagged with 'reconciliation_required' to prevent unreserved dispatch.

[Scenario 7] Two customers competing for the last component...
  ✓ Passed: Customer B blocked with HTTP 409 conflict and clear stock shortage message.

[Scenario 8] Warehouse staff BOM pick list verification...
  ✓ Passed: Pick list accurately shows frozen BOM items and warehouse locations (Bay A-01).

[Scenario 9] Return quality inspection gate...
  ✓ Passed: Unit restocked into sellable ledger only upon inspection pass; duplicate inspections rejected.

[Scenario 10] Founder business analytics & CSV export...
  ✓ Passed: Founder analytics calculated with Asia/Kolkata timezone, full metric denominators, and zero-PII CSV export.

[Scenario 11] Role-based access control (RBAC) permission check...
  ✓ Passed: Unauthorized action blocked with HTTP 403: Forbidden: Missing required permission 'manage_stock'.

[Scenario 12] Out-of-stock visibility and purchase disabling...
  ✓ Passed: Out-of-stock kit remains fully browsable, shows alternative suggestions, and blocks purchasing.

[Scenario 13] Static Storefront Assets Serving (HTML, CSS, JS)...
  ✓ Passed: Storefront SPA HTML, Design System CSS, and Client JS bundle served cleanly.

=================================================================
   ALL 12 OF 12 CORE SCENARIOS + STOREFRONT STATIC ASSETS VERIFIED (100% PASS)   
=================================================================
```

---

## 7. How to Run the Application Locally

### Running the Turnkey Server (Python 3.13)
The built-in multi-threaded server runs with zero external pip dependencies:

```powershell
# Navigate to the project root
cd C:\Users\mvish\.gemini\antigravity\scratch\cofoco

# Start the application server
python server.py
```

Open your browser:
- **Storefront**: `http://127.0.0.1:8080/`
- **Character Collections**: `http://127.0.0.1:8080/#/characters`
- **Kit Comparison**: `http://127.0.0.1:8080/#/compare`
- **Staff Operations Portal**: `http://127.0.0.1:8080/#/admin`
- **Founder Business Analytics**: `http://127.0.0.1:8080/#/admin/analytics`

### Staff Demo Credentials

Use the live role selector in the Staff Portal header to instantly evaluate role-based access:
- **Admin**: `admin` / `Admin@COFOCO2026` (Full permissions)
- **Brand Editor**: `editor` / `Editor@COFOCO2026` (Draft & preview content)
- **Publisher**: `publisher` / `Publish@COFOCO2026` (Approve & publish character experiences)
- **Warehouse Staff**: `warehouse` / `Warehouse@COFOCO2026` (Pick lists, packing, dispatch tracking)
- **Support Staff**: `support` / `Support@COFOCO2026` (Order lookups, returns initiation)
- **Finance Staff**: `finance` / `Finance@COFOCO2026` (Refund approvals, payment reconciliation)

### Running with Django + PostgreSQL
To deploy the Django project to production:

```bash
cd backend_django
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```
