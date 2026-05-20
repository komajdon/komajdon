import { describe, it, expect } from 'vitest'
import { api } from '../services/api'

describe('ApiService', () => {
  it('starts with no token', () => {
    expect(api.getToken()).toBeNull()
  })

  it('stores token', () => {
    api.setToken('test-token')
    expect(api.getToken()).toBe('test-token')
    api.setToken(null)
    expect(api.getToken()).toBeNull()
  })
})
