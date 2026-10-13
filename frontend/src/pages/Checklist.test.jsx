import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Checklist from './Checklist'

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn((path) => {
      if (path === '/api/projects') {
        return Promise.resolve([
          {
            id: 'p1',
            name: 'Target Project',
            targets: [{ id: 't1', value: 'https://target.local' }],
          },
        ])
      }
      if (path.startsWith('/api/checklists/progress')) {
        return Promise.resolve([
          {
            id: 'cp1',
            target_id: 't1',
            template_item_id: 'item1',
            item_section: 'Reconnaissance',
            item_title: 'Enumerate directories and files',
            state: 'NOT_STARTED',
            note: '',
            updated_at: new Date().toISOString(),
          },
        ])
      }
      return Promise.resolve([])
    }),
    patch: vi.fn(() => Promise.resolve({})),
  },
}))

describe('Checklist Page', () => {
  it('renders methodology checklist items and state buttons', async () => {
    render(<Checklist />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Methodology Checklists/i })).toBeDefined()
    })
    await waitFor(() => {
      expect(screen.getByText('Enumerate directories and files')).toBeDefined()
      expect(screen.getByText('Overall Checklist Completion')).toBeDefined()
    })
  })
})
