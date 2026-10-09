import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Scans from './Scans'

// Mock the API client
vi.mock('../services/api', () => ({
  api: {
    get: vi.fn((path) => {
      if (path === '/api/projects') {
        return Promise.resolve([{ id: 'p1', name: 'Alpha Target' }])
      }
      if (path.startsWith('/api/scans')) {
        return Promise.resolve([])
      }
      return Promise.resolve([])
    }),
    upload: vi.fn(() => Promise.resolve({ id: 's1', status: 'completed' })),
  },
}))

describe('Scans Page', () => {
  it('renders the Scans page header and import form', async () => {
    render(<Scans />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Scans/i })).toBeDefined()
    })
    expect(screen.getByRole('heading', { level: 2, name: /Import Scan Output/i })).toBeDefined()
    expect(screen.getByRole('heading', { level: 2, name: /Scan History/i })).toBeDefined()
  })

  it('renders supported tool options in the dropdown', async () => {
    render(<Scans />)
    await waitFor(() => {
      expect(screen.getByLabelText(/Tool/i)).toBeDefined()
    })
    expect(screen.getByText('Nmap (XML)')).toBeDefined()
    expect(screen.getByText('Feroxbuster (JSON lines)')).toBeDefined()
    expect(screen.getByText('Gobuster (text)')).toBeDefined()
  })
})
