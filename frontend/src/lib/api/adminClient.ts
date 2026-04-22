import axios from 'axios'

import { getApiBaseURL } from '@/lib/api/client'
import { useAdminStore } from '@/store/adminStore'

export const adminClient = axios.create({
  baseURL: getApiBaseURL(),
  timeout: 120_000,
})

adminClient.interceptors.request.use((config) => {
  const t = useAdminStore.getState().token
  if (t) {
    config.headers.Authorization = `Bearer ${t}`
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})
