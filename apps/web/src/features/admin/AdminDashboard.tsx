import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Download } from 'lucide-react'
import { api } from '../../shared/api'
import { Status } from '../student-dashboard/StudentDashboard'

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

  if (procedures.isLoading || sources.isLoading || metrics.isLoading || notifications.isLoading) return <div className="center">{t('loading')}</div>
  if (procedures.isError || sources.isError || metrics.isError || notifications.isError) return <div className="center"><p>{t('error')}</p><button className="secondary" onClick={() => void Promise.all([procedures.refetch(), sources.refetch(), metrics.refetch(), notifications.refetch()])}>{t('retry')}</button></div>

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
    <div className="page-title"><h1>{t('admin')}</h1></div>
    <div className="metric-grid"><Metric value={Number(metrics.data?.cases_started||0)} label={t('casesStarted')}/><Metric value={Number(metrics.data?.submitted||0)} label={t('submitted')}/><Metric value={Number(metrics.data?.verified||0)} label={t('verified')}/><Metric value={Number(metrics.data?.changes_requested||0)} label={t('changes')}/></div>
    <div className="admin-columns">
      <section className="table-card"><div className="card-heading"><h2>{t('procedures')}</h2><button className="secondary" onClick={() => void importJson()}>{t('importJson')}</button></div>{procedures.data?.map(item=><div className="admin-row" key={item.version_id}><span><strong>{item.title_i18n[i18n.language]||item.title_i18n.ru}</strong><small>{item.code}</small></span><span>v{item.version}</span><Status value={item.status}/>{item.status==='DRAFT'&&<button className="secondary" onClick={() => void activate(item)}>{t('activate')}</button>}<button className="icon-button" aria-label={t('exportJson')} onClick={() => void exportJson(item)}><Download size={16}/></button></div>)}{procedures.data?.length===0&&<div className="table-empty">{t('emptyProcedures')}</div>}</section>
      <section className="table-card"><div className="card-heading"><h2>{t('sources')}</h2></div>{sources.data?.map(item=><a className="admin-row" href={item.url} target="_blank" rel="noreferrer" key={item.id}><span><strong>{item.title}</strong><small>{item.issuer}</small></span><Status value={item.status}/></a>)}{sources.data?.length===0&&<div className="table-empty">{t('emptySources')}</div>}</section>
      <section className="table-card"><div className="card-heading"><h2>{t('notifications')}</h2></div>{notifications.data?.slice(0,8).map(item=><div className="admin-row" key={item.id}><span><strong>{notificationLabel(item.event_type,i18n.language)}</strong></span><span>{new Intl.DateTimeFormat(i18n.language,{hour:'2-digit',minute:'2-digit'}).format(new Date(item.created_at))}</span></div>)}{notifications.data?.length===0&&<div className="table-empty">{t('emptyNotifications')}</div>}</section>
    </div>
  </main>
}

function Metric({value,label}:{value:number;label:string}) { return <div className="metric"><strong>{value}</strong><span>{label}</span></div> }

function notificationLabel(event:string,language:string) {
  const labels:Record<string,{ru:string;en:string}>={
    CASE_SUBMITTED:{ru:'Комплект отправлен',en:'Package submitted'},
    CHANGES_REQUESTED:{ru:'Нужно исправление',en:'Changes requested'},
    CASE_VERIFIED:{ru:'Проверка завершена',en:'Review completed'},
    STAFF_MESSAGE:{ru:'Сообщение сотруднику',en:'Message to staff'},
    BOT_REPLY:{ru:'Ответ бота',en:'Bot reply'},
  }
  return labels[event]?.[language==='ru'?'ru':'en']||event.replaceAll('_',' ')
}
