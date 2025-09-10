import { APIKeyManager } from '@/components/api-keys'

export default function APIKeysPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
        <p className="text-muted-foreground">
          Manage API keys for programmatic access to your account.
        </p>
      </div>
      
      <APIKeyManager />
    </div>
  )
}