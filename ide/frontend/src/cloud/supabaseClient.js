import { createClient } from '@supabase/supabase-js'
import { cloudConfig } from './config.js'

let browserClient = null

export function getSupabaseClient(config = cloudConfig) {
  if (!config.configured || !config.valid) return null
  if (browserClient) return browserClient

  browserClient = createClient(config.url, config.anonKey, {
    auth: {
      autoRefreshToken: true,
      detectSessionInUrl: true,
      persistSession: true,
    },
  })
  return browserClient
}
