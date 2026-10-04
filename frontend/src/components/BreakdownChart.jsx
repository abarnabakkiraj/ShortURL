import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const COLORS = ['#0f5c4d', '#d98e04', '#3b6ea5', '#8a4f7d', '#7a8a84', '#c2503c', '#4a9c8c', '#a3a33a']

function PieView({ data }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={data} dataKey="count" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={2}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

function BarView({ data }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(140, data.length * 38 + 30)}>
      <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16 }}>
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
        <Tooltip cursor={{ fill: 'rgba(15, 92, 77, 0.08)' }} />
        <Bar dataKey="count" name="Clicks" fill={COLORS[0]} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ListView({ data }) {
  const max = Math.max(...data.map((item) => item.count))
  return (
    <ul className="space-y-3">
      {data.map((item) => (
        <li key={item.name}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate" title={item.name}>{item.name}</span>
            <span className="font-semibold tabular-nums">{item.count.toLocaleString()}</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-canvas">
            <div className="h-1.5 rounded-full bg-brand" style={{ width: `${(item.count / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

export default function BreakdownChart({ title, data, variant = 'bar' }) {
  const View = { pie: PieView, bar: BarView, list: ListView }[variant]
  return (
    <section className="panel p-4 sm:p-5" aria-label={title}>
      <h3 className="mb-3 font-bold">{title}</h3>
      {data.length === 0 ? <p className="py-8 text-center text-sm text-muted">No clicks yet</p> : <View data={data} />}
    </section>
  )
}
