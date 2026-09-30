import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, ArrowLeft, Check, ChevronDown, FileText, Sparkles, Upload } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api, localize, type Case, type Requirement, type User } from '../../shared/api'
import { Status } from '../student-dashboard/StudentDashboard'

export function CasePage({ user }: { user: User }) {
  const { caseId = '' } = useParams()
  const { t, i18n } = useTranslation()
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['case',caseId], queryFn: () => api<Case>(`/cases/${caseId}`) })
  const submit = useMutation({ mutationFn: () => api(`/cases/${caseId}/submit`, {method:'POST'}), onSuccess: () => void client.invalidateQueries({queryKey:['case',caseId]}) })
  if (!query.data) return <div className="center"><p>{query.isError ? t('error') : t('loading')}</p>{query.isError&&<button className="secondary" onClick={()=>void query.refetch()}>{t('retry')}</button>}</div>
  const item = query.data
  const incomplete = item.requirements.some((r) => r.requirement.mandatory && !['SUBMITTED','ACCEPTED','NOT_APPLICABLE'].includes(r.status))
  return <main className="page case-page"><Link className="back" to={user.role==='STUDENT'?'/':'/staff'}><ArrowLeft size={17}/>{user.role==='STUDENT'?t('myCases'):t('queue')}</Link>
    <section className="case-header"><div><Status value={item.status}/><h1>{localize(item.procedure_title,i18n.language)}</h1></div><div className="header-progress"><strong>{item.progress}%</strong><span>{t('progress')}</span></div></section>
    {item.status==='VERIFIED_BY_UNIVERSITY' && <div className="result-banner"><Check/><strong>{t('verifiedNotice')}</strong></div>}
    <div className="timeline"><div className="done"><span>1</span>{i18n.language==='ru'?'Подготовка':'Preparation'}</div><div className={item.status==='IN_PROGRESS'?'':'done'}><span>2</span>{i18n.language==='ru'?'Проверка':'Review'}</div><div className={item.status==='VERIFIED_BY_UNIVERSITY'?'done':''}><span>3</span>{i18n.language==='ru'?'Результат':'Result'}</div></div>
    <section><div className="section-heading"><h2>{t('requirements')}</h2></div><div className="requirements">{item.requirements.map((requirement,index)=><RequirementCard key={requirement.id} item={requirement} index={index+1} caseId={item.id} canEdit={user.role==='STUDENT' && ['IN_PROGRESS','CHANGES_REQUESTED'].includes(item.status)} onChanged={()=>client.invalidateQueries({queryKey:['case',caseId]})}/>)}</div></section>
    {user.role==='STUDENT' && ['IN_PROGRESS','CHANGES_REQUESTED'].includes(item.status) && <p className="upload-warning">{t('uploadWarning')}</p>}
    {user.role==='STUDENT' && ['IN_PROGRESS','CHANGES_REQUESTED'].includes(item.status) && <div className="submit-bar"><div>{incomplete&&<strong>{i18n.language==='ru'?'Заполните обязательные пункты':'Complete required items'}</strong>}{submit.error&&<small className="inline-error">{submit.error.message}</small>}</div><button className="primary" disabled={incomplete||submit.isPending} onClick={()=>submit.mutate()}>{t('submit')}</button></div>}
  </main>
}

function RequirementCard({item,index,caseId,canEdit,onChanged}:{item:Requirement;index:number;caseId:string;canEdit:boolean;onChanged:()=>Promise<void>}){
  const {t,i18n}=useTranslation()
  const [open,setOpen]=useState(item.status==='CHANGES_REQUESTED')
  const [ai,setAi]=useState('')
  const [busy,setBusy]=useState(false)
  const [uploadError,setUploadError]=useState(false)
  const upload=async(file:File)=>{
    setBusy(true)
    setUploadError(false)
    const data=new FormData()
    data.append('case_requirement_id',item.id)
    data.append('document_type',item.requirement.code)
    data.append('file',file)
    try{
      await api(`/cases/${caseId}/documents`,{method:'POST',body:data})
      await onChanged()
    }catch{
      setUploadError(true)
    }finally{
      setBusy(false)
    }
  }
  const explain=async()=>{setAi('');try{const result=await api<{answer:string}>('/ai/explain-requirement',{method:'POST',body:JSON.stringify({case_requirement_id:item.id,language:i18n.language})});setAi(result.answer)}catch{setAi(t('aiUnavailable'))}}
  return <article className={`requirement-card ${item.status==='CHANGES_REQUESTED'?'has-issue':''}`}>
    <button className="requirement-head" onClick={()=>setOpen(!open)}><span className="number">{item.status==='ACCEPTED'?<Check size={18}/>:index}</span><span className="grow"><strong>{localize(item.requirement.title_i18n,i18n.language)}</strong></span><Status value={item.status}/><ChevronDown className={open?'rotated':''}/></button>
    {open&&<div className="requirement-body">
      <p className="student-action">{localize(item.requirement.student_action_i18n,i18n.language)}</p>
      {item.staff_comment&&<div className="issue"><AlertTriangle size={18}/><div><strong>{i18n.language==='ru'?'Комментарий сотрудника':'Staff comment'}</strong><p>{item.staff_comment}</p></div></div>}
      <div className="file-list">{item.documents.map(doc=><a href={`/api/v1/documents/${doc.id}`} target="_blank" rel="noreferrer" key={doc.id}><FileText size={18}/><span>{doc.original_filename}</span></a>)}</div>
      {canEdit&&<label className="upload-button"><Upload size={18}/>{busy?t('loading'):t('upload')}<input type="file" accept=".pdf,.jpg,.jpeg,.png" disabled={busy} onChange={event=>{const file=event.target.files?.[0];event.target.value='';if(file)void upload(file)}}/></label>}
      {uploadError&&<p className="inline-error" role="alert">{t('uploadFailed')}</p>}
      <button className="ai-button" onClick={()=>void explain()}><Sparkles size={17}/>{t('explain')}</button>
      {ai&&<div className="ai-response"><p>{ai}</p></div>}
    </div>}
  </article>
}
