/**
 * Deterministic validator for iframe content
 * Validates security, accessibility, layout, and project-specific rules
 * Uses hidden sandboxed iframe with srcdoc to avoid CORS issues
 */

export interface ValidationError {
  id: string;
  severity: 'error' | 'warning';
  category: 'security' | 'accessibility' | 'layout' | 'project-specific';
  message: string;
  hint: string;
  where?: string;
  element?: Element;
}

export interface ValidationResult {
  passed: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

/**
 * Load HTML into a hidden sandboxed iframe and validate it
 */
export async function validateIframeContent(html: string): Promise<ValidationResult> {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  // Create hidden sandboxed iframe
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  iframe.style.position = 'absolute';
  iframe.style.left = '-9999px';
  iframe.setAttribute('sandbox', 'allow-same-origin'); // Same-origin for validation, but sandboxed
  iframe.srcdoc = html;
  
  document.body.appendChild(iframe);

  try {
    // Wait for iframe to load
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Iframe load timeout'));
      }, 10000); // 10 second timeout

      iframe.onload = () => {
        clearTimeout(timeout);
        resolve();
      };

      iframe.onerror = () => {
        clearTimeout(timeout);
        reject(new Error('Iframe load error'));
      };
    });

    // Wait a bit for any dynamic content to render
    await new Promise(resolve => setTimeout(resolve, 500));

    const doc = iframe.contentDocument;
    if (!doc) {
      throw new Error('Cannot access iframe document');
    }

    // Run all validation checks
    validateSecurity(doc, errors, warnings);
    validateAccessibility(doc, errors, warnings);
    validateLayout(doc, errors, warnings);
    validateProjectSpecific(doc, errors, warnings);

  } catch (error) {
    errors.push({
      id: 'LOAD_ERROR',
      severity: 'error',
      category: 'security',
      message: `Failed to load HTML for validation: ${error instanceof Error ? error.message : 'Unknown error'}`,
      hint: 'The HTML content may be malformed or contain security restrictions'
    });
  } finally {
    // Clean up iframe
    document.body.removeChild(iframe);
  }

  return {
    passed: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Security validation checks
 */
function validateSecurity(doc: Document, errors: ValidationError[], warnings: ValidationError[]): void {
  // Check for target="_blank" without rel="noopener noreferrer"
  const externalLinks = doc.querySelectorAll('a[target="_blank"]');
  externalLinks.forEach((link, index) => {
    const rel = link.getAttribute('rel') || '';
    const relLower = rel.toLowerCase();
    if (!relLower.includes('noopener') || !relLower.includes('noreferrer')) {
      errors.push({
        id: 'TARGET_BLANK_NO_NOOPENER',
        severity: 'error',
        category: 'security',
        message: `External link missing rel="noopener noreferrer" (found at index ${index})`,
        hint: 'Add rel="noopener noreferrer" to all links with target="_blank" to prevent tabnabbing attacks',
        where: getElementLocation(link),
        element: link
      });
    }
  });

  // Check for inline event handlers (XSS risk)
  const inlineHandlers = doc.querySelectorAll('[onclick], [onerror], [onload], [onmouseover]');
  inlineHandlers.forEach((element, index) => {
    warnings.push({
      id: 'INLINE_EVENT_HANDLER',
      severity: 'warning',
      category: 'security',
      message: `Inline event handler detected (${element.tagName.toLowerCase()})`,
      hint: 'Consider using addEventListener instead of inline handlers for better security',
      where: getElementLocation(element),
      element: element as Element
    });
  });

  // Check for eval() or Function() in script tags
  const scripts = doc.querySelectorAll('script');
  scripts.forEach((script, index) => {
    const content = script.textContent || script.innerHTML;
    if (content.includes('eval(') || content.includes('Function(')) {
      errors.push({
        id: 'EVAL_USAGE',
        severity: 'error',
        category: 'security',
        message: `Script contains eval() or Function() constructor (script #${index + 1})`,
        hint: 'Avoid eval() and Function() constructor as they pose XSS risks. Use alternative approaches.',
        where: `script[${index}]`,
        element: script
      });
    }
  });

  // Check for data: URIs in sensitive contexts
  const dataUris = doc.querySelectorAll('[src^="data:"], [href^="data:"]');
  dataUris.forEach((element, index) => {
    warnings.push({
      id: 'DATA_URI_USAGE',
      severity: 'warning',
      category: 'security',
      message: `Data URI detected (${element.tagName.toLowerCase()})`,
      hint: 'Data URIs should be used carefully. Ensure content is sanitized.',
      where: getElementLocation(element),
      element: element as Element
    });
  });
}

/**
 * Accessibility validation checks
 */
function validateAccessibility(doc: Document, errors: ValidationError[], warnings: ValidationError[]): void {
  // Check for images without alt text
  const images = doc.querySelectorAll('img');
  images.forEach((img, index) => {
    const alt = img.getAttribute('alt');
    if (alt === null) {
      errors.push({
        id: 'MISSING_ALT_TEXT',
        severity: 'error',
        category: 'accessibility',
        message: `Image missing alt attribute (img #${index + 1})`,
        hint: 'Add alt attribute to all images. Use empty alt="" for decorative images.',
        where: getElementLocation(img),
        element: img
      });
    }
  });

  // Check for form inputs without labels
  const inputs = doc.querySelectorAll('input:not([type="hidden"]), textarea, select');
  inputs.forEach((input, index) => {
    const id = input.getAttribute('id');
    const ariaLabel = input.getAttribute('aria-label');
    const ariaLabelledBy = input.getAttribute('aria-labelledby');
    const placeholder = input.getAttribute('placeholder');
    
    if (!id && !ariaLabel && !ariaLabelledBy) {
      const hasLabel = id && doc.querySelector(`label[for="${id}"]`);
      if (!hasLabel) {
        warnings.push({
          id: 'INPUT_WITHOUT_LABEL',
          severity: 'warning',
          category: 'accessibility',
          message: `Form input missing accessible label (${input.tagName.toLowerCase()} #${index + 1})`,
          hint: 'Add a label element with for attribute, or use aria-label/aria-labelledby',
          where: getElementLocation(input),
          element: input as Element
        });
      }
    }
  });

  // Check for heading hierarchy
  const headings = Array.from(doc.querySelectorAll('h1, h2, h3, h4, h5, h6'));
  if (headings.length > 0) {
    let previousLevel = 0;
    headings.forEach((heading, index) => {
      const level = parseInt(heading.tagName.charAt(1));
      if (index === 0 && level !== 1) {
        warnings.push({
          id: 'NO_H1',
          severity: 'warning',
          category: 'accessibility',
          message: 'First heading is not h1',
          hint: 'Consider starting with an h1 tag for better document structure',
          where: getElementLocation(heading),
          element: heading
        });
      }
      if (previousLevel > 0 && level > previousLevel + 1) {
        warnings.push({
          id: 'SKIPPED_HEADING_LEVEL',
          severity: 'warning',
          category: 'accessibility',
          message: `Heading level skipped from h${previousLevel} to h${level}`,
          hint: 'Avoid skipping heading levels. Maintain proper hierarchy (h1 → h2 → h3, etc.)',
          where: getElementLocation(heading),
          element: heading
        });
      }
      previousLevel = level;
    });
  }

  // Check for sufficient color contrast (basic check)
  const elementsWithColor = doc.querySelectorAll('[style*="color"], [style*="background"]');
  warnings.push({
    id: 'COLOR_CONTRAST_CHECK',
    severity: 'warning',
    category: 'accessibility',
    message: `${elementsWithColor.length} elements with inline color styles detected`,
    hint: 'Ensure color contrast meets WCAG AA standards (4.5:1 for normal text, 3:1 for large text)',
    where: 'Multiple elements'
  });

  // Check for keyboard navigation (presence of focusable elements)
  const focusable = doc.querySelectorAll('a, button, input, textarea, select, [tabindex]:not([tabindex="-1"])');
  if (focusable.length === 0) {
    warnings.push({
      id: 'NO_FOCUSABLE_ELEMENTS',
      severity: 'warning',
      category: 'accessibility',
      message: 'No keyboard-focusable elements found',
      hint: 'Ensure interactive elements are keyboard accessible',
      where: 'Document'
    });
  }
}

/**
 * Layout validation checks
 */
function validateLayout(doc: Document, errors: ValidationError[], warnings: ValidationError[]): void {
  // Check for viewport meta tag
  const viewport = doc.querySelector('meta[name="viewport"]');
  if (!viewport) {
    errors.push({
      id: 'MISSING_VIEWPORT',
      severity: 'error',
      category: 'layout',
      message: 'Missing viewport meta tag',
      hint: 'Add <meta name="viewport" content="width=device-width, initial-scale=1"> for responsive design',
      where: '<head>'
    });
  }

  // Check for title tag
  const title = doc.querySelector('title');
  if (!title || !title.textContent?.trim()) {
    errors.push({
      id: 'MISSING_TITLE',
      severity: 'error',
      category: 'layout',
      message: 'Missing or empty title tag',
      hint: 'Add a descriptive <title> tag for SEO and browser tabs',
      where: '<head>'
    });
  }

  // Check for basic HTML structure
  const html = doc.documentElement;
  const head = doc.head;
  const body = doc.body;

  if (!html) {
    errors.push({
      id: 'INVALID_HTML_STRUCTURE',
      severity: 'error',
      category: 'layout',
      message: 'Invalid HTML structure - missing <html> tag',
      hint: 'Ensure valid HTML5 document structure',
      where: 'Document root'
    });
  }

  if (!head) {
    errors.push({
      id: 'MISSING_HEAD',
      severity: 'error',
      category: 'layout',
      message: 'Missing <head> tag',
      hint: 'Ensure valid HTML5 document structure with <head> section',
      where: 'Document'
    });
  }

  if (!body) {
    errors.push({
      id: 'MISSING_BODY',
      severity: 'error',
      category: 'layout',
      message: 'Missing <body> tag',
      hint: 'Ensure valid HTML5 document structure with <body> section',
      where: 'Document'
    });
  }

  // Check for excessive inline styles
  const inlineStyles = doc.querySelectorAll('[style]');
  if (inlineStyles.length > 50) {
    warnings.push({
      id: 'EXCESSIVE_INLINE_STYLES',
      severity: 'warning',
      category: 'layout',
      message: `${inlineStyles.length} elements with inline styles detected`,
      hint: 'Consider moving styles to CSS classes or external stylesheets for better maintainability',
      where: 'Multiple elements'
    });
  }
}

/**
 * Project-specific validation rules
 */
function validateProjectSpecific(doc: Document, errors: ValidationError[], warnings: ValidationError[]): void {
  // Check for required hero section
  const hero = doc.querySelector('[class*="hero"], [id*="hero"], section:first-child');
  if (!hero) {
    warnings.push({
      id: 'NO_HERO_SECTION',
      severity: 'warning',
      category: 'project-specific',
      message: 'No hero section detected',
      hint: 'Landing pages typically benefit from a hero section at the top',
      where: 'Document structure'
    });
  }

  // Check for contact/CTA sections
  const hasContactInfo = doc.querySelector('[class*="contact"], [id*="contact"], [href^="tel:"], [href^="mailto:"]');
  if (!hasContactInfo) {
    warnings.push({
      id: 'NO_CONTACT_INFO',
      severity: 'warning',
      category: 'project-specific',
      message: 'No contact information detected',
      hint: 'Include contact information or CTA buttons for business landing pages',
      where: 'Document'
    });
  }

  // Check for responsive design indicators
  const hasMediaQueries = doc.querySelector('style')?.textContent?.includes('@media');
  const hasResponsiveMeta = doc.querySelector('meta[name="viewport"]');
  if (!hasMediaQueries && !hasResponsiveMeta) {
    warnings.push({
      id: 'POSSIBLY_NOT_RESPONSIVE',
      severity: 'warning',
      category: 'project-specific',
      message: 'No responsive design indicators found',
      hint: 'Ensure the page is mobile-friendly with responsive design',
      where: 'Document'
    });
  }

  // Check for external CDN resources (common in generated pages)
  const externalResources = doc.querySelectorAll('link[href^="http"], script[src^="http"]');
  if (externalResources.length === 0) {
    warnings.push({
      id: 'NO_EXTERNAL_RESOURCES',
      severity: 'warning',
      category: 'project-specific',
      message: 'No external CDN resources detected',
      hint: 'Consider using CDN resources for common libraries (Bootstrap, Font Awesome, etc.)',
      where: 'Document'
    });
  }
}

/**
 * Get a human-readable location for an element
 */
function getElementLocation(element: Element): string {
  const tagName = element.tagName.toLowerCase();
  const id = element.getAttribute('id');
  const className = element.getAttribute('class');
  
  let location = tagName;
  if (id) {
    location += `#${id}`;
  } else if (className) {
    const classes = className.split(' ').slice(0, 2).join('.');
    location += `.${classes}`;
  }
  
  return location;
}

