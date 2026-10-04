import { useState } from 'react'
import { API_URL, getErrorMessage, urlApi } from '../services/api.js'
import CopyButton from './CopyButton.jsx'

const aliasPrefix = `${new URL(API_URL).host}/`

export default function UrlForm({ onCreated }) {
  const [originalUrl, setOriginalUrl] = useState('')
  const [customAlias, setCustomAlias] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState(null)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const response = await urlApi.create({
        original_url: originalUrl,
        custom_alias: customAlias.trim() || null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      })
      setCreated(response.data)
      setOriginalUrl('')
      setCustomAlias('')
      setExpiresAt('')
      onCreated(response.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="panel p-4 sm:p-6" aria-labelledby="shorten-heading">
      <h2 id="shorten-heading" className="text-lg font-bold">
        Shorten a link
      </h2>
      <form onSubmit={handleSubmit} className="mt-4 grid gap-4 md:grid-cols-6">
        <div className="md:col-span-6">
          <label htmlFor="original-url" className="field-label">
            Original URL
          </label>
          <input
            id="original-url"
            type="text"
            inputMode="url"
            className="field"
            placeholder="https://example.com/a/very/long/link"
            value={originalUrl}
            onChange={(event) => setOriginalUrl(event.target.value)}
            required
          />
        </div>
        <div className="md:col-span-3">
          <label htmlFor="custom-alias" className="field-label">
            Custom alias <span className="font-normal text-muted">(optional)</span>
          </label>
          <div className="flex">
            <span className="flex items-center rounded-l-md border border-r-0 border-line bg-canvas px-3 font-mono text-xs text-muted">
              {aliasPrefix}
            </span>
            <input
              id="custom-alias"
              type="text"
              className="field rounded-l-none"
              placeholder="my-portfolio"
              value={customAlias}
              onChange={(event) => setCustomAlias(event.target.value)}
              maxLength={32}
              autoComplete="off"
            />
          </div>
        </div>
        <div className="md:col-span-2">
          <label htmlFor="expires-at" className="field-label">
            Expires <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="expires-at"
            type="datetime-local"
            className="field"
            value={expiresAt}
            onChange={(event) => setExpiresAt(event.target.value)}
          />
        </div>
        <div className="flex items-end md:col-span-1">
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? 'Shortening…' : 'Shorten'}
          </button>
        </div>
      </form>

      {error && (
        <p role="alert" className="alert-error mt-4">
          {error}
        </p>
      )}

      {created && (
        <div className="mt-4 rounded-md bg-brand-soft p-4" role="status">
          <p className="text-sm font-semibold text-brand-dark">Your short link is ready</p>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <a
              href={created.short_url}
              target="_blank"
              rel="noopener noreferrer"
              className="break-all font-mono text-lg font-semibold text-brand-dark hover:underline"
            >
              {created.short_url}
            </a>
            <div className="flex gap-2">
              <CopyButton text={created.short_url} className="btn-primary btn-sm" />
              <a href={created.short_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                Open
              </a>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
