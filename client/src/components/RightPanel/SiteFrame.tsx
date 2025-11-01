/**
 * Iframe container for generated landing page
 * Ref: Product.md > Section 1, line 43
 * 
 * Implements deterministic validation:
 * 1. Load HTML into hidden sandboxed iframe using srcdoc
 * 2. Validate security, accessibility, layout, and project-specific rules
 * 3. If errors found, send to MCP validator_errors for fixing
 * 4. Only show iframe once validation passes
 */

import { useEffect, useState, lazy, Suspense, useRef } from "react";
import { useBuild } from "../../contexts/BuildContext";
import { validateIframeContent, type ValidationError } from "../../utils/iframeValidator";
import { sendErrorsToMCP, type MCPValidationError } from "../../utils/mcpValidator";
import { logger } from "../../utils/logger";

// Lazy load skeleton for better code splitting
const LandingPageSkeleton = lazy(() => import("./LandingPageSkeleton"));

interface ValidationState {
  isValidating: boolean;
  isValid: boolean;
  errors: ValidationError[];
  fixing: boolean;
  fixedHtml: string | null;
}

function SiteFrame() {
  const { sessionId, isReady } = useBuild();
  const [validationState, setValidationState] = useState<ValidationState>({
    isValidating: false,
    isValid: false,
    errors: [],
    fixing: false,
    fixedHtml: null,
  });
  const [hasError, setHasError] = useState(false);
  const [validatedHtml, setValidatedHtml] = useState<string | null>(null);
  const validationAttemptRef = useRef<number>(0);
  const maxFixAttempts = 3;

  // Reset state on new session or when a new build starts
  useEffect(() => {
    setHasError(false);
    setValidatedHtml(null);
    setValidationState({
      isValidating: false,
      isValid: false,
      errors: [],
      fixing: false,
      fixedHtml: null,
    });
    validationAttemptRef.current = 0;
  }, [sessionId, isReady]);

  // Fetch and validate HTML when build is ready
  useEffect(() => {
    if (!sessionId || !isReady || validatedHtml) return;

    let cancelled = false;

    async function fetchAndValidate() {
      try {
        setValidationState(prev => ({ ...prev, isValidating: true }));

        // Fetch HTML content
        const response = await fetch(`/api/result/${sessionId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch HTML: ${response.status}`);
        }
        const html = await response.text();

        if (cancelled) return;

        // Validate HTML
        const validationResult = await validateIframeContent(html);

        if (cancelled) return;

        if (validationResult.passed) {
          // Validation passed - safe to show
          setValidatedHtml(html);
          setValidationState({
            isValidating: false,
            isValid: true,
            errors: [],
            fixing: false,
            fixedHtml: null,
          });
        } else {
          // Validation failed - try to fix via MCP
          const errorErrors = validationResult.errors.filter(e => e.severity === 'error');
          
          if (errorErrors.length > 0 && validationAttemptRef.current < maxFixAttempts) {
            setValidationState(prev => ({ ...prev, fixing: true }));
            
            // Convert to MCP format
            const mcpErrors: MCPValidationError[] = errorErrors.map(err => ({
              id: err.id,
              severity: err.severity,
              category: err.category,
              message: err.message,
              hint: err.hint,
              where: err.where,
            }));

            // Send to MCP validator_errors
            const fixResult = await sendErrorsToMCP(html, mcpErrors, sessionId);

            if (cancelled) return;

            if (fixResult.success && fixResult.fixed_html) {
              // Retry validation with fixed HTML
              validationAttemptRef.current++;
              
              const revalidationResult = await validateIframeContent(fixResult.fixed_html);
              
              if (cancelled) return;

              if (revalidationResult.passed) {
                setValidatedHtml(fixResult.fixed_html);
                setValidationState({
                  isValidating: false,
                  isValid: true,
                  errors: [],
                  fixing: false,
                  fixedHtml: fixResult.fixed_html,
                });
              } else {
                // Still has errors after fix - show what we have with warnings
                setValidatedHtml(fixResult.fixed_html);
                setValidationState({
                  isValidating: false,
                  isValid: false,
                  errors: revalidationResult.errors,
                  fixing: false,
                  fixedHtml: fixResult.fixed_html,
                });
              }
            } else {
              // MCP fix failed - show errors but proceed with warnings
              logger.warn('[SiteFrame] MCP fix failed:', fixResult.message);
              setValidatedHtml(html); // Show original with warnings
              setValidationState({
                isValidating: false,
                isValid: false,
                errors: errorErrors,
                fixing: false,
                fixedHtml: null,
              });
            }
          } else {
            // No errors or max attempts reached - show with warnings
            setValidatedHtml(html);
            setValidationState({
              isValidating: false,
              isValid: errorErrors.length === 0,
              errors: validationResult.errors,
              fixing: false,
              fixedHtml: null,
            });
          }
        }
      } catch (error) {
        if (cancelled) return;
        
        logger.error('[SiteFrame] Validation error:', error);
        setHasError(true);
        setValidationState(prev => ({
          ...prev,
          isValidating: false,
          fixing: false,
        }));
      }
    }

    fetchAndValidate();

    return () => {
      cancelled = true;
    };
  }, [sessionId, isReady, validatedHtml]);

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">
          No page generated yet. Select a business to begin.
        </p>
      </div>
    );
  }

  if (!isReady || validationState.isValidating || validationState.fixing) {
    return (
      <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
        <LandingPageSkeleton />
        {validationState.fixing && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
            <div className="bg-white p-4 rounded shadow-lg">
              <p className="text-sm text-gray-700">
                Fixing validation errors... (attempt {validationAttemptRef.current}/{maxFixAttempts})
              </p>
            </div>
          </div>
        )}
      </Suspense>
    );
  }

  if (hasError || !validatedHtml) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center p-8">
          <p className="text-red-600 text-lg font-semibold mb-2">
            Failed to load the landing page
          </p>
          <p className="text-gray-600 text-sm">
            {hasError 
              ? "The generated page could not be displayed."
              : "Validation failed and page could not be loaded."}
          </p>
          {validationState.errors.length > 0 && (
            <div className="mt-4 text-left max-w-md mx-auto">
              <p className="text-sm font-semibold mb-2">Validation Errors:</p>
              <ul className="text-xs text-gray-600 space-y-1">
                {validationState.errors.slice(0, 5).map((err, idx) => (
                  <li key={idx}>• {err.message}</li>
                ))}
                {validationState.errors.length > 5 && (
                  <li className="text-gray-500">... and {validationState.errors.length - 5} more</li>
                )}
              </ul>
            </div>
          )}
          <button
            onClick={() => {
              setHasError(false);
              setValidatedHtml(null);
              validationAttemptRef.current = 0;
              window.location.reload();
            }}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Show validated HTML in sandboxed iframe using srcdoc
  return (
    <div className="w-full h-full bg-white relative">
      {validationState.errors.length > 0 && !validationState.isValid && (
        <div className="absolute top-0 left-0 right-0 bg-yellow-50 border-b border-yellow-200 p-2 z-10">
          <p className="text-xs text-yellow-800">
            ⚠️ Page loaded with {validationState.errors.length} validation warning{validationState.errors.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
      <iframe
        srcDoc={validatedHtml}
        className="w-full h-full border-0"
        title="Generated Landing Page"
        style={{ minHeight: "100%" }}
        sandbox="allow-scripts allow-forms allow-popups"
        onError={() => setHasError(true)}
      />
    </div>
  );
}

export default SiteFrame;
