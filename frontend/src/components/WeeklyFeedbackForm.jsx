import React, {useState} from 'react'

const API = ''

export default function WeeklyFeedbackForm({ onResponse }){
  const [userId, setUserId] = useState('user_1')
  const [avg_weight, setAvgWeight] = useState(72)
  const [avg_sugar_level, setAvgSugar] = useState(110)
  const [cheat_frequency, setCheatFrequency] = useState(1)

  async function submit(e){
    e.preventDefault()
    const body = { user_id: userId, avg_weight: Number(avg_weight), avg_sugar_level: Number(avg_sugar_level), cheat_frequency: Number(cheat_frequency) }
    const res = await fetch(API + '/weekly-update', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})
    const data = await res.json()
    onResponse?.(data)
  }

  return (
    <div className="card">
      <h3>Weekly Feedback</h3>
      <p className="hint">Sends weekly metrics to `/weekly-update` for adaptation.</p>
      <form className="form" onSubmit={submit}>
        <div className="field">
          <label>User ID</label>
          <input className="control" value={userId} onChange={e=>setUserId(e.target.value)} placeholder="e.g., U0001" />
        </div>

        <div className="row2">
          <div className="field">
            <label>Average Weight</label>
            <input className="control" type="number" value={avg_weight} onChange={e=>setAvgWeight(e.target.value)} />
          </div>
          <div className="field">
            <label>Average Blood Sugar</label>
            <input className="control" type="number" value={avg_sugar_level} onChange={e=>setAvgSugar(e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label>Cheat Frequency</label>
          <input className="control" type="number" value={cheat_frequency} onChange={e=>setCheatFrequency(e.target.value)} />
        </div>

        <button className="btn" type="submit">Submit Feedback</button>
      </form>
    </div>
  )
}
