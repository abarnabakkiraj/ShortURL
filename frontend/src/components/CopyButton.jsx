import { useEffect, useRef, useState } from 'react'
import { copyText } from '../utils/format.js'

export default function CopyButton({ text, className = 'btn-secondary btn-sm' }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  const handleCopy = async () => {
    if (await copyText(text)) {
      setCopied(true)
      clearTimeout(timer.current)
      timer.current = setTimeout(() => setCopied(false), 1800)
    }
  }

  return (
    <button type="button" onClick={handleCopy} className={className} aria-live="polite">
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}
