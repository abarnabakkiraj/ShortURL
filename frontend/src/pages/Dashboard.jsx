import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AnalyticsCard from '../components/AnalyticsCard.jsx'
import UrlForm from '../components/UrlForm.jsx'
import UrlTable from '../components/UrlTable.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { analyticsApi, getErrorMessage, urlApi } from '../services/api.js'
import { displayUrl } from '../utils/format.js'

export default function Dashboard() {
  const { user } = useAuth()
  const [urls, setUrls] = useState([])
  const [topUrls, setTopUrls] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  const loadData = useCallback(async () => {
    try {
      const [list, top] = await Promise.all([urlApi.list(), analyticsApi.topUrls(3)])
      setUrls(list.data)
      setTopUrls(top.data)
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    // Refresh counts when the user comes back from a tab where they opened a short link.
    window.addEventListener('focus', loadData)
    return () => window.removeEventListener('focus', loadData)
  }, [loadData])

  const handleDelete = async (url) => {
    const confirmed = window.confirm(`Delete ${displayUrl(url.short_url)}? Its click history will be deleted too.`)
    if (!confirmed) return
    setDeletingId(url.id)
    try {
      await urlApi.remove(url.id)
      await loadData()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  const totalClicks = urls.reduce((sum, url) => sum + url.click_count, 0)

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-extrabold sm:text-3xl">Welcome back, {user.name.split(' ')[0]}</h1>
        <p className="mt-1 text-muted">Create short links and see how they perform.</p>
      </div>

      <UrlForm onCreated={loadData} />

      {error && <p role="alert" className="alert-error">{error}</p>}

      {loading ? (
        <div className="flex justify-center py-12" role="status" aria-label="Loading links">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-line border-t-brand" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <AnalyticsCard label="Links" value={urls.length} />
            <AnalyticsCard label="Total clicks" value={totalClicks} />
            <div className="panel col-span-2 p-4 sm:col-span-1 sm:p-5">
              <p className="text-sm font-medium text-muted">Top links</p>
              {topUrls.length === 0 ? (
                <p className="mt-2 text-sm text-muted">Links with clicks will show up here.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {topUrls.map((url) => (
                    <li key={url.id} className="flex items-center justify-between gap-3 text-sm">
                      <Link to={`/analytics/${url.id}`} className="truncate font-mono text-brand hover:underline">
                        {url.short_code}
                      </Link>
                      <span className="font-semibold tabular-nums">{url.click_count.toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <section aria-labelledby="links-heading">
            <h2 id="links-heading" className="mb-3 text-lg font-bold">Your links</h2>
            <UrlTable urls={urls} onDelete={handleDelete} deletingId={deletingId} />
          </section>
        </>
      )}
    </main>
  )
}
