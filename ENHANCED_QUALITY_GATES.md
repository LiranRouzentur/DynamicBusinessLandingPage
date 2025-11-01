# Enhanced Quality Gates - Prevention of Broken Designs

## 🎯 Objective

Ensure every generated landing page renders correctly with proper fonts, colors, images, and external libraries. Catch common issues that break the visual design.

---

## 🔍 New Quality Checks

### 1. **Body Visibility Check**
**Error:** `body_visibility_hidden`  
**Problem:** `body { visibility: hidden; }` makes entire page invisible  
**Fix:** Remove the property or use `visibility: visible;`

### 2. **Required CDN Libraries**
All three CDN libraries are now **MANDATORY**:

#### Bootstrap 5
**Error:** `missing_cdn:bootstrap`  
**Required:** `<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">`  
**Why:** Grid system, utilities, professional components

#### AOS (Animate On Scroll)
**Error:** `missing_cdn:aos`  
**Required:** `<link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">`  
**Why:** Smooth animations on scroll

#### Font Awesome 6
**Error:** `missing_cdn:fontawesome`  
**Required:** `<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">`  
**Why:** Icons for visual elements

### 3. **Image URL Validation**

#### Non-HTTPS Images
**Error:** `non_https_image`  
**Problem:** Using `http://` instead of `https://`  
**Fix:** Replace all `http://` with `https://`

#### Suspiciously Long URLs
**Error:** `suspicious_long_url`  
**Problem:** Image URLs over 500 characters (likely to fail/timeout)  
**Fix:** Use shorter, direct URLs from `stock_images_urls` provided

### 4. **Color Definition Check**
**Error:** `using_named_colors`  
**Problem:** CSS variables using named colors (`red`, `blue`, etc.)  
**Fix:** Use hex or rgb format:
- ✅ `--primary-color: #006491;`
- ✅ `--primary-color: rgb(0, 100, 145);`
- ❌ `--primary-color: blue;`

### 5. **Complete HTML Structure**
**Error:** `missing_tag:<!doctype>`, `missing_tag:<html>`, etc.  
**Problem:** Incomplete HTML document structure  
**Fix:** Include all required tags:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ...
</head>
<body>
  ...
</body>
</html>
```

---

## 📋 Complete Quality Gates List

| Check | Error Code | Critical? | Description |
|-------|------------|-----------|-------------|
| **Sections** | `too_few_sections` | ⚠️ | Need ≥3 sections (features, testimonial, CTA) |
| **H1 Tag** | `missing_h1` | ⚠️ | Exactly one `<h1>` required |
| **Google Fonts** | `no_google_fonts` | ✅ | Must include Google Fonts link |
| **Viewport Meta** | `missing_viewport` | ✅ | Must have viewport meta tag |
| **CSS Density** | `too_few_css_rules:N` | ⚠️ | Need ≥160 CSS rules (currently N) |
| **Hero Size** | `weak_hero` | ⚠️ | Hero needs min-height with vh |
| **CSS Tokens** | `missing_css_tokens` | ⚠️ | Must define CSS variables in :root |
| **Body Visibility** | `body_visibility_hidden` | 🚨 | CRITICAL: Body cannot be hidden |
| **Bootstrap CDN** | `missing_cdn:bootstrap` | 🚨 | REQUIRED: Bootstrap 5 CDN |
| **AOS CDN** | `missing_cdn:aos` | 🚨 | REQUIRED: AOS CDN |
| **Font Awesome CDN** | `missing_cdn:fontawesome` | 🚨 | REQUIRED: Font Awesome CDN |
| **HTTPS Images** | `non_https_image` | ✅ | All images must be HTTPS |
| **Image URL Length** | `suspicious_long_url` | ⚠️ | Image URLs must be <500 chars |
| **Named Colors** | `using_named_colors` | ⚠️ | Use hex/rgb, not named colors |
| **HTML Structure** | `missing_tag:<tag>` | ✅ | Complete HTML structure required |

**Legend:**
- 🚨 **CRITICAL** - Will break page rendering
- ✅ **Required** - Must fix for proper functionality
- ⚠️ **Warning** - Should fix for quality

---

## 🔄 Retry Logic

When quality gates fail:

1. **First attempt** - Generate with seed/knobs
2. **Quality check** - Run `qa_html_css()`
3. **If failures** - Build fix instructions:
   ```python
   fix_instructions = [explain_qa_error(err) for err in qa_errors]
   # Example: "CRITICAL: Remove 'visibility: hidden' from body tag..."
   ```
4. **Retry** - Send clear fix instructions with original HTML as template
5. **Max retries** - 2 attempts (3 total generations)
6. **Final result** - Return best output, log any remaining errors

---

## 🛠️ Fix Instructions Examples

### Example 1: Missing CDNs
**Detected Errors:**
```
missing_cdn:bootstrap
missing_cdn:fontawesome
```

**Fix Instructions Sent:**
```
1. Add Bootstrap 5 CDN in <head>: <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
2. Add Font Awesome CDN in <head>: <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
```

### Example 2: Body Visibility Hidden
**Detected Error:**
```
body_visibility_hidden
```

**Fix Instruction:**
```
CRITICAL: Remove 'visibility: hidden' from body tag - this makes page invisible! Use 'visibility: visible' or remove the property entirely
```

### Example 3: Non-HTTPS Images
**Detected Error:**
```
non_https_image
```

**Fix Instruction:**
```
All image URLs must use HTTPS, not HTTP. Replace http:// with https://
```

---

## 📊 Quality Gate Flow

```
┌─────────────────────────┐
│  Generate Landing Page  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Run qa_html_css()     │
│  - Check 15+ rules      │
│  - Return error codes   │
└───────────┬─────────────┘
            │
        ┌───┴───┐
        │ Errors? │
        └───┬───┘
            │
    Yes ◄───┴───► No
    │               │
    ▼               ▼
┌─────────────┐  ┌──────────┐
│ Attempt < 2?│  │ Success! │
└──────┬──────┘  └──────────┘
       │
   Yes │ No
       │  │
       ▼  ▼
┌──────────────┐  ┌─────────────────┐
│ Build fix    │  │ Log warnings &  │
│ instructions │  │ return output   │
│              │  └─────────────────┘
│ Retry with   │
│ template +   │
│ errors       │
└──────────────┘
```

---

## 🎨 Required CDN Usage Examples

### Bootstrap Grid
```html
<div class="container">
  <div class="row">
    <div class="col-md-4">Feature 1</div>
    <div class="col-md-4">Feature 2</div>
    <div class="col-md-4">Feature 3</div>
  </div>
</div>
```

### Bootstrap Utilities
```html
<h2 class="text-center mb-4">Section Title</h2>
<div class="card p-4 shadow-sm">Content</div>
<button class="btn btn-primary btn-lg">Call to Action</button>
```

### Font Awesome Icons
```html
<i class="fa-solid fa-star text-warning"></i>
<i class="fa-solid fa-phone me-2"></i>
<i class="fa-brands fa-facebook"></i>
```

### AOS Animations
```html
<div data-aos="fade-up" data-aos-duration="800">
  <h2>Animated Heading</h2>
</div>
<img src="..." data-aos="zoom-in" data-aos-delay="200" />
```

---

## 🧪 Testing

Run quality gates on any HTML:

```python
from agents.app.generator.generator_agent import qa_html_css, explain_qa_error

html_content = """<!DOCTYPE html>..."""
errors = qa_html_css(html_content)

if errors:
    print("Quality gate failures:")
    for err in errors:
        print(f"  - {err}: {explain_qa_error(err)}")
else:
    print("All quality gates passed!")
```

---

## 📈 Benefits

### Before Enhancement
- ❌ Pages rendered with broken fonts
- ❌ Body visibility hidden → blank page
- ❌ Long image URLs failed to load
- ❌ No consistency in design quality
- ❌ Missing professional components

### After Enhancement  
- ✅ All fonts load correctly (Google Fonts required)
- ✅ Body visibility issues caught immediately
- ✅ Image URLs validated (HTTPS, length)
- ✅ Consistent professional design (Bootstrap + Icons)
- ✅ Smooth animations (AOS)
- ✅ Clear fix instructions for retries
- ✅ Deterministic improvements

---

## 🔧 Files Modified

```
agents/app/generator/
  ├── generator_agent.py
  │   ├── qa_html_css()         ← Enhanced with 8 new checks
  │   └── explain_qa_error()    ← Human-readable fix instructions
  └── generator_prompt.py       ← Updated with CDN requirements

ENHANCED_QUALITY_GATES.md       ← This documentation
```

---

## ✅ Summary

**Quality gates now enforce:**
1. ✅ Required CDN libraries (Bootstrap, AOS, Font Awesome)
2. ✅ No `visibility: hidden` on body
3. ✅ HTTPS images only
4. ✅ Reasonable image URL lengths
5. ✅ Proper color definitions
6. ✅ Complete HTML structure

**Result:** Broken designs are caught and fixed automatically, ensuring professional, functional landing pages every time.

**Status:** ✅ Complete and Tested

