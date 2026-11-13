// Disposable automated opponent for the real, private two-device playtest.
// Account configuration arrives on stdin; no credentials are persisted.
import { createClient } from '@supabase/supabase-js'
import readline from 'node:readline'

const line = readline.createInterface({input:process.stdin, terminal:false})
const config = JSON.parse(await new Promise(resolve => line.once('line', resolve)))
line.close()
const cloud = createClient('https://ajnxexxcqfbozszwpjpk.supabase.co', config.key, {auth:{persistSession:false,autoRefreshToken:false}})
const {data, error} = await cloud.auth.signInWithPassword({email:config.email, password:config.password})
if (error || !data.session) throw new Error('Disposable opponent could not sign in.')
const token = data.session.access_token
const channel = cloud.channel(`hunter-group:${config.group}`, {config:{private:true,presence:{key:data.user.id}}})
await new Promise((resolve,reject) => {
  const timeout = setTimeout(() => reject(new Error('Private presence did not connect.')), 15000)
  channel.subscribe(async status => {
    if (status === 'SUBSCRIBED') {
      const result = await channel.track({id:data.user.id,name:'Remote test hunter',x:190,y:145,room:'online_hideout',facing:'left',look:'classic'})
      clearTimeout(timeout)
      if (result !== 'ok') reject(new Error('Presence tracking failed.')); else resolve()
    } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') { clearTimeout(timeout); reject(new Error('Private presence was rejected.')) }
  })
})
const base = `https://papasmurff-linux.tail7ca373.ts.net/groups/${config.group}`
async function request(path, body) {
  const r = await fetch(base+path, {method:body === undefined ? 'GET':'POST',headers:{Authorization:`Bearer ${token}`,...(body === undefined ? {}:{'Content-Type':'application/json'})},...(body === undefined ? {}:{body:JSON.stringify(body)})})
  const value = await r.json()
  if (!r.ok) throw new Error(`Remote opponent request failed (${r.status}): ${value.detail || 'unavailable'}`)
  return value
}
const sent = await request('/invites',{guest_id:config.opponent,chain_id:'potion',mode:'fair'})
console.log('Remote hunter connected and sent a challenge.')
const wait = ms => new Promise(resolve=>setTimeout(resolve,ms))
let match = '', last = '', started=Date.now()
while (Date.now()-started < 600000) {
  if (!match) { match = (await request(`/invites/${sent.invite_id}`)).match_id || ''; await wait(1000); continue }
  const state = await request(`/matches/${match}`)
  const id = `${state.phase}:${state.round}`
  if (id !== last) {
    if (state.phase === 'loadout' && !state.you.loadout) await request(`/matches/${match}/loadout`,{})
    else if (state.phase === 'coding' && !state.you.submitted) {
      const first = 'def can_buy(balance, price):\n    return balance >= price\n'
      const later = first + '\ndef buy_potion(balance, price):\n    return balance - price if price >= 0 and can_buy(balance, price) else balance\n'
      await request(`/matches/${match}/submit`,{stance:'attack',code:state.round === 0 ? first : later})
    } else if (state.phase === 'exchange' && !state.you.ready) await request(`/matches/${match}/ready`,{})
    else if (state.phase === 'bonus' && !state.bonus_question.answered) await request(`/matches/${match}/bonus`,{answer:0,reward:'heal'})
    else if (state.phase === 'finished' || state.phase === 'aborted') { console.log(`Remote hunter: duel ${state.phase}.`); break }
    last = id
  }
  await wait(1000)
}
await cloud.removeChannel(channel)
await cloud.auth.signOut()
