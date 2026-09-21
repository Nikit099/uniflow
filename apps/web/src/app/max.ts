declare global { interface Window { WebApp?: { initData?: string; platform?: string; version?: string; enableClosingConfirmation?: () => void; openLink?: (url: string) => void; start_param?: string } } }

export const maxBridge = {
  initData: () => window.WebApp?.initData || '',
  openLink: (url: string) => window.WebApp?.openLink ? window.WebApp.openLink(url) : window.open(url, '_blank', 'noopener,noreferrer'),
  protectUnsaved: () => window.WebApp?.enableClosingConfirmation?.(),
  startParam: () => window.WebApp?.start_param,
}

