import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const { repo } = await req.json()
  const token = process.env.GITHUB_TOKEN
  if (!token) return NextResponse.json({ error: 'No GitHub token configured' }, { status: 500 })

  const res = await fetch(`https://api.github.com/repos/${repo}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'application/vnd.github+json',
    },
    body: JSON.stringify({ archived: true }),
  })

  if (!res.ok) {
    const error = await res.text()
    return NextResponse.json({ error }, { status: res.status })
  }
  return NextResponse.json({ success: true })
}
