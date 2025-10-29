# Dynamic Landing Page Generation Agent — With QA/Validation Loop

**Version:** 1.1  
**Last updated:** 2025-10-29

This document extends the base agent spec with a **thorough self‑validation (QA) loop**. The agent must generate the landing page **and** validate its own output against functional, accessibility, performance, and structural requirements. If any checks fail, the agent must **repair and re‑run** generation until all tests pass or a retry limit is reached.

---


## 0) Scope

- Static site generation only: `index.html`, `styles.css`, `script.js`, `/assets/...`  
- Frameworks allowed **via CDN** only when justified (Bootstrap, Tailwind, AOS, GLightbox, GSAP, jQuery on demand).  
- No forms, no API calls, no storage, no login.  
- Interactivity tier default: **Enhanced**.

All rules from the previous spec remain in force.

---

## 1) Inputs (Schemas)

### 1.1 Google Data (schema)
Use the exact schema below and handle nullables/empties gracefully.

```json
{ "google data": 
{
  "properties": {
    "place_id": { "type": ["string", "null"] },
    "name": { "type": ["string", "null"] },
    "formatted_address": { "type": ["string", "null"] },
    "types": {
      "type": "array",
      "items": { "type": "string" },
      "default": []
    },
    "primary_type": { "type": ["string", "null"] },
    "website_url": { "type": ["string", "null"], "format": "uri" },
    "google_maps_url": { "type": ["string", "null"], "format": "uri" },
    "location": {
      "type": ["object", "null"],
      "properties": {
        "latitude": { "type": "number" },
        "longitude": { "type": "number" }
      },
      "required": ["latitude", "longitude"]
    },
    "viewport": {
      "type": ["object", "null"],
      "properties": {
        "low": {
          "type": "object",
          "properties": {
            "latitude": { "type": "number" },
            "longitude": { "type": "number" }
          }
        },
        "high": {
          "type": "object",
          "properties": {
            "latitude": { "type": "number" },
            "longitude": { "type": "number" }
          }
        }
      }
    },
    "contact": {
      "type": "object",
      "properties": {
        "international_phone": { "type": ["string", "null"] }
      }
    },
    "status": {
      "type": "object",
      "properties": {
        "open_now": { "type": ["boolean", "null"] },
        "weekday_descriptions": {
          "type": "array",
          "items": { "type": "string" },
          "default": []
        }
      }
    },
    "rating": { "type": ["number", "null"] },
    "user_rating_count": { "type": ["integer", "null"] },
    "price_level": { "type": ["integer", "null"] },
    "editorial_summary": { "type": ["string", "null"] },
    "reviews": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "rating": { "type": ["number", "null"] },
          "text": { "type": ["string", "null"] },
          "publish_time": { "type": ["string", "null"], "format": "date-time" },
          "relative_time": { "type": ["string", "null"] },
          "author": { "type": ["string", "null"] },
          "author_uri": { "type": ["string", "null"], "format": "uri" },
          "author_photo_uri": { "type": ["string", "null"], "format": "uri" }
        }
      },
      "default": []
    },
    "photos": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": ["string", "null"] },
          "width_px": { "type": ["integer", "null"] },
          "height_px": { "type": ["integer", "null"] },
          "author_attributions": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "displayName": { "type": ["string", "null"] },
                "uri": { "type": ["string", "null"], "format": "uri" },
                "photoUri": { "type": ["string", "null"], "format": "uri" }
              }
            },
            "default": []
          },
          "download_uri": { "type": ["string", "null"], "format": "uri" }
        }
      },
      "default": []
    }
  },
  "required": [
    "place_id",
    "name",
    "formatted_address",
    "types",
    "primary_type",
    "google_maps_url"
  ],
  "additionalProperties": false
} 
}
```

### 1.2 Mapper Agent Data (schema)
Normalized structure after mapping.

```json
mapper_agent_data: 
{
  "business_page_url": "string or null",
  "business_summary": "string",
  "assats": {
    "logo_url": "string or null",
    "business_images_urls": ["string"] | null,
    "stock_images_urls": ["string"] | null,
    "brand_colors": {
      "primary": "string",
      "secondary": "string",
      "...": "..."
    }
  }
}
```

Mapping rules:
- If `google data.website_url` exists → copy to `mapper_agent_data.business_page_url`.
- `business_summary` = 1–2 sentences using name, primary_type, editorial_summary, rating, address.
- If no brand colors, infer from images or business type.

---

## 2) Output Contract

```
index.html
styles.css
script.js
/assets/...
```
- Standalone, static. No build tools.
- All relative paths valid.
- Each run must be visually and structurally unique.

---

## 3) QA/Validation Loop (Agent must run this)
The agent must execute the following **validate → fix → re‑validate** loop (max 3 attempts by default). If a check fails, fix and regenerate only the necessary parts.

### 3.1 Structural & Linking
- [ ] Files exist: `index.html`, `styles.css`, `script.js`.
- [ ] `/assets/images` has **3–6** images.
- [ ] All `<link>`, `<script>`, and `<img>` `src/href` resolve to an existing file or valid CDN URL.
- [ ] `index.html` references `styles.css` and `script.js` with correct relative paths.
- [ ] No absolute local paths.

### 3.2 HTML Semantics & SEO
- [ ] Valid HTML5 doctype and `<meta name="viewport">`.
- [ ] `<title>` present and non‑generic.
- [ ] `<meta name="description">` present and < 170 chars.
- [ ] Required sections present: hero, about/services, features/products, testimonials/reviews, CTA/footer.
- [ ] Headings: one `<h1>`, logical `<h2>` order (no skipped levels).
- [ ] No empty anchors or headings.

### 3.3 Accessibility
- [ ] Every `<img>` has meaningful `alt`.
- [ ] Keyboard focus visible on links/buttons.
- [ ] Color contrast AA for body text (heuristic check).
- [ ] `prefers-reduced-motion` respected (animations disabled).
- [ ] ARIA attributes only where necessary (no `role="button"` on anchors unless required).

### 3.4 CSS Quality
- [ ] Uses Grid/Flex for layout (not tables).
- [ ] No massive inline styles; CSS file < 200 KB.
- [ ] Theme uniqueness: non‑default color palette and font pairing.
- [ ] No @import of remote CSS except CDNs as allowed.
- [ ] Media queries for mobile responsiveness exist.

### 3.5 JS Behavior (Tier Enforcement)
- [ ] No forms, fetch/XHR, storage (localStorage/sessionStorage/cookies).
- [ ] `script.js` < ~10 KB gzipped.
- [ ] Interactivity Tier:
  - **Basic**: smooth scroll, mobile nav toggle, dynamic year.
  - **Enhanced (default)**: + scroll reveal, lazy images, back‑to‑top, lightbox.
  - **High‑end (opt‑in)**: + parallax/theme logic.
- [ ] `defer` used or scripts at end of body.
- [ ] If CDN scripts used, they match allowed list and are necessary.

### 3.6 Performance & UX
- [ ] Below‑the‑fold images include `loading="lazy"`.
- [ ] Hero/media have dimensions to avoid CLS.
- [ ] Total image weight reasonable (< 1.5 MB suggested for placeholders).
- [ ] Lighthouse‑style heuristics: avoid large DOM bloats, minimize blocking resources.

### 3.7 Business Fit
- [ ] Visual theme matches `business_type` heuristics.
- [ ] Copy reflects provided data (name, address, rating if present).
- [ ] Reviews pulled in (if present) and sanitized.

---

## 4) Automatic Fix Rules
When a test fails, apply these remediation patterns before regenerating:

- Missing `meta description` → synthesize concise description from `business_summary`.
- Missing alt text → derive from filename or `photos` metadata.
- Heading order wrong → relevel headings; ensure single h1.
- No lazy loading → add `loading="lazy"` for non‑hero images.
- JS too large → drop non‑essential effects; prefer native over CDN.
- Interactivity tier mismatch → enforce required features; remove extra features.
- Link errors → fix relative paths; remove dead references.
- Accessibility contrast issue → increase color contrast using WCAG AA heuristics.

---

## 5) Self‑Test Harness (Reference Implementation)

> The agent can embed or execute an internal validator. The snippets below illustrate a minimal offline validation in **Python**. They can run inside your orchestrator to produce a pass/fail report and a list of fix actions.

### 5.1 Python Validator (offline)
```python
import os, re, gzip
from bs4 import BeautifulSoup

ROOT = "output"  # folder with index.html, styles.css, script.js, assets/
errors, warnings = [], []

def must(cond, msg): 
    if not cond: errors.append(msg)

def should(cond, msg):
    if not cond: warnings.append(msg)

def gz_kb(path):
    data = open(path, "rb").read()
    return len(gzip.compress(data)) / 1024.0

# Structural
must(os.path.exists(f"{ROOT}/index.html"), "index.html missing")
must(os.path.exists(f"{ROOT}/styles.css"), "styles.css missing")
must(os.path.exists(f"{ROOT}/script.js"), "script.js missing")
img_dir = f"{ROOT}/assets/images"
must(os.path.isdir(img_dir), "assets/images missing")
if os.path.isdir(img_dir):
    imgs = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png','.jpg','.jpeg','.webp','.svg'))]
    must(3 <= len(imgs) <= 6, "assets/images should contain 3–6 images")

# HTML parse
soup = BeautifulSoup(open(f"{ROOT}/index.html", encoding="utf-8").read(), "html.parser")
must(soup.title and soup.title.text.strip(), "<title> missing or empty")
desc = soup.find("meta", attrs={"name":"description"})
must(desc and desc.get("content") and len(desc["content"]) < 170, "meta description missing or too long")
must(soup.find("meta", attrs={"name":"viewport"}), "viewport meta missing")
h1s = soup.find_all("h1")
must(len(h1s) == 1, "Exactly one <h1> required")

# Linking
for tag in soup.find_all(["link","script","img","a"]):
    url = tag.get("href") or tag.get("src")
    if not url: continue
    if url.startswith(("http://","https://")): 
        continue
    local = os.path.normpath(os.path.join(ROOT, url))
    must(os.path.exists(local), f"Broken path: {url}")

# Accessibility
for img in soup.find_all("img"):
    must(img.has_attr("alt") and img["alt"].strip(), f"Image missing alt: {img.get('src')}")

# CSS / JS checks
js_gz = gz_kb(f"{ROOT}/script.js") if os.path.exists(f"{ROOT}/script.js") else 9999
must(js_gz <= 10.0, f"script.js too large when gzipped: {js_gz:.1f} KB")

js_text = open(f"{ROOT}/script.js", encoding="utf-8").read()
for bad in ["fetch(", "XMLHttpRequest(", "localStorage", "sessionStorage", "document.cookie"]:
    must(bad not in js_text, f"Forbidden API usage: {bad}")

# Interactivity tier heuristic
smooth = ("scrollIntoView(" in js_text)
reveal = ("IntersectionObserver" in js_text) or (".reveal" in open(f"{ROOT}/styles.css",encoding="utf-8").read())
should(smooth, "Smooth scroll not detected")
should(reveal, "Scroll reveal not detected (Enhanced default)")

print("ERRORS:", len(errors)); print("\n".join(errors))
print("WARNINGS:", len(warnings)); print("\n".join(warnings))
exit(1 if errors else 0)
```

### 5.2 JS Lint Heuristics (optional inline)
- Reject unused CDN scripts.
- Fail if `<script>` is missing `defer` and placed in `<head>`.
- Warn if more than 2 external CDNs are included.

---

## 6) QA Execution Order

1. **Generate** files (HTML/CSS/JS/assets) according to spec.  
2. **Run Validator** (structural → semantics → accessibility → JS tier → performance).  
3. **Repair** using Automatic Fix Rules.  
4. **Re‑validate**. Repeat up to **3** attempts.  
5. **Emit Report**: include a `<!-- QA REPORT ... -->` HTML comment at the top of `index.html` containing:
   - Timestamp
   - Interactivity tier
   - Errors fixed (list)
   - Final status: PASS/FAIL

Example:
```html
<!-- QA REPORT
timestamp: 2025-10-29T09:00:00Z
tier: enhanced
fixed: ["added meta description", "set alt text for 3 images"]
status: PASS
-->
```

---

## 7) Deliverables

- Final `.zip` with passing validation.
- `index.html` starts with the QA REPORT comment block.
- Optional: include `qa_report.json` summarizing all checks (pass/fail, metrics).

---

## 8) JS Behavior Recap (Allowed CDNs)

- Native ES6 preferred.
- Allowed when needed: Bootstrap bundle, AOS, GLightbox, GSAP, vanilla-lazyload, jQuery (on request).
- Always respect `prefers-reduced-motion`.  
- Keep compressed size small and avoid blocking main thread.

---

## 9) Example Invocation

> Generate a static landing page for a **modern flower shop** from Google data. Use Enhanced tier with scroll reveal and a lightbox gallery. Validate, auto‑fix, and re‑validate until PASS. Output a zip with HTML, CSS, JS, and assets plus a QA REPORT block inside index.html.
