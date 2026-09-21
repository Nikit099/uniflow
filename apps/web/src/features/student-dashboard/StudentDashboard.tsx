import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { ArrowRight, CalendarDays, CheckCircle2, Clock3, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { api, localize, type Case } from '../../shared/api'

export function StudentDashboard() {
  const { t, i18n } = useTranslation()
  const query = useQuery({ queryKey: ['cases'], queryFn: () => api<Case[]>('/cases') })
  if (query.isLoading) return <PageState text={t('loading')}/>
  if (query.isError) return <PageState text={t('error')} retry={() => void query.refetch()}/>
  const current = query.data?.find((item) => !['COMPLETED','CANCELLED'].includes(item.status))
  return <main className="page"><section className="welcome"><p className="eyebrow">DEMO UNIVERSITY</p><h1>{i18n.language === 'ru' ? 'Здравствуйте!' : 'Hello!'}</h1><p>{i18n.language === 'ru' ? 'Мы собрали действия по вашему делу в одном месте.' : 'Your case actions are collected in one place.'}</p></section>
    {current ? <section className="next-card"><div className="next-label"><Sparkles size={17}/>{t('nextAction')}</div><div className="next-grid"><div><Status value={current.status}/><h2>{nextTitle(current.status, i18n.language)}</h2><p>{localize(current.procedure_title, i18n.language)}</p><Link className="primary" to={`/cases/${current.id}`}>{t('open')}<ArrowRight size={18}/></Link></div><div className="progress-panel"><div className="progress-ring" style={{'--progress': `${current.progress * 3.6}deg`} as React.CSSProperties}><span>{current.progress}%</span></div><div><strong>{t('progress')}</strong>{current.due_at && <span className="deadline"><CalendarDays size={16}/>{format(new Date(current.due_at), 'dd.MM.yyyy')}</span>}</div></div></div></section> : <section className="empty"><CheckCircle2/><h2>{t('noCases')}</h2></section>}
    <section><div className="section-heading"><h2>{t('myCases')}</h2><span>{query.data?.length || 0}</span></div><div className="case-list">{query.data?.map((item) => <Link to={`/cases/${item.id}`} className="case-row" key={item.id}><span className="case-icon"><Clock3/></span><span className="grow"><strong>{localize(item.procedure_title, i18n.language)}</strong><small>{item.id.slice(0,8)} · {item.progress}%</small></span><Status value={item.status}/><ArrowRight size={18}/></Link>)}</div></section>
  </main>
}

const nextTitle = (status: string, language: string) => language === 'ru' ? ({IN_PROGRESS:'Добавьте документы в комплект',CHANGES_REQUESTED:'Исправьте замечания сотрудника',READY_FOR_REVIEW:'Комплект ожидает проверки',UNDER_REVIEW:'Сотрудник проверяет комплект',VERIFIED_BY_UNIVERSITY:'Комплект проверен университетом'}[status] || 'Откройте дело') : ({IN_PROGRESS:'Add documents to the package',CHANGES_REQUESTED:'Resolve staff comments',READY_FOR_REVIEW:'Package is awaiting review',UNDER_REVIEW:'Staff is reviewing the package',VERIFIED_BY_UNIVERSITY:'Package verified by university'}[status] || 'Open your case')
export function Status({value}:{value:string}) { return <span className={`status status-${value.toLowerCase()}`}>{value.replaceAll('_',' ')}</span> }
function PageState({text,retry}:{text:string,retry?:()=>void}) { const {t}=useTranslation(); return <div className="center"><p>{text}</p>{retry&&<button onClick={retry}>{t('retry')}</button>}</div> }

