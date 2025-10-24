import { useEffect, useId, useRef, useState } from 'react'
import './AboutButton.css'

interface AboutButtonProps {
  variant?: 'desktop' | 'mobile'
  className?: string
}

const creatorUrl = 'https://www.linkedin.com/in/liavalter/'

function AboutButton({ variant = 'desktop', className }: AboutButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const uniqueId = useId()
  const popoverId = `about-popover-${uniqueId}`

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (
        buttonRef.current &&
        !buttonRef.current.contains(target) &&
        popoverRef.current &&
        !popoverRef.current.contains(target)
      ) {
        setIsOpen(false)
      }
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const wrapperClasses = [
    'about-button-wrapper',
    `about-button-wrapper--${variant}`,
    className
  ]
    .filter(Boolean)
    .join(' ')

  const togglePopover = () => {
    setIsOpen((prev) => !prev)
  }

  return (
    <div className={wrapperClasses}>
      <button
        ref={buttonRef}
        type="button"
        className="about-btn"
        onClick={togglePopover}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls={popoverId}
        title="About the creator"
      >
        <svg viewBox="0 0 24 24" className="about-icon" aria-hidden="true" focusable="false">
          <path d="M11 7h2v2h-2zm1-5C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-4h2v-6h-2v6z" />
        </svg>
      </button>
      {isOpen && (
        <div
          ref={popoverRef}
          id={popoverId}
          role="dialog"
          aria-modal="false"
          className="about-popover"
        >
          Created by{' '}
          <a href={creatorUrl} target="_blank" rel="noopener noreferrer">
            Liav Alter
          </a>
        </div>
      )}
    </div>
  )
}

export default AboutButton
