// The private match service is exposed over HTTPS by Tailscale Funnel, so
// players do not need the Tailscale client. Deployments can override its URL.
export const onlineServiceUrl = String(import.meta.env?.VITE_QUESTLAB_ONLINE_URL || 'https://papasmurff-linux.tail7ca373.ts.net').trim()
