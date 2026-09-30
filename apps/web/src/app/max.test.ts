import { afterEach, describe, expect, test } from 'vitest'
import { maxBridge } from './max'

const caseId = '8c8a326e-1df8-4d87-aaf1-d9ad6411ef60'

afterEach(() => {
  delete window.WebApp
  window.history.replaceState(null, '', '/')
})

describe('MAX start parameter', () => {
  test('opens the referenced case from signed launch data', () => {
    window.WebApp = { initData: `auth_date=2000000000&start_param=case_${caseId}` }

    expect(maxBridge.startCasePath()).toBe(`/cases/${caseId}`)
  })

  test('ignores malformed case references', () => {
    window.WebApp = { initData: 'auth_date=2000000000&start_param=case_not-a-uuid' }

    expect(maxBridge.startCasePath()).toBe('')
  })

  test('reads a local Mini App startapp query for browser testing', () => {
    window.history.replaceState(null, '', `/?startapp=case_${caseId}`)

    expect(maxBridge.startCasePath()).toBe(`/cases/${caseId}`)
  })
})
