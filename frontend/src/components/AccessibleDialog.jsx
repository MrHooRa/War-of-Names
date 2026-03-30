import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([type="hidden"]):not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

let activeDialogCount = 0
let previousBodyOverflow = ''
let previousBodyPaddingRight = ''

function isVisible(element) {
  const style = window.getComputedStyle(element)
  return style.display !== 'none' && style.visibility !== 'hidden'
}

function getFocusableElements(container) {
  if (!container) return []

  return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
    .filter((element) => element instanceof HTMLElement && isVisible(element))
}

export default function AccessibleDialog({
  children,
  onClose,
  titleId,
  descriptionId,
  panelClassName = '',
  backdropClassName = '',
  closeOnBackdrop = true,
  zIndexClass = 'z-50',
}) {
  const panelRef = useRef(null)

  useEffect(() => {
    if (typeof document === 'undefined') return undefined

    const previousActiveElement = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null

    activeDialogCount += 1

    if (activeDialogCount === 1) {
      previousBodyOverflow = document.body.style.overflow
      previousBodyPaddingRight = document.body.style.paddingRight

      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
      document.body.style.overflow = 'hidden'
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`
      }
    }

    const frameId = window.requestAnimationFrame(() => {
      const panel = panelRef.current
      if (!panel) return

      const preferredTarget = panel.querySelector('[data-dialog-initial-focus]')
      const firstFocusable = getFocusableElements(panel)[0]
      const focusTarget = preferredTarget instanceof HTMLElement
        ? preferredTarget
        : firstFocusable || panel

      focusTarget.focus({ preventScroll: true })
    })

    return () => {
      window.cancelAnimationFrame(frameId)
      activeDialogCount = Math.max(0, activeDialogCount - 1)

      if (activeDialogCount === 0) {
        document.body.style.overflow = previousBodyOverflow
        document.body.style.paddingRight = previousBodyPaddingRight
      }

      previousActiveElement?.focus?.({ preventScroll: true })
    }
  }, [])

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
      return
    }

    if (event.key !== 'Tab') return

    const focusableElements = getFocusableElements(panelRef.current)
    if (focusableElements.length === 0) {
      event.preventDefault()
      panelRef.current?.focus({ preventScroll: true })
      return
    }

    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]
    const activeElement = document.activeElement

    if (event.shiftKey && activeElement === firstElement) {
      event.preventDefault()
      lastElement.focus({ preventScroll: true })
      return
    }

    if (!event.shiftKey && activeElement === lastElement) {
      event.preventDefault()
      firstElement.focus({ preventScroll: true })
    }
  }

  return (
    <div
      className={`fixed inset-0 ${zIndexClass} overflow-y-auto p-4 sm:p-6`}
      style={{
        paddingTop: 'max(1rem, env(safe-area-inset-top))',
        paddingBottom: 'max(1rem, env(safe-area-inset-bottom))',
      }}
    >
      <div className="flex min-h-full items-start justify-center sm:items-center">
        <div
          aria-hidden="true"
          className={`absolute inset-0 bg-black/50 backdrop-blur-sm ${backdropClassName}`}
          onClick={closeOnBackdrop ? onClose : undefined}
        />

        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          tabIndex={-1}
          onKeyDown={handleKeyDown}
          className={`relative z-10 w-full max-h-[calc(100dvh-2rem)] outline-none ${panelClassName}`}
        >
          {children}
        </div>
      </div>
    </div>
  )
}
