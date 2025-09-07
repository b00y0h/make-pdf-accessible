import { redirect } from 'next/navigation'

export default function HomePage() {
  // Redirect to login page for now - will implement auth later
  redirect('/login')
}
