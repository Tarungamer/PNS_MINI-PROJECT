import React, {useState} from 'react'

const API = ''

export default function CheatMealForm({ onResponse }){
  const [userId, setUserId] = useState('user_1')
  const [calories, setCalories] = useState(0)
  const [sugar, setSugar] = useState(0)
  const [fat, setFat] = useState(0)

  async function submit(e){
    e.preventDefault()
    const body = { user_id: userId, cheat_meal: { calories: Number(calories), sugar_g: Number(sugar), fat_g: Number(fat) } }
    const res = await fetch(API + '/recommend', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})
    const data = await res.json()
    onResponse?.(data)
  }

  return (
    <div className="card">
      <h3>Request Recommendation</h3>
      <p className="hint">Calls `/recommend` and returns a diet plan JSON.</p>
      <form className="form" onSubmit={submit}>
        <div className="field">
          <label>User ID</label>
          <input className="control" value={userId} onChange={e=>setUserId(e.target.value)} placeholder="e.g., U0001" />
        </div>

        <div className="row2">
          <div className="field">
            <label>Cheat Calories (optional)</label>
            <input className="control" type="number" value={calories} onChange={e=>setCalories(e.target.value)} />
          </div>
          <div className="field">
            <label>Cheat Sugar (g)</label>
            <input className="control" type="number" value={sugar} onChange={e=>setSugar(e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label>Cheat Fat (g)</label>
          <input className="control" type="number" value={fat} onChange={e=>setFat(e.target.value)} />
        </div>

        <button className="btn" type="submit">Get Recommendation</button>
      </form>
    </div>
  )
}
