import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import AnalyticsCard from '../components/AnalyticsCard.jsx'
import BreakdownChart from '../components/BreakdownChart.jsx'
import CopyButton from '../components/CopyButton.jsx'
import { analyticsApi, getErrorMessage } from '../services/api.js'
import { formatShortDay } from '../utils/format.js'

const RANGES = [7, 30, 90]

export default function Analytics() {
  const { id } = useParams()
  const [days, setDays] = useState(30)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    analyticsApi
      .get(id, days)
      .then((response) => {
        if (cancelled) return
        setData(response.data)
        setError('')
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, days])

  const backLink = (
    <Link to="/dashboard" className="text-sm font-semibold text-brand hover:underline">
      ← Back to dashboard
    </Link>
  )

  if (error && !data) {
    return (
      <main className="mx-auto max-w-6xl space-y-4 px-4 py-8 sm:px-6">
        {backLink}
        <p role="alert" className="alert-error">{error}</p>
      </main>
    )
  }

  if (!data) {
    return (
      <div className="flex justify-center py-24" role="status" aria-label="Loading analytics">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-line border-t-brand" />
      </div>
    )
  }

  const { url, summary } = data
  const timeline = data.timeline.map((point) => ({ date: formatShortDay(point.date), clicks: point.clicks }))
  const hasKnownCountry = data.countries.some((country) => country.name !== 'Unknown')

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      {backLink}

      <div className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="min-w-0">
          <a href={url.short_url} target="_blank" rel="noopener noreferrer" className="break-all font-mono text-xl font-bold text-brand hover:underline">
            {url.short_url}
          </a>
          <p className="mt-1 truncate text-sm text-muted" title={url.original_url}>{url.original_url}</p>
        </div>
        <CopyButton text={url.short_url} />
      </div>

      {error && <p role="alert" className="alert-error">{error}</p>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <AnalyticsCard label="Total clicks" value={summary.total_clicks} />
        <AnalyticsCard label="Today" value={summary.clicks_today} hint="Since midnight UTC" />
        <AnalyticsCard label="This week" value={summary.clicks_this_week} hint="Last 7 days" />
        <AnalyticsCard label="This month" value={summary.clicks_this_month} hint="Last 30 days" />
      </div>

      <section className="panel p-4 sm:p-5" aria-label="Clicks over time">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-bold">Clicks over time</h2>
          <div className="flex gap-1" role="group" aria-label="Time range">
            {RANGES.map((range) => (
              <button
                key={range}
                type="button"
                onClick={() => setDays(range)}
                aria-pressed={days === range}
                disabled={loading && days === range}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
                  days === range ? 'bg-brand text-white' : 'border border-line bg-white text-ink hover:bg-canvas'
                }`}
              >
                {range} days
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={timeline} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid stroke="#dce2dd" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} minTickGap={28} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Line type="monotone" dataKey="clicks" name="Clicks" stroke="#0f5c4d" strokeWidth={2.5} dot={days <= 30} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <BreakdownChart title="Devices" data={data.devices} variant="pie" />
        <BreakdownChart title="Browsers" data={data.browsers} variant="bar" />
        <BreakdownChart title="Operating systems" data={data.operating_systems} variant="bar" />
        <BreakdownChart title="Referrers" data={data.referrers} variant="list" />
        {hasKnownCountry && <BreakdownChart title="Countries" data={data.countries} variant="list" />}
      </div>
    </main>
  )
}
