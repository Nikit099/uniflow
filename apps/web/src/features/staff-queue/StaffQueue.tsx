import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, Clock3, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, localize, type Case } from '../../shared/api'
import { Status } from '../student-dashboard/StudentDashboard'

export function StaffQueue(){
 const {t,i18n}=useTranslation();const cases=useQuery({queryKey:['staff-cases'],queryFn:()=>api<Case[]>('/staff/cases')});const summary=useQuery({queryKey:['staff-summary'],queryFn:()=>api<{waiting:number;changes:number;verified:number}>('/staff/summary')})
 return <main className="wide-page"><div className="page-title"><div><p className="eyebrow">DEMO UNIVERSITY</p><h1>{t('queue')}</h1></div><div className="search"><Search size={17}/><input placeholder={i18n.language==='ru'?'Поиск студента или дела':'Search student or case'}/></div></div><div className="summary-grid"><Summary icon={Clock3} label={t('waiting')} value={summary.data?.waiting||0}/><Summary icon={AlertCircle} label={t('changes')} value={summary.data?.changes||0}/><Summary icon={CheckCircle2} label={t('verified')} value={summary.data?.verified||0}/></div><section className="table-card"><div className="filters"><button className="active">{i18n.language==='ru'?'Все дела':'All cases'}</button><button>{t('waiting')}</button><button>{t('changes')}</button></div><div className="queue-table"><div className="queue-row queue-head"><span>{i18n.language==='ru'?'Студент':'Student'}</span><span>{i18n.language==='ru'?'Процедура':'Procedure'}</span><span>{i18n.language==='ru'?'Статус':'Status'}</span><span>{t('progress')}</span><span/></div>{cases.isLoading&&<div className="table-empty">{t('loading')}</div>}{cases.data?.map(item=><Link className="queue-row" to={`/staff/cases/${item.id}`} key={item.id}><span><strong>{item.student_name}</strong><small>{item.id.slice(0,8)}</small></span><span>{localize(item.procedure_title,i18n.language)}</span><span><Status value={item.status}/></span><span>{item.progress}%</span><span>→</span></Link>)}</div></section></main>
}
function Summary({icon:Icon,label,value}:{icon:typeof Clock3;label:string;value:number}){return <div className="summary-card"><span><Icon size={20}/></span><div><strong>{value}</strong><small>{label}</small></div></div>}

