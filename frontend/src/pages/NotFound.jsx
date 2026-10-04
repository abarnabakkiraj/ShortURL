import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <main className="mx-auto max-w-md px-4 py-20 text-center">
      <h1 className="text-5xl font-extrabold">404</h1>
      <p className="mt-3 text-muted">We couldn't find that page.</p>
      <Link to="/dashboard" className="btn-primary mt-6">Back to dashboard</Link>
    </main>
  )
}
