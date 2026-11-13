// Online raid requests use the same authenticated host as Colosseum duels.
// Access tokens stay in Authorization headers and never enter URLs or storage.
import { getSupabaseClient } from './supabaseClient.js'
import { onlineServiceUrl as raw } from './onlineService.js'

let serviceUrl = ''
try {
  const parsed = new URL(raw)
  if (parsed.protocol === 'https:' && !parsed.username && !parsed.password && !parsed.search && !parsed.hash) serviceUrl = parsed.href.replace(/\/$/, '')
} catch { /* online co-op is optional until the host is configured */ }
export const onlineRaidsConfigured = Boolean(serviceUrl)

const groupIdPattern = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i
const raidIdPattern = /^[A-Za-z0-9_-]{16,64}$/
const taskPattern = /^[a-z-]{1,40}$/

async function request(path, method = 'GET', body) {
  if (!serviceUrl) throw new Error('Co-op projects are not configured yet.')
  const client = getSupabaseClient()
  if (!client) throw new Error('Sign in to Quest Lab first.')
  const { data, error } = await client.auth.getSession()
  if (error || !data?.session?.access_token) throw new Error('Your account session has expired. Sign in again.')
  const response = await fetch(serviceUrl + path, { method,
    headers: { Authorization: `Bearer ${data.session.access_token}`, ...(body ? { 'Content-Type':'application/json' } : {}) },
    ...(body ? { body:JSON.stringify(body) } : {}) })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The co-op service is unavailable.')
  return result
}

function groupPath(groupId) {
  if (!groupIdPattern.test(String(groupId))) throw new Error('Select a valid group.')
  return `/groups/${groupId}/raids`
}
function validRaid(id) {
  if (!raidIdPattern.test(String(id))) throw new Error('The project reference is invalid.')
  return id
}
function validTask(id) {
  if (!taskPattern.test(String(id))) throw new Error('The task reference is invalid.')
  return id
}

export const onlineRaid = {
  current: async group => (await request(`${groupPath(group)}/active`)).raid,
  create: group => request(groupPath(group), 'POST', {}),
  assign: (group, raid, task, target) => request(`${groupPath(group)}/${validRaid(raid)}/assign`, 'POST', { task_id:validTask(task), target_id:target }),
  openForVolunteers: (group, raid, task) => request(`${groupPath(group)}/${validRaid(raid)}/volunteer/open`, 'POST', { task_id:validTask(task) }),
  volunteer: (group, raid, task) => request(`${groupPath(group)}/${validRaid(raid)}/volunteer/claim`, 'POST', { task_id:validTask(task) }),
  swap: (group, raid, task, otherTask) => request(`${groupPath(group)}/${validRaid(raid)}/swap`, 'POST', { task_id:validTask(task), other_task_id:validTask(otherTask) }),
  submit: (group, raid, task, requestId, code) => request(`${groupPath(group)}/${validRaid(raid)}/submit`, 'POST', { task_id:validTask(task), request_id:requestId, code }),
  review: (group, raid, task, decision) => request(`${groupPath(group)}/${validRaid(raid)}/review`, 'POST', { task_id:validTask(task), decision }),
  abandon: (group, raid) => request(`${groupPath(group)}/${validRaid(raid)}/abandon`, 'POST', {}),
  startBoss: (group, raid) => request(`${groupPath(group)}/${validRaid(raid)}/boss/start`, 'POST', {}),
  submitBoss: (group, raid, question, requestId, code) => request(`${groupPath(group)}/${validRaid(raid)}/boss/submit`, 'POST', { question_id:question, request_id:requestId, code }),
  resolveBossFeint: (group, raid, decision) => request(`${groupPath(group)}/${validRaid(raid)}/boss/feint`, 'POST', { decision }),
}
