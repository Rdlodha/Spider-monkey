import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Findings from './Findings'

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn((path) => {
      if (path === '/api/projects') {
        return Promise.resolve([{ id: 'p1', name: 'Alpha Target' }])
      }
      if (path.startsWith('/api/findings')) {
        return Promise.resolve([
          {
            id: 'f1',
            title: 'Exposed Database',
            severity: 'HIGH',
            status: 'OPEN',
            tags: 'db,mysql',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ])
      }
      if (path.startsWith('/api/correlate')) {
        return Promise.resolve({
          project_id: 'p1',
          suggestions: [
            {
              rule_id: 'SVC-001',
              severity: 'MEDIUM',
              title: 'MySQL service exposed',
              description: 'Port 3306 is open.',
              entity_type: 'service',
              entity_id: 's1',
              entity_label: '192.168.1.1:3306/tcp mysql',
            },
          ],
        })
      }
      return Promise.resolve([])
    }),
    post: vi.fn(() => Promise.resolve({ id: 'f2', title: 'New' })),
    patch: vi.fn(() => Promise.resolve({})),
    delete: vi.fn(() => Promise.resolve({})),
    upload: vi.fn(() => Promise.resolve({})),
    download: vi.fn(() => Promise.resolve({})),
  },
}))

describe('Findings Page', () => {
  it('renders findings title, new finding button, and findings table', async () => {
    render(<Findings />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Findings & Evidence/i })).toBeDefined()
    })
    expect(screen.getByRole('button', { name: /New Finding/i })).toBeDefined()
    await waitFor(() => {
      expect(screen.getByText('Exposed Database')).toBeDefined()
      expect(screen.getByText('Suggested Correlations (1)')).toBeDefined()
    })
  })
})
