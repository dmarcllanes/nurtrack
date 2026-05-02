from fasthtml.common import *
from starlette.staticfiles import StaticFiles
from starlette.responses import Response as StarletteResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from supabase import create_client
from dotenv import load_dotenv
import polars as pl
import os
import uuid
import random
from datetime import date as dt_date

load_dotenv()

sb              = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_KEY", ""))
MOM_PASSWORD    = os.getenv("MOM_PASSWORD", "") or os.getenv("WOMAN_PASSWORD", "")
SESSION_SECRET  = os.getenv("SESSION_SECRET", "nurture-secret-change-me")

# ── PWA ───────────────────────────────────────────────────────────────────────

MANIFEST = """{
  "id": "/",
  "name": "Nurture-Track",
  "short_name": "NurtureTrack",
  "description": "Co-Parenting Expense Hub",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#070d19",
  "theme_color": "#00A896",
  "lang": "en",
  "categories": ["finance", "lifestyle"],
  "icons": [
    { "src": "/static/icons/icon-48.png",          "sizes": "48x48",   "type": "image/png" },
    { "src": "/static/icons/icon-72.png",          "sizes": "72x72",   "type": "image/png" },
    { "src": "/static/icons/icon-96.png",          "sizes": "96x96",   "type": "image/png" },
    { "src": "/static/icons/icon-128.png",         "sizes": "128x128", "type": "image/png" },
    { "src": "/static/icons/icon-192.png",         "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/static/icons/icon-256.png",         "sizes": "256x256", "type": "image/png" },
    { "src": "/static/icons/icon-512.png",         "sizes": "512x512", "type": "image/png", "purpose": "any" },
    { "src": "/static/icons/icon-maskable-512.png","sizes": "512x512", "type": "image/png", "purpose": "maskable" },
    { "src": "/static/icons/icon.svg",             "sizes": "any",     "type": "image/svg+xml" }
  ],
  "screenshots": [
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "form_factor": "narrow" }
  ]
}"""

SW_JS = """
const SHELL_CACHE  = 'nurture-shell-v3';
const STATIC_CACHE = 'nurture-static-v3';
const SHELL_URLS   = ['/', '/add', '/add/login', '/review', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(SHELL_CACHE)
      .then(c => c.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  const keep = [SHELL_CACHE, STATIC_CACHE];
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => !keep.includes(k)).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const { pathname } = new URL(e.request.url);

  // Static assets — cache first, then network
  if (pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(e.request).then(cached => cached ||
        fetch(e.request).then(res => {
          caches.open(STATIC_CACHE).then(c => c.put(e.request, res.clone()));
          return res;
        })
      )
    );
    return;
  }

  // Mutations / API — network only
  if (['/submit', '/acknowledge', '/add/login'].includes(pathname)) return;

  // App shell / pages — network first, stale cache fallback
  e.respondWith(
    fetch(e.request)
      .then(res => {
        if (res.ok) caches.open(SHELL_CACHE).then(c => c.put(e.request, res.clone()));
        return res;
      })
      .catch(() =>
        caches.match(e.request).then(r => r || caches.match('/'))
      )
  );
});
"""

# ── Design tokens + CSS ───────────────────────────────────────────────────────

CSS = """
/* ── Tokens ── */
:root {
  --jade:        #00A896;
  --jade-dark:   #007A6E;
  --jade-light:  #00C4B4;
  --jade-dim:    rgba(0,168,150,0.15);
  --jade-glow:   rgba(0,168,150,0.25);
  --bg:          #070d19;
  --surface:     rgba(255,255,255,0.055);
  --surface-hi:  rgba(255,255,255,0.09);
  --border:      rgba(255,255,255,0.08);
  --border-hi:   rgba(0,168,150,0.4);
  --t1:  #ddeef2;
  --t2:  #7a9aad;
  --t3:  #3d5566;
  --r-s: 10px;
  --r-m: 14px;
  --r-l: 18px;
  --r-xl:22px;
  --ease-spring: cubic-bezier(.34,1.56,.64,1);
  --ease-out:    cubic-bezier(.22,1,.36,1);
}

/* ── Reset ── */
*,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }
html { scroll-behavior:smooth; }

/* ── Native feel ── */
*, *::before, *::after {
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
}
input, textarea, select {
  -webkit-touch-callout: default;
  -webkit-user-select: text;
  user-select: text;
}
.btn, label, a, button {
  touch-action: manipulation;
}

/* ── Body + Background ── */
body {
  font-family:'Inter',system-ui,sans-serif;
  background: var(--bg);
  background-image:
    radial-gradient(ellipse at 8%  10%, rgba(0,168,150,.20) 0%, transparent 50%),
    radial-gradient(ellipse at 92% 92%, rgba(0,80, 72, .16) 0%, transparent 50%),
    radial-gradient(ellipse at 55% 0%,  rgba(0,120,110,.10) 0%, transparent 44%),
    radial-gradient(rgba(255,255,255,.018) 1px, transparent 1px);
  background-size: auto,auto,auto, 28px 28px;
  background-attachment: fixed,fixed,fixed,fixed;
  min-height:100vh; color:var(--t1);
  -webkit-font-smoothing:antialiased;
  overflow-x:hidden;
  overscroll-behavior-y: contain;
  -webkit-overflow-scrolling: touch;
}

/* ── Animated bg orbs ── */
body::before,body::after {
  content:''; position:fixed; border-radius:50%;
  filter:blur(100px); z-index:-1; pointer-events:none;
}
body::before {
  width:60vw; height:60vw; top:-15vw; left:-15vw;
  background:radial-gradient(circle, rgba(0,168,150,.10) 0%, transparent 70%);
  animation: orbA 16s ease-in-out infinite;
}
body::after {
  width:70vw; height:70vw; bottom:-20vw; right:-20vw;
  background:radial-gradient(circle, rgba(0,90,80,.09) 0%, transparent 70%);
  animation: orbB 20s ease-in-out infinite;
}
@keyframes orbA { 0%,100%{transform:translate(0,0)scale(1)} 40%{transform:translate(4%,5%)scale(1.06)} 70%{transform:translate(-3%,3%)scale(.94)} }
@keyframes orbB { 0%,100%{transform:translate(0,0)scale(1)} 35%{transform:translate(-5%,-4%)scale(1.08)} 65%{transform:translate(4%,-2%)scale(.93)} }

/* ── Cursor glow ── */
#cursor-glow {
  position:fixed; pointer-events:none; z-index:0;
  width:360px; height:360px; border-radius:50%;
  background:radial-gradient(circle, rgba(0,168,150,.06) 0%, transparent 70%);
  transform:translate(-50%,-50%);
  transition:left .12s ease, top .12s ease;
  display:none;
}
@media(pointer:fine){ #cursor-glow { display:block; } }

/* ── Scrollbar ── */
::-webkit-scrollbar{ width:5px }
::-webkit-scrollbar-track{ background:transparent }
::-webkit-scrollbar-thumb{ background:rgba(0,168,150,.25); border-radius:4px }
::-webkit-scrollbar-thumb:hover{ background:rgba(0,168,150,.45) }

/* ── Layout ── */
.page {
  max-width:480px; margin:0 auto;
  padding: 24px 16px calc(24px + env(safe-area-inset-bottom)) 16px;
  padding-left:  calc(16px + env(safe-area-inset-left));
  padding-right: calc(16px + env(safe-area-inset-right));
}
.page-landing, .lock-wrap {
  padding-bottom: calc(32px + env(safe-area-inset-bottom));
}

/* ── Nav ── */
.nav-wrap { margin-bottom:28px; }
.nav-brand { display:none; }
.nav {
  position:relative; display:flex; gap:0;
  background:rgba(255,255,255,.04);
  border:1px solid var(--border);
  border-radius:var(--r-l); padding:4px;
}
.nav-slider {
  position:absolute; top:4px; left:4px;
  height:calc(100% - 8px);
  background:linear-gradient(135deg, var(--jade), var(--jade-dark));
  border-radius:var(--r-m);
  box-shadow:0 3px 16px var(--jade-glow);
  transition:left .3s var(--ease-spring), width .3s var(--ease-out);
  pointer-events:none; z-index:0;
}
.nav a {
  position:relative; z-index:1; flex:1; text-align:center;
  padding:10px 16px; border-radius:var(--r-m);
  text-decoration:none; font-size:.875rem; font-weight:500;
  color:var(--t2); transition:color .2s;
}
.nav a.active { color:#fff; }
.nav a:not(.active):hover { color:var(--t1); }

/* ── Typography ── */
h1 {
  font-size:1.55rem; font-weight:700; letter-spacing:-.6px;
  background:linear-gradient(130deg, var(--t1) 20%, var(--jade-light) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.subtitle { color:var(--t2); font-size:.875rem; margin-top:4px; margin-bottom:24px; }

/* ── Glass surface (base for all cards) ── */
.glass {
  background:var(--surface);
  backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
  border:1px solid var(--border); border-radius:var(--r-l);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 4px 24px rgba(0,0,0,.25);
  transition:border-color .25s, box-shadow .25s;
}
.glass:hover {
  border-color:rgba(0,168,150,.28);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.09), 0 10px 36px rgba(0,168,150,.10), 0 4px 12px rgba(0,0,0,.3);
}

/* ── Form ── */
.form-wrap {
  padding:24px;
  animation:fadeUp .5s var(--ease-out) backwards;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07),
    0 0 0 1px rgba(0,168,150,.12),
    0 4px 24px rgba(0,0,0,.25);
  animation-name:fadeUp, formGlow;
  animation-duration:.5s, 6s;
  animation-timing-function:var(--ease-out), ease-in-out;
  animation-iteration-count:1, infinite;
  animation-fill-mode:backwards, none;
}
@keyframes formGlow {
  0%,100%{ box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 0 0 1px rgba(0,168,150,.10), 0 4px 24px rgba(0,0,0,.25) }
  50%    { box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 0 0 1px rgba(0,168,150,.28), 0 6px 32px rgba(0,168,150,.10) }
}

/* Float-label fields */
.ff { position:relative; margin-bottom:18px; }
.ff-input {
  width:100%; padding:22px 14px 10px;
  background:rgba(255,255,255,.04); border:1px solid var(--border); border-radius:var(--r-m);
  color:var(--t1); font-size:1rem; outline:none;
  -webkit-appearance:none; appearance:none;
  transition:border-color .25s, box-shadow .25s, background .25s;
}
.ff-input:focus {
  border-color:var(--jade); background:rgba(0,168,150,.04);
  box-shadow:0 0 0 3px rgba(0,168,150,.12), 0 2px 12px rgba(0,168,150,.06);
}
.ff-label {
  position:absolute; top:50%; left:14px; transform:translateY(-50%);
  color:var(--t2); font-size:.92rem; font-weight:400;
  pointer-events:none; transition:all .2s cubic-bezier(.4,0,.2,1);
}
.ff-input:focus ~ .ff-label,
.ff-input:not(:placeholder-shown) ~ .ff-label,
.ff-input:valid ~ .ff-label {
  top:11px; transform:none; font-size:.68rem; font-weight:600;
  color:var(--jade); letter-spacing:.3px;
}
/* Date always floated */
.ff-input[type="date"] ~ .ff-label {
  top:11px; transform:none; font-size:.68rem; font-weight:600; color:var(--jade); letter-spacing:.3px;
}
.ff-input[type="date"] { color:var(--t2); }
.ff-input[type="date"]:focus, .ff-input[type="date"]:valid { color:var(--t1); }

/* Category pills */
.cat-section { margin-bottom:18px; }
.cat-label { font-size:.68rem; font-weight:600; color:var(--jade); letter-spacing:.3px; text-transform:uppercase; margin-bottom:10px; display:block; }
.cat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
.cat-radio { display:none; }
.cat-pill {
  display:flex; flex-direction:column; align-items:center; gap:5px;
  padding:11px 6px; border-radius:var(--r-m);
  background:var(--surface); border:1px solid var(--border);
  cursor:pointer; user-select:none;
  transition:all .2s var(--ease-out);
}
.cat-pill:hover { border-color:rgba(0,168,150,.3); background:var(--surface-hi); }
.cat-pill.selected {
  background:rgba(0,168,150,.12); border-color:var(--jade);
  box-shadow:0 0 0 3px rgba(0,168,150,.1), 0 4px 16px rgba(0,168,150,.12);
  transform:translateY(-1px);
}
.cat-icon { font-size:1.4rem; line-height:1; }
.cat-name { font-size:.73rem; color:var(--t2); font-weight:500; transition:color .2s; }
.cat-pill.selected .cat-name { color:var(--jade); font-weight:600; }

/* Child avatar initial */
.child-avatar {
  width:32px; height:32px; border-radius:50%;
  background:linear-gradient(135deg, rgba(0,168,150,.25), rgba(0,80,72,.2));
  border:1px solid rgba(0,168,150,.3);
  color:var(--jade); font-weight:700; font-size:.95rem;
  display:flex; align-items:center; justify-content:center;
  transition:all .2s;
}
.cat-pill.selected .child-avatar {
  background:var(--jade); color:#fff; border-color:var(--jade);
  box-shadow:0 2px 10px rgba(0,168,150,.4);
}
/* Child tag on cards */
.child-tag {
  display:inline-flex; align-items:center; gap:5px;
  background:rgba(0,168,150,.1); border:1px solid rgba(0,168,150,.22);
  border-radius:20px; padding:2px 8px 2px 4px;
  font-size:.7rem; font-weight:600; color:var(--jade); margin-bottom:4px;
}
.child-tag-dot {
  width:16px; height:16px; border-radius:50%;
  background:linear-gradient(135deg, var(--jade), var(--jade-dark));
  color:#fff; font-size:.62rem; font-weight:700;
  display:flex; align-items:center; justify-content:center;
}

/* Upload drop zone */
.dz {
  position:relative; border:1.5px dashed rgba(0,168,150,.22);
  border-radius:var(--r-m); padding:22px 16px 18px; text-align:center;
  cursor:pointer; overflow:hidden; background:rgba(0,168,150,.02);
  transition:all .25s var(--ease-out);
}
.dz:hover, .dz.dz-on {
  border-color:var(--jade); border-style:solid;
  background:rgba(0,168,150,.06);
  box-shadow:0 0 0 3px rgba(0,168,150,.08);
}
.dz-icon { font-size:1.8rem; display:block; margin-bottom:8px; transition:transform .3s var(--ease-spring); }
.dz:hover .dz-icon, .dz.dz-on .dz-icon { transform:translateY(-4px) scale(1.12); }
.dz-hint { color:var(--t2); font-size:.85rem; }
.dz-link { color:var(--jade); font-weight:600; }
.dz-file { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; }
.dz-preview {
  width:88px; height:88px; object-fit:cover; border-radius:var(--r-s);
  margin:0 auto; border:1px solid var(--border); display:none;
}

/* ── Buttons ── */
.btn {
  display:inline-flex; align-items:center; justify-content:center; gap:8px;
  border:none; cursor:pointer; font-weight:600; position:relative; overflow:hidden;
  transition:box-shadow .25s, transform .15s, opacity .2s;
}
.btn:active { transform:scale(.97); }
.btn-primary {
  width:100%; padding:14px 24px; border-radius:var(--r-m); font-size:.95rem;
  background:linear-gradient(135deg, var(--jade) 0%, var(--jade-dark) 100%);
  color:#fff; box-shadow:0 4px 20px var(--jade-glow);
}
.btn-primary:hover:not(:disabled) { box-shadow:0 6px 28px rgba(0,168,150,.45); transform:translateY(-1px); }
.btn-primary:disabled { opacity:.6; cursor:not-allowed; transform:none; }
.btn-sm {
  padding:7px 14px; border-radius:9px; font-size:.78rem;
  background:rgba(0,168,150,.12); color:var(--jade);
  border:1px solid rgba(0,168,150,.28);
}
.btn-sm:hover { background:rgba(0,168,150,.22); border-color:rgba(0,168,150,.45); box-shadow:0 2px 12px rgba(0,168,150,.2); }

/* Ripple */
.ripple {
  position:absolute; border-radius:50%;
  background:rgba(255,255,255,.22); transform:scale(0);
  animation:ripple .65s linear; pointer-events:none;
}
@keyframes ripple { to { transform:scale(4); opacity:0; } }

/* Spinner */
.spin {
  display:inline-block; width:14px; height:14px; border-radius:50%;
  border:2px solid rgba(255,255,255,.3); border-top-color:#fff;
  animation:spinning .7s linear infinite;
}
@keyframes spinning { to { transform:rotate(360deg); } }

/* ── Expense cards ── */
.expense-card {
  background:var(--surface);
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  border:1px solid var(--border); border-radius:var(--r-l); padding:20px;
  display:flex; gap:18px; align-items:flex-start;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06), 0 2px 12px rgba(0,0,0,.2);
  transition:transform .3s ease, box-shadow .3s, border-color .3s;
  animation:fadeUp .5s var(--ease-out) backwards;
  will-change:transform;
}
.expense-card:hover {
  border-color:rgba(0,168,150,.3);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.09),
    0 12px 36px rgba(0,168,150,.12), 0 4px 12px rgba(0,0,0,.3);
}
.thumb {
  width:68px; height:68px; border-radius:var(--r-m); flex-shrink:0;
  overflow:hidden; border:1px solid var(--border);
}
.thumb img { width:100%; height:100%; object-fit:cover; transition:transform .4s var(--ease-out); }
.expense-card:hover .thumb img { transform:scale(1.08); }
.thumb-ph {
  width:68px; height:68px; border-radius:var(--r-m); flex-shrink:0;
  background:linear-gradient(135deg, rgba(0,168,150,.08), rgba(0,60,55,.05));
  border:1px dashed rgba(0,168,150,.2);
  display:flex; align-items:center; justify-content:center; font-size:1.5rem;
  transition:transform .3s;
}
.expense-card:hover .thumb-ph { transform:scale(1.06); }
.card-body { flex:1; min-width:0; }
.card-amount { font-size:1.25rem; font-weight:700; color:var(--jade); line-height:1.2; letter-spacing:-.3px; }
.card-meta { font-size:.77rem; color:var(--t2); margin-top:4px; }
.card-actions { margin-top:10px; display:flex; flex-wrap:wrap; gap:6px; align-items:center; }

/* ── Badges ── */
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:.72rem; font-weight:600; margin-top:6px; }
.badge-p { background:rgba(255,160,0,.10); color:#ffb84d; border:1px solid rgba(255,160,0,.22); animation:badgePulse 3s ease-in-out infinite; }
.badge-a { background:rgba(0,168,150,.10); color:var(--jade); border:1px solid rgba(0,168,150,.25); }
@keyframes badgePulse {
  0%,100%{ box-shadow:0 0 0 0 rgba(255,160,0,0) }
  50%    { box-shadow:0 0 0 5px rgba(255,160,0,.07) }
}

/* ── Stats bar ── */
/* ── Dashboard ── */
.dash { display:flex; flex-direction:column; gap:16px; margin-bottom:28px; }
.kpi-row { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-bottom:14px; }
@media(min-width:560px){ .kpi-row{ grid-template-columns:repeat(4,1fr); } }
.kpi-card {
  background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
  border-radius:14px; padding:14px 16px; position:relative; overflow:hidden;
  transition:transform .22s, box-shadow .22s; cursor:default;
}
.kpi-card:hover { transform:translateY(-2px); box-shadow:0 8px 22px rgba(0,0,0,.28); }
.kpi-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(90deg,#00C4B4,#00A896);
}
.kpi-icon { font-size:1rem; margin-bottom:5px; display:block; }
.kpi-val { font-size:1.35rem; font-weight:800; letter-spacing:-.5px; line-height:1; }
.kpi-val.teal  { color:#00C4B4; }
.kpi-val.amber { color:#ffb84d; }
.kpi-val.blue  { color:#00C4E8; }
.kpi-val.green { color:#00A896; }
.kpi-label { font-size:.6rem; color:var(--t2); margin-top:5px; text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
.kpi-sub { font-size:.65rem; color:#00A896; font-weight:600; margin-top:2px; }
.chart-row { display:grid; grid-template-columns:1fr; gap:16px; }
@media(min-width:640px){ .chart-row-2 { grid-template-columns:1fr 1fr; } }
.chart-card {
  background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.07);
  border-radius:18px; padding:20px 22px;
}
.chart-title {
  font-size:.67rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase;
  color:#00A896; margin-bottom:16px; display:flex; align-items:center; gap:7px;
}
.chart-title span { opacity:.5; font-weight:400; font-size:.9em; text-transform:none; letter-spacing:0; }
/* ── Tabs ── */
.tab-bar {
  display:flex; gap:6px; padding:5px;
  background:rgba(9,14,28,.92); border:1px solid rgba(255,255,255,.08);
  border-radius:14px; margin-bottom:20px;
  position:sticky; top:0; z-index:90;
  backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
}
.tab-btn {
  flex:1; padding:9px 10px; border-radius:10px; font-size:.78rem; font-weight:700;
  color:var(--t2); background:transparent; border:none; cursor:pointer;
  transition:all .22s; letter-spacing:.02em; white-space:nowrap;
}
.tab-btn:hover { color:var(--t1); background:rgba(255,255,255,.05); }
.tab-btn.active {
  background:linear-gradient(135deg,rgba(0,196,180,.2),rgba(0,168,150,.12));
  color:#00C4B4; border:1px solid rgba(0,196,180,.3);
  box-shadow:0 2px 12px rgba(0,168,150,.15);
}
.tab-panel { display:none; }
.tab-panel.active { display:block; animation:fadeUp .3s var(--ease-out); }
.chart-card canvas { min-height:200px; }
.stats-bar { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; margin-bottom:24px; }
.stat-item {
  padding:16px 18px; cursor:default;
  transition:transform .25s var(--ease-spring), box-shadow .25s, border-color .25s;
  animation:fadeUp .5s var(--ease-out) backwards;
}
.stat-item:hover {
  transform:translateY(-3px);
  border-color:rgba(0,168,150,.32);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.09), 0 8px 28px rgba(0,168,150,.13);
}
.stat-icon { font-size:1.3rem; margin-bottom:8px; display:block; }
.stat-label { font-size:.68rem; color:var(--t2); text-transform:uppercase; letter-spacing:.5px; margin-bottom:6px; font-weight:600; }
.stat-value { font-size:1.1rem; font-weight:700; font-variant-numeric:tabular-nums; letter-spacing:-.3px; }
.stat-total { color:var(--jade); text-shadow:0 0 16px rgba(0,168,150,.35); }

/* ── Cards grid ── */
.expense-grid { display:grid; grid-template-columns:1fr; gap:16px; }

/* ── Empty state ── */
.empty { text-align:center; padding:64px 0; color:var(--t2); font-size:.9rem; animation:fadeUp .5s var(--ease-out); }
.empty-icon { font-size:2.8rem; margin-bottom:14px; filter:grayscale(.3); }

/* ── Toast ── */
.toast {
  position:fixed; bottom:28px; left:50%; transform:translateX(-50%);
  background:linear-gradient(135deg, var(--jade), var(--jade-dark));
  color:#fff; padding:13px 26px; border-radius:var(--r-m);
  font-size:.9rem; font-weight:600;
  box-shadow:0 8px 32px rgba(0,168,150,.4), 0 2px 8px rgba(0,0,0,.3);
  animation:toastIn .35s var(--ease-spring), toastOut .4s ease 2.4s forwards;
  z-index:999; white-space:nowrap;
}
@keyframes toastIn  { from{opacity:0;transform:translate(-50%,16px)} to{opacity:1;transform:translate(-50%,0)} }
@keyframes toastOut { to{opacity:0;transform:translate(-50%,8px)} }

/* ── Animations ── */
@keyframes fadeUp { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }

/* ── Tablet 640px ── */
@media(min-width:640px){
  .page { max-width:768px; padding:28px 24px; }
  h1 { font-size:1.75rem; }
  .form-wrap { max-width:560px; margin:0 auto; }
  .expense-grid { grid-template-columns:1fr 1fr; gap:16px; }
  .expense-card { padding:18px; gap:16px; }
  .thumb, .thumb-ph { width:74px; height:74px; }
  .cat-grid { grid-template-columns:repeat(6,1fr); }
  .chart-row-2 { grid-template-columns:1fr 1fr; }
  .kpi-row { grid-template-columns:repeat(4,1fr); }
  .view-hero-review { flex-wrap:nowrap; }
}

/* ── Desktop 1024px ── */
@media(min-width:1024px){
  .page { max-width:1100px; padding:0 40px 56px; }
  h1 { font-size:1.9rem; }
  .nav-wrap {
    position:sticky; top:0; z-index:100;
    display:flex; align-items:center; justify-content:space-between;
    margin:0 -40px 40px; padding:16px 40px;
    background:rgba(7,13,25,.85);
    backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px);
    border-bottom:1px solid var(--border);
  }
  .nav-brand {
    display:flex; align-items:center; gap:10px;
    font-size:1.05rem; font-weight:700; color:var(--jade); letter-spacing:-.3px;
  }
  .nav-brand::before {
    content:''; width:8px; height:8px; border-radius:50%; background:var(--jade);
    box-shadow:0 0 10px rgba(0,168,150,.9), 0 0 22px rgba(0,168,150,.4);
    animation:dotPulse 2.5s ease-in-out infinite;
  }
  @keyframes dotPulse {
    0%,100%{ box-shadow:0 0 8px rgba(0,168,150,.8), 0 0 18px rgba(0,168,150,.35) }
    50%    { box-shadow:0 0 14px rgba(0,168,150,1),  0 0 30px rgba(0,168,150,.6)  }
  }
  .nav { gap:6px; margin-bottom:0; }
  .nav a { flex:none; padding:9px 22px; }
  .form-wrap { max-width:560px; }
  .expense-grid { grid-template-columns:repeat(3,1fr); gap:20px; }
  .expense-card { padding:20px; gap:16px; }
  .thumb, .thumb-ph { width:80px; height:80px; }
  .card-amount { font-size:1.3rem; }
  .stat-value { font-size:1.25rem; }
  .stat-item { padding:18px 22px; }
}

/* ── Large 1400px ── */
@media(min-width:1400px){
  .page { max-width:1320px; padding:0 56px 64px; }
  .nav-wrap { margin:0 -56px 44px; padding-left:56px; padding-right:56px; }
  .expense-grid { grid-template-columns:repeat(4,1fr); gap:22px; }
}

/* ── Custom date picker ── */
.dp-wrap { position:relative; margin-bottom:18px; }
.dp-trigger {
  width:100%; padding:14px 16px;
  background:rgba(255,255,255,.04); border:1px solid var(--border); border-radius:var(--r-m);
  cursor:pointer; display:flex; align-items:center; gap:10px;
  color:var(--t1); font-size:1rem; text-align:left;
  transition:border-color .25s, background .25s, box-shadow .25s;
}
.dp-trigger:hover, .dp-trigger.dp-open {
  border-color:var(--jade); background:rgba(0,168,150,.04);
  box-shadow:0 0 0 3px rgba(0,168,150,.12);
}
.dp-label { font-size:.68rem; font-weight:600; color:var(--jade); letter-spacing:.3px; margin-bottom:2px; display:block; }
.dp-display { flex:1; font-weight:500; font-size:.95rem; }
.dp-caret { color:var(--t2); font-size:.8rem; transition:transform .25s var(--ease-spring); margin-left:auto; }
.dp-trigger.dp-open .dp-caret { transform:rotate(180deg); }
.dp-panel {
  position:absolute; top:calc(100% + 8px); left:0; right:0; z-index:300;
  background:rgba(7,13,26,.98); backdrop-filter:blur(28px); -webkit-backdrop-filter:blur(28px);
  border:1px solid rgba(0,168,150,.22); border-radius:var(--r-l); padding:14px;
  box-shadow:0 16px 48px rgba(0,0,0,.55), 0 0 0 1px rgba(0,168,150,.06);
  opacity:0; transform:translateY(-10px) scale(.97); pointer-events:none;
  transition:opacity .25s, transform .28s var(--ease-spring);
}
.dp-panel.dp-open { opacity:1; transform:translateY(0) scale(1); pointer-events:all; }
.dp-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--border);
}
.dp-month-yr { font-size:.92rem; font-weight:700; color:var(--t1); }
.dp-nav {
  width:32px; height:32px; border-radius:var(--r-s);
  background:rgba(255,255,255,.05); border:1px solid var(--border);
  color:var(--t2); cursor:pointer; font-size:1.1rem;
  display:flex; align-items:center; justify-content:center;
  transition:background .2s, color .2s, border-color .2s;
}
.dp-nav:hover { background:rgba(0,168,150,.14); color:var(--jade); border-color:rgba(0,168,150,.3); }
.dp-weekdays {
  display:grid; grid-template-columns:repeat(7,1fr); gap:2px; margin-bottom:6px;
}
.dp-wday { text-align:center; font-size:.65rem; font-weight:600; color:var(--t3); padding:4px 0; text-transform:uppercase; letter-spacing:.3px; }
.dp-days { display:grid; grid-template-columns:repeat(7,1fr); gap:3px; }
.dp-day {
  aspect-ratio:1; display:flex; align-items:center; justify-content:center;
  border-radius:var(--r-s); font-size:.82rem; cursor:pointer; color:var(--t2);
  transition:background .15s, color .15s, transform .15s var(--ease-spring);
  user-select:none;
}
.dp-day:hover:not(.dp-empty) { background:rgba(0,168,150,.14); color:var(--jade); transform:scale(1.1); }
.dp-empty { pointer-events:none; }
.dp-today {
  color:var(--jade); font-weight:700;
  box-shadow:inset 0 0 0 1.5px rgba(0,168,150,.55);
}
.dp-selected {
  background:linear-gradient(135deg,var(--jade),var(--jade-dark)) !important;
  color:#fff !important; font-weight:700;
  box-shadow:0 2px 12px var(--jade-glow) !important;
  transform:scale(1.08);
}
.dp-selected:hover { transform:scale(1.08) !important; }

/* ── Submit success overlay ── */
.success-overlay {
  position:fixed; inset:0; z-index:900;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  background:rgba(5,10,20,.93); backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px);
  padding:32px; opacity:0; pointer-events:none; transition:opacity .4s;
}
.success-overlay.show { opacity:1; pointer-events:all; }
.confetti { position:absolute; inset:0; overflow:hidden; pointer-events:none; }
.cf { position:absolute; top:-12px; border-radius:2px; animation:cfFall linear forwards; opacity:0; }
@keyframes cfFall {
  0%   { transform:translateY(0) rotate(0deg) scaleX(1);   opacity:1; }
  80%  { opacity:1; }
  100% { transform:translateY(105vh) rotate(760deg) scaleX(.4); opacity:0; }
}
.s-check-ring {
  width:88px; height:88px; border-radius:50%;
  background:linear-gradient(135deg,var(--jade),var(--jade-dark));
  display:flex; align-items:center; justify-content:center;
  margin-bottom:28px; font-size:2.5rem; color:#fff;
  box-shadow:0 0 0 18px rgba(0,168,150,.12), 0 0 0 36px rgba(0,168,150,.06);
  animation:sPop .55s var(--ease-spring) .1s both;
}
@keyframes sPop {
  0%  { transform:scale(0) rotate(-30deg); opacity:0; }
  65% { transform:scale(1.14) rotate(6deg); }
  100%{ transform:scale(1)   rotate(0deg); opacity:1; }
}
.s-title {
  font-size:1.8rem; font-weight:800; letter-spacing:-.6px; text-align:center;
  background:linear-gradient(130deg,var(--t1) 20%,var(--jade-light) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  margin-bottom:8px; animation:fadeUp .45s var(--ease-out) .25s both;
}
.s-sub {
  color:var(--t2); font-size:.9rem; margin-bottom:36px; text-align:center;
  animation:fadeUp .45s var(--ease-out) .35s both;
}
.s-done {
  padding:13px 36px; border-radius:var(--r-m);
  background:linear-gradient(135deg,var(--jade),var(--jade-dark));
  color:#fff; font-weight:700; font-size:.95rem; border:none; cursor:pointer;
  box-shadow:0 4px 22px var(--jade-glow);
  animation:fadeUp .45s var(--ease-out) .45s both;
  transition:transform .2s, box-shadow .2s;
}
.s-done:hover { transform:translateY(-2px); box-shadow:0 7px 30px rgba(0,168,150,.55); }

/* ── Print: handled via popup window, no page-level print styles needed ── */

/* ── Install prompt banner ── */
.install-banner {
  position:fixed; z-index:2000;
  bottom: calc(20px + env(safe-area-inset-bottom));
  left:50%; transform:translateX(-50%);
  width:calc(100% - 32px); max-width:380px;
  display:none; align-items:center; gap:12px;
  padding:14px 16px; border-radius:var(--r-l);
  background:rgba(7,13,25,.96);
  backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px);
  border:1px solid rgba(0,168,150,.28);
  box-shadow:0 8px 40px rgba(0,0,0,.55), 0 0 0 1px rgba(0,168,150,.10);
  animation:toastIn .4s var(--ease-spring);
}
.install-banner.visible { display:flex; }
.install-app-icon {
  width:44px; height:44px; border-radius:11px; flex-shrink:0;
  overflow:hidden; border:1px solid rgba(0,168,150,.25);
}
.install-app-icon img { width:100%; height:100%; object-fit:cover; }
.install-text { flex:1; min-width:0; }
.install-title { font-size:.88rem; font-weight:700; color:var(--t1); }
.install-sub { font-size:.75rem; color:var(--t2); margin-top:2px; }
.install-btn {
  padding:7px 14px; border-radius:8px; font-size:.8rem; font-weight:700;
  background:linear-gradient(135deg, var(--jade), var(--jade-dark));
  color:#fff; border:none; cursor:pointer; flex-shrink:0;
  transition:box-shadow .2s, transform .15s;
}
.install-btn:hover { box-shadow:0 4px 16px var(--jade-glow); transform:translateY(-1px); }
.install-dismiss {
  width:26px; height:26px; border-radius:50%; border:none; cursor:pointer;
  background:rgba(255,255,255,.06); color:var(--t2); font-size:.95rem;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
  transition:background .2s, color .2s;
}
.install-dismiss:hover { background:rgba(255,255,255,.12); color:var(--t1); }
/* iOS tip bar */
.ios-tip {
  position:fixed; z-index:2000;
  bottom: calc(20px + env(safe-area-inset-bottom));
  left:50%; transform:translateX(-50%);
  width:calc(100% - 32px); max-width:360px;
  display:none; align-items:center; gap:10px;
  padding:13px 16px; border-radius:var(--r-l);
  background:rgba(7,13,25,.96);
  backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px);
  border:1px solid rgba(0,168,150,.22);
  box-shadow:0 8px 32px rgba(0,0,0,.5);
  font-size:.82rem; color:var(--t2);
  animation:toastIn .4s var(--ease-spring);
}
.ios-tip.visible { display:flex; }
.ios-tip strong { color:var(--t1); }
.ios-tip-close {
  margin-left:auto; width:24px; height:24px; border-radius:50%;
  border:none; cursor:pointer; background:rgba(255,255,255,.06);
  color:var(--t2); font-size:.85rem; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
}
.ios-tip-arrow {
  position:absolute; bottom:-8px; left:50%; transform:translateX(-50%);
  width:0; height:0;
  border-left:8px solid transparent; border-right:8px solid transparent;
  border-top:8px solid rgba(7,13,25,.96);
}

/* ── Detail sheet / modal ── */
.detail-overlay {
  position:fixed; inset:0; z-index:500;
  background:rgba(4,8,18,.72);
  backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
  opacity:0; pointer-events:none; transition:opacity .3s;
}
.detail-overlay.open { opacity:1; pointer-events:all; }
.detail-sheet {
  position:fixed; z-index:501;
  left:0; right:0; bottom:0;
  max-height:88vh; overflow-y:auto;
  background:rgba(9,15,30,.98);
  backdrop-filter:blur(28px); -webkit-backdrop-filter:blur(28px);
  border:1px solid rgba(0,100,200,.18);
  border-bottom:none; border-radius:22px 22px 0 0;
  padding-bottom:calc(20px + env(safe-area-inset-bottom));
  transform:translateY(102%);
  transition:transform .4s var(--ease-spring);
  will-change:transform;
  pointer-events:none;
}
.detail-sheet.open { transform:translateY(0); pointer-events:all; }
.sheet-handle {
  width:38px; height:4px; border-radius:2px;
  background:rgba(255,255,255,.14); margin:12px auto 0;
}
@media(min-width:640px){
  .detail-sheet {
    left:50%; right:auto; bottom:auto; top:50%;
    transform:translate(-50%,-50%) scale(.93);
    border-radius:var(--r-xl); border:1px solid rgba(0,100,200,.22);
    width:90%; max-width:480px; max-height:86vh;
    opacity:0; transition:transform .35s var(--ease-spring), opacity .3s;
  }
  .detail-sheet.open { transform:translate(-50%,-50%) scale(1); opacity:1; }
  .sheet-handle { display:none; }
}
.sheet-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 20px 12px;
  border-bottom:1px solid var(--border);
  position:sticky; top:0; background:rgba(9,15,30,.98); z-index:1;
}
.sheet-label {
  font-size:.72rem; font-weight:700; color:#0099CC;
  text-transform:uppercase; letter-spacing:.6px;
}
.sheet-close {
  width:28px; height:28px; border-radius:50%; border:none; cursor:pointer;
  background:rgba(255,255,255,.07); color:var(--t2); font-size:1.05rem;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
  transition:background .2s, color .2s;
}
.sheet-close:hover { background:rgba(255,255,255,.13); color:var(--t1); }
.sheet-receipt-wrap {
  width:100%; overflow:hidden; max-height:220px; display:none;
  border-bottom:1px solid var(--border);
}
.sheet-receipt-wrap.has-img { display:block; }
.sheet-receipt-wrap img { width:100%; height:220px; object-fit:cover; display:block; }
.sheet-receipt-ph {
  width:100%; height:120px;
  background:linear-gradient(135deg,rgba(0,80,180,.08),rgba(0,140,210,.04));
  display:flex; align-items:center; justify-content:center; font-size:2.8rem;
}
.sheet-body { padding:20px; }
.sheet-child-row { margin-bottom:10px; }
.sheet-amount {
  font-size:2.4rem; font-weight:800; letter-spacing:-.9px;
  color:#00C4E8; line-height:1; margin-bottom:16px;
  text-shadow:0 0 24px rgba(0,153,204,.3);
}
.sheet-info-row {
  display:flex; align-items:center; gap:10px;
  padding:11px 0; border-bottom:1px solid var(--border);
  font-size:.88rem;
}
.sheet-info-row:last-child { border-bottom:none; }
.sheet-info-icon { font-size:1.05rem; width:22px; text-align:center; flex-shrink:0; }
.sheet-info-content { display:flex; flex-direction:column; gap:1px; }
.sheet-info-label { font-size:.67rem; font-weight:600; color:var(--t3); text-transform:uppercase; letter-spacing:.4px; }
.sheet-info-val { font-size:.92rem; font-weight:600; color:var(--t1); }
.sheet-actions { padding:16px 20px 4px; display:flex; gap:10px; flex-direction:column; }
/* View button on cards */
.btn-view {
  padding:7px 14px; border-radius:9px; font-size:.78rem;
  background:rgba(0,153,204,.1); color:#00C4E8;
  border:1px solid rgba(0,153,204,.25);
}
.btn-view:hover { background:rgba(0,153,204,.2); border-color:rgba(0,153,204,.45); }
.btn-export {
  padding:7px 14px; border-radius:9px; font-size:.78rem;
  background:rgba(0,168,150,.08); color:#00A896;
  border:1px solid rgba(0,168,150,.22); text-decoration:none; display:inline-block;
}
.btn-export:hover { background:rgba(0,168,150,.18); border-color:rgba(0,168,150,.4); }
/* ── Comments ── */
.comments-section { border-top:1px solid rgba(255,255,255,.07); padding:16px 20px 20px; }
.comments-heading { font-size:.72rem; font-weight:700; color:var(--jade); letter-spacing:.07em; text-transform:uppercase; margin-bottom:12px; }
.comments-list { display:flex; flex-direction:column; gap:8px; max-height:180px; overflow-y:auto; margin-bottom:12px; }
.comment-bubble { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); border-radius:10px; padding:9px 12px; }
.comment-meta { display:flex; justify-content:space-between; align-items:center; margin-bottom:3px; }
.comment-author { font-size:.7rem; font-weight:700; }
.comment-author.mom { color:#ff80c0; }
.comment-author.dad { color:#00C4E8; }
.comment-time { font-size:.62rem; color:#4a6a7a; }
.comment-body { font-size:.83rem; color:var(--t1); line-height:1.45; }
.comment-empty { font-size:.78rem; color:#4a6a7a; text-align:center; padding:6px 0; }
.author-toggle { display:flex; gap:6px; margin-bottom:8px; }
.author-btn {
  padding:5px 16px; border-radius:20px; font-size:.74rem; font-weight:600;
  background:rgba(255,255,255,.04); color:#7a9aad;
  border:1px solid rgba(255,255,255,.1); cursor:pointer; transition:all .18s;
}
.author-btn.active { background:rgba(0,168,150,.14); color:#00A896; border-color:rgba(0,168,150,.38); }
.comment-input {
  width:100%; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.1);
  border-radius:10px; color:var(--t1); font-size:.83rem; padding:9px 12px;
  resize:none; outline:none; font-family:inherit; transition:border-color .2s; display:block; margin-bottom:8px;
}
.comment-input:focus { border-color:rgba(0,168,150,.4); }
.comment-send { width:100%; }
/* ── Card explanation as title ── */
.card-comment { margin-top:8px; }
.card-comment-label { display:none; }
.card-comment-text {
  font-size:.95rem; font-weight:700; line-height:1.35;
  background:linear-gradient(90deg,#e0f7f5,#a8edea);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}

/* ── Landing page ── */
.page-landing {
  min-height:100vh; display:flex; flex-direction:column;
  align-items:center; justify-content:center; padding:32px 20px;
  gap:0;
}
.landing-logo {
  text-align:center; margin-bottom:52px;
  animation:fadeUp .5s var(--ease-out) backwards;
}
.landing-wordmark {
  display:inline-flex; align-items:center; gap:10px;
  font-size:1.6rem; font-weight:800; letter-spacing:-.5px;
  background:linear-gradient(130deg, var(--t1) 30%, var(--jade-light) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.landing-wordmark::before {
  content:''; display:block; width:10px; height:10px; border-radius:50%;
  background:var(--jade); flex-shrink:0;
  box-shadow:0 0 12px rgba(0,168,150,.9), 0 0 28px rgba(0,168,150,.4);
  animation:dotPulse 2.5s ease-in-out infinite;
}
.landing-tag {
  margin-top:10px; color:var(--t2); font-size:.88rem; letter-spacing:.2px;
}
.portal-grid {
  display:grid; grid-template-columns:1fr 1fr; gap:16px;
  width:100%; max-width:540px;
  animation:fadeUp .5s var(--ease-out) .12s backwards;
}
@media(max-width:500px){
  .portal-grid { grid-template-columns:1fr; max-width:340px; }
}
.portal-card {
  position:relative; overflow:hidden;
  text-decoration:none; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:0;
  padding:36px 20px 32px;
  border-radius:var(--r-xl);
  backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
  transition:transform .35s var(--ease-spring), box-shadow .35s, border-color .3s;
  cursor:pointer;
}
.portal-card:hover { transform:translateY(-8px) scale(1.015); }
.portal-card::before {
  content:''; position:absolute; inset:0; border-radius:inherit;
  opacity:0; transition:opacity .35s;
}
.portal-card:hover::before { opacity:1; }
/* Mom's portal */
.portal-mom {
  background:rgba(0,168,150,.06);
  border:1px solid rgba(0,168,150,.18);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 4px 24px rgba(0,0,0,.25);
}
.portal-mom::before {
  background:linear-gradient(135deg, rgba(0,168,150,.10) 0%, rgba(0,210,180,.05) 100%);
}
.portal-mom:hover {
  border-color:rgba(0,210,180,.45);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.1),
    0 24px 60px rgba(0,168,150,.22), 0 8px 24px rgba(0,0,0,.3);
}
/* Dad's portal */
.portal-dad {
  background:rgba(0,80,180,.06);
  border:1px solid rgba(0,100,200,.18);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 4px 24px rgba(0,0,0,.25);
}
.portal-dad::before {
  background:linear-gradient(135deg, rgba(0,80,200,.10) 0%, rgba(0,153,204,.05) 100%);
}
.portal-dad:hover {
  border-color:rgba(0,153,204,.45);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.1),
    0 24px 60px rgba(0,100,200,.22), 0 8px 24px rgba(0,0,0,.3);
}
.portal-icon-wrap {
  width:66px; height:66px; border-radius:50%;
  display:flex; align-items:center; justify-content:center;
  font-size:1.9rem; margin-bottom:18px; flex-shrink:0;
  transition:transform .35s var(--ease-spring), box-shadow .3s;
}
.portal-card:hover .portal-icon-wrap { transform:scale(1.12) translateY(-3px); }
.portal-icon-mom {
  background:rgba(0,168,150,.15); border:1px solid rgba(0,168,150,.3);
  box-shadow:0 0 22px rgba(0,168,150,.18);
}
.portal-card:hover .portal-icon-mom { box-shadow:0 0 32px rgba(0,168,150,.35); }
.portal-icon-dad {
  background:rgba(0,100,200,.13); border:1px solid rgba(0,100,200,.28);
  box-shadow:0 0 22px rgba(0,100,200,.15);
}
.portal-card:hover .portal-icon-dad { box-shadow:0 0 32px rgba(0,100,200,.32); }
.portal-title {
  font-size:1.05rem; font-weight:700; color:var(--t1);
  letter-spacing:-.3px; margin-bottom:7px; text-align:center;
}
.portal-desc {
  font-size:.78rem; color:var(--t2); text-align:center;
  line-height:1.55; margin-bottom:20px; max-width:160px;
}
.portal-arrow {
  font-size:1.1rem; color:var(--t3);
  transition:transform .25s var(--ease-spring), color .25s;
}
.portal-mom:hover .portal-arrow { color:var(--jade); transform:translateX(5px); }
.portal-dad:hover   .portal-arrow { color:#0099CC;     transform:translateX(5px); }

/* ── Lock / Auth screen ── */
.lock-wrap {
  min-height:100vh; display:flex; flex-direction:column;
  align-items:center; justify-content:center; padding:24px 16px;
}
.lock-card {
  width:100%; max-width:380px; padding:40px 32px; text-align:center;
  animation:fadeUp .45s var(--ease-out) backwards;
}
.lock-icon-wrap {
  width:72px; height:72px; border-radius:50%; margin:0 auto 24px;
  background:rgba(0,168,150,.12); border:1px solid rgba(0,168,150,.25);
  display:flex; align-items:center; justify-content:center; font-size:2rem;
  animation:lockPulse 3s ease-in-out infinite;
}
@keyframes lockPulse {
  0%,100%{ box-shadow:0 0 20px rgba(0,168,150,.15) }
  50%    { box-shadow:0 0 38px rgba(0,168,150,.38) }
}
.lock-title {
  font-size:1.3rem; font-weight:700; letter-spacing:-.4px; margin-bottom:7px;
  background:linear-gradient(130deg, var(--t1) 20%, var(--jade-light) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.lock-subtitle { color:var(--t2); font-size:.85rem; margin-bottom:28px; line-height:1.55; }
.lock-error {
  color:#ff7b7b; font-size:.82rem; margin-bottom:14px; text-align:left;
  padding:9px 14px; border-radius:var(--r-s);
  background:rgba(255,80,80,.08); border:1px solid rgba(255,80,80,.22);
  animation:fadeUp .3s var(--ease-out) backwards;
}
.lock-home {
  display:inline-flex; align-items:center; gap:6px; margin-top:22px;
  color:var(--t3); font-size:.8rem; text-decoration:none;
  transition:color .2s;
}
.lock-home:hover { color:var(--t2); }

/* ── Back nav ── */
.back-nav {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:28px;
}
.back-btn {
  display:inline-flex; align-items:center; gap:6px;
  padding:8px 14px; border-radius:var(--r-m);
  background:rgba(255,255,255,.05); border:1px solid var(--border);
  color:var(--t2); text-decoration:none; font-size:.83rem; font-weight:500;
  transition:all .2s; line-height:1;
}
.back-btn:hover {
  background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.14);
  color:var(--t1); transform:translateX(-2px);
}
.back-chip {
  font-size:.73rem; font-weight:600; color:var(--t3);
  padding:5px 12px; border-radius:20px;
  background:rgba(255,255,255,.03); border:1px solid var(--border);
}

/* ════════════════════════════════════════════════════════════════
   VIEW IDENTITIES
   ════════════════════════════════════════════════════════════════ */

/* ── Add View (Mom's) — warm jade-mint ── */
body[data-view="add"]::before {
  background:radial-gradient(circle, rgba(0,210,180,.13) 0%, transparent 70%);
}
body[data-view="add"]::after {
  background:radial-gradient(circle, rgba(180,60,90,.06) 0%, transparent 70%);
}
body[data-view="add"] h1 {
  background:linear-gradient(130deg, var(--t1) 15%, #7FFFE4 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
/* Add view hero strip */
.view-hero-add {
  display:flex; align-items:center; gap:14px;
  margin-bottom:22px; padding:14px 18px; border-radius:var(--r-l);
  background:linear-gradient(135deg, rgba(0,168,150,.09) 0%, rgba(0,210,180,.04) 100%);
  border:1px solid rgba(0,168,150,.18);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06);
  animation:fadeUp .4s var(--ease-out) .05s backwards;
}
.vha-emoji { font-size:1.9rem; line-height:1; flex-shrink:0; }
.vha-greeting { font-size:.99rem; font-weight:700; color:var(--t1); }
.vha-date { font-size:.78rem; color:var(--jade); font-weight:500; margin-top:3px; letter-spacing:.2px; }
.vha-children {
  margin-left:auto; display:flex; gap:6px; flex-shrink:0;
}
.vha-child-dot {
  width:28px; height:28px; border-radius:50%;
  background:linear-gradient(135deg, rgba(0,168,150,.25), rgba(0,80,72,.2));
  border:1px solid rgba(0,168,150,.3);
  color:var(--jade); font-weight:700; font-size:.82rem;
  display:flex; align-items:center; justify-content:center;
}

/* ── Review View (Dad's) — cool electric-blue/cyan ── */
body[data-view="review"] {
  --r-blue:  #0099CC;
  --r-cyan:  #00C4E8;
  --r-glow:  rgba(0,153,204,.25);
  background-image:
    radial-gradient(ellipse at 8%  10%, rgba(0,80,200,.15) 0%, transparent 50%),
    radial-gradient(ellipse at 92% 92%, rgba(0,40,110,.13) 0%, transparent 50%),
    radial-gradient(ellipse at 55% 0%,  rgba(0,140,210,.10) 0%, transparent 44%),
    radial-gradient(rgba(255,255,255,.018) 1px, transparent 1px);
}
body[data-view="review"]::before {
  background:radial-gradient(circle, rgba(0,80,200,.09) 0%, transparent 70%);
}
body[data-view="review"]::after {
  background:radial-gradient(circle, rgba(0,40,130,.09) 0%, transparent 70%);
}
body[data-view="review"] h1 {
  background:linear-gradient(130deg, var(--t1) 20%, #00D4FF 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
body[data-view="review"] .nav-slider {
  background:linear-gradient(135deg, #0099CC, #005D9A);
  box-shadow:0 3px 16px rgba(0,100,200,.35);
}
body[data-view="review"] .nav-brand { color:#0099CC; }
body[data-view="review"] .nav-brand::before {
  background:#0099CC;
  box-shadow:0 0 10px rgba(0,153,204,.9), 0 0 22px rgba(0,100,200,.4);
  animation:dotPulseBlue 2.5s ease-in-out infinite;
}
@keyframes dotPulseBlue {
  0%,100%{ box-shadow:0 0 8px rgba(0,153,204,.8),  0 0 18px rgba(0,100,200,.35) }
  50%    { box-shadow:0 0 14px rgba(0,153,204,1),   0 0 30px rgba(0,100,200,.6)  }
}
body[data-view="review"] #cursor-glow {
  background:radial-gradient(circle, rgba(0,100,200,.06) 0%, transparent 70%);
}
body[data-view="review"] .stat-total {
  color:var(--r-cyan);
  text-shadow:0 0 16px rgba(0,153,204,.4);
}
body[data-view="review"] .stat-item:hover {
  border-color:rgba(0,153,204,.32);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.09), 0 8px 28px rgba(0,100,200,.15);
}
body[data-view="review"] .expense-card:hover {
  border-color:rgba(0,153,204,.32);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.09),
    0 12px 36px rgba(0,100,200,.14), 0 4px 12px rgba(0,0,0,.3);
}
body[data-view="review"] .btn-sm {
  background:rgba(0,153,204,.12); color:var(--r-cyan); border-color:rgba(0,153,204,.28);
}
body[data-view="review"] .btn-sm:hover {
  background:rgba(0,153,204,.22); border-color:rgba(0,153,204,.45);
  box-shadow:0 2px 12px rgba(0,100,200,.2);
}
body[data-view="review"] .child-tag {
  background:rgba(0,153,204,.10); border-color:rgba(0,153,204,.22); color:var(--r-cyan);
}
body[data-view="review"] .child-tag-dot {
  background:linear-gradient(135deg, #0099CC, #005D9A);
}
/* Review hero dashboard strip */
.view-hero-review {
  display:grid; grid-template-columns:1fr auto 1fr auto 1fr;
  align-items:center; gap:0;
  margin-bottom:20px; padding:14px 16px; border-radius:var(--r-l);
  background:linear-gradient(135deg, rgba(0,80,200,.09) 0%, rgba(0,140,210,.04) 100%);
  border:1px solid rgba(0,100,200,.16);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06);
  animation:fadeUp .4s var(--ease-out) .05s backwards;
}
.vhr-stat { text-align:center; }
.vhr-title {
  font-size:.64rem; font-weight:700; color:#0099CC;
  text-transform:uppercase; letter-spacing:.6px; margin-bottom:5px;
}
.vhr-count { font-size:1.45rem; font-weight:700; color:var(--t1); letter-spacing:-.5px; line-height:1; }
.vhr-sub { font-size:.73rem; color:var(--t2); margin-top:4px; }
.vhr-divider { width:1px; height:44px; background:rgba(0,100,200,.18); flex-shrink:0; }
"""

# ── Interactive JS ────────────────────────────────────────────────────────────

JS = Script("""
document.addEventListener('DOMContentLoaded', () => {

  // ── Nav slider ─────────────────────────────────────────
  const slider  = document.querySelector('.nav-slider');
  const navEl   = document.querySelector('.nav');
  function syncSlider() {
    const a = navEl?.querySelector('a.active');
    if (!slider || !a) return;
    slider.style.left  = a.offsetLeft + 'px';
    slider.style.width = a.offsetWidth + 'px';
  }
  requestAnimationFrame(() => requestAnimationFrame(syncSlider));
  window.addEventListener('resize', syncSlider);

  // ── Cursor glow ─────────────────────────────────────────
  const glow = document.getElementById('cursor-glow');
  if (glow) {
    document.addEventListener('mousemove', e => {
      glow.style.left = e.clientX + 'px';
      glow.style.top  = e.clientY + 'px';
    });
  }

  // ── Stat counter animation ─────────────────────────────
  document.querySelectorAll('.stat-value').forEach(el => {
    const raw    = el.textContent.replace(/[$,\\s]/g, '');
    const target = parseFloat(raw);
    if (isNaN(target)) return;
    const t0  = performance.now();
    const dur = 1100;
    const fmt = v => '$' + v.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
    el.textContent = fmt(0);
    const tick = now => {
      const p = Math.min((now - t0) / dur, 1);
      el.textContent = fmt((1 - Math.pow(1 - p, 4)) * target);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  // ── Pill selection (child + category) ─────────────────
  document.querySelectorAll('.cat-grid').forEach(grid => {
    const labels = Array.from(grid.querySelectorAll('label.cat-pill'));
    const inputs = Array.from(grid.querySelectorAll('input.cat-radio'));

    // Mark first as selected on load
    if (labels.length) labels[0].classList.add('selected');

    labels.forEach((label, idx) => {
      label.addEventListener('click', () => {
        labels.forEach(l => l.classList.remove('selected'));
        label.classList.add('selected');
        if (inputs[idx]) inputs[idx].checked = true;
      });
    });
  });

  // ── Card stagger ────────────────────────────────────────
  document.querySelectorAll('.expense-card').forEach((c, i) => c.style.animationDelay = i * 60 + 'ms');
  document.querySelectorAll('.stat-item').forEach((c, i)    => c.style.animationDelay = i * 50 + 'ms');

  // ── Card 3-D tilt (pointer device) ─────────────────────
  if (window.matchMedia('(pointer:fine)').matches) {
    document.querySelectorAll('.portal-card').forEach(card => {
      card.addEventListener('mousemove', e => {
        const r = card.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width  - .5) * 10;
        const y = ((e.clientY - r.top)  / r.height - .5) * 10;
        card.style.transition = 'transform .08s ease, box-shadow .3s, border-color .3s';
        card.style.transform  = `translateY(-8px) scale(1.015) perspective(600px) rotateX(${-y}deg) rotateY(${x}deg)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transition = 'transform .45s var(--ease-spring,ease), box-shadow .3s, border-color .3s';
        card.style.transform  = '';
      });
    });
    document.querySelectorAll('.expense-card').forEach(card => {
      let leaving = false;
      card.addEventListener('mousemove', e => {
        leaving = false;
        const r = card.getBoundingClientRect();
        const x = ((e.clientX - r.left)  / r.width  - .5) * 9;
        const y = ((e.clientY - r.top)   / r.height - .5) * 9;
        card.style.transition = 'transform .08s ease, box-shadow .3s, border-color .3s';
        card.style.transform  = `perspective(700px) rotateX(${-y}deg) rotateY(${x}deg) translateY(-5px)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transition = 'transform .5s ease, box-shadow .3s, border-color .3s';
        card.style.transform  = '';
      });
    });
  }

  // ── Ripple ──────────────────────────────────────────────
  document.querySelectorAll('.btn-primary, .btn-sm').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const r    = this.getBoundingClientRect();
      const size = Math.max(r.width, r.height);
      const el   = document.createElement('span');
      el.className = 'ripple';
      el.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-r.left-size/2}px;top:${e.clientY-r.top-size/2}px`;
      this.appendChild(el);
      setTimeout(() => el.remove(), 700);
    });
  });

  // ── Upload drop zone ────────────────────────────────────
  const zone     = document.getElementById('drop-zone');
  const fileIn   = document.getElementById('receipt-input');
  const dzPrev   = document.getElementById('dz-preview');
  const dzIcon   = document.getElementById('dz-icon');
  const dzHint   = document.getElementById('dz-hint');

  function showPreview(file) {
    if (!file?.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = e => {
      if (dzPrev) { dzPrev.src = e.target.result; dzPrev.style.display = 'block'; }
      if (dzIcon) dzIcon.style.display = 'none';
      if (dzHint) dzHint.innerHTML = '<span style="color:var(--jade);font-weight:600;font-size:.82rem">' + file.name + '</span>';
    };
    reader.readAsDataURL(file);
  }
  if (zone) {
    ['dragenter','dragover'].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('dz-on'); }));
    zone.addEventListener('dragleave', e => { if (!zone.contains(e.relatedTarget)) zone.classList.remove('dz-on'); });
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('dz-on');
      const f = e.dataTransfer?.files[0];
      if (f && fileIn) { const dt = new DataTransfer(); dt.items.add(f); fileIn.files = dt.files; showPreview(f); }
    });
  }
  if (fileIn) fileIn.addEventListener('change', () => showPreview(fileIn.files[0]));

  // ── Form submit loading ─────────────────────────────────
  document.querySelectorAll('form[action="/submit"]').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('.btn-primary');
      if (btn) { btn.innerHTML = '<span class="spin"></span> Saving…'; btn.disabled = true; }
    });
  });

  // ── Custom date picker ──────────────────────────────────
  const dpTrigger = document.getElementById('dp-trigger');
  const dpPanel   = document.getElementById('dp-panel');
  const dpHidden  = document.getElementById('dp-hidden');
  const dpDisplay = document.getElementById('dp-display');
  const dpDays    = document.getElementById('dp-days');
  const dpMonthYr = document.getElementById('dp-month-yr');

  const DP_MONTHS = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December'];

  let dpCur = { year:0, month:0 };
  let dpSel = null;

  function dpFmtDisplay(d) {
    return d.toLocaleDateString('en-US',{weekday:'short',month:'long',day:'numeric',year:'numeric'});
  }
  function dpFmtValue(d) {
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }
  function dpRender() {
    if (!dpDays) return;
    const today    = new Date();
    const firstDay = new Date(dpCur.year, dpCur.month, 1).getDay();
    const last     = new Date(dpCur.year, dpCur.month+1, 0).getDate();
    if (dpMonthYr) dpMonthYr.textContent = `${DP_MONTHS[dpCur.month]} ${dpCur.year}`;
    let html = '';
    for (let i=0;i<firstDay;i++) html += '<span class="dp-day dp-empty"></span>';
    for (let d=1;d<=last;d++) {
      const isToday = d===today.getDate() && dpCur.month===today.getMonth() && dpCur.year===today.getFullYear();
      const isSel   = dpSel && d===dpSel.getDate() && dpCur.month===dpSel.getMonth() && dpCur.year===dpSel.getFullYear();
      const cls = ['dp-day', isToday?'dp-today':'', isSel?'dp-selected':''].filter(Boolean).join(' ');
      html += `<span class="${cls}" data-d="${d}">${d}</span>`;
    }
    dpDays.innerHTML = html;
  }
  function dpInit() {
    const raw = dpHidden?.value;
    const d   = raw ? new Date(raw+'T00:00:00') : new Date();
    dpSel = d; dpCur = {year:d.getFullYear(), month:d.getMonth()};
    if (dpDisplay) dpDisplay.textContent = dpFmtDisplay(d);
    dpRender();
  }
  dpTrigger?.addEventListener('click', e => {
    e.stopPropagation();
    const open = dpPanel.classList.toggle('dp-open');
    dpTrigger.classList.toggle('dp-open', open);
  });
  dpDays?.addEventListener('click', e => {
    const day = e.target.dataset.d;
    if (!day) return;
    dpSel = new Date(dpCur.year, dpCur.month, +day);
    if (dpHidden)  dpHidden.value = dpFmtValue(dpSel);
    if (dpDisplay) dpDisplay.textContent = dpFmtDisplay(dpSel);
    dpRender();
    dpPanel.classList.remove('dp-open');
    dpTrigger.classList.remove('dp-open');
  });
  document.getElementById('dp-prev')?.addEventListener('click', e => {
    e.stopPropagation();
    if (--dpCur.month < 0) { dpCur.month=11; dpCur.year--; }
    dpRender();
  });
  document.getElementById('dp-next')?.addEventListener('click', e => {
    e.stopPropagation();
    if (++dpCur.month > 11) { dpCur.month=0; dpCur.year++; }
    dpRender();
  });
  document.addEventListener('click', e => {
    if (!dpTrigger?.contains(e.target) && !dpPanel?.contains(e.target)) {
      dpPanel?.classList.remove('dp-open');
      dpTrigger?.classList.remove('dp-open');
    }
  });
  dpInit();

  // ── Submit success overlay ───────────────────────────────
  const successEl = document.getElementById('success-overlay');
  if (successEl) {
    requestAnimationFrame(() => requestAnimationFrame(() => successEl.classList.add('show')));
    const t = setTimeout(() => dismissSuccess(), 5000);
    function dismissSuccess() {
      clearTimeout(t);
      successEl.style.opacity = '0';
      setTimeout(() => { successEl.remove(); history.replaceState({},'','/add'); }, 420);
    }
    document.getElementById('success-done')?.addEventListener('click', dismissSuccess);
  }

  // ── PWA install prompt ──────────────────────────────────
  const isIOS       = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isStandalone = ('standalone' in navigator && navigator.standalone) ||
                       window.matchMedia('(display-mode: standalone)').matches;
  const dismissed   = sessionStorage.getItem('install-dismissed');

  if (!isStandalone && !dismissed) {
    if (isIOS) {
      // iOS: show share-sheet tip after short delay
      const isSafari = /Safari/.test(navigator.userAgent) && !/CriOS|FxiOS/.test(navigator.userAgent);
      if (isSafari) {
        setTimeout(() => {
          const tip = document.getElementById('ios-tip');
          if (tip) tip.classList.add('visible');
        }, 2500);
      }
    } else {
      // Android/Chrome: listen for beforeinstallprompt
      window.addEventListener('beforeinstallprompt', e => {
        e.preventDefault();
        window._pwaPrompt = e;
        setTimeout(() => {
          const banner = document.getElementById('install-banner');
          if (banner) banner.classList.add('visible');
        }, 1500);
      });
    }
  }

  document.getElementById('install-btn')?.addEventListener('click', async () => {
    const p = window._pwaPrompt;
    if (!p) return;
    p.prompt();
    await p.userChoice;
    window._pwaPrompt = null;
    document.getElementById('install-banner')?.classList.remove('visible');
    sessionStorage.setItem('install-dismissed', '1');
  });
  document.getElementById('install-dismiss')?.addEventListener('click', () => {
    document.getElementById('install-banner')?.classList.remove('visible');
    sessionStorage.setItem('install-dismissed', '1');
  });
  document.getElementById('ios-tip-close')?.addEventListener('click', () => {
    document.getElementById('ios-tip')?.classList.remove('visible');
    sessionStorage.setItem('install-dismissed', '1');
  });

  // ── Expense detail sheet ────────────────────────────────
  const overlay  = document.getElementById('detail-overlay');
  const sheet    = document.getElementById('detail-sheet');

  function openSheet(btn) {
    const d = btn.dataset;

    // Receipt image
    const imgWrap = document.getElementById('sheet-img-wrap');
    const imgEl   = document.getElementById('sheet-img');
    if (d.image) {
      imgEl.src = d.image;
      imgWrap.classList.add('has-img');
    } else {
      imgWrap.classList.remove('has-img');
    }

    // Child tag
    const childRow = document.getElementById('sheet-child-row');
    if (d.child) {
      childRow.innerHTML = `<span class="child-tag"><span class="child-tag-dot">${d.child[0].toUpperCase()}</span>${d.child}</span>`;
      childRow.style.display = 'block';
    } else {
      childRow.style.display = 'none';
    }

    // Core fields
    document.getElementById('sheet-amount').textContent = d.amount;
    document.getElementById('sheet-cat-val').textContent   = `${d.caticon} ${d.category}`;
    document.getElementById('sheet-date-val').textContent  = d.date;
    document.getElementById('sheet-status-val').innerHTML  =
      `<span class="badge ${d.status === 'Acknowledged' ? 'badge-a' : 'badge-p'}">${d.status}</span>`;

    // Acknowledge action
    const ackWrap = document.getElementById('sheet-ack-wrap');
    if (d.status === 'Pending') {
      ackWrap.innerHTML = `
        <form method="post" action="/acknowledge">
          <input type="hidden" name="id" value="${d.id}">
          <button type="submit" class="btn btn-primary" style="width:100%">✓ Acknowledge</button>
        </form>`;
    } else {
      ackWrap.innerHTML = '';
    }

    overlay.classList.add('open');
    sheet.classList.add('open');
    document.body.style.overflow = 'hidden';

    // Load comments for this expense
    currentExpId = d.id;
    loadComments(d.id);
  }

  function closeSheet() {
    overlay.classList.remove('open');
    sheet.classList.remove('open');
    document.body.style.overflow = '';
    currentExpId = null;
  }

  // ── Comments ──────────────────────────────────────────────
  let currentExpId = null;
  let selectedAuthor = 'Mom';

  function renderComments(comments) {
    const list = document.getElementById('comments-list');
    if (!comments.length) {
      list.innerHTML = '<div class="comment-empty">No comments yet. Start the conversation.</div>';
      return;
    }
    list.innerHTML = comments.map(c => {
      const cls = c.author === 'Mom' ? 'mom' : 'dad';
      const t = new Date(c.created_at).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
      return `<div class="comment-bubble">
        <div class="comment-meta">
          <span class="comment-author ${cls}">${c.author}</span>
          <span class="comment-time">${t}</span>
        </div>
        <div class="comment-body">${c.body.replace(/</g,'&lt;')}</div>
      </div>`;
    }).join('');
    list.scrollTop = list.scrollHeight;
  }

  function loadComments(expId) {
    fetch(`/comments/${expId}`)
      .then(r => r.json()).then(renderComments).catch(() => {});
  }

  document.addEventListener('click', e => {
    const btn = e.target.closest('.btn-view');
    if (btn) { e.preventDefault(); openSheet(btn); }

    const ab = e.target.closest('.author-btn');
    if (ab) {
      document.querySelectorAll('.author-btn').forEach(b => b.classList.remove('active'));
      ab.classList.add('active');
      selectedAuthor = ab.dataset.author;
    }
  });

  document.getElementById('comment-submit')?.addEventListener('click', () => {
    const input = document.getElementById('comment-input');
    const body = (input.value || '').trim();
    if (!body || !currentExpId) return;
    const fd = new FormData();
    fd.append('author', selectedAuthor);
    fd.append('body', body);
    fetch(`/comments/${currentExpId}`, {method:'POST', body:fd})
      .then(r => r.json()).then(comments => { renderComments(comments); input.value = ''; })
      .catch(() => {});
  });

  document.getElementById('comment-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      document.getElementById('comment-submit')?.click();
    }
  });

  overlay?.addEventListener('click', e => { if (e.target === overlay) closeSheet(); });
  document.getElementById('sheet-close-btn')?.addEventListener('click', closeSheet);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSheet(); });

  // Swipe down to close (mobile)
  let touchStartY = 0;
  sheet?.addEventListener('touchstart', e => { touchStartY = e.touches[0].clientY; }, {passive:true});
  sheet?.addEventListener('touchmove', e => {
    const dy = e.touches[0].clientY - touchStartY;
    if (dy > 60 && sheet.scrollTop === 0) closeSheet();
  }, {passive:true});

});
""")

# ── Data ─────────────────────────────────────────────────────────────────────

CATEGORIES = {
    "Medical": "🏥", "Education": "📚", "Essentials": "🛒",
    "Clothing": "👕", "Activities": "⚽", "Other": "📎",
}

CHILDREN = ["Hailey", "Makayla"]

# ── App ───────────────────────────────────────────────────────────────────────

app, rt = fast_app(
    pico=False,
    hdrs=[
        Meta(name="viewport", content="width=device-width, initial-scale=1, viewport-fit=cover"),
        Meta(name="theme-color", content="#070d19"),
        Meta(name="mobile-web-app-capable", content="yes"),
        Meta(name="apple-mobile-web-app-capable", content="yes"),
        Meta(name="apple-mobile-web-app-status-bar-style", content="black-translucent"),
        Meta(name="apple-mobile-web-app-title", content="NurtureTrack"),
        Meta(name="application-name", content="NurtureTrack"),
        Meta(name="msapplication-TileColor", content="#070d19"),
        Meta(name="msapplication-TileImage", content="/static/icons/icon-192.png"),
        Link(rel="manifest", href="/manifest.json"),
        # iOS icons
        Link(rel="apple-touch-icon", href="/static/icons/apple-touch-icon.png"),
        Link(rel="apple-touch-icon", sizes="152x152", href="/static/icons/icon-128.png"),
        Link(rel="apple-touch-icon", sizes="180x180", href="/static/icons/apple-touch-icon.png"),
        # iOS splash (black background matches app bg)
        Meta(name="apple-mobile-web-app-status-bar-style", content="black-translucent"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"),
        Style(CSS),
        Script("if('serviceWorker' in navigator) window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js'));"),
        JS,
    ]
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, https_only=False)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Write SW to project root so FastHTML's static catch-all route can serve it
with open("sw.js", "w") as _sw_f:
    _sw_f.write(SW_JS)


@rt("/manifest.json")
def get(): return StarletteResponse(content=MANIFEST, media_type="application/manifest+json")


# ── Components ────────────────────────────────────────────────────────────────

def _success_overlay():
    colors = ["#00A896","#00C4B4","#7FFFE4","#FFD93D","#FF6B9D","#A78BFA","#60A5FA","#34D399"]
    pieces = [
        Div(cls="cf", style=(
            f"left:{random.randint(2,98)}%;"
            f"width:{random.randint(5,12)}px;height:{random.randint(6,14)}px;"
            f"border-radius:{random.randint(0,50)}%;"
            f"background:{random.choice(colors)};"
            f"animation-duration:{random.uniform(1.8,3.4):.1f}s;"
            f"animation-delay:{random.uniform(0,1.2):.1f}s"
        ))
        for _ in range(40)
    ]
    return Div(
        Div(*pieces, cls="confetti"),
        Div("✓", cls="s-check-ring"),
        H2("Expense Submitted!", cls="s-title"),
        P("Logged and saved for the kids. ✦", cls="s-sub"),
        Button("Done →", type="button", id="success-done", cls="btn s-done"),
        id="success-overlay", cls="success-overlay",
    )

def _date_picker(value: str):
    return Div(
        Span("Date", cls="dp-label"),
        Button(
            Span("📅"),
            Span(value, id="dp-display", cls="dp-display"),
            Span("▾", cls="dp-caret"),
            type="button", id="dp-trigger", cls="dp-trigger",
        ),
        Input(type="hidden", name="date", id="dp-hidden", value=value),
        Div(
            Div(
                Button("‹", type="button", id="dp-prev", cls="dp-nav"),
                Span("", id="dp-month-yr", cls="dp-month-yr"),
                Button("›", type="button", id="dp-next", cls="dp-nav"),
                cls="dp-header",
            ),
            Div(*[Span(d, cls="dp-wday") for d in ["Su","Mo","Tu","We","Th","Fr","Sa"]],
                cls="dp-weekdays"),
            Div(id="dp-days", cls="dp-days"),
            id="dp-panel", cls="dp-panel",
        ),
        cls="dp-wrap",
    )

def back_nav(label="", show_lock=False):
    return Div(
        A("← Home", href="/", cls="back-btn"),
        Span(label, cls="back-chip") if label else "",
        A("🔒 Lock", href="/add/logout", cls="back-btn", style="margin-left:auto") if show_lock else "",
        cls="back-nav",
    )

def page_shell(*content, view=""):
    script = Script(f"document.body.setAttribute('data-view','{view}');") if view else ""
    return Div(Div(id="cursor-glow"), script, *content, cls="page")

def _install_ui():
    return (
        # Android / Chrome install banner
        Div(
            Div(Img(src="/static/icons/icon-192.png", alt="icon"), cls="install-app-icon"),
            Div(Div("Install NurtureTrack", cls="install-title"),
                Div("Add to your home screen", cls="install-sub"), cls="install-text"),
            Button("Install", cls="install-btn", id="install-btn"),
            Button("×", cls="install-dismiss", id="install-dismiss"),
            id="install-banner", cls="install-banner",
        ),
        # iOS Safari tip
        Div(
            Span("Tap "),
            Span("⬆ Share", style="color:var(--jade);font-weight:600"),
            Span(" then "),
            Strong("Add to Home Screen"),
            Div(cls="ios-tip-arrow"),
            Button("×", cls="ios-tip-close", id="ios-tip-close"),
            id="ios-tip", cls="ios-tip",
        ),
    )

def landing_shell(*content):
    return Div(Div(id="cursor-glow"), *_install_ui(), *content, cls="page-landing")

def lock_shell(*content):
    return Div(Div(id="cursor-glow"), *content, cls="lock-wrap")

def detail_modal():
    return (
        Div(id="detail-overlay", cls="detail-overlay"),
        Div(
            Div(cls="sheet-handle"),
            Div(
                Span("Expense Details", cls="sheet-label"),
                Button("×", id="sheet-close-btn", cls="sheet-close"),
                cls="sheet-header",
            ),
            Div(
                Img(src="", id="sheet-img", alt="receipt"),
                id="sheet-img-wrap", cls="sheet-receipt-wrap",
            ),
            Div("🧾", cls="sheet-receipt-ph"),
            Div(
                Div(id="sheet-child-row", cls="sheet-child-row"),
                Div("", id="sheet-amount", cls="sheet-amount"),
                Div(
                    Span("🏷", cls="sheet-info-icon"),
                    Div(Div("Category", cls="sheet-info-label"),
                        Div("", id="sheet-cat-val", cls="sheet-info-val"),
                        cls="sheet-info-content"),
                    cls="sheet-info-row",
                ),
                Div(
                    Span("📅", cls="sheet-info-icon"),
                    Div(Div("Date", cls="sheet-info-label"),
                        Div("", id="sheet-date-val", cls="sheet-info-val"),
                        cls="sheet-info-content"),
                    cls="sheet-info-row",
                ),
                Div(
                    Span("●", cls="sheet-info-icon"),
                    Div(Div("Status", cls="sheet-info-label"),
                        Div("", id="sheet-status-val", cls="sheet-info-val"),
                        cls="sheet-info-content"),
                    cls="sheet-info-row",
                ),
                cls="sheet-body",
            ),
            Div(id="sheet-ack-wrap", cls="sheet-actions"),
            Div(
                Div("💬 Comments", cls="comments-heading"),
                Div(id="comments-list", cls="comments-list"),
                Div(
                    Div(
                        Button("Mom", type="button", cls="author-btn active", **{"data-author": "Mom"}),
                        Button("Dad", type="button", cls="author-btn", **{"data-author": "Dad"}),
                        cls="author-toggle",
                    ),
                    Textarea(id="comment-input", cls="comment-input", placeholder="Add a comment...", rows="2"),
                    Button("Send", type="button", id="comment-submit", cls="btn btn-primary comment-send"),
                    cls="comment-form",
                ),
                cls="comments-section",
            ),
            id="detail-sheet", cls="detail-sheet",
        ),
    )


# ── Landing Page ─────────────────────────────────────────────────────────────

@rt("/")
def get():
    return Titled("", landing_shell(
        Div(
            Div("Nurture·Track", cls="landing-wordmark"),
            P("Co-Parenting Expense Hub", cls="landing-tag"),
            cls="landing-logo",
        ),
        Div(
            A(
                Div("📷", cls="portal-icon-wrap portal-icon-mom"),
                Div("Mom's Portal", cls="portal-title"),
                P("Log receipts for the kids instantly", cls="portal-desc"),
                Span("→", cls="portal-arrow"),
                href="/add", cls="portal-card portal-mom",
            ),
            A(
                Div("📋", cls="portal-icon-wrap portal-icon-dad"),
                Div("Dad's Portal", cls="portal-title"),
                P("Audit and acknowledge submitted expenses", cls="portal-desc"),
                Span("→", cls="portal-arrow"),
                href="/review", cls="portal-card portal-dad",
            ),
            cls="portal-grid",
        ),
    ))


# ── Auth: Mom's Access ───────────────────────────────────────────────────────

def _login_page(error=False):
    return Titled("", lock_shell(
        Div(
            Div("🔐", cls="lock-icon-wrap"),
            H1("Mom's Portal", cls="lock-title"),
            P("Enter your password to continue.", cls="lock-subtitle"),
            Div("Incorrect password — try again.", cls="lock-error") if error else "",
            Form(
                Div(
                    Input(type="password", name="password", id="f-pw",
                          placeholder=" ", required=True, autocomplete="current-password",
                          cls="ff-input"),
                    Label("Password", for_="f-pw", cls="ff-label"),
                    cls="ff",
                ),
                Button("Unlock ✦", type="submit", cls="btn btn-primary"),
                method="post", action="/add/login",
            ),
            A("← Back to Home", href="/", cls="lock-home"),
            cls="glass lock-card",
        ),
    ))

@rt("/add/login")
def get(req):
    if req.session.get("woman_auth"):
        return RedirectResponse("/add", status_code=303)
    return _login_page()

@rt("/add/login")
async def post(req):
    form = await req.form()
    if form.get("password", "") == MOM_PASSWORD and MOM_PASSWORD:
        req.session["woman_auth"] = True
        return RedirectResponse("/add", status_code=303)
    return _login_page(error=True)

@rt("/add/logout")
def get(req):
    req.session.pop("woman_auth", None)
    return RedirectResponse("/", status_code=303)


# ── Add Expense View (Mom's) ─────────────────────────────────────────────────

@rt("/add")
def get(req, submitted: str = ""):
    if not req.session.get("woman_auth"):
        return RedirectResponse("/add/login", status_code=303)
    toast = _success_overlay() if submitted == "1" else ""

    cat_items = []
    for i, (cat, icon) in enumerate(CATEGORIES.items()):
        cat_items.append(Input(type="radio", name="category", value=cat,
                               id=f"cat-{cat}", cls="cat-radio", checked=(i == 0)))
        cat_items.append(Label(Span(icon, cls="cat-icon"), Span(cat, cls="cat-name"),
                               for_=f"cat-{cat}", cls="cat-pill"))

    child_items = []
    for i, child in enumerate(CHILDREN):
        child_items.append(Input(type="radio", name="child", value=child,
                                 id=f"child-{i}", cls="cat-radio", checked=(i == 0)))
        child_items.append(Label(
            Span(child[0].upper(), cls="child-avatar"),
            Span(child, cls="cat-name"),
            for_=f"child-{i}", cls="cat-pill",
        ))

    hero_add = Div(
        Span("✨", cls="vha-emoji"),
        Div(
            Div("Hey there 👋", cls="vha-greeting"),
            Div(dt_date.today().strftime("%A, %B %-d"), cls="vha-date"),
        ),
        Div(
            *[Div(c[0].upper(), cls="vha-child-dot", title=c) for c in CHILDREN],
            cls="vha-children",
        ),
        cls="view-hero-add",
    )

    return Titled("", page_shell(
        toast,
        back_nav("Add Expense", show_lock=True),
        hero_add,
        H1("Log Expense"),
        P("Capture receipts instantly.", cls="subtitle"),
        Div(
            Form(
                # Date picker
                _date_picker(str(dt_date.today())),
                # Child picker
                Div(
                    Span("For which child?", cls="cat-label"),
                    Div(*child_items, cls="cat-grid"),
                    cls="cat-section",
                ),
                # Category pills
                Div(
                    Span("Category", cls="cat-label"),
                    Div(*cat_items, cls="cat-grid"),
                    cls="cat-section",
                ),
                # Amount
                Div(
                    Input(type="number", name="amount", id="f-amt",
                          placeholder=" ", step="0.01", min="0", required=True, cls="ff-input"),
                    Label("Amount ($)", for_="f-amt", cls="ff-label"),
                    cls="ff",
                ),
                # Upload zone
                Div(
                    Span("Receipt Photo", cls="cat-label"),
                    Div(
                        Span("📷", cls="dz-icon", id="dz-icon"),
                        P(Span("Drop receipt here or ", cls="dz-hint"),
                          Label("browse", for_="receipt-input", cls="dz-link"),
                          id="dz-hint"),
                        Img(src="", alt="preview", id="dz-preview", cls="dz-preview"),
                        Input(type="file", name="receipt", id="receipt-input",
                              accept="image/*", capture="environment", cls="dz-file"),
                        cls="dz", id="drop-zone",
                    ),
                    cls="cat-section",
                ),
                # Explanation
                Div(
                    Span("Explanation", cls="cat-label"),
                    Textarea(name="comment", id="f-comment", cls="comment-input",
                             placeholder="Why is this expense needed? e.g. Hailey's dental checkup at St. Luke's", rows="3"),
                    cls="cat-section",
                ),
                Button("Submit Expense", type="submit", cls="btn btn-primary"),
                method="post", action="/submit", enctype="multipart/form-data",
            ),
            cls="glass form-wrap",
        ),
        view="add",
    ))


@rt("/submit")
async def post(req):
    form     = await req.form()
    date_val = form.get("date") or str(dt_date.today())
    child    = form.get("child", CHILDREN[0] if CHILDREN else "")
    category = form.get("category", "Other")
    amount   = float(form.get("amount") or 0)
    receipt  = form.get("receipt")

    image_url = None
    if receipt and getattr(receipt, "filename", None):
        file_bytes = await receipt.read()
        if file_bytes:
            try:
                ext = receipt.filename.rsplit(".", 1)[-1] if "." in receipt.filename else "jpg"
                filename = f"{uuid.uuid4()}.{ext}"
                sb.storage.from_("receipts").upload(filename, file_bytes,
                    {"content-type": receipt.content_type or "image/jpeg"})
                image_url = sb.storage.from_("receipts").get_public_url(filename)
            except Exception:
                pass  # photo upload failure shouldn't block the expense save

    comment = (form.get("comment") or "").strip()

    try:
        result = sb.table("expenses").insert({
            "date": date_val, "child": child, "category": category,
            "amount": amount, "image_url": image_url, "status": "Pending",
        }).execute()
    except Exception as e:
        err = str(e)
        if "child" in err:
            result = sb.table("expenses").insert({
                "date": date_val, "category": category,
                "amount": amount, "image_url": image_url, "status": "Pending",
            }).execute()
        else:
            raise

    if comment and result.data:
        expense_id = result.data[0]["id"]
        sb.table("comments").insert({
            "expense_id": expense_id, "author": "Mom", "body": comment,
        }).execute()

    return RedirectResponse("/add?submitted=1", status_code=303)


# ── Review Feed (Dad's) ──────────────────────────────────────────────────────

@rt("/review")
def get():
    rows = sb.table("expenses").select("*").order("created_at", desc=True).execute().data or []

    pending_count = sum(1 for r in rows if r.get("status") == "Pending")
    ack_count     = sum(1 for r in rows if r.get("status") == "Acknowledged")

    if rows:
        df = pl.DataFrame([{
            "category": r["category"],
            "amount":   float(r["amount"]),
            "child":    r.get("child") or "Unknown",
            "status":   r.get("status", "Pending"),
            "month":    str(r.get("date", ""))[:7],
        } for r in rows])

        grand    = df["amount"].sum()
        avg_amt  = grand / len(rows)
        grand_fmt = f"${grand:,.2f}"

        # Category breakdown
        cat_df = df.group_by("category").agg(
            pl.col("amount").sum().alias("total"),
            pl.col("amount").len().alias("count"),
        ).sort("total", descending=True)

        # Child breakdown
        child_df = df.group_by("child").agg(
            pl.col("amount").sum().alias("total"),
            pl.col("amount").len().alias("count"),
        ).sort("total", descending=True)

        # Monthly trend
        month_df = df.group_by("month").agg(
            pl.col("amount").sum().alias("total"),
        ).sort("month")
        month_max = month_df["total"].max() or 1

        ack_pct   = round(ack_count / len(rows) * 100) if rows else 0
        month_rows = month_df.to_dicts()

        import json
        chart_data = json.dumps({
            "monthly":    {"labels": [r["month"][5:] for r in month_rows],
                           "amounts": [round(r["total"], 2) for r in month_rows]},
            "categories": {"labels": [r["category"] for r in cat_df.to_dicts()],
                           "icons":  [CATEGORIES.get(r["category"], "📎") for r in cat_df.to_dicts()],
                           "amounts": [round(r["total"], 2) for r in cat_df.to_dicts()],
                           "counts":  [r["count"] for r in cat_df.to_dicts()]},
            "children":   {"labels": [r["child"] for r in child_df.to_dicts()],
                           "amounts": [round(r["total"], 2) for r in child_df.to_dicts()]},
            "status":     {"acknowledged": ack_count, "pending": pending_count},
        })

        ack_pct   = round(ack_count / len(rows) * 100) if rows else 0

        # ── KPI cards (Overview tab) ──
        kpi_section = Div(
            Div(Span("📋", cls="kpi-icon"), Div(str(len(rows)),      cls="kpi-val teal"),  Div("Total Entries",  cls="kpi-label"), cls="kpi-card"),
            Div(Span("⏳", cls="kpi-icon"), Div(str(pending_count),  cls="kpi-val amber"), Div("Pending",        cls="kpi-label"), cls="kpi-card"),
            Div(Span("✅", cls="kpi-icon"), Div(str(ack_count),      cls="kpi-val green"), Div("Acknowledged",   cls="kpi-label"), Div(f"{ack_pct}% done", cls="kpi-sub"), cls="kpi-card"),
            Div(Span("💰", cls="kpi-icon"), Div(f"${avg_amt:,.2f}",  cls="kpi-val blue"),  Div("Avg per Expense",cls="kpi-label"), cls="kpi-card"),
            cls="kpi-row",
        )

        # ── Chart canvases (Analytics tab, lazy-init on first open) ──
        charts_section = Div(
            Div(
                Div(Div("📅 Monthly Spending", Span("— per month"), cls="chart-title"),
                    NotStr('<canvas id="monthChart"></canvas>'), cls="chart-card"),
                Div(Div("⚖️ Status", Span(f"— {ack_pct}% done"), cls="chart-title"),
                    NotStr('<canvas id="statusChart" style="max-height:220px"></canvas>'), cls="chart-card"),
                cls="chart-row chart-row-2",
            ),
            Div(
                Div(Div("🏷 By Category", Span("— total spend"), cls="chart-title"),
                    NotStr('<canvas id="catChart"></canvas>'), cls="chart-card"),
                Div(Div("👧 By Child", Span("— total spend"), cls="chart-title"),
                    NotStr('<canvas id="childChart"></canvas>'), cls="chart-card"),
                cls="chart-row chart-row-2",
            ),
            cls="dash",
        )

        chartjs_data   = chart_data
        chartjs_script = Script(f"""
window._chartData = {chartjs_data};
window._chartsReady = false;
function initDashCharts(){{
  if(window._chartsReady) return;
  if(typeof Chart==='undefined'){{ setTimeout(initDashCharts,100); return; }}
  window._chartsReady = true;
  const D=window._chartData;
  const teal='#00C4B4',jade='#00A896',amber='rgba(255,180,0,.85)',blue='#00C4E8';
  const t2='rgba(122,154,173,.7)',grid='rgba(255,255,255,.05)';
  const fmt=v=>'$'+v.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
  Chart.defaults.color=t2; Chart.defaults.font.family='system-ui,sans-serif';
  new Chart(document.getElementById('monthChart'),{{type:'bar',
    data:{{labels:D.monthly.labels,datasets:[{{label:'Spend',data:D.monthly.amounts,
      backgroundColor:'rgba(0,196,180,.22)',borderColor:teal,borderWidth:2,
      borderRadius:8,borderSkipped:false,hoverBackgroundColor:'rgba(0,196,180,.42)'}}]}},
    options:{{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>fmt(c.raw)}}}}}},
      scales:{{y:{{ticks:{{callback:v=>'$'+v,color:t2}},grid:{{color:grid}}}},x:{{ticks:{{color:t2}},grid:{{display:false}}}}}}}}
  }});
  new Chart(document.getElementById('statusChart'),{{type:'doughnut',
    data:{{labels:['Acknowledged','Pending'],datasets:[{{data:[D.status.acknowledged,D.status.pending],
      backgroundColor:[jade,amber],borderWidth:0,hoverOffset:8}}]}},
    options:{{responsive:true,cutout:'70%',plugins:{{
      legend:{{position:'bottom',labels:{{padding:16,usePointStyle:true}}}},
      tooltip:{{callbacks:{{label:c=>c.label+': '+c.raw}}}}}}}}
  }});
  new Chart(document.getElementById('catChart'),{{type:'bar',
    data:{{labels:D.categories.labels,datasets:[{{label:'Amount',data:D.categories.amounts,
      backgroundColor:'rgba(0,168,150,.28)',borderColor:jade,borderWidth:2,
      borderRadius:6,hoverBackgroundColor:'rgba(0,168,150,.48)'}}]}},
    options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{display:false}},
      tooltip:{{callbacks:{{label:c=>fmt(c.raw)+' ('+D.categories.counts[c.dataIndex]+'x)'}}}}}},
      scales:{{x:{{ticks:{{callback:v=>'$'+v,color:t2}},grid:{{color:grid}}}},y:{{ticks:{{color:t2}},grid:{{display:false}}}}}}}}
  }});
  new Chart(document.getElementById('childChart'),{{type:'bar',
    data:{{labels:D.children.labels,datasets:[{{label:'Amount',data:D.children.amounts,
      backgroundColor:'rgba(0,196,232,.22)',borderColor:blue,borderWidth:2,
      borderRadius:6,hoverBackgroundColor:'rgba(0,196,232,.42)'}}]}},
    options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{display:false}},
      tooltip:{{callbacks:{{label:c=>fmt(c.raw)}}}}}},
      scales:{{x:{{ticks:{{callback:v=>'$'+v,color:t2}},grid:{{color:grid}}}},y:{{ticks:{{color:t2}},grid:{{display:false}}}}}}}}
  }});
}}
""")
        stats = ""

    else:
        kpi_section    = ""
        charts_section = ""
        chartjs_script = NotStr("")
        stats          = ""
        grand_fmt      = "$0.00"

    hero_review = Div(
        Div(
            Div("Entries", cls="vhr-title"),
            Div(str(len(rows)), cls="vhr-count"),
            Div("total logged", cls="vhr-sub"),
            cls="vhr-stat",
        ),
        Div(cls="vhr-divider"),
        Div(
            Div("Pending", cls="vhr-title"),
            Div(str(pending_count), cls="vhr-count"),
            Div("awaiting review", cls="vhr-sub"),
            cls="vhr-stat",
        ),
        Div(cls="vhr-divider"),
        Div(
            Div("Total Spend", cls="vhr-title"),
            Div(grand_fmt, cls="vhr-count"),
            Div("all time", cls="vhr-sub"),
            cls="vhr-stat",
        ),
        cls="view-hero-review",
    )

    # Fetch first comment per expense in one query
    expense_ids = [str(r["id"]) for r in rows]
    first_comments: dict = {}
    if expense_ids:
        all_comments = sb.table("comments").select("expense_id,body,author").in_("expense_id", expense_ids).order("created_at").execute().data or []
        for c in all_comments:
            eid = str(c["expense_id"])
            if eid not in first_comments:
                first_comments[eid] = (c["author"], c["body"])

    cards = []
    for row in rows:
        thumb = (
            Div(Img(src=row["image_url"], alt="receipt", loading="lazy"), cls="thumb")
            if row.get("image_url")
            else Div("🧾", cls="thumb-ph")
        )
        status    = row.get("status", "Pending")
        badge_cls = "badge-a" if status == "Acknowledged" else "badge-p"
        child     = row.get("child") or ""
        child_tag = (
            Div(
                Div(child[0].upper(), cls="child-tag-dot"),
                child,
                cls="child-tag",
            ) if child else ""
        )
        amount_fmt = f"${float(row['amount']):,.2f}"
        card_data = {
            "data-id":       str(row["id"]),
            "data-child":    child,
            "data-category": row["category"],
            "data-caticon":  CATEGORIES.get(row["category"], "📎"),
            "data-amount":   amount_fmt,
            "data-date":     str(row["date"]),
            "data-status":   status,
            "data-image":    row.get("image_url") or "",
        }

        first = first_comments.get(str(row["id"]))
        comment_preview = ""
        if first:
            author, body = first
            preview = body if len(body) <= 120 else body[:120] + "…"
            comment_preview = Div(
                Div(Span("📝"), Span("Explanation"), cls="card-comment-label"),
                Div(preview, cls="card-comment-text"),
                cls="card-comment",
            )

        view_btn   = Button("View", type="button", cls="btn btn-view", **card_data)
        export_btn = A("⬇ Excel", href=f"/export/{row['id']}", cls="btn btn-export")
        cards.append(Div(
            thumb,
            Div(
                child_tag,
                Div(amount_fmt, cls="card-amount"),
                P(f"{row['category']} · {row['date']}", cls="card-meta"),
                Span(status, cls=f"badge {badge_cls}"),
                comment_preview,
                Div(view_btn, export_btn, cls="card-actions"),
                cls="card-body",
            ),
            cls="expense-card",
        ))

    feed = (
        Div(*cards, cls="expense-grid")
        if cards
        else Div(Div("📂", cls="empty-icon"), P("No expenses logged yet."), cls="empty")
    )

    return Titled("", page_shell(
        Div(
            A("← Home", href="/", cls="back-btn"),
            Span("Review Feed", cls="back-chip"),
            cls="back-nav",
        ),
        hero_review,
        Script(src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"),
        chartjs_script,
        Div(
            Button("📊 Dashboard", cls="tab-btn active", **{"data-tab": "dashboard"}),
            Button("🧾 Feed",      cls="tab-btn",        **{"data-tab": "feed"}),
            cls="tab-bar",
        ),
        Div(kpi_section, charts_section, id="panel-dashboard", cls="tab-panel active"),
        Div(feed,                        id="panel-feed",       cls="tab-panel"),
        Script("""
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + btn.dataset.tab)?.classList.add('active');
    if (btn.dataset.tab === 'dashboard') initDashCharts();
  });
});
// Init charts on page load since dashboard is the default tab
document.addEventListener('DOMContentLoaded', () => initDashCharts());
"""),
        *detail_modal(),
        view="review",
    ))


@rt("/acknowledge")
async def post(req):
    form   = await req.form()
    exp_id = form.get("id")
    if exp_id:
        sb.table("expenses").update({"status": "Acknowledged"}).eq("id", exp_id).execute()
    return RedirectResponse("/review", status_code=303)


@rt("/comments/{expense_id}")
def get(expense_id: str):
    rows = sb.table("comments").select("*").eq("expense_id", expense_id).order("created_at").execute().data
    return JSONResponse(rows)

@rt("/comments/{expense_id}")
async def post(req, expense_id: str):
    form   = await req.form()
    author = (form.get("author") or "").strip()
    body   = (form.get("body") or "").strip()
    if author and body:
        sb.table("comments").insert({"expense_id": expense_id, "author": author, "body": body}).execute()
    rows = sb.table("comments").select("*").eq("expense_id", expense_id).order("created_at").execute().data
    return JSONResponse(rows)


@rt("/export/{expense_id}")
def get(expense_id: str):
    from io import BytesIO
    row = sb.table("expenses").select("*").eq("id", expense_id).single().execute().data
    df = pl.DataFrame({
        "Date":        [str(row.get("date", ""))],
        "Child":       [row.get("child") or ""],
        "Category":    [row.get("category", "")],
        "Amount":      [float(row.get("amount", 0))],
        "Status":      [row.get("status", "")],
        "Receipt URL": [row.get("image_url") or ""],
    })
    buf = BytesIO()
    df.write_excel(buf)
    buf.seek(0)
    filename = f"expense_{row.get('date','unknown')}_{row.get('category','').lower()}.xlsx"
    return StarletteResponse(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


serve()
