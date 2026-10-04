import { Link } from 'react-router-dom'
import { displayUrl, formatDate } from '../utils/format.js'
import CopyButton from './CopyButton.jsx'

function isExpired(url) {
  return Boolean(url.expires_at) && new Date(url.expires_at) <= new Date()
}

function StatusBadge({ url }) {
  if (!url.is_active) return <span className="rounded-full bg-canvas px-2 py-0.5 text-xs font-semibold text-muted">Disabled</span>
  if (isExpired(url)) return <span className="rounded-full bg-danger-soft px-2 py-0.5 text-xs font-semibold text-danger">Expired</span>
  if (url.expires_at) {
    return (
      <span className="rounded-full bg-canvas px-2 py-0.5 text-xs font-semibold text-muted">
        Expires {formatDate(url.expires_at)}
      </span>
    )
  }
  return null
}

function ShortLink({ url }) {
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <a
          href={url.short_url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-sm font-semibold text-brand hover:underline"
        >
          {displayUrl(url.short_url)}
        </a>
        <StatusBadge url={url} />
      </div>
      <p className="mt-0.5 max-w-md truncate text-xs text-muted" title={url.original_url}>
        {url.original_url}
      </p>
    </div>
  )
}

function Actions({ url, onDelete, deleting }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <CopyButton text={url.short_url} />
      <Link to={`/analytics/${url.id}`} className="btn-secondary btn-sm">
        Analytics
      </Link>
      <button type="button" className="btn-danger btn-sm" onClick={() => onDelete(url)} disabled={deleting}>
        {deleting ? 'Deleting…' : 'Delete'}
      </button>
    </div>
  )
}

export default function UrlTable({ urls, onDelete, deletingId }) {
  if (urls.length === 0) {
    return (
      <div className="panel p-10 text-center">
        <p className="font-semibold">No links yet</p>
        <p className="mt-1 text-sm text-muted">Paste a long URL above to create your first short link.</p>
      </div>
    )
  }

  return (
    <div className="panel overflow-hidden">
      {/* Tablet and desktop: table */}
      <table className="hidden w-full text-left text-sm md:table">
        <thead className="border-b border-line bg-canvas text-muted">
          <tr>
            <th scope="col" className="px-4 py-3 font-semibold">Link</th>
            <th scope="col" className="px-4 py-3 text-right font-semibold">Clicks</th>
            <th scope="col" className="px-4 py-3 font-semibold">Created</th>
            <th scope="col" className="px-4 py-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {urls.map((url) => (
            <tr key={url.id}>
              <td className="px-4 py-3">
                <ShortLink url={url} />
              </td>
              <td className="px-4 py-3 text-right font-semibold tabular-nums">{url.click_count.toLocaleString()}</td>
              <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDate(url.created_at)}</td>
              <td className="px-4 py-3">
                <Actions url={url} onDelete={onDelete} deleting={deletingId === url.id} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile: stacked list */}
      <ul className="divide-y divide-line md:hidden">
        {urls.map((url) => (
          <li key={url.id} className="space-y-3 p-4">
            <ShortLink url={url} />
            <p className="text-xs text-muted">
              <span className="font-semibold text-ink">{url.click_count.toLocaleString()}</span> clicks · created{' '}
              {formatDate(url.created_at)}
            </p>
            <Actions url={url} onDelete={onDelete} deleting={deletingId === url.id} />
          </li>
        ))}
      </ul>
    </div>
  )
}
