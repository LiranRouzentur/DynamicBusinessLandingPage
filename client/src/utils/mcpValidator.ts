/**
 * MCP Validator Client
 * Sends validation errors to MCP validator_errors endpoint for automatic fixing
 */

import { logger } from "./logger";

export interface MCPValidationError {
  id: string;
  severity: 'error' | 'warning';
  category: 'security' | 'accessibility' | 'layout' | 'project-specific';
  message: string;
  hint: string;
  where?: string;
}

export interface MCPFixRequest {
  html: string;
  errors: MCPValidationError[];
  session_id: string;
}

export interface MCPFixResponse {
  fixed_html?: string;
  remaining_errors?: MCPValidationError[];
  success: boolean;
  message?: string;
}

/**
 * Send validation errors to MCP validator_errors endpoint
 */
export async function sendErrorsToMCP(
  html: string,
  errors: MCPValidationError[],
  sessionId: string
): Promise<MCPFixResponse> {
  try {
    const response = await fetch('/api/mcp/validator_errors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        html,
        errors,
        session_id: sessionId,
      } as MCPFixRequest),
    });

    if (!response.ok) {
      throw new Error(`MCP validator_errors endpoint returned ${response.status}`);
    }

    const result = await response.json() as MCPFixResponse;
    return result;
  } catch (error) {
    logger.error('[MCP Validator] Failed to send errors to MCP:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

