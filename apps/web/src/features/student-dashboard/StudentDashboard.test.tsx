import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import '../../shared/i18n'
import { StudentDashboard } from './StudentDashboard'

beforeEach(() => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok:true,status:200,json:async()=>[]})) })
test('renders empty student dashboard', async () => { render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><StudentDashboard/></MemoryRouter></QueryClientProvider>); expect(await screen.findByText(/Нет активных дел|No active cases/)).toBeInTheDocument() })

