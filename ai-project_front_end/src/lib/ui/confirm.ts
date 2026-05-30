export type ConfirmActionOptions = {
  title?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

let closeActiveConfirm: (() => void) | null = null

export function confirmAction(message: string, options: ConfirmActionOptions = {}): Promise<boolean> {
  if (typeof document === 'undefined') return Promise.resolve(false)

  closeActiveConfirm?.()

  return new Promise((resolve) => {
    const overlay = document.createElement('div')
    overlay.setAttribute('role', 'dialog')
    overlay.setAttribute('aria-modal', 'true')
    overlay.style.cssText = [
      'position:fixed',
      'inset:0',
      'z-index:1000',
      'display:flex',
      'align-items:center',
      'justify-content:center',
      'background:rgba(0,0,0,0.45)',
      'padding:16px'
    ].join(';')

    const card = document.createElement('div')
    card.style.cssText = [
      'width:100%',
      'max-width:360px',
      'border-radius:14px',
      'background:#fff',
      'box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)',
      'overflow:hidden',
      'font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    ].join(';')

    const body = document.createElement('div')
    body.style.cssText = 'padding:22px 22px 16px'

    const title = document.createElement('div')
    title.textContent = options.title || '确认操作'
    title.style.cssText = 'font-size:16px;font-weight:600;line-height:24px;color:#0A0A0A'

    const content = document.createElement('div')
    content.textContent = message
    content.style.cssText = 'margin-top:8px;font-size:14px;line-height:20px;color:#52525B;white-space:pre-line'

    const footer = document.createElement('div')
    footer.style.cssText = 'display:flex;justify-content:flex-end;gap:8px;padding:12px 22px 20px'

    const cancelButton = document.createElement('button')
    cancelButton.type = 'button'
    cancelButton.textContent = options.cancelText || '取消'
    cancelButton.style.cssText = [
      'height:34px',
      'border-radius:10px',
      'border:1px solid rgba(0,0,0,0.1)',
      'background:#fff',
      'padding:0 14px',
      'font-size:14px',
      'font-weight:500',
      'color:#0A0A0A',
      'cursor:pointer'
    ].join(';')

    const confirmButton = document.createElement('button')
    confirmButton.type = 'button'
    confirmButton.textContent = options.confirmText || '确认'
    confirmButton.style.cssText = [
      'height:34px',
      'border-radius:10px',
      'border:0',
      `background:${options.danger === false ? '#155DFC' : '#DC2626'}`,
      'padding:0 14px',
      'font-size:14px',
      'font-weight:500',
      'color:#fff',
      'cursor:pointer'
    ].join(';')

    let settled = false
    const settle = (value: boolean) => {
      if (settled) return
      settled = true
      closeActiveConfirm = null
      window.removeEventListener('keydown', onKeydown)
      overlay.remove()
      resolve(value)
    }
    const onKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') settle(false)
    }

    cancelButton.addEventListener('click', () => settle(false))
    confirmButton.addEventListener('click', () => settle(true))
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) settle(false)
    })
    window.addEventListener('keydown', onKeydown)

    body.append(title, content)
    footer.append(cancelButton, confirmButton)
    card.append(body, footer)
    overlay.append(card)
    document.body.append(overlay)
    closeActiveConfirm = () => settle(false)
    window.setTimeout(() => confirmButton.focus(), 0)
  })
}
