declare global {
  interface Window {
    WebApp?: {
      initData?: string
    }
  }
}

export const maxBridge = {
  initData: () => window.WebApp?.initData || new URLSearchParams(window.location.hash.slice(1)).get('WebAppData') || '',
  isAvailable: () => Boolean(window.WebApp || new URLSearchParams(window.location.hash.slice(1)).has('WebAppData')),
  startCasePath: () => {
    const param = new URLSearchParams(maxBridge.initData()).get('start_param') || new URLSearchParams(window.location.search).get('startapp') || ''
    const match = /^case_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i.exec(param)
    return match ? `/cases/${match[1]}` : ''
  },
}
