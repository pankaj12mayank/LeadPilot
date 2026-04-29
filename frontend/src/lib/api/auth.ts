import type { AuthResponse, User } from '@/types/models'

import { api } from './client'

export async function login(email: string, password: string) {
  const { data } = await api.post<AuthResponse>('/auth/login', { email, password })
  return data
}

export async function register(email: string, password: string, role: 'user' | 'buyer' = 'user') {
  const { data } = await api.post<AuthResponse>('/auth/register', { email, password, role })
  return data
}

export async function fetchMe() {
  const { data } = await api.get<User>('/auth/me')
  return data
}
