import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './shared/i18n'
import './styles.css'
import { App } from './app/App'

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10_000 } } })
createRoot(document.getElementById('root')!).render(<StrictMode><QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider></StrictMode>)

