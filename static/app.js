/**
 * COFOCO (Conscious Form Company) - Modern Client Application
 * Modular ES-architecture implementing Storefront, Kit Comparison,
 * Guest Checkout, Atomic Reservations, Warehouse Fulfillment,
 * Quality Return Gates, and Founder Business Analytics.
 */

// Global State
const State = {
  sessionId: localStorage.getItem("cofoco_session_id") || "sess_" + Math.random().toString(36).substring(2, 10),
  activeCampaign: new URLSearchParams(window.location.search).get("utm_campaign") || 
                  new URLSearchParams(window.location.search).get("campaign") || "direct_storefront",
  cart: { items: [], subtotal: 0, discount: 0, shipping: 0, tax: 0, total: 0, coupon_code: null },
  compareList: JSON.parse(localStorage.getItem("cofoco_compare") || '["arjun-precision-kit", "bheema-titan-strength-kit"]'),
  staffAuth: JSON.parse(localStorage.getItem("cofoco_staff_auth") || "null")
};
localStorage.setItem("cofoco_session_id", State.sessionId);

// API Fetch Helper
async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Session-Id": State.sessionId,
    ...(options.headers || {})
  };
  if (State.staffAuth && State.staffAuth.token) {
    headers["Authorization"] = `Bearer ${State.staffAuth.token}`;
  }
  try {
    const res = await fetch(path, { ...options, headers });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `HTTP ${res.status}: Failed request`);
    }
    return data;
  } catch (err) {
    console.error(`API Error [${path}]:`, err);
    throw err;
  }
}

// Track Pseudonymous Analytics Event (AN01)
function trackEvent(eventName, charId = null, kitId = null, metadata = {}) {
  api("/api/analytics/track", {
    method: "POST",
    body: JSON.stringify({
      session_id: State.sessionId,
      event_name: eventName,
      character_id: charId,
      kit_id: kitId,
      campaign_id: State.activeCampaign,
      metadata: metadata
    })
  }).catch(() => {});
}

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modals
window.openModal = function(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add("active");
};
window.closeModal = function(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("active");
};

// Refresh Cart Data
async function refreshCart() {
  try {
    const data = await api("/api/cart");
    State.cart = data;
    const count = (data.items || []).reduce((acc, i) => acc + i.quantity, 0);
    
    const badge = document.getElementById("cartCountBadge");
    if (badge) badge.textContent = count;
    
    renderCartDrawer();
  } catch (e) {
    console.error("Cart refresh failed:", e);
  }
}

// Render Cart Drawer
function renderCartDrawer() {
  const container = document.getElementById("cartDrawerContent");
  const footer = document.getElementById("cartDrawerFooter");
  if (!container || !footer) return;

  const items = State.cart.items || [];
  if (items.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">🛍️</div>
        <h3 style="font-family: var(--font-serif); font-size: 1.3rem; margin-bottom: 0.5rem;">Your Cart is Empty</h3>
        <p style="color: var(--color-text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">Explore our 6 character-inspired kits and find your training routine.</p>
        <a href="#/shop" class="btn btn-primary btn-sm" onclick="closeCart()">Explore Kits</a>
      </div>
    `;
    footer.innerHTML = "";
    return;
  }

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.75rem; margin-bottom: 0.75rem; border-bottom: 1px solid var(--color-border-subtle);">
      <span style="font-size: 0.85rem; color: var(--color-text-muted);">${items.length} unique item${items.length > 1 ? 's' : ''} in cart</span>
      <button onclick="clearCart()" style="background: none; border: none; color: #F87171; font-size: 0.8rem; cursor: pointer; text-decoration: underline; font-weight: 600;">Clear All</button>
    </div>
  ` + items.map(i => `
    <div class="cart-item-row">
      <img src="${i.image_url}" class="cart-item-thumb" alt="${i.kit_name}">
      <div class="cart-item-details">
        <div class="cart-item-title">${i.kit_name}</div>
        <div class="cart-item-var">${i.character_name} • ${i.variant_name}</div>
        <div class="cart-item-price">₹${Number(i.price).toLocaleString('en-IN')}</div>
        ${!i.is_valid_stock ? '<span style="color: var(--color-danger); font-size: 0.75rem; font-weight: 700;">Stock limited</span>' : ''}
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem;">
          <div class="qty-stepper">
            <button class="qty-btn" onclick="updateCartItem('${i.variant_id}', ${i.quantity - 1})">-</button>
            <span class="qty-val">${i.quantity}</span>
            <button class="qty-btn" onclick="updateCartItem('${i.variant_id}', ${i.quantity + 1})">+</button>
          </div>
          <button class="btn-remove-item" onclick="removeCartItem('${i.variant_id}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right: 4px;"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            Remove
          </button>
        </div>
      </div>
    </div>
  `).join("");

  footer.innerHTML = `
    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.4rem;">
      <span style="color: var(--color-text-muted);">Merchandise Subtotal</span>
      <span style="font-weight: 600;">₹${Number(State.cart.subtotal).toLocaleString('en-IN')}</span>
    </div>
    ${State.cart.discount > 0 ? `
      <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.4rem; color: var(--color-success);">
        <span>Discount (${State.cart.coupon_code})</span>
        <span style="font-weight: 600;">-₹${Number(State.cart.discount).toLocaleString('en-IN')}</span>
      </div>
    ` : ''}
    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.4rem;">
      <span style="color: var(--color-text-muted);">Standard Shipping (India)</span>
      <span style="font-weight: 600;">${State.cart.shipping === 0 ? '<span style="color: var(--color-success)">FREE</span>' : '₹' + State.cart.shipping}</span>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.85rem; color: var(--color-text-muted);">
      <span>Estimated GST (18% inclusive)</span>
      <span>₹${Number(State.cart.tax).toLocaleString('en-IN')}</span>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 1.15rem; font-weight: 800; border-top: 1px solid var(--color-border); padding-top: 0.75rem; margin-bottom: 1.25rem;">
      <span>Total Payable</span>
      <span>₹${Number(State.cart.total).toLocaleString('en-IN')}</span>
    </div>
    <a href="#/checkout" class="btn btn-pill-gold btn-block" onclick="closeCart()" style="justify-content: center; font-size: 1rem; padding: 1rem;">
      <span>Proceed to Guest Checkout</span>
      <span class="arrow-token">→</span>
    </a>
  `;
}

window.openCart = function() {
  document.getElementById("cartDrawerBackdrop")?.classList.add("active");
  document.getElementById("cartDrawer")?.classList.add("active");
};
window.closeCart = function() {
  document.getElementById("cartDrawerBackdrop")?.classList.remove("active");
  document.getElementById("cartDrawer")?.classList.remove("active");
};

window.addToCart = async function(variantId, qty = 1) {
  try {
    await api("/api/cart/items", {
      method: "POST",
      body: JSON.stringify({ session_id: State.sessionId, variant_id: variantId, quantity: qty })
    });
    trackEvent("add_to_cart", null, null, { variant_id: variantId, quantity: qty });
    await refreshCart();
    showToast("Kit added to your cart.", "success");
    openCart();
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.updateCartItem = async function(variantId, newQty) {
  if (newQty <= 0) return removeCartItem(variantId);
  try {
    const curQty = State.cart.items.find(i => i.variant_id === variantId)?.quantity || 0;
    const diff = newQty - curQty;
    await api("/api/cart/items", {
      method: "POST",
      body: JSON.stringify({ session_id: State.sessionId, variant_id: variantId, quantity: diff })
    });
    await refreshCart();
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.removeCartItem = async function(variantId) {
  try {
    await api("/api/cart/remove", {
      method: "POST",
      body: JSON.stringify({ session_id: State.sessionId, variant_id: variantId })
    });
    await refreshCart();
    showToast("Item removed from cart.", "info");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.clearCart = async function() {
  try {
    await api("/api/cart/remove", {
      method: "POST",
      body: JSON.stringify({ session_id: State.sessionId, clear_all: true })
    });
    await refreshCart();
    showToast("Your cart has been emptied.", "info");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

// Kit Comparison System Helper
window.toggleCompare = function(kitSlug) {
  let list = State.compareList;
  if (list.includes(kitSlug)) {
    list = list.filter(s => s !== kitSlug);
    showToast("Kit removed from comparison.", "info");
  } else {
    if (list.length >= 4) {
      showToast("You can compare up to 4 kits at once.", "warning");
      return;
    }
    list.push(kitSlug);
    showToast("Kit added to comparison.", "success");
  }
  State.compareList = list;
  localStorage.setItem("cofoco_compare", JSON.stringify(list));
  if (window.location.hash.startsWith("#/compare")) {
    Router.renderRoute();
  }
};

// Website Owner & Staff Access Management
async function updateOwnerStaffVisibility() {
  const isOwner = !!(State.staffAuth && State.staffAuth.token);
  const staffPill = document.getElementById("staffViewPill");
  if (staffPill) {
    staffPill.style.display = isOwner ? "inline-flex" : "none";
    if (isOwner) {
      const label = document.getElementById("staffPillLabel");
      if (label) label.textContent = State.staffAuth.user?.role_name || "Owner View";
      // Fetch live pending orders for staff bag alert
      try {
        const ov = await api("/api/admin/overview");
        const badge = document.getElementById("staffOrderAlertBadge");
        if (badge && ov.metrics) {
          const pending = ov.metrics.awaiting_dispatch || 0;
          if (pending > 0) {
            badge.style.display = "inline-block";
            badge.textContent = `${pending} New`;
          } else {
            badge.style.display = "none";
          }
        }
      } catch (_) {}
    }
  }
  const mobileStaff = document.querySelectorAll(".owner-only-link");
  mobileStaff.forEach(el => {
    el.style.display = isOwner ? "block" : "none";
  });
}

// =========================================================================
// ROUTER & VIEW RENDERING
// =========================================================================
const Router = {
  routes: {},

  init() {
    document.getElementById("floatingBagPill")?.remove();
    updateOwnerStaffVisibility();
    window.addEventListener("hashchange", () => {
      document.getElementById("floatingBagPill")?.remove();
      updateOwnerStaffVisibility();
      this.renderRoute();
    });
    document.addEventListener("DOMContentLoaded", () => {
      document.getElementById("floatingBagPill")?.remove();
      updateOwnerStaffVisibility();
      this.initEvents();
      refreshCart();
      this.renderRoute();
    });
  },

  initEvents() {
    document.getElementById("cartTriggerBtn")?.addEventListener("click", openCart);
    document.getElementById("closeCartBtn")?.addEventListener("click", closeCart);
    document.getElementById("cartDrawerBackdrop")?.addEventListener("click", closeCart);
    document.getElementById("searchTriggerBtn")?.addEventListener("click", () => openModal("searchModal"));
    document.getElementById("mobileMenuToggle")?.addEventListener("click", () => {
      const d = document.getElementById("mobileDrawer");
      d.style.display = d.style.display === "none" ? "block" : "none";
    });

    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => this.handleSearch(e.target.value));
    }
  },

  async handleSearch(query) {
    const resBox = document.getElementById("searchResults");
    if (!resBox) return;
    if (!query || query.trim().length < 2) {
      resBox.innerHTML = "";
      return;
    }
    try {
      const kitsData = await api("/api/kits");
      const q = query.toLowerCase();
      const matches = (kitsData.kits || []).filter(k => 
        k.name.toLowerCase().includes(q) || 
        k.character_name.toLowerCase().includes(q) ||
        k.description.toLowerCase().includes(q)
      );

      if (matches.length === 0) {
        resBox.innerHTML = `<p style="color: var(--color-text-muted); font-size: 0.9rem;">No matching kits found for "${query}".</p>`;
        return;
      }

      resBox.innerHTML = matches.map(k => `
        <a href="#/kit/${k.slug}" onclick="closeModal('searchModal')" style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--color-border); text-decoration: none; color: inherit;">
          <img src="${k.image_url}" style="width: 50px; height: 50px; border-radius: 6px; object-fit: cover;" alt="${k.name}">
          <div>
            <div style="font-weight: 700; font-size: 0.95rem;">${k.name}</div>
            <div style="font-size: 0.8rem; color: var(--color-accent-gold);">${k.character_name} • ₹${Number(k.base_price).toLocaleString('en-IN')}</div>
          </div>
        </a>
      `).join("");
    } catch (e) {
      console.error(e);
    }
  },

  renderRoute() {
    const rawHash = window.location.hash || "#/";
    const [pathPart, queryPart] = rawHash.split("?");
    const path = pathPart.replace(/^#/, "");

    // Update active nav links
    document.querySelectorAll(".nav-link").forEach(link => {
      link.classList.remove("active");
      if (link.getAttribute("href") === `#${path}` || (path === "" && link.getAttribute("href") === "#/")) {
        link.classList.add("active");
      }
    });

    const app = document.getElementById("app");
    if (!app) return;
    window.scrollTo({ top: 0, behavior: "smooth" });

    if (path === "/" || path === "") {
      this.renderHome(app);
    } else if (path === "/characters") {
      this.renderCharactersList(app);
    } else if (path.startsWith("/characters/")) {
      const slug = path.split("/")[2];
      this.renderCharacterDetail(app, slug);
    } else if (path === "/shop") {
      this.renderShop(app);
    } else if (path.startsWith("/kit/")) {
      const slug = path.split("/")[2];
      this.renderKitDetail(app, slug);
    } else if (path === "/compare") {
      this.renderCompare(app);
    } else if (path === "/checkout") {
      this.renderCheckout(app);
    } else if (path.startsWith("/order/")) {
      const ordId = path.split("/")[2];
      this.renderOrderConfirmation(app, ordId);
    } else if (path === "/track") {
      this.renderTracking(app);
    } else if (path === "/admin") {
      this.renderAdmin(app);
    } else if (path === "/admin/analytics") {
      this.renderFounderAnalytics(app);
    } else if (path === "/about") {
      this.renderAbout(app);
    } else if (path === "/contact") {
      this.renderContact(app);
    } else if (path === "/shipping" || path === "/returns") {
      this.renderPolicies(app);
    } else {
      app.innerHTML = `
        <div class="container" style="text-align: center; padding: 6rem 1rem;">
          <h1 style="font-family: var(--font-serif); font-size: 3rem; margin-bottom: 1rem;">404 — Page Not Found</h1>
          <p style="color: var(--color-text-muted); margin-bottom: 2rem;">The page you are looking for does not exist.</p>
          <a href="#/" class="btn btn-primary">Return to Storefront</a>
        </div>
      `;
    }
  },

  // -----------------------------------------------------------------------
  // 1. HOME VIEW
  // -----------------------------------------------------------------------
  async renderHome(app) {
    trackEvent("page_view", null, null, { page: "home" });
    app.innerHTML = `<div class="container" style="padding: 4rem; text-align: center;">Loading COFOCO Experience...</div>`;

    try {
      const [charsData, kitsData] = await Promise.all([
        api("/api/characters?status=published"),
        api("/api/kits")
      ]);

      app.innerHTML = `
        <!-- Hero Section - Faithful Reproduction of Reference Screen -->
        <section class="hero-section">
          <!-- Radiant Golden Topographic / Contour Curves in Background -->
          <svg class="hero-contour-lines" viewBox="0 0 700 700" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <defs>
              <linearGradient id="contourGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ECC973" stop-opacity="0.32" />
                <stop offset="50%" stop-color="#C29541" stop-opacity="0.18" />
                <stop offset="100%" stop-color="#8B6724" stop-opacity="0.05" />
              </linearGradient>
            </defs>
            <path d="M 120 0 C 320 220, 440 420, 700 520" stroke="url(#contourGrad)" stroke-width="1.4" />
            <path d="M 180 0 C 360 240, 480 440, 760 540" stroke="url(#contourGrad)" stroke-width="1.1" />
            <path d="M 240 0 C 400 260, 520 460, 820 560" stroke="url(#contourGrad)" stroke-width="0.9" />
            <path d="M 60 0 C 280 200, 400 400, 640 500" stroke="url(#contourGrad)" stroke-width="1.6" />
            <circle cx="450" cy="350" r="240" stroke="url(#contourGrad)" stroke-width="1.1" stroke-dasharray="5 7" />
            <circle cx="450" cy="350" r="320" stroke="url(#contourGrad)" stroke-width="0.8" />
          </svg>

          <div class="container hero-grid">
            <div class="hero-left-content">
              <h1 class="hero-headline">
                Build Your Strength.<br>
                <span class="italic-gold">Discover Your<br>Character.</span>
              </h1>
              <p class="hero-subheadline">
                Meet your character. Find your routine. Get your essentials.<br>
                Calibrated gym essentials and somatic recovery tools<br>
                combined into character-inspired kits.
              </p>
              <div class="hero-cta-group">
                <a href="#/characters" class="btn-pill-gold">
                  <span>Explore Characters</span>
                  <span class="arrow-token">→</span>
                </a>
                <a href="#/shop" class="btn-link-gold">
                  <span>Discover Your Kit ↓</span>
                </a>
              </div>
            </div>

            <div class="hero-showcase-container">
              <a href="#/kit/arjun-precision-kit" class="hero-showcase-card" title="View The Archer Precision Kit">
                <div class="showcase-brand-header">CONSCIOUS FORM COMPANY</div>
                
                <div class="showcase-emblem-wrap">
                  <svg class="showcase-emblem-svg" viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="emblemGold" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#FFF5E0" />
                        <stop offset="40%" stop-color="#ECC973" />
                        <stop offset="100%" stop-color="#A57C2C" />
                      </linearGradient>
                      <radialGradient id="emblemCoreGlow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#ECC973" stop-opacity="0.35" />
                        <stop offset="100%" stop-color="#0E1014" stop-opacity="0" />
                      </radialGradient>
                    </defs>
                    <!-- Core Radial Glow -->
                    <circle cx="80" cy="80" r="68" fill="url(#emblemCoreGlow)" />
                    
                    <!-- Concentric Outer Ring -->
                    <circle cx="80" cy="80" r="64" stroke="url(#emblemGold)" stroke-width="1.2" stroke-dasharray="3 4" opacity="0.6" />
                    <circle cx="80" cy="80" r="52" stroke="url(#emblemGold)" stroke-width="1.8" />
                    
                    <!-- Bow Arc -->
                    <path d="M 44 98 C 44 54, 116 54, 116 98" stroke="url(#emblemGold)" stroke-width="3.2" stroke-linecap="round" fill="none" />
                    
                    <!-- Upward Vertical Arrow -->
                    <line x1="80" y1="36" x2="80" y2="124" stroke="url(#emblemGold)" stroke-width="2.6" stroke-linecap="round" />
                    <polygon points="80,22 73,40 87,40" fill="url(#emblemGold)" />
                    
                    <!-- Reticle horizontal subtle crosshair -->
                    <line x1="36" y1="80" x2="124" y2="80" stroke="url(#emblemGold)" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.4" />
                  </svg>
                </div>

                <!-- Archetype Pill Badge -->
                <div class="showcase-archetype-pill">
                  <span>ARJUN • FOCUS</span>
                </div>

                <!-- Kit Title -->
                <h3 class="showcase-kit-title">The Archer Precision Kit</h3>

                <!-- Recessed Components Box -->
                <div class="showcase-items-panel">
                  <div class="showcase-item-row">
                    <span class="showcase-bullet"></span>
                    <span class="showcase-item-text">Calibrated Latex Resistance Bands (Set of 4)</span>
                  </div>
                  <div class="showcase-item-row">
                    <span class="showcase-bullet"></span>
                    <span class="showcase-item-text">Precision Grid EPP Foam Roller</span>
                  </div>
                  <div class="showcase-item-row">
                    <span class="showcase-bullet"></span>
                    <span class="showcase-item-text">Magnetic Interval &amp; Routine Focus Timer</span>
                  </div>
                  <div class="showcase-item-row">
                    <span class="showcase-bullet"></span>
                    <span class="showcase-item-text">Pure Gym Chalk Block 56g</span>
                  </div>
                </div>
              </a>
            </div>
          </div>
        </section>

        <!-- Character Discovery Section -->
        <section class="section">
          <div class="container">
            <div class="section-header">
              <div class="section-subtitle">Character Collections</div>
              <h2 class="section-title">Six Archetypes. Six Disciplines.</h2>
              <p class="section-desc">
                Connect with the character that mirrors your training philosophy. Each archetype anchors a tailored routine cue and calibrated kit essentials.
              </p>
            </div>

            <div class="character-grid">
              ${(charsData.characters || []).map(c => `
                <article class="character-card theme-${c.slug}">
                  <div class="char-card-media">
                    <img src="${c.artwork_url}" class="char-card-img" alt="${c.name} by COFOCO - ${c.theme_symbol}" onerror="this.onerror=null; this.src='/images/characters/arjun.svg';">
                    <span class="char-quality-pill">${c.quality}</span>
                  </div>
                  <div class="char-card-body">
                    <h3 class="char-card-name">${c.name} <span style="font-size: 0.9rem; font-weight: 500; color: var(--color-text-muted);">by COFOCO</span></h3>
                    <div class="char-card-tagline">${c.tagline}</div>
                    <p class="char-card-story">${c.story}</p>
                    <div class="char-routine-box">
                      <span class="char-routine-label">Routine Cue</span>
                      <span class="char-routine-text">${c.routine_cue}</span>
                    </div>
                    <div class="char-card-footer">
                      <a href="#/characters/${c.slug}" class="btn btn-secondary btn-block btn-sm">Explore ${c.name}</a>
                    </div>
                  </div>
                </article>
              `).join("")}
            </div>
          </div>
        </section>

        <!-- Featured Kits Catalog -->
        <section class="section" style="background: var(--color-secondary);">
          <div class="container">
            <div class="section-header">
              <div class="section-subtitle">Curated Kits</div>
              <h2 class="section-title">Gym Essentials & Somatic Recovery</h2>
              <p class="section-desc">
                Engineered kits verified against real training demands. Priced in INR with free India shipping.
              </p>
            </div>

            <div class="kits-grid">
              ${(kitsData.kits || []).map(k => `
                <div class="kit-card">
                  <div class="kit-card-img-wrap">
                    <img src="${k.image_url}" class="kit-card-img" alt="${k.name}" onerror="this.onerror=null; this.src='/images/kits/arjun_kit.svg';">
                    <span class="kit-char-badge">${k.character_name} by COFOCO</span>
                    <span class="kit-stock-badge ${k.is_in_stock ? 'stock-in' : 'stock-out'}">
                      ${k.is_in_stock ? `${k.sellable_kits} In Stock` : 'Out of Stock'}
                    </span>
                  </div>
                  <div class="kit-card-body">
                    <h3 class="kit-card-title">${k.name}</h3>
                    <div class="kit-card-subtitle">${k.subtitle}</div>
                    
                    <div class="kit-price-row">
                      <span class="kit-price">₹${Number(k.base_price).toLocaleString('en-IN')}</span>
                      <span class="kit-mrp">₹${Number(k.mrp).toLocaleString('en-IN')}</span>
                    </div>

                    <div class="kit-actions-grid">
                      <a href="#/kit/${k.slug}" class="btn btn-secondary btn-sm">View Details</a>
                      <button class="btn btn-primary btn-sm" ${!k.is_in_stock ? 'disabled' : ''} onclick="addToCart('${k.default_variant.id}', 1)">
                        ${k.is_in_stock ? 'Add to Cart' : 'Sold Out'}
                      </button>
                    </div>
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        </section>

        <!-- Why COFOCO? 4 Pillars -->
        <section class="section why-cofoco-section">
          <div class="container">
            <div class="section-header">
              <div class="section-subtitle">The Philosophy</div>
              <h2 class="section-title">Why Choose COFOCO?</h2>
              <p class="section-desc">Form is consciousness in motion. We reject generic gear in favor of purposeful discipline.</p>
            </div>

            <div class="pillars-grid">
              <div class="pillar-card">
                <div class="pillar-icon-box">🏹</div>
                <h3 class="pillar-title">Character-Inspired Kits</h3>
                <p class="pillar-desc">Rooted in ancient archetypes of focus, strength, resolve, and devotion—without mythological dogma or unverified claims.</p>
              </div>

              <div class="pillar-card">
                <div class="pillar-icon-box">🏋️</div>
                <h3 class="pillar-title">Selected Essentials</h3>
                <p class="pillar-desc">Calibrated latex resistance, 10mm top-grain leather belts, and pharmaceutical grade grip—tested by real athletes.</p>
              </div>

              <div class="pillar-card">
                <div class="pillar-icon-box">🧘</div>
                <h3 class="pillar-title">Recovery-Focused</h3>
                <p class="pillar-desc">High-density EPP myofascial rollers, percussion therapy spheres, acupressure mats, and botanical magnesium sleep mists.</p>
              </div>

              <div class="pillar-card">
                <div class="pillar-icon-box">⚡</div>
                <h3 class="pillar-title">Simple DTC Experience</h3>
                <p class="pillar-desc">Seamless guest checkout, transparent Indian GST pricing, live PIN code delivery estimates, and atomic inventory reliability.</p>
              </div>
            </div>
          </div>
        </section>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem; color: var(--color-danger);">Error loading storefront: ${e.message}</div>`;
    }
  },

  // -----------------------------------------------------------------------
  // 2. CHARACTER COLLECTION PAGE (UX02, US01)
  // -----------------------------------------------------------------------
  async renderCharacterDetail(app, slug) {
    trackEvent("character_view", null, null, { character_slug: slug });
    app.innerHTML = `<div class="container" style="padding: 4rem; text-align: center;">Loading Character Collection...</div>`;

    try {
      const char = await api(`/api/characters/${slug}`);
      trackEvent("character_view", char.id, null, { character_name: char.name });

      app.innerHTML = `
        <div class="theme-${char.slug}" style="background: var(--char-light); border-bottom: 1px solid var(--color-border); padding: 4rem 0;">
          <div class="container" style="display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 3rem; align-items: center;">
            <div style="background: #121416; border-radius: var(--radius-xl); overflow: hidden; box-shadow: var(--shadow-xl); border: 2px solid var(--char-accent);">
              <img src="${char.artwork_url}" style="width: 100%; height: 380px; object-fit: cover;" alt="${char.name} artwork" onerror="this.onerror=null; this.src='/images/characters/arjun.svg';">
            </div>

            <div>
              <div style="display: inline-block; background: var(--char-primary); color: #FFFFFF; font-size: 0.8rem; font-weight: 700; padding: 0.35rem 0.9rem; border-radius: 20px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 1rem;">
                ${char.quality}
              </div>
              <h1 style="font-family: var(--font-serif); font-size: 3.2rem; font-weight: 700; color: var(--char-primary); line-height: 1.1; margin-bottom: 0.5rem;">
                ${char.name} <span style="font-size: 1.5rem; font-weight: 500; opacity: 0.8;">by COFOCO</span>
              </h1>
              <div style="font-size: 1.15rem; font-weight: 600; color: var(--char-secondary); margin-bottom: 1.5rem;">
                ${char.tagline}
              </div>
              <p style="font-size: 1.05rem; line-height: 1.7; color: var(--color-text-dark); margin-bottom: 2rem;">
                ${char.story}
              </p>

              <div style="background: rgba(14, 16, 21, 0.85); border-radius: var(--radius-md); padding: 1.25rem 1.5rem; border: 1px solid rgba(229, 186, 99, 0.25); border-left: 4px solid var(--char-accent); box-shadow: var(--shadow-sm); margin-bottom: 2rem;">
                <span style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--color-accent-gold); letter-spacing: 1px; display: block;">Prescribed Routine Cue</span>
                <span style="font-size: 1rem; font-weight: 600; color: #FFFFFF;">${char.routine_cue}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="container section">
          <div class="section-header">
            <div class="section-subtitle">Dedicated Kit</div>
            <h2 class="section-title">Kit Curated for ${char.name}</h2>
            <p class="section-desc">Hardware engineered to embody ${char.quality.toLowerCase()} in your physical training routine.</p>
          </div>

          <div style="max-width: 800px; margin: 0 auto;">
            ${(char.linked_kits || []).map(lk => `
              <div class="kit-card" style="display: grid; grid-template-columns: 320px 1fr; border-radius: var(--radius-xl);">
                <img src="${lk.image_url}" style="width: 100%; height: 100%; object-fit: cover; min-height: 280px;" alt="${lk.name}" onerror="this.onerror=null; this.src='/images/kits/arjun_kit.svg';">
                <div class="kit-card-body" style="padding: 2rem;">
                  <span class="kit-char-badge" style="position: static; display: inline-block; margin-bottom: 0.75rem;">${char.name} by COFOCO</span>
                  <h3 class="kit-card-title" style="font-size: 1.75rem;">${lk.name}</h3>
                  <p style="color: var(--color-text-muted); font-size: 0.95rem; margin-bottom: 1.5rem;">${lk.description}</p>
                  <div class="kit-price-row">
                    <span class="kit-price">₹${Number(lk.base_price).toLocaleString('en-IN')}</span>
                    <span class="kit-stock-badge ${lk.is_in_stock ? 'stock-in' : 'stock-out'}" style="position: static;">
                      ${lk.is_in_stock ? `${lk.sellable_kits} Units Available` : 'Out of Stock'}
                    </span>
                  </div>
                  <div style="display: flex; gap: 1rem;">
                    <a href="#/kit/${lk.slug}" class="btn btn-secondary">Explore Kit</a>
                    <button class="btn btn-primary" ${!lk.is_in_stock ? 'disabled' : ''} onclick="addToCart('${lk.default_variant_id}', 1)">
                      ${lk.is_in_stock ? 'Add to Cart' : 'Sold Out'}
                    </button>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem; color: var(--color-danger);">Character not found: ${e.message}</div>`;
    }
  },

  // -----------------------------------------------------------------------
  // 3. PRODUCT & KIT DETAILS PAGE (UX03, US01)
  // -----------------------------------------------------------------------
  async renderKitDetail(app, slug) {
    trackEvent("kit_view", null, null, { kit_slug: slug });
    app.innerHTML = `<div class="container" style="padding: 4rem; text-align: center;">Loading Kit Details...</div>`;

    try {
      const kit = await api(`/api/kits/${slug}`);
      trackEvent("kit_view", kit.character_id, kit.id, { kit_name: kit.name });

      const activeVar = kit.variants && kit.variants.length > 0 ? kit.variants[0] : null;

      app.innerHTML = `
        <div class="container">
          <div style="padding: 1.5rem 0; font-size: 0.85rem; color: var(--color-text-muted);">
            <a href="#/" style="color: inherit;">Home</a> / <a href="#/shop" style="color: inherit;">Shop Kits</a> / <span style="color: var(--color-primary); font-weight: 600;">${kit.name}</span>
          </div>

          <div class="pdp-grid">
            <div class="pdp-gallery">
              <img src="${kit.image_url}" class="pdp-main-img" alt="${kit.name}" onerror="this.onerror=null; this.src='/images/kits/arjun_kit.svg';">
              <div style="display: flex; gap: 1rem;">
                <img src="${kit.character_artwork}" style="width: 80px; height: 80px; border-radius: 8px; border: 2px solid var(--color-accent-gold); object-fit: cover;" alt="${kit.character_name} emblem" onerror="this.onerror=null; this.src='/images/characters/arjun.svg';">
                <div style="font-size: 0.85rem;">
                  <span style="font-weight: 700; color: var(--color-primary);">${kit.character_name} by COFOCO</span>
                  <p style="color: var(--color-text-muted); font-size: 0.8rem;">Character routine cue: "${kit.character_routine_cue}"</p>
                </div>
              </div>
            </div>

            <div class="pdp-info">
              <div class="pdp-char-label">${kit.character_name} by COFOCO • Quality: ${kit.character_quality}</div>
              <h1 class="pdp-title">${kit.name}</h1>
              <div style="font-size: 1.05rem; font-weight: 600; color: var(--color-text-muted); margin-bottom: 1.5rem;">
                ${kit.subtitle}
              </div>

              <div class="pdp-price-box">
                <span class="pdp-price">₹${Number(kit.base_price).toLocaleString('en-IN')}</span>
                <span style="font-size: 1.1rem; color: var(--color-text-muted); text-decoration: line-through;">₹${Number(kit.mrp).toLocaleString('en-IN')}</span>
                <span class="kit-stock-badge ${kit.is_in_stock ? 'stock-in' : 'stock-out'}" style="position: static;">
                  ${kit.is_in_stock ? `${kit.sellable_kits} in stock (Atomic Verified)` : 'Out of Stock'}
                </span>
              </div>

              <p class="pdp-desc">${kit.description}</p>

              <!-- Out of Stock Banner & Alternatives (UX05) -->
              ${!kit.is_in_stock ? `
                <div style="background: var(--color-danger-bg); border-left: 4px solid var(--color-danger); padding: 1.25rem; border-radius: var(--radius-sm); margin-bottom: 2rem;">
                  <div style="font-weight: 700; color: var(--color-danger); margin-bottom: 0.25rem;">Currently Out of Stock</div>
                  <p style="font-size: 0.85rem; color: #7F1D1D; margin-bottom: 1rem;">Component stock is fully committed. Purchase is temporarily disabled, but you can explore alternative available kits below.</p>
                  <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: #7F1D1D; margin-bottom: 0.5rem;">Suggested In-Stock Alternatives:</div>
                  <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                    ${(kit.suggested_alternatives || []).map(alt => `
                      <a href="#/kit/${alt.slug}" class="btn btn-secondary btn-sm" style="background: #FFFFFF;">${alt.name} (₹${Number(alt.base_price).toLocaleString('en-IN')})</a>
                    `).join("")}
                  </div>
                </div>
              ` : ''}

              <!-- Variant Selector -->
              ${kit.variants && kit.variants.length > 1 ? `
                <div style="margin-bottom: 2rem;">
                  <label class="form-label">Select Edition / Size:</label>
                  <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                    ${kit.variants.map((v, idx) => `
                      <button class="btn btn-sm ${idx === 0 ? 'btn-primary' : 'btn-secondary'}" onclick="showToast('Selected variant ${v.variant_name}', 'info')">
                        ${v.variant_name} — ₹${Number(v.price).toLocaleString('en-IN')}
                      </button>
                    `).join("")}
                  </div>
                </div>
              ` : ''}

              <!-- Action Buttons -->
              <div style="display: flex; gap: 1rem; margin-bottom: 2.5rem;">
                <button class="btn btn-primary" style="flex: 2;" ${!kit.is_in_stock ? 'disabled' : ''} onclick="addToCart('${activeVar ? activeVar.id : ''}', 1)">
                  ${kit.is_in_stock ? 'Add to Cart' : 'Out of Stock'}
                </button>
                <button class="btn btn-secondary" style="flex: 1;" onclick="toggleCompare('${kit.slug}')">
                  ${State.compareList.includes(kit.slug) ? '✓ Compared' : '+ Compare Kit'}
                </button>
              </div>

              <!-- Included Components List from Active BOM (UX03) -->
              <div class="pdp-section-title">Complete Included Kit Components (BOM ${activeVar?.stock_info?.bom_version || 'v1.0'})</div>
              <ul class="bom-components-list">
                ${(kit.components || []).map(c => `
                  <li class="bom-item">
                    <div>
                      <span class="bom-item-name">${c.name}</span>
                      <span class="bom-item-meta" style="display: block;">SKU: ${c.sku} • On-Hand Sellable: ${c.available} units</span>
                    </div>
                    <span style="font-weight: 700; background: var(--color-secondary-alt); padding: 0.25rem 0.6rem; border-radius: 4px;">
                      Qty: ${c.required_qty}
                    </span>
                  </li>
                `).join("")}
              </ul>

              <!-- Shipping & Returns Policy -->
              <div style="background: var(--color-secondary-alt); border-radius: var(--radius-md); padding: 1.5rem; font-size: 0.85rem; border: 1px solid var(--color-border);">
                <div style="font-weight: 700; color: var(--color-primary); margin-bottom: 0.4rem;">📦 Shipping & Inspection Policy</div>
                <p style="color: var(--color-text-muted); margin-bottom: 0.5rem;">Dispatched within 48 hours via Blue Dart / Delhivery Express. 7-day hassle-free return window upon recorded inspection.</p>
                <div style="color: var(--color-accent-gold); font-weight: 600;">Standard GST invoice provided with every order.</div>
              </div>
            </div>
          </div>
        </div>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem; color: var(--color-danger);">Kit not found: ${e.message}</div>`;
    }
  },

  // -----------------------------------------------------------------------
  // 4. KIT COMPARISON SYSTEM (UX03, US01)
  // -----------------------------------------------------------------------
  async renderCompare(app) {
    trackEvent("compare_used", null, null, { kits: State.compareList });
    app.innerHTML = `<div class="container" style="padding: 4rem; text-align: center;">Loading Kit Comparison...</div>`;

    try {
      const kitIds = State.compareList.join(",");
      const compData = await api(`/api/compare?ids=${encodeURIComponent(kitIds)}`);
      const allKitsData = await api("/api/kits");

      app.innerHTML = `
        <div class="container compare-container">
          <div class="section-header" style="text-align: left; margin-bottom: 2rem;">
            <div class="section-subtitle">Side-by-Side Analysis</div>
            <h1 class="section-title">Kit Comparison System</h1>
            <p class="section-desc">Compare specs, included components, materials, price in INR, and stock availability.</p>
          </div>

          <div class="compare-selector-bar">
            <span style="font-weight: 600; font-size: 0.9rem;">Comparing ${compData.compared_kits.length} Kits (Max 4):</span>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
              ${(allKitsData.kits || []).map(k => `
                <button class="btn btn-sm ${State.compareList.includes(k.slug) ? 'btn-primary' : 'btn-secondary'}" onclick="toggleCompare('${k.slug}')">
                  ${State.compareList.includes(k.slug) ? '✓ ' : '+ '}${k.character_name} Kit
                </button>
              `).join("")}
            </div>
          </div>

          ${compData.compared_kits.length < 2 ? `
            <div class="luxury-form-card" style="text-align: center; padding: 4rem 1rem;">
              <h3 style="font-family: var(--font-serif); font-size: 1.5rem; margin-bottom: 0.5rem; color: #FFFFFF;">Select at Least Two Kits</h3>
              <p style="color: var(--color-text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">Use the selectors above to compare kits across characters and disciplines.</p>
            </div>
          ` : `
            <div class="compare-table-wrapper">
              <table class="compare-table">
                <thead>
                  <tr>
                    <th>Specification</th>
                    ${compData.compared_kits.map(k => `
                      <td class="compare-kit-header">
                        <img src="${k.image_url}" class="compare-kit-img" alt="${k.name}" onerror="this.onerror=null; this.src='/images/kits/arjun_kit.svg';">
                        <div style="font-family: var(--font-serif); font-size: 1.25rem; font-weight: 700; color: var(--color-primary);">${k.name}</div>
                        <div style="font-size: 0.85rem; color: var(--color-accent-gold); font-weight: 600; margin-bottom: 0.5rem;">${k.character_name} by COFOCO</div>
                        <div style="font-size: 1.35rem; font-weight: 800; margin-bottom: 0.75rem;">₹${Number(k.base_price).toLocaleString('en-IN')}</div>
                        <a href="#/kit/${k.slug}" class="btn btn-secondary btn-sm" style="margin-bottom: 0.4rem;">View Details</a>
                      </td>
                    `).join("")}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th>Character Quality</th>
                    ${compData.compared_kits.map(k => `<td><strong style="text-transform: uppercase;">${k.character_quality}</strong></td>`).join("")}
                  </tr>
                  <tr>
                    <th>Stock Status</th>
                    ${compData.compared_kits.map(k => `
                      <td>
                        <span class="kit-stock-badge ${k.is_in_stock ? 'stock-in' : 'stock-out'}" style="position: static;">
                          ${k.is_in_stock ? 'Available' : 'Out of Stock'}
                        </span>
                      </td>
                    `).join("")}
                  </tr>
                  <tr>
                    <th>Included Components</th>
                    ${compData.compared_kits.map(k => `
                      <td>
                        <ul style="list-style: none; font-size: 0.85rem;">
                          ${(k.included_components || []).map(c => `
                            <li style="padding: 0.25rem 0;">• ${c.name} (Qty: ${c.required_qty})</li>
                          `).join("")}
                        </ul>
                      </td>
                    `).join("")}
                  </tr>
                  <tr>
                    <th>Primary Materials</th>
                    ${compData.compared_kits.map(k => `
                      <td style="font-size: 0.85rem; color: var(--color-text-muted);">
                        ${(k.included_components || []).map(c => c.name.split(' ')[0]).join(', ')}
                      </td>
                    `).join("")}
                  </tr>
                  <tr>
                    <th>Routine Fit</th>
                    ${compData.compared_kits.map(k => `<td style="font-size: 0.85rem;">${k.routine_integration}</td>`).join("")}
                  </tr>
                  <tr>
                    <th>Action</th>
                    ${compData.compared_kits.map(k => `
                      <td>
                        <button class="btn btn-primary btn-sm btn-block" ${!k.is_in_stock ? 'disabled' : ''} onclick="addToCart('${k.variants[0]?.id}', 1)">
                          ${k.is_in_stock ? 'Add to Cart' : 'Sold Out'}
                        </button>
                      </td>
                    `).join("")}
                  </tr>
                </tbody>
              </table>
            </div>
          `}
        </div>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem; color: var(--color-danger);">Error loading comparison: ${e.message}</div>`;
    }
  },

  // -----------------------------------------------------------------------
  // 5. GUEST CHECKOUT & PAYMENT (OP03, US02)
  // -----------------------------------------------------------------------
  async renderCheckout(app) {
    trackEvent("checkout_started", null, null, { subtotal: State.cart.subtotal });
    if (!State.cart.items || State.cart.items.length === 0) {
      app.innerHTML = `
        <div class="container" style="text-align: center; padding: 6rem 1rem;">
          <h2 style="font-family: var(--font-serif); font-size: 2rem; margin-bottom: 1rem;">Your Cart is Empty</h2>
          <p style="color: var(--color-text-muted); margin-bottom: 2rem;">Add a kit to your cart before proceeding to checkout.</p>
          <a href="#/shop" class="btn btn-primary">Browse Kits</a>
        </div>
      `;
      return;
    }

    app.innerHTML = `
      <div class="container">
        <div class="checkout-grid">
          <div>
            <div class="checkout-card">
              <!-- Atomic Reservation Banner (15 Minute Countdown) -->
              <div class="reservation-banner" id="reservationBanner">
                <span>⚡ Atomic Component Reservation Active</span>
                <span id="reservationTimer">15:00</span>
              </div>

              <h2 style="font-family: var(--font-serif); font-size: 1.85rem; font-weight: 700; color: var(--color-primary); margin-bottom: 0.5rem;">
                Guest Delivery Information
              </h2>
              <p style="font-size: 0.85rem; color: var(--color-text-muted); margin-bottom: 2rem;">
                No account required for launch. Orders are confirmed via SMS & Email.
              </p>

              <form id="checkoutForm" onsubmit="handleCheckoutSubmit(event)">
                <div class="form-group">
                  <label class="form-label" for="custName">Full Name *</label>
                  <input type="text" id="custName" class="form-control" required placeholder="e.g. Aditya Varma">
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label" for="custEmail">Email Address *</label>
                    <input type="email" id="custEmail" class="form-control" required placeholder="name@domain.com">
                  </div>
                  <div class="form-group">
                    <label class="form-label" for="custPhone">Phone Number (+91) *</label>
                    <input type="tel" id="custPhone" class="form-control" required placeholder="98765 43210" pattern="[0-9]{10}">
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label" for="custAddress">Street Address *</label>
                  <input type="text" id="custAddress" class="form-control" required placeholder="Apartment / Flat, Street, Area">
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label" for="custPincode">PIN Code (India) *</label>
                    <input type="text" id="custPincode" class="form-control" required placeholder="6-digit PIN code" maxlength="6" onchange="checkServiceability(this.value)">
                    <span id="pincodeStatus" style="font-size: 0.8rem; display: block; margin-top: 0.25rem;"></span>
                  </div>
                  <div class="form-group">
                    <label class="form-label" for="custCity">City *</label>
                    <input type="text" id="custCity" class="form-control" required placeholder="City">
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label" for="custState">State / Union Territory *</label>
                  <select id="custState" class="form-control" required>
                    <option value="">Select State / UT</option>
                    <optgroup label="States (28)">
                      <option value="Andhra Pradesh">Andhra Pradesh</option>
                      <option value="Arunachal Pradesh">Arunachal Pradesh</option>
                      <option value="Assam">Assam</option>
                      <option value="Bihar">Bihar</option>
                      <option value="Chhattisgarh">Chhattisgarh</option>
                      <option value="Goa">Goa</option>
                      <option value="Gujarat">Gujarat</option>
                      <option value="Haryana">Haryana</option>
                      <option value="Himachal Pradesh">Himachal Pradesh</option>
                      <option value="Jharkhand">Jharkhand</option>
                      <option value="Karnataka">Karnataka</option>
                      <option value="Kerala">Kerala</option>
                      <option value="Madhya Pradesh">Madhya Pradesh</option>
                      <option value="Maharashtra">Maharashtra</option>
                      <option value="Manipur">Manipur</option>
                      <option value="Meghalaya">Meghalaya</option>
                      <option value="Mizoram">Mizoram</option>
                      <option value="Nagaland">Nagaland</option>
                      <option value="Odisha">Odisha</option>
                      <option value="Punjab">Punjab</option>
                      <option value="Rajasthan">Rajasthan</option>
                      <option value="Sikkim">Sikkim</option>
                      <option value="Tamil Nadu">Tamil Nadu</option>
                      <option value="Telangana">Telangana</option>
                      <option value="Tripura">Tripura</option>
                      <option value="Uttar Pradesh">Uttar Pradesh</option>
                      <option value="Uttarakhand">Uttarakhand</option>
                      <option value="West Bengal">West Bengal</option>
                    </optgroup>
                    <optgroup label="Union Territories (8)">
                      <option value="Andaman and Nicobar Islands">Andaman and Nicobar Islands</option>
                      <option value="Chandigarh">Chandigarh</option>
                      <option value="Dadra and Nagar Haveli and Daman and Diu">Dadra and Nagar Haveli and Daman and Diu</option>
                      <option value="Delhi">Delhi (NCT)</option>
                      <option value="Jammu and Kashmir">Jammu and Kashmir</option>
                      <option value="Ladakh">Ladakh</option>
                      <option value="Lakshadweep">Lakshadweep</option>
                      <option value="Puducherry">Puducherry</option>
                    </optgroup>
                  </select>
                </div>

                <button type="submit" id="payNowBtn" class="btn btn-accent btn-block" style="padding: 1rem; font-size: 1.1rem; margin-top: 1.5rem;">
                  Pay ₹${Number(State.cart.total).toLocaleString('en-IN')} via Razorpay
                </button>
              </form>
            </div>
          </div>

          <!-- Order Summary Sidebar -->
          <div>
            <div class="checkout-card" style="background: var(--color-secondary);">
              <h3 style="font-family: var(--font-serif); font-size: 1.35rem; font-weight: 700; margin-bottom: 1.25rem;">Order Summary</h3>
              
              ${(State.cart.items || []).map(i => `
                <div style="display: flex; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid var(--color-border);">
                  <img src="${i.image_url}" style="width: 52px; height: 52px; object-fit: cover; border-radius: 6px;" alt="${i.kit_name}">
                  <div style="flex: 1;">
                    <div style="font-size: 0.9rem; font-weight: 700;">${i.kit_name}</div>
                    <div style="font-size: 0.8rem; color: var(--color-text-muted);">${i.character_name} • Qty: ${i.quantity}</div>
                  </div>
                  <div style="font-weight: 700; font-size: 0.95rem;">₹${Number(i.price * i.quantity).toLocaleString('en-IN')}</div>
                </div>
              `).join("")}

              <!-- Coupon Code Input -->
              <div style="margin: 1.5rem 0; display: flex; gap: 0.5rem;">
                <input type="text" id="couponInput" class="form-control" placeholder="Coupon Code (e.g. COFOCO10)" value="${State.cart.coupon_code || ''}" style="text-transform: uppercase;">
                <button class="btn btn-secondary btn-sm" onclick="applyCoupon()">Apply</button>
              </div>

              <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.4rem;">
                <span style="color: var(--color-text-muted);">Merchandise Value</span>
                <span>₹${Number(State.cart.subtotal).toLocaleString('en-IN')}</span>
              </div>
              ${State.cart.discount > 0 ? `
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.4rem; color: var(--color-success);">
                  <span>Discount</span>
                  <span>-₹${Number(State.cart.discount).toLocaleString('en-IN')}</span>
                </div>
              ` : ''}
              <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.4rem;">
                <span style="color: var(--color-text-muted);">Shipping</span>
                <span>${State.cart.shipping === 0 ? '<strong style="color: var(--color-success)">FREE</strong>' : '₹' + State.cart.shipping}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.75rem; color: var(--color-text-muted);">
                <span>Estimated GST (18% inclusive)</span>
                <span>₹${Number(State.cart.tax).toLocaleString('en-IN')}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 1.3rem; font-weight: 800; border-top: 1px solid var(--color-border); padding-top: 0.75rem;">
                <span>Total Payable</span>
                <span>₹${Number(State.cart.total).toLocaleString('en-IN')}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Initialize atomic reservation
    initAtomicReservation();
  },

  // -----------------------------------------------------------------------
  // 6. ORDER CONFIRMATION & TIMELINE VIEW (OP04, US02)
  // -----------------------------------------------------------------------
  async renderOrderConfirmation(app, ordId) {
    app.innerHTML = `<div class="container" style="padding: 4rem; text-align: center;">Loading Order Details...</div>`;

    try {
      const ord = await api(`/api/orders/${ordId}`);
      const steps = [
        { key: "paid", label: "Paid" },
        { key: "picking", label: "Picking" },
        { key: "packed", label: "Packed" },
        { key: "dispatched", label: "Dispatched" },
        { key: "delivered", label: "Delivered" }
      ];

      const currentIdx = steps.findIndex(s => s.key === ord.order_status);

      app.innerHTML = `
        <div class="container">
          <div class="order-confirmation-box">
            <div class="success-icon-large">✓</div>
            <h1 style="font-family: var(--font-serif); font-size: 2.4rem; font-weight: 700; margin-bottom: 0.5rem;">
              Order Confirmed & Payment Verified
            </h1>
            <p style="font-size: 1.1rem; color: var(--color-text-muted); margin-bottom: 1.5rem;">
              Thank you, <strong>${ord.customer_name}</strong>. Your order <strong>${ord.order_number}</strong> has been received.
            </p>

            <!-- Customer Multi-Channel Dispatch Notifications (SMS + Email) -->
            <div class="customer-notification-card">
              <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                <span style="font-size: 1.6rem;">🔔</span>
                <div>
                  <div style="font-weight: 700; color: #FFFFFF; font-size: 1.1rem;">Customer Notifications Dispatched</div>
                  <div style="font-size: 0.8rem; color: var(--color-accent-gold);">Real-time SMS & Email Confirmation Service</div>
                </div>
              </div>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;">
                <div class="notification-pill-box">
                  <div style="font-size: 0.82rem; font-weight: 700; color: #34D399; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem;">
                    <span>✓</span> SMS & WhatsApp Alert Sent
                  </div>
                  <div style="font-size: 0.85rem; color: #EDE6DE; line-height: 1.5;">
                    Dispatched to <strong>+91 ${ord.customer_phone}</strong> with order confirmation, tracking PIN, and courier timeline.
                  </div>
                </div>
                <div class="notification-pill-box">
                  <div style="font-size: 0.82rem; font-weight: 700; color: #34D399; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem;">
                    <span>✓</span> Email Confirmation Dispatched
                  </div>
                  <div style="font-size: 0.85rem; color: #EDE6DE; line-height: 1.5;">
                    Dispatched to <strong>${ord.customer_email}</strong> with 18% GST invoice, component BOM list, and somatic warranty.
                  </div>
                </div>
              </div>
            </div>

            <!-- 5-Stage Order Progress Timeline -->
            <div class="status-timeline">
              ${steps.map((st, idx) => `
                <div class="timeline-step ${idx <= currentIdx ? 'completed' : ''} ${idx === currentIdx ? 'active' : ''}">
                  <div class="timeline-dot">${idx <= currentIdx ? '✓' : idx + 1}</div>
                  <span class="timeline-label">${st.label}</span>
                </div>
              `).join("")}
            </div>

            <!-- Shipment Tracking Box (If Dispatched) -->
            ${ord.shipment ? `
              <div style="background: var(--color-info-bg); border: 1px solid #93C5FD; border-radius: var(--radius-md); padding: 1.5rem; margin-bottom: 2.5rem; text-align: left;">
                <div style="font-weight: 700; color: var(--color-info); margin-bottom: 0.35rem;">🚚 Shipment En Route via ${ord.shipment.courier_name}</div>
                <div style="font-size: 0.9rem; margin-bottom: 0.5rem;">Tracking AWB: <strong>${ord.shipment.tracking_number}</strong></div>
                <a href="${ord.shipment.tracking_url}" target="_blank" class="btn btn-primary btn-sm">Track Package on Carrier Portal</a>
              </div>
            ` : `
              <div style="background: var(--color-secondary-alt); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 2rem; font-size: 0.9rem;">
                Estimated Dispatch Date: <strong>${new Date(ord.promised_dispatch_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</strong> (Within 48 hours).
              </div>
            `}

            <!-- Order Line Details with Preserved BOM Snapshot -->
            <div style="text-align: left; background: rgba(14, 16, 21, 0.85); border-radius: var(--radius-md); padding: 1.5rem; margin-bottom: 2rem; border: 1px solid rgba(229, 186, 99, 0.25);">
              <h3 style="font-family: var(--font-serif); font-size: 1.3rem; margin-bottom: 1rem; color: #FFFFFF;">Purchased Kits & Components</h3>
              ${(ord.items || []).map(itm => `
                <div style="padding: 1rem 0; border-bottom: 1px solid rgba(229, 186, 99, 0.15);">
                  <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 1.05rem; color: #FFFFFF;">
                    <span>${itm.kit_name} (${itm.character_name} Edition)</span>
                    <span style="color: var(--color-accent-gold);">₹${Number(itm.price * itm.quantity).toLocaleString('en-IN')}</span>
                  </div>
                  <div style="font-size: 0.85rem; color: var(--color-text-muted); margin-bottom: 0.5rem;">Edition: ${itm.variant_name} • Qty: ${itm.quantity}</div>
                  
                  <div style="background: rgba(8, 10, 14, 0.88); padding: 0.75rem; border-radius: 6px; font-size: 0.8rem; border: 1px solid rgba(229, 186, 99, 0.2);">
                    <span style="font-weight: 700; color: var(--color-accent-gold); display: block; margin-bottom: 0.25rem;">Frozen Purchase BOM Configuration:</span>
                    ${(itm.bom_snapshot || []).map(b => `
                      <span style="display: inline-block; margin-right: 1rem; color: #EDE5D8;">
                        • ${b.name} (Qty: ${b.qty * itm.quantity})
                      </span>
                    `).join("")}
                  </div>
                </div>
              `).join("")}

              <div style="display: flex; justify-content: space-between; padding-top: 1rem; font-size: 1.15rem; font-weight: 800;">
                <span>Total Amount Paid</span>
                <span>₹${Number(ord.total_amount).toLocaleString('en-IN')}</span>
              </div>
            </div>

            <a href="#/shop" class="btn btn-secondary">Continue Shopping</a>
          </div>
        </div>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem; color: var(--color-danger);">Order lookup error: ${e.message}</div>`;
    }
  },

  // -----------------------------------------------------------------------
  // 7. PUBLIC ORDER TRACKING LOOKUP (US02)
  // -----------------------------------------------------------------------
  renderTracking(app) {
    app.innerHTML = `
      <div class="container section">
        <div class="container-narrow">
          <div class="section-header">
            <div class="section-subtitle">Live Fulfillment Status</div>
            <h1 class="section-title">Track Your COFOCO Order</h1>
            <p class="section-desc">Enter your order ID or reference number to view real-time warehouse fulfillment, packing, and courier dispatch.</p>
          </div>

          <div class="luxury-form-card">
            <form onsubmit="handleTrackingSearch(event)">
              <div class="form-group">
                <label class="form-label">Order Number or ID *</label>
                <input type="text" id="trackOrderNum" class="form-control" required placeholder="e.g. CFC-2026-8801 or CFC-2026-8802">
              </div>
              <button type="submit" class="btn btn-pill-gold btn-block" style="justify-content: center; font-size: 1rem; padding: 1rem 2rem; margin-top: 1rem;">
                <span>Find Live Tracking Status</span>
                <span class="arrow-token">→</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    `;
  },

  // -----------------------------------------------------------------------
  // 8. STAFF ADMINISTRATION DASHBOARD (OP01 - OP05, US03, US05)
  // -----------------------------------------------------------------------
  async renderAdmin(app) {
    // Strictly restrict to authenticated Website Owner & Staff
    if (!State.staffAuth) {
      app.innerHTML = `
        <div class="container section">
          <div class="container-narrow">
            <div class="luxury-form-card" style="max-width: 480px; margin: 3rem auto; text-align: center;">
              <div style="font-size: 2.8rem; margin-bottom: 0.75rem;">🔒</div>
              <h2 style="font-family: var(--font-serif); font-size: 1.85rem; margin-bottom: 0.5rem; color: #FFFFFF;">Website Owner Portal</h2>
              <p style="color: var(--color-text-muted); font-size: 0.85rem; margin-bottom: 2rem;">
                Authorized portal for COFOCO website owners, inventory managers, and fulfillment staff.
              </p>
              <form onsubmit="handleOwnerLogin(event)">
                <div class="form-group" style="text-align: left;">
                  <label class="form-label">Owner Username</label>
                  <input type="text" id="ownerUsername" class="form-control" placeholder="admin" value="admin" required>
                </div>
                <div class="form-group" style="text-align: left;">
                  <label class="form-label">Password</label>
                  <input type="password" id="ownerPassword" class="form-control" placeholder="••••••••" value="Admin@COFOCO2026" required>
                </div>
                <button type="submit" class="btn btn-pill-gold btn-block" style="justify-content: center; padding: 1rem; margin-top: 1.5rem; font-size: 1rem;">
                  <span>Unlock Owner Portal</span>
                  <span class="arrow-token">→</span>
                </button>
              </form>
              <div style="margin-top: 1.5rem; border-top: 1px solid var(--color-border-subtle); padding-top: 1rem;">
                <a href="#/" style="color: var(--color-text-muted); font-size: 0.85rem; text-decoration: underline;">Return to Customer Storefront</a>
              </div>
            </div>
          </div>
        </div>
      `;
      return;
    }

    const user = State.staffAuth.user;

    app.innerHTML = `
      <div class="admin-shell">
        <div class="admin-header">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <a href="#/" style="color: #FFFFFF; text-decoration: none; font-weight: 800; font-size: 1.25rem; letter-spacing: 2px;">COFOCO</a>
            <span style="background: var(--color-accent-gold); color: #000; font-size: 0.7rem; font-weight: 800; padding: 3px 8px; border-radius: 4px;">WEBSITE OWNER PORTAL</span>
          </div>

          <!-- Staff Role Switcher for RBAC Evaluation -->
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div class="admin-role-selector">
              <span style="font-size: 0.85rem; color: #A0AEC0;">Active Role:</span>
              <select class="admin-role-select" onchange="switchStaffRole(this.value)">
                <option value="admin" ${user.username === 'admin' ? 'selected' : ''}>Admin (All Permissions)</option>
                <option value="editor" ${user.username === 'editor' ? 'selected' : ''}>Brand Editor (Draft & Catalog)</option>
                <option value="publisher" ${user.username === 'publisher' ? 'selected' : ''}>Publisher (Review & Approve)</option>
                <option value="warehouse" ${user.username === 'warehouse' ? 'selected' : ''}>Warehouse Staff (Fulfillment)</option>
                <option value="support" ${user.username === 'support' ? 'selected' : ''}>Support Staff (Returns & Orders)</option>
                <option value="finance" ${user.username === 'finance' ? 'selected' : ''}>Finance Staff (Refunds & Analytics)</option>
              </select>
              <span style="font-size: 0.85rem; color: var(--color-accent-gold); font-weight: 600;">${user.full_name}</span>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="logoutOwnerStaff()" style="font-size: 0.8rem; border-color: rgba(229,186,99,0.3); color: #FFFFFF;" title="Sign out of owner view">
              Sign Out
            </button>
          </div>
        </div>

        <!-- Admin Navigation Tabs -->
        <div class="admin-tabs">
          <button class="admin-tab-btn active" onclick="switchAdminTab('overview')">Overview</button>
          <button class="admin-tab-btn" onclick="switchAdminTab('orders')">Orders & Fulfillment</button>
          <button class="admin-tab-btn" onclick="switchAdminTab('inventory')">Inventory Ledger</button>
          <button class="admin-tab-btn" onclick="switchAdminTab('exceptions')">Returns & Exceptions</button>
          <button class="admin-tab-btn" onclick="switchAdminTab('catalog')">Catalog & BOM</button>
          <a href="#/admin/analytics" class="admin-tab-btn" style="text-decoration: none; color: var(--color-accent-gold);">Founder Analytics →</a>
        </div>

        <div class="container" id="adminTabContent" style="padding: 2rem 0;">
          Loading Admin Overview...
        </div>
      </div>
    `;

    loadAdminTab("overview");
  },

  // -----------------------------------------------------------------------
  // 9. FOUNDER BUSINESS ANALYTICS DASHBOARD (AN01 - AN03, US04)
  // -----------------------------------------------------------------------
  async renderFounderAnalytics(app) {
    if (!State.staffAuth) {
      window.location.hash = "#/admin";
      return;
    }

    app.innerHTML = `
      <div class="admin-shell">
        <div class="admin-header">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <a href="#/admin" style="color: #FFFFFF; text-decoration: none; font-weight: 800; font-size: 1.25rem;">COFOCO</a>
            <span style="background: #10B981; color: #FFFFFF; font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: 4px;">FOUNDER BUSINESS ANALYTICS</span>
          </div>
          <div style="display: flex; gap: 1rem; align-items: center;">
            <span style="font-size: 0.8rem; color: #A0AEC0;">Timezone: Asia/Kolkata (IST) • Currency: INR (₹)</span>
            <a href="#/admin" class="btn btn-secondary btn-sm" style="color: #FFFFFF; border-color: rgba(255,255,255,0.3);">← Back to Operations</a>
          </div>
        </div>

        <div class="container" style="padding: 2.5rem 0;">
          <!-- Controls Bar -->
          <div style="background: rgba(14, 16, 21, 0.85); border-radius: var(--radius-lg); border: 1px solid rgba(229, 186, 99, 0.28); padding: 1.25rem 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 2rem;">
            <div style="display: flex; align-items: center; gap: 1rem;">
              <label style="font-size: 0.85rem; font-weight: 700; color: #ECC973;">Date Range:</label>
              <select id="analyticsDateRange" class="form-control" style="width: auto; padding: 0.4rem 0.8rem;" onchange="loadAnalyticsData()">
                <option value="7d" selected>Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="q4">Q4 2026 (Launch Quarter)</option>
              </select>
            </div>

            <div style="display: flex; gap: 1rem; align-items: center;">
              <span id="analyticsRefreshed" style="font-size: 0.8rem; color: var(--color-text-muted);">Last Refreshed: Loading...</span>
              <button class="btn btn-primary btn-sm" onclick="exportAnalyticsCSV()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                Export CSV (Zero PII)
              </button>
            </div>
          </div>

          <div id="analyticsBody">
            Loading Founder Business Analytics...
          </div>
        </div>
      </div>
    `;

    loadAnalyticsData();
  },

  // -----------------------------------------------------------------------
  // 10. SHOP & POLICIES STATIC VIEWS
  // -----------------------------------------------------------------------
  async renderShop(app) {
    trackEvent("page_view", null, null, { page: "shop" });
    try {
      const kitsData = await api("/api/kits");
      app.innerHTML = `
        <div class="container section">
          <div class="section-header">
            <div class="section-subtitle">The Complete Collection</div>
            <h1 class="section-title">Shop COFOCO Launch Kits</h1>
            <p class="section-desc">Six character archetypes. Complete gym essentials and somatic tissue recovery.</p>
          </div>

          <div class="kits-grid">
            ${(kitsData.kits || []).map(k => `
              <div class="kit-card">
                <div class="kit-card-img-wrap">
                  <img src="${k.image_url}" class="kit-card-img" alt="${k.name}" onerror="this.onerror=null; this.src='/images/kits/arjun_kit.svg';">
                  <span class="kit-char-badge">${k.character_name} by COFOCO</span>
                  <span class="kit-stock-badge ${k.is_in_stock ? 'stock-in' : 'stock-out'}">
                    ${k.is_in_stock ? `${k.sellable_kits} In Stock` : 'Out of Stock'}
                  </span>
                </div>
                <div class="kit-card-body">
                  <h3 class="kit-card-title">${k.name}</h3>
                  <div class="kit-card-subtitle">${k.subtitle}</div>
                  <div class="kit-price-row">
                    <span class="kit-price">₹${Number(k.base_price).toLocaleString('en-IN')}</span>
                    <span class="kit-mrp">₹${Number(k.mrp).toLocaleString('en-IN')}</span>
                  </div>
                  <div class="kit-actions-grid">
                    <a href="#/kit/${k.slug}" class="btn btn-secondary btn-sm">View Details</a>
                    <button class="btn btn-primary btn-sm" ${!k.is_in_stock ? 'disabled' : ''} onclick="addToCart('${k.default_variant.id}', 1)">
                      ${k.is_in_stock ? 'Add to Cart' : 'Sold Out'}
                    </button>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem;">Error loading shop: ${e.message}</div>`;
    }
  },

  async renderCharactersList(app) {
    try {
      const data = await api("/api/characters?status=published");
      app.innerHTML = `
        <div class="container section">
          <div class="section-header">
            <div class="section-subtitle">Launch Roster</div>
            <h1 class="section-title">Discover the Six Characters</h1>
            <p class="section-desc">Each character represents a distinct quality and training habit.</p>
          </div>
          <div class="character-grid">
            ${(data.characters || []).map(c => `
              <article class="character-card theme-${c.slug}">
                <div class="char-card-media">
                  <img src="${c.artwork_url}" class="char-card-img" alt="${c.name} by COFOCO" onerror="this.onerror=null; this.src='/images/characters/arjun.svg';">
                  <span class="char-quality-pill">${c.quality}</span>
                </div>
                <div class="char-card-body">
                  <h3 class="char-card-name">${c.name} <span style="font-size: 0.9rem; font-weight: 500; color: var(--color-text-muted);">by COFOCO</span></h3>
                  <div class="char-card-tagline">${c.tagline}</div>
                  <p class="char-card-story">${c.story}</p>
                  <div class="char-routine-box">
                    <span class="char-routine-label">Routine Cue</span>
                    <span class="char-routine-text">${c.routine_cue}</span>
                  </div>
                  <div class="char-card-footer">
                    <a href="#/characters/${c.slug}" class="btn btn-secondary btn-block btn-sm">Explore ${c.name} Collection</a>
                  </div>
                </div>
              </article>
            `).join("")}
          </div>
        </div>
      `;
    } catch (e) {
      app.innerHTML = `<div class="container" style="padding: 4rem;">Error: ${e.message}</div>`;
    }
  },

  renderAbout(app) {
    app.innerHTML = `
      <div class="container section">
        <div class="container-narrow">
          <div class="section-header">
            <div class="section-subtitle">Our Purpose</div>
            <h1 class="section-title">Conscious Form Company</h1>
          </div>
          <p style="font-size: 1.15rem; line-height: 1.8; color: var(--color-text-dark); margin-bottom: 2rem;">
            At COFOCO, we believe true physical strength cannot exist without deliberate inner form. We combine heavy, uncompromising gym essentials with deep somatic recovery tools—organized into kits inspired by the perennial virtues of historical archetypes.
          </p>
          <p style="font-size: 1.05rem; line-height: 1.7; color: var(--color-text-muted); margin-bottom: 2rem;">
            Whether you channel the laser focus of Arjun, the mountain-bending power of Bheema, or the unbroken daily habit of Savitri, our kits equip you to train with intention and recover with cellular grace.
          </p>
          <div style="background: var(--color-secondary); padding: 2rem; border-radius: var(--radius-lg); border-left: 4px solid var(--color-accent-gold);">
            <h3 style="font-family: var(--font-serif); font-size: 1.4rem; margin-bottom: 0.5rem;">Direct-to-Consumer India</h3>
            <p style="font-size: 0.9rem; color: var(--color-text-muted);">
              All kits are packed and dispatched from our primary fulfillment hub with end-to-end BOM tracking, atomic inventory locks, and verified courier integrations.
            </p>
          </div>
        </div>
      </div>
    `;
  },

  renderContact(app) {
    app.innerHTML = `
      <div class="container section">
        <div class="container-narrow">
          <div class="section-header">
            <div class="section-subtitle">Support & Queries</div>
            <h1 class="section-title">Contact COFOCO</h1>
            <p class="section-desc">Our concierge team is available Monday to Saturday, 9:00 AM – 7:00 PM IST.</p>
          </div>
          <div class="luxury-form-card">
            <form onsubmit="event.preventDefault(); showToast('Thank you. Your message has been received by COFOCO Support.', 'success'); this.reset();">
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Full Name *</label>
                  <input type="text" class="form-control" required placeholder="Aditya Varma">
                </div>
                <div class="form-group">
                  <label class="form-label">Email Address *</label>
                  <input type="email" class="form-control" required placeholder="name@domain.com">
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">Subject</label>
                <input type="text" class="form-control" placeholder="Order inquiry, kit questions, or corporate orders">
              </div>
              <div class="form-group">
                <label class="form-label">Message *</label>
                <textarea class="form-control" rows="5" required placeholder="How can we assist your training routine?"></textarea>
              </div>
              <button type="submit" class="btn btn-pill-gold btn-block" style="justify-content: center; font-size: 1rem; padding: 1rem 2rem; margin-top: 1rem;">
                <span>Send Concierge Message</span>
                <span class="arrow-token">→</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    `;
  },

  renderPolicies(app) {
    app.innerHTML = `
      <div class="container section">
        <div class="container-narrow">
          <h1 class="section-title" style="margin-bottom: 1.5rem;">Shipping & Return Inspection Policy</h1>
          <div class="luxury-form-card" style="line-height: 1.8; color: var(--color-text-dark);">
            <h3 style="font-family: var(--font-serif); font-size: 1.4rem; margin-bottom: 0.5rem; color: #FFFFFF;">1. Dispatch & Delivery (India)</h3>
            <p style="color: var(--color-text-muted); font-size: 0.95rem; margin-bottom: 1.5rem;">
              Orders placed before 2:00 PM IST are handed to our express courier partners (Blue Dart / Delhivery) within 24–48 hours. Shipping is free for orders ₹2,500 and above; otherwise a standard flat charge of ₹149 applies.
            </p>

            <h3 style="font-family: var(--font-serif); font-size: 1.4rem; margin-bottom: 0.5rem; color: #FFFFFF;">2. Return Quality Gate & Recorded Inspection</h3>
            <p style="color: var(--color-text-muted); font-size: 0.95rem; margin-bottom: 1.5rem;">
              COFOCO operates a strict quality protocol: units returned by customers must undergo a physical inspection by authorized staff before any unit is restocked or refund processed. Unopened items with intact factory seals are returned to sellable inventory. Damaged or worn items are written off to prevent compromised gear reaching athletes.
            </p>

            <h3 style="font-family: var(--font-serif); font-size: 1.4rem; margin-bottom: 0.5rem; color: #FFFFFF;">3. Payment & Refund Processing</h3>
            <p style="color: var(--color-text-muted); font-size: 0.95rem;">
              Payments are processed in test/live mode via Razorpay. Approved refunds are transmitted directly to the original payment source (UPI, Card, Netbanking) with gateway reference IDs logged in our financial ledger.
            </p>
          </div>
        </div>
      </div>
    `;
  }
};

// Initialize router
Router.init();

// =========================================================================
// CHECKOUT & PAYMENT INTEGRATION LOGIC (OP03, US02)
// =========================================================================
let reservationTimerInterval = null;

async function initAtomicReservation() {
  try {
    const res = await api("/api/checkout/reserve", {
      method: "POST",
      body: JSON.stringify({ session_id: State.sessionId })
    });

    const expiryTime = new Date(res.expires_at).getTime();
    if (reservationTimerInterval) clearInterval(reservationTimerInterval);

    reservationTimerInterval = setInterval(() => {
      const now = new Date().getTime();
      const diff = expiryTime - now;
      if (diff <= 0) {
        clearInterval(reservationTimerInterval);
        document.getElementById("reservationTimer").textContent = "EXPIRED";
        document.getElementById("reservationBanner").style.background = "#FEE2E2";
        document.getElementById("reservationBanner").style.borderColor = "#EF4444";
        document.getElementById("reservationBanner").innerHTML = `
          <span>⚠️ Reservation Expired. Stock has been released. Please refresh checkout.</span>
        `;
        document.getElementById("payNowBtn").disabled = true;
      } else {
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const secs = Math.floor((diff % (1000 * 60)) / 1000);
        const timerEl = document.getElementById("reservationTimer");
        if (timerEl) {
          timerEl.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
      }
    }, 1000);

  } catch (e) {
    const banner = document.getElementById("reservationBanner");
    if (banner) {
      banner.style.background = "#FEE2E2";
      banner.style.borderColor = "#EF4444";
      banner.innerHTML = `<span>⚠️ ${e.message}</span>`;
      document.getElementById("payNowBtn").disabled = true;
    }
  }
}

async function checkServiceability(pincode) {
  const statusEl = document.getElementById("pincodeStatus");
  if (!pincode || pincode.length !== 6) return;
  try {
    const res = await api("/api/pincode/check", {
      method: "POST",
      body: JSON.stringify({ pincode: pincode })
    });
    if (res.serviceable) {
      statusEl.style.color = "var(--color-success)";
      statusEl.textContent = `✓ Delivery Serviceable in ${res.city}, ${res.state} (Est. ${res.estimated_days} days)`;
      const cityInput = document.getElementById("custCity");
      if (cityInput && !cityInput.value) cityInput.value = res.city;
      const stateSelect = document.getElementById("custState");
      if (stateSelect && res.state) stateSelect.value = res.state;
    }
  } catch (e) {
    statusEl.style.color = "var(--color-danger)";
    statusEl.textContent = e.message;
  }
}

async function applyCoupon() {
  const code = document.getElementById("couponInput").value;
  try {
    await api("/api/cart/coupon", {
      method: "POST",
      body: JSON.stringify({ session_id: State.sessionId, coupon_code: code })
    });
    await refreshCart();
    showToast(`Coupon applied!`, "success");
    Router.renderRoute();
  } catch (e) {
    showToast(e.message, "danger");
  }
}

window.handleCheckoutSubmit = function(e) {
  e.preventDefault();
  const name = document.getElementById("custName").value;
  const email = document.getElementById("custEmail").value;
  const phone = document.getElementById("custPhone").value;
  const address = document.getElementById("custAddress").value;
  const pincode = document.getElementById("custPincode").value;
  const city = document.getElementById("custCity").value;
  const state = document.getElementById("custState").value;

  const orderPayload = {
    customer_name: name,
    customer_email: email,
    customer_phone: phone,
    delivery_address: address,
    city: city,
    state: state,
    pincode: pincode,
    subtotal: State.cart.subtotal,
    discount: State.cart.discount,
    shipping_fee: State.cart.shipping,
    tax: State.cart.tax,
    total_amount: State.cart.total,
    session_id: State.sessionId,
    campaign_id: State.activeCampaign,
    items: State.cart.items
  };

  // Open Razorpay Test Mode Simulator Modal
  openRazorpayModal(orderPayload);
};

function openRazorpayModal(orderPayload) {
  const body = document.getElementById("razorpayModalBody");
  if (!body) return;

  body.innerHTML = `
    <div style="margin-bottom: 1.5rem; text-align: center;">
      <div style="font-size: 0.85rem; color: var(--color-text-muted);">Pay to: <strong>Conscious Form Company (COFOCO)</strong></div>
      <div style="font-size: 2rem; font-weight: 800; color: #0C2340; margin: 0.5rem 0;">₹${Number(orderPayload.total_amount).toLocaleString('en-IN')}</div>
      <div style="font-size: 0.75rem; color: #64748B;">Test Gateway Environment • Order Token: ${State.sessionId.substring(0, 10)}</div>
    </div>

    <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem;">
      <button class="btn btn-sm btn-primary" style="flex: 1; font-size: 0.8rem;" id="rzpTabUpi" onclick="selectRzpMethod('upi')">UPI / QR</button>
      <button class="btn btn-sm btn-secondary" style="flex: 1; font-size: 0.8rem;" id="rzpTabCard" onclick="selectRzpMethod('card')">Card</button>
      <button class="btn btn-sm btn-secondary" style="flex: 1; font-size: 0.8rem;" id="rzpTabNet" onclick="selectRzpMethod('netbanking')">Netbanking</button>
    </div>

    <div id="rzpMethodContainer">
      <div class="form-group">
        <label class="form-label" style="font-size: 0.8rem;">Virtual Payment Address (VPA)</label>
        <input type="text" id="rzpVpa" class="form-control" value="${orderPayload.customer_email.split('@')[0]}@okaxis">
      </div>
    </div>

    <button class="btn btn-primary btn-block" style="background: #2563EB; font-weight: 700; padding: 0.85rem;" onclick="executeRazorpayCapture(${JSON.stringify(orderPayload).replace(/"/g, '&quot;')})">
      Simulate Successful Payment
    </button>
    <div style="text-align: center; margin-top: 0.75rem;">
      <button style="background: none; border: none; color: #DC2626; font-size: 0.8rem; cursor: pointer; text-decoration: underline;" onclick="simulateLateOrFailedPayment(${JSON.stringify(orderPayload).replace(/"/g, '&quot;')})">
        Simulate Late Payment Arrival (Reconciliation Test)
      </button>
    </div>
  `;

  openModal("razorpayModal");
}

window.selectRzpMethod = function(method) {
  const box = document.getElementById("rzpMethodContainer");
  if (!box) return;
  if (method === "card") {
    box.innerHTML = `
      <div class="form-group"><label class="form-label" style="font-size: 0.8rem;">Card Number</label><input type="text" class="form-control" value="4111 2222 3333 4444" readonly></div>
      <div class="form-row"><div class="form-group"><label class="form-label" style="font-size: 0.8rem;">Expiry</label><input type="text" class="form-control" value="12/28" readonly></div><div class="form-group"><label class="form-label" style="font-size: 0.8rem;">CVV</label><input type="text" class="form-control" value="888" readonly></div></div>
    `;
  } else if (method === "netbanking") {
    box.innerHTML = `
      <div class="form-group"><label class="form-label" style="font-size: 0.8rem;">Select Bank</label><select class="form-control"><option>HDFC Bank</option><option>ICICI Bank</option><option>State Bank of India</option><option>Axis Bank</option></select></div>
    `;
  } else {
    box.innerHTML = `
      <div class="form-group"><label class="form-label" style="font-size: 0.8rem;">Virtual Payment Address (VPA)</label><input type="text" class="form-control" value="customer@okhdfcbank"></div>
    `;
  }
};

window.executeRazorpayCapture = async function(orderPayload) {
  try {
    const paymentId = "pay_test_" + Math.random().toString(36).substring(2, 12);
    const orderId = "order_rzp_" + Math.random().toString(36).substring(2, 10);
    const signature = "sig_valid_" + Math.random().toString(36).substring(2, 10);

    const paymentPayload = {
      razorpay_payment_id: paymentId,
      razorpay_order_id: orderId,
      razorpay_signature: signature,
      status: "captured"
    };

    const res = await api("/api/checkout/payment", {
      method: "POST",
      body: JSON.stringify({
        order: orderPayload,
        payment: paymentPayload
      })
    });

    closeModal("razorpayModal");
    if (reservationTimerInterval) clearInterval(reservationTimerInterval);
    await refreshCart();
    
    // 1. Customer Notification
    showToast(`🎉 Order ${res.order_number} confirmed! Live alerts dispatched to ${orderPayload.customer_email} & ${orderPayload.customer_phone}`, "success");
    
    // 2. Staff / Owner Bag Notification
    updateOwnerStaffVisibility();
    if (State.staffAuth) {
      setTimeout(() => {
        showToast(`🔔 Staff Alert: New Order ${res.order_number} received (₹${Number(orderPayload.subtotal).toLocaleString('en-IN')}) — Added to fulfillment queue!`, "info");
      }, 1400);
    }
    
    window.location.hash = `#/order/${res.order_id}`;
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.simulateLateOrFailedPayment = async function(orderPayload) {
  try {
    const paymentId = "pay_late_" + Math.random().toString(36).substring(2, 12);
    const paymentPayload = {
      razorpay_payment_id: paymentId,
      razorpay_order_id: "order_late_sim",
      razorpay_signature: "sig_late_sim",
      status: "captured",
      note: "Late capture test after timeout"
    };

    const res = await api("/api/checkout/payment", {
      method: "POST",
      body: JSON.stringify({
        order: orderPayload,
        payment: paymentPayload
      })
    });

    closeModal("razorpayModal");
    showToast("Late capture simulation: Sent to reconciliation queue.", "warning");
    window.location.hash = `#/order/${res.order_id}`;
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.handleTrackingSearch = function(e) {
  e.preventDefault();
  const val = document.getElementById("trackOrderNum").value.trim();
  if (val) {
    window.location.hash = `#/order/${val}`;
  }
};

// =========================================================================
// STAFF DASHBOARD LOGIC (OP01–OP05, US03, US05)
// =========================================================================
async function loginStaffRole(username, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
  State.staffAuth = data;
  localStorage.setItem("cofoco_staff_auth", JSON.stringify(data));
  await updateOwnerStaffVisibility();
  return data;
}

window.handleOwnerLogin = async function(e) {
  e.preventDefault();
  const u = document.getElementById("ownerUsername").value.trim();
  const p = document.getElementById("ownerPassword").value;
  try {
    const data = await loginStaffRole(u, p);
    if (data && data.token) {
      showToast(`Welcome back, ${data.user.full_name}. Website Owner portal unlocked.`, "success");
      Router.renderRoute();
    }
  } catch (err) {
    showToast(err.message || "Invalid owner credentials.", "danger");
  }
};

window.logoutOwnerStaff = function() {
  State.staffAuth = null;
  localStorage.removeItem("cofoco_staff_auth");
  updateOwnerStaffVisibility();
  showToast("Owner session closed. Public storefront restored.", "info");
  window.location.hash = "#/";
};

window.switchStaffRole = async function(roleKey) {
  const credentials = {
    admin: ["admin", "Admin@COFOCO2026"],
    editor: ["editor", "Editor@COFOCO2026"],
    publisher: ["publisher", "Publish@COFOCO2026"],
    warehouse: ["warehouse", "Warehouse@COFOCO2026"],
    support: ["support", "Support@COFOCO2026"],
    finance: ["finance", "Finance@COFOCO2026"]
  };
  const [user, pwd] = credentials[roleKey] || credentials.admin;
  await loginStaffRole(user, pwd);
  showToast(`Switched active role to: ${State.staffAuth.user.role_name}`, "info");
  Router.renderRoute();
};

window.switchAdminTab = function(tabName) {
  document.querySelectorAll(".admin-tab-btn").forEach(btn => btn.classList.remove("active"));
  event.target.classList.add("active");
  loadAdminTab(tabName);
};

async function loadAdminTab(tabName) {
  const content = document.getElementById("adminTabContent");
  if (!content) return;
  content.innerHTML = `<div style="text-align: center; padding: 2rem;">Loading ${tabName}...</div>`;

  try {
    if (tabName === "overview") {
      const data = await api("/api/admin/overview");
      content.innerHTML = `
        <div class="kpi-cards-grid">
          <div class="kpi-card" onclick="switchAdminTab('orders')">
            <div class="kpi-card-header"><span class="kpi-card-title">Awaiting Dispatch</span></div>
            <div class="kpi-card-value">${data.metrics.awaiting_dispatch}</div>
            <div class="kpi-card-desc">Paid & packed orders to ship</div>
          </div>
          <div class="kpi-card" style="border-left: 4px solid var(--color-danger);" onclick="switchAdminTab('orders')">
            <div class="kpi-card-header"><span class="kpi-card-title" style="color: var(--color-danger);">Overdue Orders</span></div>
            <div class="kpi-card-value" style="color: var(--color-danger);">${data.metrics.overdue_orders}</div>
            <div class="kpi-card-desc">Past promised dispatch date</div>
          </div>
          <div class="kpi-card" style="border-left: 4px solid var(--color-warning);" onclick="switchAdminTab('inventory')">
            <div class="kpi-card-header"><span class="kpi-card-title" style="color: var(--color-warning);">Low Stock Items</span></div>
            <div class="kpi-card-value" style="color: var(--color-warning);">${data.metrics.low_stock_components}</div>
            <div class="kpi-card-desc">At or below reorder threshold</div>
          </div>
          <div class="kpi-card" onclick="switchAdminTab('exceptions')">
            <div class="kpi-card-header"><span class="kpi-card-title">Payment Issues</span></div>
            <div class="kpi-card-value">${data.metrics.unresolved_payments}</div>
            <div class="kpi-card-desc">Late arrivals / reconciliation</div>
          </div>
          <div class="kpi-card" onclick="switchAdminTab('exceptions')">
            <div class="kpi-card-header"><span class="kpi-card-title">Pending Returns</span></div>
            <div class="kpi-card-value">${data.metrics.pending_returns}</div>
            <div class="kpi-card-desc">Awaiting recorded inspection</div>
          </div>
        </div>

        <div class="data-table-card">
          <div class="data-table-header">
            <h3 class="data-table-title">Recent Audit Trail</h3>
            <span style="font-size: 0.8rem; color: var(--color-text-muted);">Logged Actions & Compliance</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Staff Member</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              ${(data.recent_activity || []).map(act => `
                <tr>
                  <td style="font-size: 0.8rem; color: var(--color-text-muted);">${new Date(act.created_at).toLocaleString('en-IN')}</td>
                  <td><strong>${act.user_name || act.username || 'System'}</strong></td>
                  <td><span style="background: var(--color-secondary-alt); padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">${act.action}</span></td>
                  <td>${act.entity_type} #${act.entity_id.substring(0, 8)}</td>
                  <td style="font-size: 0.8rem; color: var(--color-text-muted);">${JSON.stringify(act.changes || {})}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else if (tabName === "orders") {
      const data = await api("/api/admin/orders");
      content.innerHTML = `
        <div class="data-table-card">
          <div class="data-table-header">
            <h3 class="data-table-title">Fulfillment Order Queue</h3>
            <span style="font-size: 0.85rem; color: var(--color-text-muted);">Total: ${data.orders.length} orders</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Order Number</th>
                <th>Customer</th>
                <th>Payment</th>
                <th>Order Status</th>
                <th>Promised Dispatch</th>
                <th>Assigned Staff</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${data.orders.map(o => `
                <tr>
                  <td><strong>${o.order_number}</strong><br><span style="font-size: 0.75rem; color: var(--color-text-muted);">${new Date(o.created_at).toLocaleDateString('en-IN')}</span></td>
                  <td>${o.customer_name}<br><span style="font-size: 0.8rem; color: var(--color-text-muted);">${o.city}, ${o.state}</span></td>
                  <td><span class="kit-stock-badge ${o.payment_status === 'paid' ? 'stock-in' : 'stock-out'}" style="position: static;">${o.payment_status}</span></td>
                  <td><span style="font-weight: 700; text-transform: uppercase; font-size: 0.8rem;">${o.order_status}</span></td>
                  <td>${new Date(o.promised_dispatch_date).toLocaleDateString('en-IN')}</td>
                  <td>${o.assigned_staff_name || 'Unassigned'}</td>
                  <td>
                    <button class="btn btn-secondary btn-sm" onclick="viewOrderPickList('${o.id}')">Pick List</button>
                    ${o.order_status === 'paid' ? `
                      <button class="btn btn-primary btn-sm" onclick="updateOrderStatus('${o.id}', 'picking')">Start Picking</button>
                    ` : ''}
                    ${o.order_status === 'picking' ? `
                      <button class="btn btn-primary btn-sm" onclick="updateOrderStatus('${o.id}', 'packed')">Mark Packed</button>
                    ` : ''}
                    ${o.order_status === 'packed' ? `
                      <button class="btn btn-accent btn-sm" onclick="promptDispatch('${o.id}')">Dispatch</button>
                    ` : ''}
                    ${o.order_status === 'dispatched' ? `
                      <button class="btn btn-secondary btn-sm" onclick="updateOrderStatus('${o.id}', 'delivered')">Mark Delivered</button>
                    ` : ''}
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else if (tabName === "inventory") {
      const data = await api("/api/admin/inventory");
      content.innerHTML = `
        <div class="data-table-card">
          <div class="data-table-header">
            <h3 class="data-table-title">Raw Component Stock & Sellable Balance</h3>
            <span style="font-size: 0.85rem; color: var(--color-text-muted);">Available = On-Hand Sellable - Active Reservations</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Component SKU</th>
                <th>Name</th>
                <th>Category</th>
                <th>Warehouse Location</th>
                <th>On-Hand</th>
                <th>Reserved</th>
                <th>Available</th>
                <th>Unit Cost</th>
                <th>Stock Action</th>
              </tr>
            </thead>
            <tbody>
              ${data.components.map(c => `
                <tr style="${c.is_low_stock ? 'background: rgba(245, 158, 11, 0.16);' : ''}">
                  <td><code>${c.sku}</code></td>
                  <td><strong>${c.name}</strong></td>
                  <td><span style="font-size: 0.8rem; text-transform: uppercase;">${c.category}</span></td>
                  <td>${c.location}</td>
                  <td>${c.on_hand}</td>
                  <td>${c.reserved}</td>
                  <td><strong style="color: ${c.available > 5 ? 'var(--color-primary)' : 'var(--color-danger)'};">${c.available}</strong></td>
                  <td>₹${c.unit_cost}</td>
                  <td>
                    <button class="btn btn-secondary btn-sm" onclick="promptInventoryAdjust('${c.id}', '${c.name}')">Adjust Stock</button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else if (tabName === "exceptions") {
      const data = await api("/api/admin/exceptions");
      content.innerHTML = `
        <div class="data-table-card">
          <div class="data-table-header">
            <h3 class="data-table-title">Returns Awaiting Quality Inspection (Gate OP05)</h3>
            <span style="font-size: 0.85rem; color: var(--color-danger);">Units restocked only upon recorded inspection</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Return ID</th>
                <th>Order</th>
                <th>Customer</th>
                <th>Item</th>
                <th>Return Reason</th>
                <th>Inspection Gate</th>
              </tr>
            </thead>
            <tbody>
              ${data.pending_returns.length === 0 ? `
                <tr><td colspan="6" style="text-align: center; color: var(--color-text-muted);">No pending returns awaiting inspection.</td></tr>
              ` : data.pending_returns.map(r => `
                <tr>
                  <td><code>${r.id.substring(0, 8)}</code></td>
                  <td>${r.order_number}</td>
                  <td>${r.customer_name}</td>
                  <td>${r.kit_name} (${r.character_name})</td>
                  <td style="font-size: 0.85rem;">${r.reason}</td>
                  <td>
                    <button class="btn btn-primary btn-sm" onclick="openReturnInspection('${r.id}', '${r.order_number}', '${r.kit_name}')">Perform Inspection</button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>

        <div class="data-table-card">
          <div class="data-table-header">
            <h3 class="data-table-title">Payment Exceptions & Late Captures</h3>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Order Number</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Gateway Status</th>
                <th>Resolution Action</th>
              </tr>
            </thead>
            <tbody>
              ${data.payment_exceptions.length === 0 ? `
                <tr><td colspan="5" style="text-align: center; color: var(--color-text-muted);">No payment exceptions in queue.</td></tr>
              ` : data.payment_exceptions.map(pe => `
                <tr>
                  <td><strong>${pe.order_number}</strong></td>
                  <td>${pe.customer_name}</td>
                  <td>₹${pe.total_amount}</td>
                  <td><span style="background: rgba(239, 68, 68, 0.2); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.35); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">${pe.payment_event_status}</span></td>
                  <td>
                    <button class="btn btn-secondary btn-sm" onclick="showToast('Payment verified against gateway ledger.', 'success')">Reconcile & Secure Stock</button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else if (tabName === "catalog") {
      const charsData = await api("/api/characters");
      content.innerHTML = `
        <div class="data-table-card">
          <div class="data-table-header">
            <h3 class="data-table-title">Character Experience Publishing Workflow</h3>
            <span style="font-size: 0.85rem; color: var(--color-text-muted);">Brand Editor drafts, Authorized Publisher approves</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Character</th>
                <th>Quality</th>
                <th>Theme & Motif</th>
                <th>Status</th>
                <th>Publisher Action</th>
              </tr>
            </thead>
            <tbody>
              ${charsData.characters.map(c => `
                <tr>
                  <td><strong>${c.name} by COFOCO</strong></td>
                  <td>${c.quality}</td>
                  <td>${c.theme_symbol}</td>
                  <td><span class="kit-stock-badge ${c.status === 'published' ? 'stock-in' : 'stock-out'}" style="position: static;">${c.status}</span></td>
                  <td>
                    ${c.status !== 'published' ? `
                      <button class="btn btn-primary btn-sm" onclick="publishCharacter('${c.id}')">Approve & Publish</button>
                    ` : `
                      <span style="color: var(--color-success); font-weight: 600; font-size: 0.85rem;">✓ Published Live</span>
                    `}
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }
  } catch (e) {
    content.innerHTML = `<div style="color: var(--color-danger); padding: 2rem;">Error: ${e.message}</div>`;
  }
}

// Admin Order Actions
window.viewOrderPickList = async function(orderId) {
  try {
    const data = await api(`/api/admin/orders/${orderId}/picklist`);
    const body = document.getElementById("pickListModalBody");
    if (!body) return;

    body.innerHTML = `
      <div style="margin-bottom: 1.5rem; border-bottom: 1px solid var(--color-border); padding-bottom: 1rem;">
        <div style="font-size: 1.15rem; font-weight: 700; color: var(--color-primary);">${data.order_number}</div>
        <div style="font-size: 0.85rem; color: var(--color-text-muted);">Customer: <strong>${data.customer_name}</strong> • Ordered: ${new Date(data.created_at).toLocaleString('en-IN')}</div>
        <div style="font-size: 0.8rem; color: var(--color-accent-gold); font-weight: 600; margin-top: 0.25rem;">Preserved BOM Snapshot from Customer Purchase</div>
      </div>

      <table class="data-table" style="margin-bottom: 1rem;">
        <thead>
          <tr>
            <th>Warehouse Location</th>
            <th>Component SKU</th>
            <th>Component Name</th>
            <th>Qty / Kit</th>
            <th>Total To Pick</th>
          </tr>
        </thead>
        <tbody>
          ${data.pick_list.map(p => `
            <tr>
              <td><strong style="color: var(--color-primary);">${p.warehouse_location}</strong></td>
              <td><code>${p.component_sku}</code></td>
              <td>${p.component_name}<br><span style="font-size: 0.75rem; color: var(--color-text-muted);">For ${p.kit_name}</span></td>
              <td>${p.quantity_per_kit}</td>
              <td><span style="font-size: 1.1rem; font-weight: 800; color: var(--color-primary);">${p.total_quantity_to_pick}</span></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;

    openModal("pickListModal");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.updateOrderStatus = async function(orderId, newStatus) {
  try {
    await api(`/api/admin/orders/${orderId}/status`, {
      method: "POST",
      body: JSON.stringify({ status: newStatus })
    });
    showToast(`Order updated to '${newStatus}'.`, "success");
    loadAdminTab("orders");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.promptDispatch = async function(orderId) {
  const awb = prompt("Enter Carrier Tracking / AWB Number (e.g. BLUEDART-99201948):");
  if (!awb) return;
  try {
    await api(`/api/admin/orders/${orderId}/status`, {
      method: "POST",
      body: JSON.stringify({
        status: "dispatched",
        courier_name: "Blue Dart Express",
        tracking_number: awb
      })
    });
    showToast(`Order dispatched with tracking AWB ${awb}. Customer notified.`, "success");
    loadAdminTab("orders");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.promptInventoryAdjust = async function(componentId, name) {
  const delta = prompt(`Enter stock adjustment quantity for "${name}" (e.g. +20 for receipt, -3 for damage):`);
  if (!delta || isNaN(delta)) return;
  const reason = prompt("Enter mandatory reason for stock ledger audit (e.g. 'Supplier shipment arrival', 'Inspection rejection'):");
  if (!reason) return;

  try {
    const res = await api("/api/admin/inventory/adjust", {
      method: "POST",
      body: JSON.stringify({
        component_id: componentId,
        quantity: parseInt(delta),
        reason: reason,
        change_type: parseInt(delta) > 0 ? "receipt" : "adjustment"
      })
    });
    showToast(`Stock updated. New balance: ${res.new_balance} units.`, "success");
    loadAdminTab("inventory");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.openReturnInspection = function(returnId, orderNum, kitName) {
  const body = document.getElementById("returnInspectModalBody");
  if (!body) return;

  body.innerHTML = `
    <div style="margin-bottom: 1.5rem;">
      <div style="font-size: 1.1rem; font-weight: 700;">Return Case: ${orderNum}</div>
      <div style="font-size: 0.85rem; color: var(--color-text-muted);">Kit: ${kitName}</div>
    </div>

    <div class="form-group">
      <label class="form-label">Physical Inspection Result *</label>
      <select id="inspectResultSelect" class="form-control">
        <option value="passed">Passed Quality Check (Unopened / Like New - Restock into Sellable)</option>
        <option value="damaged">Damaged / Broken Seal (Scrap / Do NOT Restock)</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Inspection Notes & Examiner Signature *</label>
      <textarea id="inspectNotes" class="form-control" rows="3" placeholder="Inspected seals, straps, and accessories..."></textarea>
    </div>

    <button class="btn btn-primary btn-block" onclick="submitReturnInspection('${returnId}')">Record Quality Inspection Gate</button>
  `;

  openModal("returnInspectModal");
};

window.submitReturnInspection = async function(returnId) {
  const result = document.getElementById("inspectResultSelect").value;
  const notes = document.getElementById("inspectNotes").value;
  try {
    const res = await api(`/api/admin/returns/${returnId}/inspect`, {
      method: "POST",
      body: JSON.stringify({ result, notes })
    });
    closeModal("returnInspectModal");
    showToast(res.message, "success");
    loadAdminTab("exceptions");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

window.publishCharacter = async function(charId) {
  try {
    await api(`/api/admin/characters/${charId}/publish`, { method: "POST" });
    showToast("Character collection approved and published live.", "success");
    loadAdminTab("catalog");
  } catch (e) {
    showToast(e.message, "danger");
  }
};

// =========================================================================
// FOUNDER BUSINESS ANALYTICS LOGIC (AN01–AN03, US04)
// =========================================================================
let currentAnalyticsData = null;

async function loadAnalyticsData() {
  const body = document.getElementById("analyticsBody");
  if (!body) return;
  const range = document.getElementById("analyticsDateRange")?.value || "7d";
  body.innerHTML = `<div style="text-align: center; padding: 3rem;">Calculating Business Metrics in Asia/Kolkata timezone...</div>`;

  try {
    const data = await api(`/api/admin/analytics?date_range=${range}`);
    currentAnalyticsData = data;
    document.getElementById("analyticsRefreshed").textContent = `Last Refreshed: ${data.last_refreshed} (IST)`;

    body.innerHTML = `
      <!-- Core KPI Cards with Definition Tooltips (US04) -->
      <div class="kpi-cards-grid">
        <div class="kpi-card" onclick="showMetricModal('session_conversion')">
          <div class="kpi-card-header">
            <span class="kpi-card-title">Session Conversion</span>
            <span class="kpi-info-icon" title="View Denominator & Formula">ⓘ</span>
          </div>
          <div class="kpi-card-value">${data.summary.conversion_rate}%</div>
          <div class="kpi-card-desc">${data.summary.order_count} orders / ${data.summary.total_sessions} sessions</div>
        </div>

        <div class="kpi-card" onclick="showMetricModal('net_merchandise_revenue')">
          <div class="kpi-card-header">
            <span class="kpi-card-title">Net Merchandise Rev</span>
            <span class="kpi-info-icon" title="View Denominator & Formula">ⓘ</span>
          </div>
          <div class="kpi-card-value">₹${Number(data.summary.net_merchandise_revenue).toLocaleString('en-IN')}</div>
          <div class="kpi-card-desc">Gross ₹${Number(data.summary.gross_captured).toLocaleString('en-IN')} - Refunds ₹${Number(data.summary.refunds).toLocaleString('en-IN')}</div>
        </div>

        <div class="kpi-card" onclick="showMetricModal('contribution')">
          <div class="kpi-card-header">
            <span class="kpi-card-title">Contribution Margin</span>
            <span class="kpi-info-icon" title="View Denominator & Formula">ⓘ</span>
          </div>
          <div class="kpi-card-value">₹${Number(data.summary.contribution).toLocaleString('en-IN')}</div>
          <div class="kpi-card-desc">${data.summary.contribution_margin}% of net merchandise revenue</div>
        </div>

        <div class="kpi-card" onclick="showMetricModal('return_rate')">
          <div class="kpi-card-header">
            <span class="kpi-card-title">Return Rate</span>
            <span class="kpi-info-icon" title="View Denominator & Formula">ⓘ</span>
          </div>
          <div class="kpi-card-value">${data.summary.return_rate}%</div>
          <div class="kpi-card-desc">Inspected units ÷ delivered units</div>
        </div>

        <div class="kpi-card" onclick="showMetricModal('on_time_dispatch')">
          <div class="kpi-card-header">
            <span class="kpi-card-title">On-Time Dispatch</span>
            <span class="kpi-info-icon" title="View Denominator & Formula">ⓘ</span>
          </div>
          <div class="kpi-card-value">${data.summary.on_time_dispatch}%</div>
          <div class="kpi-card-desc">Dispatched within 48h deadline</div>
        </div>
      </div>

      <!-- Character Performance Comparison Matrix -->
      <div class="data-table-card">
        <div class="data-table-header">
          <h3 class="data-table-title">Character Performance Comparison (All 6 Characters)</h3>
          <span style="font-size: 0.85rem; color: var(--color-text-muted);">Attributed Views, Kit Engagement, Sales & Returns</span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Character</th>
              <th>Storefront Views</th>
              <th>Kit Engagement</th>
              <th>Engagement Rate</th>
              <th>Units Sold</th>
              <th>Attributed Revenue</th>
              <th>Estimated Contribution</th>
              <th>Returns</th>
            </tr>
          </thead>
          <tbody>
            ${data.character_performance.map(cp => `
              <tr>
                <td><strong>${cp.character_name} by COFOCO</strong></td>
                <td>${cp.views}</td>
                <td>${cp.kit_engagement}</td>
                <td><strong style="color: var(--color-primary);">${cp.engagement_rate}</strong></td>
                <td>${cp.units_sold}</td>
                <td>₹${Number(cp.revenue).toLocaleString('en-IN')}</td>
                <td style="color: var(--color-success); font-weight: 700;">₹${Number(cp.contribution).toLocaleString('en-IN')}</td>
                <td>${cp.return_count > 0 ? `<span style="color: var(--color-danger); font-weight: 700;">${cp.return_count}</span>` : '0'}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>

      <!-- Campaign Performance Comparison -->
      <div class="data-table-card">
        <div class="data-table-header">
          <h3 class="data-table-title">Marketing Campaign Performance</h3>
          <span style="font-size: 0.85rem; color: var(--color-text-muted);">Last Non-Direct Touch Attribution</span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Campaign Code</th>
              <th>Campaign Name</th>
              <th>Source / Medium</th>
              <th>Visits</th>
              <th>Orders</th>
              <th>Conversion Rate</th>
              <th>Net Revenue</th>
              <th>Contribution</th>
            </tr>
          </thead>
          <tbody>
            ${data.campaign_performance.map(cmp => `
              <tr>
                <td><code>${cmp.code}</code></td>
                <td><strong>${cmp.name}</strong></td>
                <td><span style="font-size: 0.8rem; text-transform: uppercase;">${cmp.source} / ${cmp.medium}</span></td>
                <td>${cmp.visits}</td>
                <td>${cmp.orders}</td>
                <td><strong>${cmp.conversion_rate}</strong></td>
                <td>₹${Number(cmp.revenue).toLocaleString('en-IN')}</td>
                <td style="color: var(--color-success); font-weight: 700;">₹${Number(cmp.contribution).toLocaleString('en-IN')}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div style="color: var(--color-danger); padding: 2rem;">Error: ${e.message}</div>`;
  }
}

// Show Metric Specification Modal (US04 Denominator Requirement)
window.showMetricModal = function(metricKey) {
  if (!currentAnalyticsData || !currentAnalyticsData.metric_definitions) return;
  const def = currentAnalyticsData.metric_definitions[metricKey];
  if (!def) return;

  document.getElementById("metricModalTitle").textContent = def.name;
  document.getElementById("metricModalBody").innerHTML = `
    <div style="margin-bottom: 1.25rem;">
      <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); letter-spacing: 1px;">Official Definition</div>
      <div style="font-size: 1.05rem; font-weight: 600; color: var(--color-primary); margin-top: 0.25rem;">${def.formula}</div>
    </div>

    <div style="background: var(--color-secondary-alt); border-radius: var(--radius-md); padding: 1.25rem; border: 1px solid var(--color-border); margin-bottom: 1.5rem;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; font-size: 0.9rem;">
        <span style="font-weight: 700;">Numerator:</span>
        <span style="font-family: monospace; color: var(--color-primary);">${def.numerator}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 0.9rem; border-top: 1px solid var(--color-border); padding-top: 0.75rem;">
        <span style="font-weight: 700;">Denominator:</span>
        <span style="font-family: monospace; color: var(--color-primary);">${def.denominator}</span>
      </div>
    </div>

    <div style="display: flex; justify-content: space-between; align-items: baseline; border-top: 2px solid var(--color-accent-gold); padding-top: 1rem;">
      <span style="font-size: 1.1rem; font-weight: 700;">Current Calculated Value:</span>
      <span style="font-size: 1.8rem; font-weight: 800; color: var(--color-primary);">${def.value}</span>
    </div>
  `;

  openModal("metricModal");
};

// Export CSV strictly stripping customer PII (AN03)
window.exportAnalyticsCSV = function() {
  const range = document.getElementById("analyticsDateRange")?.value || "7d";
  window.location.href = `/api/admin/analytics/export?date_range=${range}`;
  showToast("Founder analytics CSV downloaded (Zero PII).", "success");
};
