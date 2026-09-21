import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { BarChart3, BookOpenCheck, Bot, Download, GitBranch } from 'lucide-react'
import { api } from '../../shared/api'

type Procedure = { template_id:string; code:string; title_i18n:Record<string,string>; version_id:string; version:number; status:string }
type Source = { id:string; title:string; issuer:string; url:string; excerpt:string; status:string; last_verified_at:string|null }
type DemoNotification = { id:string; event_type:string; label:string; created_at:string; payload:Record<string,unknown> }

export function AdminDashboard() {
  const { t, i18n } = useTranslation()
  const client = useQueryClient()
  const procedures = useQuery({ queryKey:['admin-procedures'], queryFn:()=>api<Procedure[]>('/admin/procedures') })
  const sources = useQuery({ queryKey:['admin-sources'], queryFn:()=>api<Source[]>('/admin/sources') })
  const metrics = useQuery({ queryKey:['admin-metrics'], queryFn:()=>api<Record<string,number|string>>('/admin/metrics') })
  const notifications = useQuery({ queryKey:['demo-notifications'], queryFn:()=>api<DemoNotification[]>('/admin/demo-notifications') })

  const importJson = async () => {
    const raw = window.prompt(i18n.language === 'ru' ? 'Вставьте JSON новой версии процедуры' : 'Paste the new procedure version JSON')
    if (!raw) return
    try {
      await api('/admin/procedures/import', { method:'POST', body:JSON.stringify(JSON.parse(raw)) })
      await client.invalidateQueries({ queryKey:['admin-procedures'] })
    } catch (error) {
      window.alert(error instanceof Error ? error.message : t('error'))
    }
  }
  const exportJson = async (item: Procedure) => {
    const data = await api<Record<string,unknown>>(`/admin/procedures/${item.version_id}/export`)
    const href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type:'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = href
    anchor.download = `${item.code}-v${item.version}.json`
    anchor.click()
    URL.revokeObjectURL(href)
  }
  const activate = async (item: Procedure) => {
    await api(`/admin/procedures/${item.version_id}/activate`, { method:'POST' })
    await client.invalidateQueries({ queryKey:['admin-procedures'] })
  }
  return <main className="wide-page">
    <div className="page-title"><div><p className="eyebrow">ORGANIZATION ADMIN</p><h1>Demo University</h1></div></div>
    <div className="admin-tabs"><button className="active"><BarChart3/>{t('analytics')}</button><button><GitBranch/>{t('procedures')}</button><button><BookOpenCheck/>{t('sources')}</button><button><Bot/>AI</button></div>
    <div className="metric-grid"><Metric value={Number(metrics.data?.cases_started||0)} label={i18n.language==='ru'?'Создано дел':'Cases started'}/><Metric value={Number(metrics.data?.submitted||0)} label={i18n.language==='ru'?'Отправлено':'Submitted'}/><Metric value={Number(metrics.data?.verified||0)} label={t('verified')}/><Metric value={Number(metrics.data?.changes_requested||0)} label={t('changes')}/></div>
    <div className="admin-columns">
      <section className="table-card"><div className="card-heading"><h2>{t('procedures')}</h2><button className="secondary" onClick={() => void importJson()}>Import JSON</button></div>{procedures.data?.map(item=><div className="admin-row" key={item.version_id}><span><strong>{item.title_i18n[i18n.language]||item.title_i18n.ru}</strong><small>{item.code}</small></span><span>v{item.version}</span><span className={`status status-${item.status.toLowerCase()}`}>{item.status}</span>{item.status==='DRAFT'&&<button className="secondary" onClick={() => void activate(item)}>Activate</button>}<button className="icon-button" aria-label="Export JSON" onClick={() => void exportJson(item)}><Download size={16}/></button></div>)}</section>
      <section className="table-card"><div className="card-heading"><h2>{t('sources')}</h2></div>{sources.data?.map(item=><a className="admin-row" href={item.url} target="_blank" rel="noreferrer" key={item.id}><span><strong>{item.title}</strong><small>{item.issuer}</small></span><span className={`status status-${item.status.toLowerCase()}`}>{item.status}</span></a>)}</section>
      <section className="table-card"><div className="card-heading"><h2>Demo notification inbox</h2></div>{notifications.data?.slice(0,8).map(item=><div className="admin-row" key={item.id}><span><strong>{item.event_type}</strong><small>{item.label}</small></span><span>{new Date(item.created_at).toLocaleTimeString()}</span></div>)}</section>
    </div>
    <p className="provenance-note">SYNTHETIC_DEMO · {i18n.language==='ru'?'Показатели отражают только локальные демонстрационные данные, не результаты пилота.':'Metrics reflect local demo data only, not pilot results.'}</p>
  </main>
}

function Metric({value,label}:{value:number;label:string}) { return <div className="metric"><strong>{value}</strong><span>{label}</span></div> }
