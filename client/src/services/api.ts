/**
 * API client
 */

import axios from 'axios'
import type { BuildRequest, BuildResponse } from '../types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const startBuild = async (request: BuildRequest): Promise<BuildResponse> => {
  const response = await api.post<BuildResponse>('/build', request)
  return response.data
}

export default api


