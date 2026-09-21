import { expect, request, test } from '@playwright/test'

test('student correction and university verification flow', async ({ baseURL }) => {
  const student = await request.newContext({ baseURL })
  const staff = await request.newContext({ baseURL })
  const studentLogin = await student.post('/api/v1/auth/demo/login', { data: { role: 'student' } })
  const staffLogin = await staff.post('/api/v1/auth/demo/login', { data: { role: 'staff' } })
  expect(studentLogin.ok()).toBeTruthy()
  expect(staffLogin.ok()).toBeTruthy()
  const studentCsrf = (await studentLogin.json()).csrf_token as string
  const staffCsrf = (await staffLogin.json()).csrf_token as string
  const mutateStudent = { 'X-CSRF-Token': studentCsrf }
  const mutateStaff = { 'X-CSRF-Token': staffCsrf }

  const cases = await (await student.get('/api/v1/cases')).json()
  const caseId = cases[0].id as string
  const initial = await (await student.get(`/api/v1/cases/${caseId}`)).json()
  expect(initial.status).toBe('IN_PROGRESS')
  for (const item of initial.requirements) {
    const upload = await student.post(`/api/v1/cases/${caseId}/documents`, {
      headers: mutateStudent,
      multipart: {
        case_requirement_id: item.id,
        document_type: item.requirement.code,
        file: { name: `${item.id}.pdf`, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n% synthetic demo\n') },
      },
    })
    expect(upload.status()).toBe(201)
  }
  expect((await student.post(`/api/v1/cases/${caseId}/submit`, { headers: mutateStudent })).ok()).toBeTruthy()

  const review = await (await staff.get(`/api/v1/staff/cases/${caseId}`)).json()
  for (const item of review.requirements.slice(0, 2)) {
    expect((await staff.post(`/api/v1/staff/requirements/${item.id}/accept`, { headers: mutateStaff, data: { version: item.version } })).ok()).toBeTruthy()
  }
  const problem = review.requirements[2]
  expect((await staff.post(`/api/v1/staff/requirements/${problem.id}/request-changes`, { headers: mutateStaff, data: { version: problem.version, reason: 'Missing reverse side', reason_code: 'missing_page' } })).ok()).toBeTruthy()

  const correctionCase = await (await student.get(`/api/v1/cases/${caseId}`)).json()
  const correction = correctionCase.requirements.find((item: {status: string}) => item.status === 'CHANGES_REQUESTED')
  const replacement = await student.post(`/api/v1/cases/${caseId}/documents`, {
    headers: mutateStudent,
    multipart: {
      case_requirement_id: correction.id,
      document_type: correction.requirement.code,
      file: { name: 'corrected.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n% corrected synthetic demo\n') },
    },
  })
  expect(replacement.status()).toBe(201)
  expect((await student.post(`/api/v1/cases/${caseId}/submit`, { headers: mutateStudent })).ok()).toBeTruthy()

  const finalReview = await (await staff.get(`/api/v1/staff/cases/${caseId}`)).json()
  const finalItem = finalReview.requirements.find((item: {id: string}) => item.id === correction.id)
  expect((await staff.post(`/api/v1/staff/requirements/${finalItem.id}/accept`, { headers: mutateStaff, data: { version: finalItem.version } })).ok()).toBeTruthy()
  const verified = await staff.post(`/api/v1/staff/cases/${caseId}/verify`, { headers: mutateStaff })
  expect(verified.ok()).toBeTruthy()
  expect((await verified.json()).status).toBe('VERIFIED_BY_UNIVERSITY')
})
