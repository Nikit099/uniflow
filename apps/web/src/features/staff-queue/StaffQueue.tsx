import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, Clock3, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, localize, type Case } from '../../shared/api'
import { Status } from '../student-dashboard/StudentDashboard'

export function StaffQueue(){
 const {t,i18n}=useTranslation()
 const cases=useQuery({queryKey:['staff-cases'],queryFn:()=>api<Case[]>('/staff/cases')})
 const summary=useQuery({queryKey:['staff-summary'],queryFn:()=>api<{waiting:number;changes:number;verified:number}>('/staff/summary')})
 const [filter,setFilter]=useState('all')
 const [search,setSearch]=useState('')
 const visibleCases=useMemo(()=>cases.data?.filter((item)=>{
   const matchesFilter=filter==='all'||item.status===filter
   const term=search.trim().toLocaleLowerCase()
   const matchesSearch=!term||[item.student_name,item.id,localize(item.procedure_title,i18n.language)].some((value)=>value?.toLocaleLowerCase().includes(term))
   return matchesFilter&&matchesSearch
 })||[],[cases.data,filter,search,i18n.language])

 if(cases.isLoading||summary.isLoading)return <div className="center">{t('loading')}</div>
 if(cases.isError||summary.isError)return <div className="center"><p>{t('error')}</p><button className="secondary" onClick={()=>void Promise.all([cases.refetch(),summary.refetch()])}>{t('retry')}</button></div>
 const emptyMessage=visibleCases.length===0?(search.trim()||filter!=='all'?t('noMatchingCases'):t('emptyQueue')):null

 return <main className="wide-page">
  <div className="page-title"><div><h1>{t('queue')}</h1></div><div className="search"><Search size={17}/><input value={search} onChange={(event)=>setSearch(event.target.value)} placeholder={t('queueSearch')}/></div></div>
  <div className="summary-grid"><Summary icon={Clock3} label={t('waiting')} value={summary.data?.waiting||0}/><Summary icon={AlertCircle} label={t('changes')} value={summary.data?.changes||0}/><Summary icon={CheckCircle2} label={t('verified')} value={summary.data?.verified||0}/></div>
  <section className="table-card"><div className="filters"><button className={filter==='all'?'active':''} onClick={()=>setFilter('all')}>{t('allCases')}</button><button className={filter==='READY_FOR_REVIEW'?'active':''} onClick={()=>setFilter('READY_FOR_REVIEW')}>{t('waiting')}</button><button className={filter==='CHANGES_REQUESTED'?'active':''} onClick={()=>setFilter('CHANGES_REQUESTED')}>{t('changes')}</button></div>
   <div className="queue-table"><div className="queue-row queue-head"><span>{i18n.language==='ru'?'Студент':'Student'}</span><span>{i18n.language==='ru'?'Процедура':'Procedure'}</span><span>{i18n.language==='ru'?'Статус':'Status'}</span><span>{t('progress')}</span><span/></div>
    {visibleCases.map(item=><Link className="queue-row" to={`/staff/cases/${item.id}`} key={item.id}><span><strong>{item.student_name}</strong></span><span>{localize(item.procedure_title,i18n.language)}</span><span><Status value={item.status}/></span><span>{item.progress}%</span><span>→</span></Link>)}
    {emptyMessage&&<div className="table-empty">{emptyMessage}</div>}
   </div>
  </section>
 </main>
}
function Summary({icon:Icon,label,value}:{icon:typeof Clock3;label:string;value:number}){return <div className="summary-card"><span><Icon size={20}/></span><div><strong>{value}</strong><small>{label}</small></div></div>}
