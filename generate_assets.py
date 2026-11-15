"""
Generate bespoke, premium SVG vector assets for COFOCO 6 launch characters and kit showcases.
"""

import os

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "images")
CHAR_DIR = os.path.join(IMAGES_DIR, "characters")
KIT_DIR = os.path.join(IMAGES_DIR, "kits")
os.makedirs(CHAR_DIR, exist_ok=True)
os.makedirs(KIT_DIR, exist_ok=True)

# 1. Arjun: Moon and Flowing Water in Cool Blues
arjun_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgArj" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F2B48" />
      <stop offset="100%" stop-color="#08182B" />
    </linearGradient>
    <linearGradient id="waterGrad" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#1E5B94" />
      <stop offset="50%" stop-color="#6BA4D9" />
      <stop offset="100%" stop-color="#D9E8F5" />
    </linearGradient>
    <radialGradient id="moonGlow" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#D9E8F5" stop-opacity="0.9" />
      <stop offset="50%" stop-color="#6BA4D9" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#0F2B48" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bgArj)"/>
  <circle cx="200" cy="180" r="140" fill="url(#moonGlow)"/>
  <!-- Focus Rings (Precision reticle) -->
  <circle cx="200" cy="180" r="120" stroke="#6BA4D9" stroke-width="1.5" stroke-dasharray="4 6" fill="none" opacity="0.6"/>
  <circle cx="200" cy="180" r="90" stroke="#D9E8F5" stroke-width="1" fill="none" opacity="0.4"/>
  <circle cx="200" cy="180" r="60" stroke="#6BA4D9" stroke-width="2" fill="none" opacity="0.8"/>
  <line x1="200" y1="50" x2="200" y2="310" stroke="#D9E8F5" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>
  <line x1="70" y1="180" x2="330" y2="180" stroke="#D9E8F5" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>
  <!-- Crescent Moon Symbol -->
  <path d="M 230,120 A 70,70 0 1,0 230,240 A 55,55 0 1,1 230,120 Z" fill="#D9E8F5" opacity="0.95"/>
  <!-- Flowing Water Wave Curves -->
  <path d="M 50,320 C 110,280 150,340 200,300 C 250,260 290,320 350,290 L 350,380 L 50,380 Z" fill="url(#waterGrad)" opacity="0.85"/>
  <path d="M 50,340 C 130,310 170,360 230,330 C 290,300 320,350 350,330 L 350,380 L 50,380 Z" fill="#0F2B48" opacity="0.5"/>
  <!-- Text Label -->
  <text x="200" y="375" text-anchor="middle" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#D9E8F5" letter-spacing="4">ARJUN • FOCUS</text>
</svg>"""

# 2. Bheema: Mountain and Warm Earth Tones
bheema_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgBhm" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3B2219" />
      <stop offset="100%" stop-color="#1F110B" />
    </linearGradient>
    <linearGradient id="mntnGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#EADCC9" />
      <stop offset="40%" stop-color="#C08A5E" />
      <stop offset="100%" stop-color="#7D4F38" />
    </linearGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bgBhm)"/>
  <!-- Earth Sun disk -->
  <circle cx="200" cy="160" r="110" fill="#C08A5E" opacity="0.25"/>
  <!-- Heavy Mountain Peaks (Geometric Strength) -->
  <polygon points="200,70 330,320 70,320" fill="url(#mntnGrad)"/>
  <polygon points="200,70 200,320 330,320" fill="#7D4F38" opacity="0.6"/>
  <!-- Secondary Peaks -->
  <polygon points="120,160 210,320 30,320" fill="#3B2219" opacity="0.85"/>
  <polygon points="280,180 370,320 190,320" fill="#2A1710" opacity="0.9"/>
  <!-- Strength Lines -->
  <line x1="80" y1="340" x2="320" y2="340" stroke="#EADCC9" stroke-width="3" stroke-linecap="round"/>
  <line x1="120" y1="352" x2="280" y2="352" stroke="#C08A5E" stroke-width="2" stroke-linecap="round"/>
  <!-- Text Label -->
  <text x="200" y="380" text-anchor="middle" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#EADCC9" letter-spacing="4">BHEEMA • STRENGTH</text>
</svg>"""

# 3. Karna: Amber Sun
karna_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgKrn" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3D2504" />
      <stop offset="100%" stop-color="#1C1001" />
    </linearGradient>
    <radialGradient id="sunBurst" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FCECD5" />
      <stop offset="40%" stop-color="#E09F3E" />
      <stop offset="80%" stop-color="#B87314" />
      <stop offset="100%" stop-color="#3D2504" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bgKrn)"/>
  <circle cx="200" cy="185" r="140" fill="url(#sunBurst)"/>
  <!-- 12 Solar Rays of Resolve -->
  <g stroke="#E09F3E" stroke-width="3" stroke-linecap="round" opacity="0.8">
    <line x1="200" y1="65" x2="200" y2="95"/>
    <line x1="200" y1="275" x2="200" y2="305"/>
    <line x1="80" y1="185" x2="110" y2="185"/>
    <line x1="290" y1="185" x2="320" y2="185"/>
    <line x1="115" y1="100" x2="135" y2="120"/>
    <line x1="265" y1="250" x2="285" y2="270"/>
    <line x1="115" y1="270" x2="135" y2="250"/>
    <line x1="265" y1="120" x2="285" y2="100"/>
  </g>
  <!-- Inner Golden Sun Shield -->
  <circle cx="200" cy="185" r="65" fill="#B87314" stroke="#FCECD5" stroke-width="3"/>
  <circle cx="200" cy="185" r="50" fill="#E09F3E"/>
  <circle cx="200" cy="185" r="30" fill="#FCECD5"/>
  <!-- Text Label -->
  <text x="200" y="375" text-anchor="middle" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#FCECD5" letter-spacing="4">KARNA • RESOLVE</text>
</svg>"""

# 4. Sita: Ivory Lotus Rising from Water
sita_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgSit" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#253028" />
      <stop offset="100%" stop-color="#121814" />
    </linearGradient>
    <linearGradient id="lotusGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF" />
      <stop offset="60%" stop-color="#E9F0EB" />
      <stop offset="100%" stop-color="#92B89E" />
    </linearGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bgSit)"/>
  <!-- Ripples of Stillness -->
  <ellipse cx="200" cy="270" rx="140" ry="30" fill="none" stroke="#4A6B56" stroke-width="1.5" opacity="0.6"/>
  <ellipse cx="200" cy="270" rx="100" ry="20" fill="none" stroke="#92B89E" stroke-width="2" opacity="0.8"/>
  <ellipse cx="200" cy="270" rx="60" ry="12" fill="none" stroke="#E9F0EB" stroke-width="1.5"/>
  <!-- Ivory Lotus Petals -->
  <!-- Outer Petals -->
  <path d="M 200,260 C 130,220 120,160 200,100 C 280,160 270,220 200,260 Z" fill="url(#lotusGrad)" opacity="0.95"/>
  <!-- Left Side Petal -->
  <path d="M 200,260 C 140,240 100,180 150,130 C 180,170 190,220 200,260 Z" fill="#92B89E" opacity="0.85"/>
  <!-- Right Side Petal -->
  <path d="M 200,260 C 260,240 300,180 250,130 C 220,170 210,220 200,260 Z" fill="#92B89E" opacity="0.85"/>
  <!-- Center Bud -->
  <path d="M 200,260 C 175,220 175,150 200,110 C 225,150 225,220 200,260 Z" fill="#FFFFFF"/>
  <!-- Text Label -->
  <text x="200" y="375" text-anchor="middle" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#E9F0EB" letter-spacing="4">SITA • STEADINESS</text>
</svg>"""

# 5. Draupadi: Rose Motif with Rich Tones
draupadi_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgDrp" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3A121E" />
      <stop offset="100%" stop-color="#1A070D" />
    </linearGradient>
    <radialGradient id="roseGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#C85A7A" />
      <stop offset="60%" stop-color="#8B2643" />
      <stop offset="100%" stop-color="#3A121E" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bgDrp)"/>
  <circle cx="200" cy="180" r="130" fill="url(#roseGlow)" opacity="0.4"/>
  <!-- Sovereign Crown Geometric Spikes -->
  <path d="M 120,140 L 140,80 L 170,110 L 200,60 L 230,110 L 260,80 L 280,140 Z" fill="none" stroke="#C85A7A" stroke-width="2" opacity="0.6"/>
  <!-- Stylized Geometric Rose Petals -->
  <g transform="translate(200, 190)">
    <!-- Layer 1 -->
    <circle cx="0" cy="0" r="85" fill="none" stroke="#8B2643" stroke-width="1.5" stroke-dasharray="8 6"/>
    <!-- Layer 2 -->
    <path d="M 0,-70 C 45,-70 70,-45 70,0 C 70,45 45,70 0,70 C -45,70 -70,45 -70,0 C -70,-45 -45,-70 0,-70 Z" fill="#8B2643" opacity="0.8"/>
    <!-- Layer 3 -->
    <path d="M -40,-40 C -10,-60 40,-50 50,-20 C 60,15 30,50 -10,50 C -40,40 -60,0 -40,-40 Z" fill="#C85A7A" opacity="0.9"/>
    <!-- Layer 4 Core -->
    <circle cx="0" cy="0" r="28" fill="#F7E5EB"/>
    <circle cx="0" cy="0" r="14" fill="#3A121E"/>
  </g>
  <!-- Text Label -->
  <text x="200" y="375" text-anchor="middle" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#F7E5EB" letter-spacing="4">DRAUPADI • SELF-POSSESSION</text>
</svg>"""

# 6. Savitri: Olive Tones & Continuum Habit Motif
savitri_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgSvt" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#232A1C" />
      <stop offset="100%" stop-color="#11160D" />
    </linearGradient>
    <linearGradient id="oliveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ECF0E7" />
      <stop offset="50%" stop-color="#879A63" />
      <stop offset="100%" stop-color="#4F5D38" />
    </linearGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bgSvt)"/>
  <!-- Continuum Habit Infinite Loop (Daily Dedication) -->
  <g transform="translate(200, 180)">
    <path d="M -60,0 C -60,-45 -25,-45 0,0 C 25,45 60,45 60,0 C 60,-45 25,-45 0,0 C -25,45 -60,45 -60,0 Z"
          fill="none" stroke="url(#oliveGrad)" stroke-width="14" stroke-linecap="round"/>
    <circle cx="0" cy="0" r="95" fill="none" stroke="#4F5D38" stroke-width="1.5" stroke-dasharray="6 6" opacity="0.6"/>
    <!-- Olive Leaves of Growth -->
    <path d="M -80,-50 C -60,-60 -50,-40 -70,-30 Z" fill="#879A63"/>
    <path d="M 80,50 C 60,60 50,40 70,30 Z" fill="#879A63"/>
    <path d="M 0,-85 C 15,-100 25,-85 10,-75 Z" fill="#ECF0E7"/>
  </g>
  <!-- Text Label -->
  <text x="200" y="375" text-anchor="middle" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#ECF0E7" letter-spacing="4">SAVITRI • CONSISTENCY</text>
</svg>"""

# Kit Visuals (Realistic kit layout renderings in SVG)
def generate_kit_svg(title, char_name, color1, color2, accent, items_list):
    badges_xml = ""
    for idx, itm in enumerate(items_list[:4]):
        y_pos = 260 + (idx * 26)
        badges_xml += f'<rect x="40" y="{y_pos}" width="320" height="20" rx="4" fill="{color1}" opacity="0.5"/>'
        badges_xml += f'<text x="50" y="{y_pos + 14}" font-family="sans-serif" font-size="10" font-weight="600" fill="{accent}">✓ {itm}</text>'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="kitBg_{char_name}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color1}" />
      <stop offset="100%" stop-color="#121416" />
    </linearGradient>
  </defs>
  <rect width="400" height="400" rx="16" fill="url(#kitBg_{char_name})"/>
  <!-- Kit Container Box Graphic -->
  <rect x="50" y="45" width="300" height="190" rx="12" fill="{color2}" opacity="0.3" stroke="{accent}" stroke-width="1.5"/>
  <circle cx="200" cy="120" r="50" fill="{color1}" stroke="{accent}" stroke-width="2"/>
  <text x="200" y="115" text-anchor="middle" font-family="'Inter', sans-serif" font-size="11" font-weight="700" fill="{accent}" letter-spacing="2">COFOCO</text>
  <text x="200" y="132" text-anchor="middle" font-family="'Inter', sans-serif" font-size="14" font-weight="800" fill="#FFFFFF">{char_name.upper()}</text>
  <!-- Kit Title -->
  <text x="200" y="210" text-anchor="middle" font-family="'Inter', sans-serif" font-size="15" font-weight="700" fill="#FFFFFF">{title}</text>
  <!-- Components pill breakdown -->
  {badges_xml}
  <rect x="40" y="370" width="320" height="2" fill="{accent}" opacity="0.8"/>
</svg>"""

with open(os.path.join(CHAR_DIR, "arjun.svg"), "w", encoding="utf-8") as f: f.write(arjun_svg)
with open(os.path.join(CHAR_DIR, "bheema.svg"), "w", encoding="utf-8") as f: f.write(bheema_svg)
with open(os.path.join(CHAR_DIR, "karna.svg"), "w", encoding="utf-8") as f: f.write(karna_svg)
with open(os.path.join(CHAR_DIR, "sita.svg"), "w", encoding="utf-8") as f: f.write(sita_svg)
with open(os.path.join(CHAR_DIR, "draupadi.svg"), "w", encoding="utf-8") as f: f.write(draupadi_svg)
with open(os.path.join(CHAR_DIR, "savitri.svg"), "w", encoding="utf-8") as f: f.write(savitri_svg)

# Write Kit images
with open(os.path.join(KIT_DIR, "arjun_kit.jpg"), "w", encoding="utf-8") as f:
    f.write(generate_kit_svg("The Archer Precision Kit", "Arjun", "#0F2B48", "#1E5B94", "#6BA4D9",
                             ["Calibrated Latex Resistance Bands (Set of 4)", "Precision Grid EPP Foam Roller", "Magnetic Interval & Routine Focus Timer", "Pure Gym Chalk Block 56g"]))

with open(os.path.join(KIT_DIR, "bheema_kit.jpg"), "w", encoding="utf-8") as f:
    f.write(generate_kit_svg("The Titan Strength Kit", "Bheema", "#3B2219", "#7D4F38", "#C08A5E",
                             ["Top-Grain Leather Lifting Belt 10mm", "Competition Wrist Wraps (Pair)", "Zero-Dust Liquid Grip Chalk 150ml", "Percussion Recovery Lacrosse Ball"]))

with open(os.path.join(KIT_DIR, "karna_kit.jpg"), "w", encoding="utf-8") as f:
    f.write(generate_kit_svg("The Sol Invictus Kit", "Karna", "#3D2504", "#B87314", "#E09F3E",
                             ["1000D Cordura Athlete Duffel 42L", "Reinforced Weighted Dip & Pull-up Belt", "Zero-Dust Liquid Grip Chalk", "Deep-Tissue Percussion Ball"]))

with open(os.path.join(KIT_DIR, "sita_kit.jpg"), "w", encoding="utf-8") as f:
    f.write(generate_kit_svg("The Lotus Restoration Kit", "Sita", "#253028", "#4A6B56", "#92B89E",
                             ["Natural Organic Cork & Rubber Mat", "Therapeutic Acupressure Mat & Pillow", "Botanical Magnesium Sleep Mist", "Multi-Loop Stretch Therapy Strap"]))

with open(os.path.join(KIT_DIR, "draupadi_kit.jpg"), "w", encoding="utf-8") as f:
    f.write(generate_kit_svg("The Sovereign Form Kit", "Draupadi", "#3A121E", "#8B2643", "#C85A7A",
                             ["Ergonomic Barbell Squat Pad", "Neoprene Padded Cable Ankle Cuffs", "Vacuum Insulated Stainless Shaker", "Calibrated Latex Resistance Bands"]))

with open(os.path.join(KIT_DIR, "savitri_kit.jpg"), "w", encoding="utf-8") as f:
    f.write(generate_kit_svg("The Continuum Habit Kit", "Savitri", "#232A1C", "#4F5D38", "#879A63",
                             ["180-Day Daily Fitness Routine Journal", "Multi-Loop Physical Therapy Strap", "Calibrated Resistance Bands Set", "Pure Gym Chalk Block"]))

print("[COFOCO] Vector artwork and kit graphics generated successfully.")
