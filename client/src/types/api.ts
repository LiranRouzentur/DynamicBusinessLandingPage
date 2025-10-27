/**
 * API types and interfaces
 */

export interface BuildRequest {
  place_id: string
  render_prefs?: RenderPrefs
}

export interface RenderPrefs {
  language?: string
  direction?: string
  brand_colors?: Record<string, string>
  font_stack?: string
  allow_external_cdns?: boolean
  max_reviews?: number
}

export interface BuildResponse {
  session_id: string
  cached: boolean
}

export interface ProgressEvent {
  ts: string
  session_id: string
  phase: 'FETCHING' | 'ORCHESTRATING' | 'GENERATING' | 'QA' | 'READY' | 'ERROR'
  step: string
  detail: string
  progress: number
}


