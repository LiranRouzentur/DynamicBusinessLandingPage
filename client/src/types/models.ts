/**
 * Domain models
 */

export interface Place {
  place_id: string
  name: string
  types: string[]
  formatted_address: string
  geometry: {
    lat: number
    lng: number
  }
  website?: string
  formatted_phone_number?: string
  rating?: number
  user_ratings_total?: number
  price_level?: number
}

export interface BuildState {
  phase: 'IDLE' | 'FETCHING' | 'ORCHESTRATING' | 'GENERATING' | 'QA' | 'READY' | 'ERROR'
  progress: number
  current_step: string
  detail: string
}


