import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Check, ExternalLink, RotateCcw } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api, localize, type Case, type Requirement } from '../../shared/api'
import { Status } from '../student-dashboard/StudentDashboard'

export function StaffReview() {
  const { caseId = '' } = useParams()
  const { t, i18n } = useTranslation()
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['staff-case', caseId], queryFn: () => api<Case>(`/staff/cases/${caseId}`) })
  const refresh = () => void client.invalidateQueries({ queryKey: ['staff-case', caseId] })
  const assign = useMutation({ mutationFn: () => api(`/staff/cases/${caseId}/assign`, { method: 'POST' }), onSuccess: refresh })
  const verify = useMutation({ mutationFn: () => api(`/staff/cases/${caseId}/verify`, { method: 'POST' }), onSuccess: refresh })

  if (!query.data) {
    return <div className="center"><p>{query.isError ? t('error') : t('loading')}</p>{query.isError && <button className="secondary" onClick={() => void query.refetch()}>{t('retry')}</button>}</div>
  }

  const data = query.data
  const canVerify = data.requirements
    .filter((item) => item.requirement.mandatory)
    .every((item) => ['ACCEPTED', 'NOT_APPLICABLE'].includes(item.status))

  return <main className="wide-page">
    <Link className="back" to="/staff"><ArrowLeft size={17}/>{t('queue')}</Link>
    <div className="review-layout">
      <aside className="context-panel">
        <h1>{data.student_name}</h1>
        <Status value={data.status}/>
        <dl>
          <dt>{i18n.language === 'ru' ? 'Процедура' : 'Procedure'}</dt>
          <dd>{localize(data.procedure_title, i18n.language)}</dd>
        </dl>
        {!data.assigned_staff_user_id && <button className="secondary full" onClick={() => assign.mutate()}>{t('assign')}</button>}
        {assign.error && <p className="inline-error" role="alert">{assign.error.message}</p>}
        <div className="boundary">
          <strong>{i18n.language === 'ru' ? 'Проверка университета' : 'University review'}</strong>
          <p>{i18n.language === 'ru' ? 'Это не решение госоргана.' : 'This is not a government decision.'}</p>
        </div>
      </aside>
      <section className="review-main">
        <div className="section-heading"><h2>{t('requirements')}</h2></div>
        {data.requirements.map((item) => <ReviewItem key={item.id} item={item} onChanged={refresh}/>) }
        <div className="verify-panel">
          <button className="primary" disabled={!canVerify || verify.isPending} onClick={() => verify.mutate()}>
            <Check size={18}/>{t('verify')}
          </button>
          {verify.error && <p className="inline-error" role="alert">{verify.error.message}</p>}
        </div>
      </section>
    </div>
  </main>
}

function ReviewItem({ item, onChanged }: { item: Requirement; onChanged: () => void }) {
  const { t, i18n } = useTranslation()
  const [reasonOpen, setReasonOpen] = useState(false)
  const [reason, setReason] = useState('')
  const accept = useMutation({
    mutationFn: () => api(`/staff/requirements/${item.id}/accept`, {
      method: 'POST',
      body: JSON.stringify({ version: item.version }),
    }),
    onSuccess: onChanged,
  })
  const changes = useMutation({
    mutationFn: (reason: string) => api(`/staff/requirements/${item.id}/request-changes`, {
      method: 'POST',
      body: JSON.stringify({ version: item.version, reason, reason_code: 'other' }),
    }),
    onSuccess: () => {
      setReasonOpen(false)
      setReason('')
      onChanged()
    },
  })

  const submitReason = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmedReason = reason.trim()
    if (trimmedReason) changes.mutate(trimmedReason)
  }

  return <article className="review-item">
    <div className="review-title">
      <h3>{localize(item.requirement.title_i18n, i18n.language)}</h3>
      <Status value={item.status}/>
    </div>
    {item.documents.map((document) => <a className="document-preview" href={`/api/v1/documents/${document.id}`} target="_blank" rel="noreferrer" key={document.id}>
      <span className="fake-preview">PDF</span>
      <span><strong>{document.original_filename}</strong></span>
      <ExternalLink size={17}/>
    </a>)}
    {item.staff_comment && <div className="issue">{item.staff_comment}</div>}
    <div className="review-actions">
      <button className="accept" disabled={accept.isPending} onClick={() => accept.mutate()}><Check size={17}/>{t('accept')}</button>
      <button className="changes" disabled={changes.isPending} onClick={() => { setReason(''); setReasonOpen(true) }}><RotateCcw size={17}/>{t('requestChanges')}</button>
    </div>
    {(accept.error || changes.error) && <p className="inline-error" role="alert">{(accept.error || changes.error)?.message}</p>}
    {reasonOpen && <div className="dialog-backdrop" onKeyDown={(event) => { if (event.key === 'Escape' && !changes.isPending) setReasonOpen(false) }}>
      <section className="reason-dialog" role="dialog" aria-modal="true" aria-labelledby={`reason-title-${item.id}`}>
        <h2 id={`reason-title-${item.id}`}>{t('requestChanges')}</h2>
        <p>{localize(item.requirement.title_i18n, i18n.language)}</p>
        <form onSubmit={submitReason}>
          <label htmlFor={`reason-input-${item.id}`}>{t('reason')}</label>
          <textarea id={`reason-input-${item.id}`} autoFocus required value={reason} onChange={(event) => setReason(event.target.value)} />
          {changes.error && <p className="inline-error" role="alert">{changes.error.message}</p>}
          <div className="reason-actions">
            <button className="secondary" type="button" onClick={() => setReasonOpen(false)}>{t('cancel')}</button>
            <button className="primary" type="submit" disabled={!reason.trim() || changes.isPending}>{t('sendReason')}</button>
          </div>
        </form>
      </section>
    </div>}
  </article>
}
