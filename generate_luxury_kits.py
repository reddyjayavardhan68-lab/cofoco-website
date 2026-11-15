"""
Generate ultra-luxury, high-resolution vector artwork for all 6 COFOCO kits and characters.
Uses authentic design motifs, gilded borders, archetype symbols, and product silhouettes.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KIT_DIR = os.path.join(BASE_DIR, "static", "images", "kits")
CHAR_DIR = os.path.join(BASE_DIR, "static", "images", "characters")
os.makedirs(KIT_DIR, exist_ok=True)
os.makedirs(CHAR_DIR, exist_ok=True)

# Helper to create a luxury kit artwork SVG
def build_kit_svg(kit_title, char_name, quality, primary_color, secondary_color, accent_color, gold_color, items, icon_type):
    # Icon paths for different kits
    icons = {
        "bow": """
            <!-- Bow & Arrow Motif -->
            <path d="M 140 180 C 140 110, 260 110, 260 180" fill="none" stroke="{gold}" stroke-width="3" stroke-linecap="round"/>
            <line x1="200" y1="90" x2="200" y2="210" stroke="{gold}" stroke-width="2.5" stroke-linecap="round"/>
            <polygon points="200,80 193,98 207,98" fill="{gold}"/>
            <circle cx="200" cy="180" r="45" fill="none" stroke="{accent}" stroke-width="1.5" stroke-dasharray="4 4"/>
        """,
        "mountain": """
            <!-- Mountain & Strength Crest -->
            <polygon points="200,85 270,195 130,195" fill="none" stroke="{gold}" stroke-width="3" stroke-linejoin="round"/>
            <polygon points="200,115 240,195 160,195" fill="{accent}" opacity="0.3"/>
            <line x1="105" y1="210" x2="295" y2="210" stroke="{gold}" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="200" cy="155" r="42" fill="none" stroke="{accent}" stroke-width="1.5" stroke-dasharray="3 5"/>
        """,
        "sun": """
            <!-- Solar Disk & Radiance -->
            <circle cx="200" cy="150" r="38" fill="url(#coreGlow_{char_name})" stroke="{gold}" stroke-width="2.5"/>
            <!-- 8 Radiant Rays -->
            <line x1="200" y1="95" x2="200" y2="108" stroke="{gold}" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="200" y1="192" x2="200" y2="205" stroke="{gold}" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="145" y1="150" x2="158" y2="150" stroke="{gold}" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="242" y1="150" x2="255" y2="150" stroke="{gold}" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="161" y1="111" x2="170" y2="120" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>
            <line x1="239" y1="189" x2="230" y2="180" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>
            <line x1="161" y1="189" x2="170" y2="180" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>
            <line x1="239" y1="111" x2="230" y2="120" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>
        """,
        "lotus": """
            <!-- Sacred Lotus Motif -->
            <path d="M 200,95 C 180,130 185,170 200,190 C 215,170 220,130 200,95 Z" fill="{accent}" opacity="0.4" stroke="{gold}" stroke-width="1.8"/>
            <path d="M 200,190 C 160,185 140,150 155,125 C 170,145 185,170 200,190 Z" fill="none" stroke="{gold}" stroke-width="2"/>
            <path d="M 200,190 C 240,185 260,150 245,125 C 230,145 215,170 200,190 Z" fill="none" stroke="{gold}" stroke-width="2"/>
            <ellipse cx="200" cy="195" rx="55" ry="8" fill="none" stroke="{accent}" stroke-width="1.5" stroke-dasharray="2 4"/>
        """,
        "rose": """
            <!-- Geometric Rose & Sovereignty -->
            <circle cx="200" cy="150" r="44" fill="none" stroke="{gold}" stroke-width="2" stroke-dasharray="6 4"/>
            <path d="M 200,120 C 225,120 235,145 220,165 C 205,185 180,175 180,155 C 180,135 195,125 200,120 Z" fill="{accent}" opacity="0.35" stroke="{gold}" stroke-width="2"/>
            <circle cx="200" cy="150" r="16" fill="{gold}" opacity="0.8"/>
        """,
        "infinity": """
            <!-- Infinite Habit Continuum -->
            <path d="M 160,150 C 160,125 180,125 200,150 C 220,175 240,175 240,150 C 240,125 220,125 200,150 C 180,175 160,175 160,150 Z" 
                  fill="none" stroke="{gold}" stroke-width="3.5" stroke-linecap="round"/>
            <circle cx="200" cy="150" r="50" fill="none" stroke="{accent}" stroke-width="1" stroke-dasharray="4 6"/>
        """
    }

    icon_svg = icons.get(icon_type, "").format(gold=gold_color, accent=accent_color, char_name=char_name)

    items_svg = ""
    for idx, itm in enumerate(items[:4]):
        y_pos = 280 + (idx * 26)
        items_svg += f"""
        <g transform="translate(36, {y_pos})">
            <rect width="328" height="21" rx="4" fill="rgba(10, 8, 6, 0.65)" stroke="rgba(229, 186, 99, 0.25)" stroke-width="0.8"/>
            <circle cx="12" cy="10.5" r="3" fill="{gold_color}"/>
            <text x="24" y="14.5" font-family="'Plus Jakarta Sans', sans-serif" font-size="10" font-weight="600" fill="#EDE4D8">{itm}</text>
        </g>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 420" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad_{char_name}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{primary_color}"/>
      <stop offset="50%" stop-color="{secondary_color}"/>
      <stop offset="100%" stop-color="#0A0806"/>
    </linearGradient>

    <!-- Metallic Gold Foil Gradient -->
    <linearGradient id="goldFoil_{char_name}" x1="0%" y1="0%" x2="100%" y2="80%">
      <stop offset="0%" stop-color="#FFF2D6"/>
      <stop offset="35%" stop-color="{gold_color}"/>
      <stop offset="70%" stop-color="#C29541"/>
      <stop offset="100%" stop-color="#8B6724"/>
    </linearGradient>

    <!-- Radial Core Glow -->
    <radialGradient id="coreGlow_{char_name}" cx="50%" cy="40%" r="55%">
      <stop offset="0%" stop-color="{gold_color}" stop-opacity="0.28"/>
      <stop offset="60%" stop-color="{accent_color}" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Outer Rounded Container -->
  <rect width="400" height="420" rx="20" fill="url(#bgGrad_{char_name})"/>

  <!-- Hairline Gold Luxury Border -->
  <rect x="10" y="10" width="380" height="400" rx="16" fill="none" stroke="url(#goldFoil_{char_name})" stroke-width="1.2" opacity="0.85"/>

  <!-- Radial Aura Glow behind emblem -->
  <circle cx="200" cy="150" r="120" fill="url(#coreGlow_{char_name})"/>

  <!-- Corner Filigree Ornaments -->
  <path d="M 22 36 L 36 22 M 22 22 L 36 36" stroke="{gold_color}" stroke-width="1" opacity="0.6"/>
  <path d="M 378 36 L 364 22 M 378 22 L 364 36" stroke="{gold_color}" stroke-width="1" opacity="0.6"/>
  <path d="M 22 384 L 36 398 M 22 398 L 36 384" stroke="{gold_color}" stroke-width="1" opacity="0.6"/>
  <path d="M 378 384 L 364 398 M 378 398 L 364 384" stroke="{gold_color}" stroke-width="1" opacity="0.6"/>

  <!-- Top Brand Seal -->
  <text x="200" y="44" text-anchor="middle" font-family="'Cinzel', serif" font-size="11" font-weight="700" fill="url(#goldFoil_{char_name})" letter-spacing="3.5">CONSCIOUS FORM COMPANY</text>
  <line x1="80" y1="52" x2="320" y2="52" stroke="url(#goldFoil_{char_name})" stroke-width="0.8" opacity="0.4"/>

  <!-- Central Archetype Icon & Crest -->
  {icon_svg}

  <!-- Character & Quality Banner -->
  <rect x="110" y="215" width="180" height="22" rx="11" fill="rgba(10, 8, 6, 0.7)" stroke="url(#goldFoil_{char_name})" stroke-width="1"/>
  <text x="200" y="230" text-anchor="middle" font-family="'Plus Jakarta Sans', sans-serif" font-size="10" font-weight="700" fill="{gold_color}" letter-spacing="2">{char_name.upper()} • {quality.upper()}</text>

  <!-- Kit Title Display -->
  <text x="200" y="262" text-anchor="middle" font-family="'Playfair Display', serif" font-size="16" font-weight="700" font-style="italic" fill="#FFFFFF">{kit_title}</text>

  <!-- Included Items Specification -->
  {items_svg}

  <!-- Subtle Bottom Quality Seal -->
  <text x="200" y="398" text-anchor="middle" font-family="'Plus Jakarta Sans', sans-serif" font-size="8.5" font-weight="600" fill="{gold_color}" opacity="0.8" letter-spacing="1.5">CALIBRATED GYM &amp; RECOVERY KIT</text>
</svg>"""
    return svg

# Definitions for the 6 official COFOCO kits
kits_data = [
    {
        "slug": "kit_arjun_precision",
        "file_base": "arjun_kit",
        "title": "The Archer Precision Kit",
        "char": "Arjun",
        "quality": "Focus",
        "p_color": "#0B1D2F",
        "s_color": "#122A42",
        "accent": "#6BA4D9",
        "gold": "#E5BA63",
        "icon": "bow",
        "items": [
            "Calibrated Latex Resistance Bands (Set of 4)",
            "Precision Grid EPP Foam Roller",
            "Magnetic Interval Routine Timer",
            "Pure Gym Chalk Block 56g"
        ]
    },
    {
        "slug": "kit_bheema_titan",
        "file_base": "bheema_kit",
        "title": "The Titan Strength Kit",
        "char": "Bheema",
        "quality": "Strength",
        "p_color": "#281711",
        "s_color": "#3D2419",
        "accent": "#D49B6A",
        "gold": "#ECC973",
        "icon": "mountain",
        "items": [
            "Top-Grain Leather Lifting Belt 10mm",
            "Competition Wrist Wraps (Pair)",
            "Zero-Dust Liquid Grip Chalk 150ml",
            "Percussion Recovery Ball"
        ]
    },
    {
        "slug": "kit_karna_resolve",
        "file_base": "karna_kit",
        "title": "The Sol Invictus Kit",
        "char": "Karna",
        "quality": "Resolve",
        "p_color": "#2C1B06",
        "s_color": "#4A2F0A",
        "accent": "#F5B041",
        "gold": "#F2CC79",
        "icon": "sun",
        "items": [
            "1000D Cordura Athlete Duffel 42L",
            "Reinforced Dip & Pull-up Belt",
            "Zero-Dust Liquid Grip Chalk",
            "Deep-Tissue Percussion Ball"
        ]
    },
    {
        "slug": "kit_sita_lotus",
        "file_base": "sita_kit",
        "title": "The Lotus Restoration Kit",
        "char": "Sita",
        "quality": "Steadiness",
        "p_color": "#16221A",
        "s_color": "#25382B",
        "accent": "#A3C9AE",
        "gold": "#E5BA63",
        "icon": "lotus",
        "items": [
            "Natural Organic Cork & Rubber Mat",
            "Therapeutic Acupressure Mat & Pillow",
            "Botanical Magnesium Sleep Mist",
            "Multi-Loop Stretch Therapy Strap"
        ]
    },
    {
        "slug": "kit_draupadi_sovereign",
        "file_base": "draupadi_kit",
        "title": "The Sovereign Form Kit",
        "char": "Draupadi",
        "quality": "Self-Possession",
        "p_color": "#290E16",
        "s_color": "#441824",
        "accent": "#D86E8C",
        "gold": "#F0C878",
        "icon": "rose",
        "items": [
            "Ergonomic Barbell Squat Pad",
            "Neoprene Padded Cable Ankle Cuffs",
            "Vacuum Insulated Stainless Shaker",
            "Calibrated Latex Resistance Bands"
        ]
    },
    {
        "slug": "kit_savitri_habit",
        "file_base": "savitri_kit",
        "title": "The Continuum Habit Kit",
        "char": "Savitri",
        "quality": "Consistency",
        "p_color": "#1A2016",
        "s_color": "#2C3725",
        "accent": "#9EB378",
        "gold": "#ECC973",
        "icon": "infinity",
        "items": [
            "180-Day Daily Fitness Routine Journal",
            "Multi-Loop Physical Therapy Strap",
            "Calibrated Resistance Bands Set",
            "Pure Gym Chalk Block"
        ]
    }
]

# Generate both .svg and .jpg (serving SVG XML) for maximum compatibility
for kd in kits_data:
    svg_content = build_kit_svg(
        kd["title"], kd["char"], kd["quality"],
        kd["p_color"], kd["s_color"], kd["accent"], kd["gold"],
        kd["items"], kd["icon"]
    )
    svg_path = os.path.join(KIT_DIR, f"{kd['file_base']}.svg")
    jpg_path = os.path.join(KIT_DIR, f"{kd['file_base']}.jpg")
    
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    with open(jpg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated {svg_path} & {jpg_path}")

# Now update the SQLite database to use local reliable SVG image paths
db_path = os.path.join(BASE_DIR, "cofoco.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Update kits
for kd in kits_data:
    kit_img = f"/images/kits/{kd['file_base']}.svg"
    cur.execute("UPDATE kits SET image_url = ? WHERE id = ? OR slug LIKE ?;", (kit_img, kd["slug"], f"%{kd['file_base']}%"))

# Update characters
char_map = {
    "arjun": "/images/characters/arjun.svg",
    "bheema": "/images/characters/bheema.svg",
    "karna": "/images/characters/karna.svg",
    "sita": "/images/characters/sita.svg",
    "draupadi": "/images/characters/draupadi.svg",
    "savitri": "/images/characters/savitri.svg"
}

for c_slug, c_img in char_map.items():
    cur.execute("UPDATE characters SET artwork_url = ? WHERE slug = ?;", (c_img, c_slug))

conn.commit()
print(f"Updated {len(kits_data)} kits and {len(char_map)} characters in database.")
conn.close()
