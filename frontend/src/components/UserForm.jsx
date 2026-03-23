import React, {useState} from 'react'

const API = ''

export default function UserForm({ onResponse }){
  const [user, setUser] = useState({
    user_id:'user_1', age:30, gender:'Male', height_cm:170, weight_kg:70, diet_type:'Veg', activity_level:'Medium', allergies:[], diabetes:false, blood_pressure:'Normal', cholesterol:'Normal', oxygen_level:98, hemoglobin:'Normal'
  })

  function update(k,v){
    setUser(prev=>({...prev,[k]:v}))
  }

  async function submit(e){
    e.preventDefault()
    // ensure allergies as array
    const payload = {...user, allergies: Array.isArray(user.allergies)?user.allergies:[]}
    const res = await fetch(API + '/register', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
    const data = await res.json()
    onResponse?.(data)
  }

  return (
    <div className="card">
      <h3>Register / Update User</h3>
      <p className="hint">Saves profile to the backend (`/register`).</p>
      <form className="form" onSubmit={submit}>
        <div className="field">
          <label>User ID</label>
          <input className="control" value={user.user_id} onChange={e=>update('user_id',e.target.value)} placeholder="e.g., U0001" />
        </div>

        <div className="row2">
          <div className="field">
            <label>Age</label>
            <input className="control" type="number" value={user.age} onChange={e=>update('age',Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Gender</label>
            <select className="control" value={user.gender} onChange={e=>update('gender',e.target.value)}>
              <option>Male</option>
              <option>Female</option>
              <option>Other</option>
            </select>
          </div>
        </div>

        <div className="row2">
          <div className="field">
            <label>Height (cm)</label>
            <input className="control" type="number" value={user.height_cm} onChange={e=>update('height_cm',Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Weight (kg)</label>
            <input className="control" type="number" value={user.weight_kg} onChange={e=>update('weight_kg',Number(e.target.value))} />
          </div>
        </div>

        <div className="row2">
          <div className="field">
            <label>Diet Type</label>
            <select className="control" value={user.diet_type} onChange={e=>update('diet_type',e.target.value)}>
              <option>Veg</option>
              <option>Non-Veg</option>
            </select>
          </div>
          <div className="field">
            <label>Activity Level</label>
            <select className="control" value={user.activity_level} onChange={e=>update('activity_level',e.target.value)}>
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
            </select>
          </div>
        </div>

        <div className="field">
          <label>Allergies (comma-separated)</label>
          <input className="control" value={user.allergies.join?.(',')||''} onChange={e=>update('allergies', e.target.value.split(',').map(s=>s.trim()).filter(Boolean))} placeholder="e.g., lactose, peanut" />
        </div>

        <label className="check">
          <input type="checkbox" checked={user.diabetes} onChange={e=>update('diabetes', e.target.checked)} />
          Diabetes
        </label>

        <button className="btn" type="submit">Register</button>
      </form>
    </div>
  )
}
