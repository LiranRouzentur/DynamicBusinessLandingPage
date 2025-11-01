# Quality Gates Documentation

## Overview

The generator uses comprehensive quality gates to ensure landing pages render correctly, look professional, and function properly. These gates catch common issues that break designs BEFORE the page is saved.

---

## ✅ Quality Gate Checks

### 1. **Structural Requirements**

#### Minimum Sections (3+)
- **Check**: `section_count >= 3`
- **Error**: `too_few_sections`
- **Fix**: Add more `<section>` tags (features, testimonial, CTA)
- **Why**: Ensures content richness and proper page structure

#### Single H1 Tag
- **Check**: Exactly one `<h1>` present
- **Error**: `missing_h1`
- **Fix**: Add exactly one `<h1>` tag for the main heading
- **Why**: SEO requirement and accessibility

#### Complete HTML Structure
- **Check**: `<!DOCTYPE>`, `<html>`, `<head>`, `<body>`, `</html>` all present
- **Error**: `missing_tag:<tag>`
- **Fix**: Add missing HTML tag
- **Why**: Valid HTML5 document structure

---

### 2. **Required CDN Libraries** ⭐ MANDATORY

#### Bootstrap 5
- **Check**: `cdn.jsdelivr.net/npm/bootstrap` present in HTML
- **Error**: `missing_cdn:bootstrap`
- **Fix**: Add in `<head>`:
  ```html
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  ```
- **Why**: Professional responsive grid and components

#### AOS (Animate On Scroll)
- **Check**: `unpkg.com/aos` present in HTML
- **Error**: `missing_cdn:aos`
- **Fix**: Add in `<head>`:
  ```html
  <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
  ```
  And before `</body>`:
  ```html
  <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
  <script>AOS.init();</script>
  ```
- **Why**: Smooth scroll animations

#### Font Awesome 6
- **Check**: `font-awesome` present in HTML
- **Error**: `missing_cdn:fontawesome`
- **Fix**: Add in `<head>`:
  ```html
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  ```
- **Why**: Professional icons throughout the page

#### Google Fonts
- **Check**: `fonts.googleapis.com` present in HTML
- **Error**: `no_google_fonts`
- **Fix**: Add in `<head>`:
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  ```
- **Why**: Professional typography

---

### 3. **CSS & Styling**

#### CSS Rule Density
- **Check**: CSS rule count >= 160
- **Error**: `too_few_css_rules:<count>`
- **Fix**: Expand styles with more component classes, responsive breakpoints, hover states
- **Why**: Ensures rich, polished design

#### CSS Variables (Tokens)
- **Check**: `:root` with `--` variables present
- **Error**: `missing_css_tokens`
- **Fix**: Define CSS variables in `:root` (e.g., `--primary-color`, `--radius`, `--shadow`)
- **Why**: Consistent design system and easy theming

#### No Named Colors in Variables
- **Check**: CSS variables don't use `red`, `blue`, `green`, etc.
- **Error**: `using_named_colors`
- **Fix**: Use hex/rgb colors (`#006491`, `rgb(0,100,145)`) instead of named colors
- **Why**: Precise color control and consistency

---

### 4. **Layout & Responsiveness**

#### Viewport Meta Tag
- **Check**: `<meta name="viewport">` present
- **Error**: `missing_viewport`
- **Fix**: Add in `<head>`:
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **Why**: Mobile responsiveness

#### Hero Size
- **Check**: `min-height:` with `vh` units present
- **Error**: `weak_hero`
- **Fix**: Set hero to `min-height: 60vh` or higher
- **Why**: Impactful above-the-fold section

---

### 5. **Critical Rendering Issues** 🚨

#### Body Visibility Hidden
- **Check**: `body { visibility: hidden; }` NOT present
- **Error**: `body_visibility_hidden`
- **Fix**: **CRITICAL** - Remove `visibility: hidden` from body tag. Use `visibility: visible` or remove the property entirely
- **Why**: Makes entire page invisible! Common mistake that completely breaks rendering

#### Image URLs Must Be HTTPS
- **Check**: No `http://` image URLs
- **Error**: `non_https_image`
- **Fix**: Replace `http://` with `https://` in all image URLs
- **Why**: Security and mixed content warnings

#### Suspicious Long URLs
- **Check**: Image URLs under 500 characters
- **Error**: `suspicious_long_url`
- **Fix**: Use shorter, direct image URLs from `stock_images_urls` provided
- **Why**: Long URLs (especially Google Photos) often fail to load or expire

---

## 🔄 Auto-Fix System

### Retry Logic

When quality gates fail, the system automatically:

1. **Logs the errors** with clear descriptions
2. **Generates human-readable fix instructions** using `explain_qa_error()`
3. **Retries generation** with specific guidance (up to 2 retries)
4. **Passes corrected HTML** as template for incremental fixes

```python
# Example retry flow
attempt_1 = generate()  # Missing Bootstrap CDN
qa_errors = ["missing_cdn:bootstrap"]

fix_instructions = [
    "REQUIRED: Add Bootstrap 5 CDN link in <head>: <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>"
]

attempt_2 = generate(validator_errors=fix_instructions)  # Now includes Bootstrap
```

### Fix Message Enhancement

Each error code is converted to actionable instructions:

```python
"missing_cdn:bootstrap" 
  → "REQUIRED: Add Bootstrap 5 CDN link in <head>: <link href='...'>"

"body_visibility_hidden"
  → "CRITICAL: Remove 'visibility: hidden' from body tag - this makes page invisible!"

"too_few_css_rules:85"
  → "Add more CSS rules (currently 85, need ≥160). Expand with responsive breakpoints..."
```

---

## 📊 Quality Gate Results

### Logged in Meta
If any gates fail after all retries, they're added to the response metadata:

```json
{
  "html": "...",
  "meta": {
    "theme": "high-end",
    "seed": 254391827,
    "design_fingerprint": "a3f72c9e",
    "qa_gate_errors": ["too_few_css_rules:145", "weak_hero"]
  }
}
```

### Success Logging
```
[Generator] ✓ Quality gates passed after 1 fix attempts
[Generator] ✓ Generation completed successfully | html_size: 8543 chars
```

### Failure Logging
```
[Generator] Quality gates failed (attempt 1/3) | errors: ['missing_cdn:bootstrap', 'body_visibility_hidden']
[Generator] Retrying with quality gate fix instructions...
[Generator] ✓ Quality gates passed after 1 fix attempts
```

---

## 🎯 Common Issues & Solutions

### Issue: Page Appears Blank

**Likely Causes:**
1. `body { visibility: hidden; }` - Gate catches this
2. Missing CDN libraries - Gate catches this
3. Invalid image URLs - Gate catches this

**Solution:** Quality gates will force retry with specific fix instructions

---

### Issue: Fonts Look Wrong

**Likely Cause:** Missing Google Fonts CDN

**Solution:** 
- Gate: `no_google_fonts`
- Auto-fix: Adds Google Fonts link

---

### Issue: No Animations

**Likely Cause:** Missing AOS library or initialization

**Solution:**
- Gate: `missing_cdn:aos`
- Auto-fix: Adds AOS CSS + JS + init script

---

### Issue: Icons Missing

**Likely Cause:** Missing Font Awesome CDN

**Solution:**
- Gate: `missing_cdn:fontawesome`
- Auto-fix: Adds Font Awesome CDN

---

### Issue: Layout Broken on Mobile

**Likely Causes:**
1. Missing viewport meta tag - Gate catches this
2. Missing Bootstrap CDN - Gate catches this

**Solution:** Gates enforce both requirements

---

### Issue: Design Looks Basic/Unpolished

**Likely Cause:** Too few CSS rules

**Solution:**
- Gate: `too_few_css_rules:<count>`
- Auto-fix: Instructs to add responsive breakpoints, hover states, etc.

---

## 🔧 Development & Testing

### Testing Quality Gates

```python
from app.generator.generator_agent import qa_html_css

html = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <h1>Test</h1>
</body>
</html>
"""

errors = qa_html_css(html)
# Expected: ['missing_cdn:bootstrap', 'missing_cdn:aos', 'missing_cdn:fontawesome', 
#            'no_google_fonts', 'too_few_css_rules:0', ...]
```

### Adding New Gates

1. Add check in `qa_html_css()` function
2. Add error explanation in `explain_qa_error()` function
3. Update generator prompt with new requirement
4. Test with sample HTML

---

## 📚 Reference

### All Error Codes

| Code | Severity | Category |
|------|----------|----------|
| `too_few_sections` | Warning | Structure |
| `missing_h1` | Error | SEO/Accessibility |
| `no_google_fonts` | Error | Typography |
| `missing_viewport` | Error | Responsiveness |
| `too_few_css_rules:<n>` | Warning | Design Quality |
| `weak_hero` | Warning | Design Quality |
| `missing_css_tokens` | Warning | Design System |
| `body_visibility_hidden` | **CRITICAL** | Rendering |
| `missing_cdn:bootstrap` | **Error** | CDN Libraries |
| `missing_cdn:aos` | **Error** | CDN Libraries |
| `missing_cdn:fontawesome` | **Error** | CDN Libraries |
| `non_https_image` | Error | Security |
| `suspicious_long_url` | Warning | Images |
| `using_named_colors` | Warning | Design System |
| `missing_tag:<tag>` | Error | Structure |

---

## ✅ Success Criteria

A landing page passes quality gates when:

1. ✅ All 3 required CDNs present (Bootstrap, AOS, Font Awesome)
2. ✅ Google Fonts link present
3. ✅ No `visibility: hidden` on body
4. ✅ At least 3 sections
5. ✅ Exactly one H1
6. ✅ Viewport meta tag present
7. ✅ At least 160 CSS rules
8. ✅ Hero with vh units
9. ✅ CSS variables defined
10. ✅ All images HTTPS
11. ✅ Complete HTML structure

**Result:** Professional, polished, functional landing page that renders perfectly! 🎉

