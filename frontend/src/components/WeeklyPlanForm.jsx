import React, { useState } from 'react'

import { getFoodImageSrc } from '../utils/foodImage'

const API = ''

function clamp(n, lo, hi) {
  const v = Number(n)
  if (Number.isNaN(v)) return lo
  return Math.max(lo, Math.min(hi, v))
}

function nextDateForWeekday(targetIdx) {
  const today = new Date()
  const todayIdx = today.getDay() // 0 Sun
  const delta = (targetIdx - todayIdx + 7) % 7
  const d = new Date(today)
  d.setDate(today.getDate() + delta)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

function safeJson(res) {
  return res.json().catch(() => ({}))
}

export default function WeeklyPlanForm({ onResponse }) {
  const [tab, setTab] = useState('basic') // basic | advanced

  const cuisineChoices = ['Any', 'Indian', 'South Indian', 'Mediterranean', 'Italian', 'Mexican', 'Chinese']

  const [user, setUser] = useState({
    user_id: '',
    age: 30,
    gender: 'Male',
    units: 'Metric',
    height_cm: 170,
    weight_kg: 70,
    diet_type: 'Veg',
    activity_level: 'Medium',
    goal: 'Lose fat',
    allergiesText: '',
    diabetes: false,
    blood_pressure: 'Normal',
    cholesterol: 'Normal',
    oxygen_level: 98,
    hemoglobin: 'Normal',
    heart_disease: false,
    thyroid: false,
    pcos: false,
    cuisines: ['Any'],
  })

  const [startDayIdx, setStartDayIdx] = useState(new Date().getDay())
  const [days, setDays] = useState(7)

  const [foods, setFoods] = useState([])
  const [loadingFoods, setLoadingFoods] = useState(false)
  const [foodError, setFoodError] = useState('')

  const [picks, setPicks] = useState({ breakfast: [], lunch: [], dinner: [] })

  const [cheatDay, setCheatDay] = useState(0)
  const [cheatCalories, setCheatCalories] = useState(0)
  const [cheatSugar, setCheatSugar] = useState(0)
  const [cheatFat, setCheatFat] = useState(0)

  function updateUser(k, v) {
    setUser(prev => ({ ...prev, [k]: v }))
  }

  function toggleCuisine(name) {
    setUser(prev => {
      const current = Array.isArray(prev.cuisines) ? prev.cuisines : ['Any']
      const n = String(name || '').trim()
      if (!n) return prev

      // 'Any' clears other selections
      if (n === 'Any') {
        return { ...prev, cuisines: ['Any'] }
      }

      const withoutAny = current.filter(x => x !== 'Any')
      const exists = withoutAny.includes(n)
      const next = exists ? withoutAny.filter(x => x !== n) : [...withoutAny, n]
      return { ...prev, cuisines: next.length ? next : ['Any'] }
    })
  }

  function parseAllergies(text) {
    return String(text || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
  }

  function togglePick(meal, foodId) {
    setPicks(prev => {
      const current = prev[meal] || []
      const exists = current.includes(foodId)
      let next = exists ? current.filter(x => x !== foodId) : [...current, foodId]
      next = next.slice(0, 2)
      return { ...prev, [meal]: next }
    })
  }

  async function loadFoods() {
    setLoadingFoods(true)
    setFoodError('')
    try {
      const payload = {
        user: {
          user_id: String(user.user_id || '').trim() || undefined,
          age: Number(user.age) || 0,
          gender: user.gender,
          height_cm: Number(user.height_cm) || 0,
          weight_kg: Number(user.weight_kg) || 0,
          diet_type: user.diet_type,
          activity_level: user.activity_level,
          allergies: parseAllergies(user.allergiesText),
          diabetes: Boolean(user.diabetes),
          blood_pressure: user.blood_pressure,
          cholesterol: user.cholesterol,
          oxygen_level: Number(user.oxygen_level) || 0,
          hemoglobin: user.hemoglobin,
          heart_disease: Boolean(user.heart_disease),
          thyroid: Boolean(user.thyroid),
          pcos: Boolean(user.pcos),
          goal: user.goal,
        },
        limit: 60,
      }

      const res = await fetch(API + '/foods', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await safeJson(res)
      if (!res.ok) {
        setFoodError(data?.error || 'Failed to load foods')
        setFoods([])
        return
      }
      setFoods(Array.isArray(data?.foods) ? data.foods : [])
    } catch {
      setFoodError('Failed to load foods')
      setFoods([])
    } finally {
      setLoadingFoods(false)
    }
  }

  async function submit(e) {
    e.preventDefault()

    const payload = {
      start_date: nextDateForWeekday(startDayIdx),
      days: clamp(days, 1, 14),
    }

    payload.user = {
      user_id: String(user.user_id || '').trim() || undefined,
      age: Number(user.age) || 0,
      gender: user.gender,
      height_cm: Number(user.height_cm) || 0,
      weight_kg: Number(user.weight_kg) || 0,
      diet_type: user.diet_type,
      activity_level: user.activity_level,
      allergies: parseAllergies(user.allergiesText),
      diabetes: Boolean(user.diabetes),
      blood_pressure: user.blood_pressure,
      cholesterol: user.cholesterol,
      oxygen_level: Number(user.oxygen_level) || 0,
      hemoglobin: user.hemoglobin,
      heart_disease: Boolean(user.heart_disease),
      thyroid: Boolean(user.thyroid),
      pcos: Boolean(user.pcos),
      goal: user.goal,
      cuisines: Array.isArray(user.cuisines) ? user.cuisines.filter(x => x && x !== 'Any') : undefined,
    }

    payload.picks = picks

    if (Number(cheatDay) > 0) {
      payload.cheat = {
        day: Number(cheatDay),
        cheat_meal: {
          calories: Number(cheatCalories),
          sugar_g: Number(cheatSugar),
          fat_g: Number(cheatFat),
        },
      }
    }

    const res = await fetch(API + '/weekly-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const data = await safeJson(res)
    onResponse?.(data)
  }

  return (
    <div className="card">
      <div className="sectionTitleRow">
        <h3 className="sectionTitle">Meal Planner</h3>
        <div className="tabs" role="tablist" aria-label="Planner tabs">
          <button type="button" className={`tab ${tab === 'basic' ? 'tabActive' : ''}`} onClick={() => setTab('basic')}>Basic</button>
          <button type="button" className={`tab ${tab === 'advanced' ? 'tabActive' : ''}`} onClick={() => setTab('advanced')}>Advanced</button>
        </div>
      </div>
      <p className="hint">Fill your profile and generate a weekly diet plan. Optional recipe picks will be used for Day 1.</p>

      <form className="form" onSubmit={submit}>
        {tab === 'basic' ? (
          <>
            <div className="row2">
              <div className="field">
                <label>Gender</label>
                <select className="control" value={user.gender} onChange={e => updateUser('gender', e.target.value)}>
                  <option>Male</option>
                  <option>Female</option>
                  <option>Other</option>
                </select>
              </div>
              <div className="field">
                <label>Age</label>
                <input className="control" type="number" min="1" value={user.age} onChange={e => updateUser('age', e.target.value)} />
              </div>
            </div>

            <div className="row2">
              <div className="field">
                <label>Units</label>
                <select className="control" value={user.units} onChange={e => updateUser('units', e.target.value)}>
                  <option>Metric</option>
                </select>
              </div>
              <div className="field">
                <label>Weight goal</label>
                <select className="control" value={user.goal} onChange={e => updateUser('goal', e.target.value)}>
                  <option>Lose fat</option>
                  <option>Maintain</option>
                  <option>Build muscle</option>
                </select>
              </div>
            </div>

            <div className="row2">
              <div className="field">
                <label>Height (cm)</label>
                <input className="control" type="number" min="1" value={user.height_cm} onChange={e => updateUser('height_cm', e.target.value)} />
              </div>
              <div className="field">
                <label>Weight (kg)</label>
                <input className="control" type="number" min="1" value={user.weight_kg} onChange={e => updateUser('weight_kg', e.target.value)} />
              </div>
            </div>

            <div className="row2">
              <div className="field">
                <label>Activity level</label>
                <select className="control" value={user.activity_level} onChange={e => updateUser('activity_level', e.target.value)}>
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                </select>
              </div>
              <div className="field">
                <label>Diet type</label>
                <select className="control" value={user.diet_type} onChange={e => updateUser('diet_type', e.target.value)}>
                  <option>Veg</option>
                  <option>Non-Veg</option>
                </select>
              </div>
            </div>

            <div className="field">
              <label>Cuisine preference</label>
              <div className="weekdays" aria-label="Cuisine preferences">
                {cuisineChoices.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`dayBtn ${(user.cuisines || []).includes(c) ? 'dayBtnActive' : ''}`}
                    onClick={() => toggleCuisine(c)}
                  >
                    {c}
                  </button>
                ))}
              </div>
              <div className="hint" style={{ marginTop: 6 }}>Choose one or more cuisines (or keep “Any”).</div>
            </div>

            <div className="field">
              <label>Allergies (comma-separated)</label>
              <input className="control" value={user.allergiesText} onChange={e => updateUser('allergiesText', e.target.value)} placeholder="e.g., lactose, peanut" />
            </div>

            <div className="field">
              <label>Start meal plan each week on</label>
              <div className="weekdays">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d, idx) => (
                  <button
                    key={d}
                    type="button"
                    className={`dayBtn ${idx === startDayIdx ? 'dayBtnActive' : ''}`}
                    onClick={() => setStartDayIdx(idx)}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <div className="row2">
              <div className="field">
                <label>Days</label>
                <input className="control" type="number" min="1" max="14" value={days} onChange={e => setDays(e.target.value)} />
              </div>
              <div className="field">
                <label>User ID (optional)</label>
                <input className="control" value={user.user_id} onChange={e => updateUser('user_id', e.target.value)} placeholder="e.g., demo_user" />
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="row2">
              <div className="field">
                <label>Blood pressure</label>
                <select className="control" value={user.blood_pressure} onChange={e => updateUser('blood_pressure', e.target.value)}>
                  <option>Normal</option>
                  <option>High</option>
                </select>
              </div>
              <div className="field">
                <label>Cholesterol</label>
                <select className="control" value={user.cholesterol} onChange={e => updateUser('cholesterol', e.target.value)}>
                  <option>Normal</option>
                  <option>High</option>
                </select>
              </div>
            </div>

            <div className="row2">
              <div className="field">
                <label>Oxygen level</label>
                <input className="control" type="number" min="0" value={user.oxygen_level} onChange={e => updateUser('oxygen_level', e.target.value)} />
              </div>
              <div className="field">
                <label>Hemoglobin</label>
                <select className="control" value={user.hemoglobin} onChange={e => updateUser('hemoglobin', e.target.value)}>
                  <option>Normal</option>
                  <option>Low</option>
                </select>
              </div>
            </div>

            <label className="check">
              <input type="checkbox" checked={user.diabetes} onChange={e => updateUser('diabetes', e.target.checked)} />
              Diabetes
            </label>

            <div className="row2">
              <label className="check">
                <input type="checkbox" checked={user.heart_disease} onChange={e => updateUser('heart_disease', e.target.checked)} />
                Heart disease
              </label>
              <label className="check">
                <input type="checkbox" checked={user.thyroid} onChange={e => updateUser('thyroid', e.target.checked)} />
                Thyroid
              </label>
            </div>

            <label className="check">
              <input type="checkbox" checked={user.pcos} onChange={e => updateUser('pcos', e.target.checked)} />
              PCOS
            </label>

            <div className="row2">
              <div className="field">
                <label>Cheat day (0 = none)</label>
                <input className="control" type="number" min="0" max="14" value={cheatDay} onChange={e => setCheatDay(e.target.value)} />
              </div>
              <div className="field">
                <label>Cheat calories</label>
                <input className="control" type="number" value={cheatCalories} onChange={e => setCheatCalories(e.target.value)} />
              </div>
            </div>

            <div className="row2">
              <div className="field">
                <label>Cheat sugar (g)</label>
                <input className="control" type="number" value={cheatSugar} onChange={e => setCheatSugar(e.target.value)} />
              </div>
              <div className="field">
                <label>Cheat fat (g)</label>
                <input className="control" type="number" value={cheatFat} onChange={e => setCheatFat(e.target.value)} />
              </div>
            </div>
          </>
        )}

        <div className="sectionTitleRow">
          <h3 className="sectionTitle" style={{ margin: 0, fontSize: 16 }}>Optional: Pick 1–2 recipes for each meal</h3>
          <button type="button" className="btn btnSecondary" onClick={loadFoods} disabled={loadingFoods}>
            {loadingFoods ? 'Loading…' : (foods.length ? 'Refresh recipes' : 'Load recipes')}
          </button>
        </div>
        <div className="hint">Your meal plan will be built around your choices (applied on Day 1 for variety).</div>

        {foodError ? <div className="hint" style={{ color: '#b91c1c' }}>{foodError}</div> : null}

        <div className="recipes">
          {['breakfast', 'lunch', 'dinner'].map((meal) => (
            <div className="recipeRow" key={meal}>
              <div className="rowHeader">
                <h4>{meal.charAt(0).toUpperCase() + meal.slice(1)}</h4>
                <div className="rowHint">Selected: {(picks[meal] || []).length}/2</div>
              </div>
              <div className="scrollX">
                {(foods || []).slice(0, 18).map((f) => {
                  const selected = (picks[meal] || []).includes(f.food_id)
                  return (
                    <div
                      key={`${meal}-${f.food_id}`}
                      className={`recipeCard ${selected ? 'recipeSelected' : ''}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => togglePick(meal, f.food_id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') togglePick(meal, f.food_id)
                      }}
                    >
                      <div className="recipeImg">
                        <img src={getFoodImageSrc(f.food_name)} alt={f.food_name} loading="lazy" />
                      </div>
                      <div className="recipeBody">
                        <div className="recipeName">{f.food_name}</div>
                        <div className="recipeMeta">{f.calories} kcal • {f.diet_type}</div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        <button className="btn" type="submit">Generate diet plan</button>
      </form>
    </div>
  )
}
