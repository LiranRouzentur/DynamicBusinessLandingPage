/**
 * API types and interfaces
 */

export interface ProgressEvent {
  ts: string
  session_id: string
  phase: 'FETCHING' | 'ORCHESTRATING' | 'GENERATING' | 'QA' | 'READY' | 'ERROR'
  step: string
  detail: string
  progress: number
}

