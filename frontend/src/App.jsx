import React, { useEffect, useMemo, useState } from 'react'
import WeeklyPlanForm from './components/WeeklyPlanForm'
import { getFoodImageSrc } from './utils/foodImage'

function FoodThumb({ name }) {
  const label = String(name || '').trim() || 'Food'
  return (
    <span className="mealThumb" aria-hidden="true">
      <img src={getFoodImageSrc(label)} alt="" loading="lazy" />
    </span>
  )
}

function asStringArray(v) {
  if (Array.isArray(v)) return v.map((x) => String(x ?? '').trim()).filter(Boolean)
  if (typeof v === 'string') {
    const s = v.trim()
    return s ? [s] : []
  }
  return []
}

function RecipeDetails({ item }) {
  const r = item?.recipe
  if (!r || typeof r !== 'object') return null

  const ingredients = asStringArray(r.ingredients)
  const steps = asStringArray(r.steps)
  if (!ingredients.length && !steps.length) return null

  const time = Number(r.time_minutes)
  const cuisine = String(r.cuisine || '').trim()

  return (
    <details className="recipeDetails">
      <summary className="recipeSummary">Recipe</summary>
      {(time || cuisine) ? (
        <div className="recipeMetaRow">
          {time ? <span className="recipeMeta">Time: {time} min</span> : null}
          {cuisine ? <span className="recipeMeta">Cuisine: {cuisine}</span> : null}
        </div>
      ) : null}
      {ingredients.length ? (
        <div className="recipeSection">
          <div className="recipeLabel">Ingredients</div>
          <ul className="recipeList">
            {ingredients.map((ing) => <li key={ing}>{ing}</li>)}
          </ul>
        </div>
      ) : null}
      {steps.length ? (
        <div className="recipeSection">
          <div className="recipeLabel">Steps</div>
          <ol className="recipeList">
            {steps.map((step, i) => <li key={`${i}-${step}`}>{step}</li>)}
          </ol>
        </div>
      ) : null}
    </details>
  )
}

function sumCalories(items) {
  if (!Array.isArray(items)) return 0
  return items.reduce((acc, it) => acc + (Number(it?.calories) || 0), 0)
}

function displayDish(it) {
  return String(it?.dish_name || it?.recipe?.title || it?.food_name || '').trim() || 'Meal'
}

function toCsvRow(cells) {
  return cells
    .map((c) => {
      const s = String(c ?? '')
      const needsQuotes = /[\n\r,"]/.test(s)
      const escaped = s.replace(/"/g, '""')
      return needsQuotes ? `"${escaped}"` : escaped
    })
    .join(',')
}

function downloadTextFile(filename, text, mime = 'text/plain;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 250)
}

function GroceryList({ weekDoc }) {
  const items = useMemo(() => {
    const week = Array.isArray(weekDoc?.week) ? weekDoc.week : []
    const counts = new Map()

    for (const day of week) {
      const meals = day?.meals || {}
      for (const mealName of ['breakfast', 'lunch', 'dinner']) {
        const arr = Array.isArray(meals?.[mealName]) ? meals[mealName] : []
        for (const it of arr) {
          const name = String(it?.food_name || '').trim()
          if (!name) continue
          counts.set(name, (counts.get(name) || 0) + 1)
        }
      }
    }

    return Array.from(counts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  }, [weekDoc])

  const csv = useMemo(() => {
    const lines = [toCsvRow(['Food', 'Count'])]
    for (const it of items) lines.push(toCsvRow([it.name, it.count]))
    return lines.join('\n')
  }, [items])

  async function copy() {
    const text = items.map((it) => `${it.count}× ${it.name}`).join('\n')
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // clipboard may be blocked in some contexts; fall back to download
      downloadTextFile('grocery-list.txt', text)
    }
  }

  if (!items.length) return null

  return (
    <div className="groceryCard">
      <div className="sectionTitleRow">
        <h3 className="sectionTitle" style={{ margin: 0, fontSize: 16 }}>Grocery List</h3>
        <div className="groceryActions">
          <button type="button" className="btn btnSecondary" onClick={copy}>Copy</button>
          <button
            type="button"
            className="btn btnSecondary"
            onClick={() => downloadTextFile('grocery-list.csv', csv, 'text/csv;charset=utf-8')}
          >
            Download CSV
          </button>
        </div>
      </div>
      <p className="hint" style={{ marginBottom: 10 }}>Counts show how many times each food appears across the week.</p>

      <div className="groceryGrid">
        {items.map((it) => (
          <div className="groceryItem" key={it.name}>
            <div className="groceryCount">{it.count}×</div>
            <div className="groceryName">{it.name}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function WeekView({ weekDoc }) {
  const week = Array.isArray(weekDoc?.week) ? weekDoc.week : []
  if (!week.length) return null

  return (
    <div className="weekWrap">
      <div className="weekHeader">
        <div>
          <div className="weekTitle">Weekly Diet Plan</div>
          <div className="weekSub">{weekDoc.start_date} • {weekDoc.days} days</div>
        </div>
        {weekDoc?.cheat?.day ? (
          <div className="badge">Cheat day: Day {weekDoc.cheat.day}</div>
        ) : null}
      </div>

      <div className="weekGrid">
        {week.map((d) => (
          (() => {
            const b = d?.meals?.breakfast || []
            const l = d?.meals?.lunch || []
            const dn = d?.meals?.dinner || []
            const planned = sumCalories(b) + sumCalories(l) + sumCalories(dn)
            return (
          <div className="dayCard" key={d.date || d.day}>
            <div className="dayTop">
              <div className="dayTitle">Day {d.day}</div>
              <div className="dayDate">{d.date}</div>
            </div>

            <div className="dayCalories">Target: {d?.targets?.calories ?? '-'} kcal • Planned: {planned || 0} kcal</div>

            <div className="mealBlock">
              <div className="mealTitle">Breakfast</div>
              <ul className="mealList">
                {(b || []).length ? (b || []).map((it) => (
                  <li className="mealItem" key={it.food_id || it.food_name}>
                    <FoodThumb name={it.food_name} />
                    <div className="mealBody">
                      <div className="mealLine">
                        <span className="mealText">{displayDish(it)}</span>
                        <span className="mealMeta">({it.calories} kcal{it?.recipe?.cuisine ? ` • ${it.recipe.cuisine}` : ''})</span>
                      </div>
                      <RecipeDetails item={it} />
                    </div>
                  </li>
                )) : <li className="mealEmpty">No items (try reducing filters)</li>}
              </ul>
            </div>

            <div className="mealBlock">
              <div className="mealTitle">Lunch</div>
              <ul className="mealList">
                {(l || []).length ? (l || []).map((it) => (
                  <li className="mealItem" key={it.food_id || it.food_name}>
                    <FoodThumb name={it.food_name} />
                    <div className="mealBody">
                      <div className="mealLine">
                        <span className="mealText">{displayDish(it)}</span>
                        <span className="mealMeta">({it.calories} kcal{it?.recipe?.cuisine ? ` • ${it.recipe.cuisine}` : ''})</span>
                      </div>
                      <RecipeDetails item={it} />
                    </div>
                  </li>
                )) : <li className="mealEmpty">No items (try reducing filters)</li>}
              </ul>
            </div>

            <div className="mealBlock">
              <div className="mealTitle">Dinner</div>
              <ul className="mealList">
                {(dn || []).length ? (dn || []).map((it) => (
                  <li className="mealItem" key={it.food_id || it.food_name}>
                    <FoodThumb name={it.food_name} />
                    <div className="mealBody">
                      <div className="mealLine">
                        <span className="mealText">{displayDish(it)}</span>
                        <span className="mealMeta">({it.calories} kcal{it?.recipe?.cuisine ? ` • ${it.recipe.cuisine}` : ''})</span>
                      </div>
                      <RecipeDetails item={it} />
                    </div>
                  </li>
                )) : <li className="mealEmpty">No items (try reducing filters)</li>}
              </ul>
            </div>
          </div>
            )
          })()
        ))}
      </div>
    </div>
  )
}

function DayOnePlan({ weekDoc }) {
  const day1 = useMemo(() => {
    const week = Array.isArray(weekDoc?.week) ? weekDoc.week : []
    const found = week.find((d) => Number(d?.day) === 1)
    return found || week[0] || null
  }, [weekDoc])

  const day1Text = useMemo(() => {
    if (!day1) return ''
    const lines = []
    lines.push(`Day 1 (${day1.date || ''})`)
    for (const meal of ['breakfast', 'lunch', 'dinner']) {
      lines.push('')
      lines.push(meal.charAt(0).toUpperCase() + meal.slice(1) + ':')
      for (const it of (day1?.meals?.[meal] || [])) {
        lines.push(`- ${displayDish(it)} (${it.calories} kcal)`) 
      }
    }
    const target = day1?.targets?.calories
    if (target != null) {
      lines.push('')
      lines.push(`Target calories: ${target}`)
    }
    return lines.join('\n')
  }, [day1])

  const day1Planned = useMemo(() => {
    if (!day1) return 0
    return (
      sumCalories(day1?.meals?.breakfast) +
      sumCalories(day1?.meals?.lunch) +
      sumCalories(day1?.meals?.dinner)
    )
  }, [day1])

  async function copy() {
    if (!day1Text) return
    try {
      await navigator.clipboard.writeText(day1Text)
    } catch {
      downloadTextFile('day-1-plan.txt', day1Text)
    }
  }

  if (!day1) return null

  return (
    <div className="dayOneCard" id="day1">
      <div className="sectionTitleRow">
        <h3 className="sectionTitle" style={{ margin: 0, fontSize: 16 }}>Day 1 Plan</h3>
        <div className="groceryActions">
          <button type="button" className="btn btnSecondary" onClick={copy}>Copy</button>
          <button
            type="button"
            className="btn btnSecondary"
            onClick={() => downloadTextFile('day-1-plan.txt', day1Text)}
          >
            Download
          </button>
        </div>
      </div>

      <p className="hint" style={{ marginBottom: 10 }}>{day1.date ? `Date: ${day1.date}` : 'Date: -'} • Target: {day1?.targets?.calories ?? '-'} kcal • Planned: {day1Planned || 0} kcal</p>

      <div className="dayOneMeals">
        {['breakfast', 'lunch', 'dinner'].map((meal) => (
          <div className="dayOneMeal" key={meal}>
            <div className="mealTitle">{meal}</div>
            <div className="dayOneList">
              {(day1?.meals?.[meal] || []).length ? (day1?.meals?.[meal] || []).map((it) => (
                <div className="dayOneItem" key={it.food_id || it.food_name}>
                  <FoodThumb name={it.food_name} />
                  <div className="dayOneText">
                    <div className="dayOneName">{displayDish(it)}</div>
                    <div className="dayOneMeta">{it.calories} kcal{it?.recipe?.cuisine ? ` • ${it.recipe.cuisine}` : ''}</div>
                    <RecipeDetails item={it} />
                  </div>
                </div>
              )) : <div className="mealEmpty">No items (try reducing filters)</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [response, setResponse] = useState(null)
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('theme') || 'light'
    } catch {
      return 'light'
    }
  })

  useEffect(() => {
    try {
      document.documentElement.dataset.theme = theme
      localStorage.setItem('theme', theme)
    } catch {
      // ignore
    }
  }, [theme])

  const raw = useMemo(() => {
    if (!response) return ''
    try {
      return JSON.stringify(response, null, 2)
    } catch {
      return String(response)
    }
  }, [response])

  const isWeekly = response && typeof response === 'object' && Array.isArray(response.week)

  function jumpToDay1() {
    const el = document.getElementById('day1')
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    window.location.hash = '#day1'
  }

  function printPlan() {
    window.print()
  }

  return (
    <div className="container">
      <div className="topbar">
        <div className="brand">
          <div className="brandMark" />
          <div>Macro Meal Planner</div>
        </div>
        <div className="nav">
          <a href="#planner">Meal Plans</a>
          <a href="#results">Results</a>
          <button
            type="button"
            className="btn btnSecondary"
            onClick={() => setTheme(t => (t === 'dark' ? 'light' : 'dark'))}
          >
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
        </div>
      </div>

      <div className="hero">
        <div>
          <h1 className="heroTitle">Customizable Diet Meal Planner & Generator</h1>
          <p className="heroSub">
            Fill your profile, optionally pick 1–2 recipes per meal, and generate a 7-day plan. If you log a cheat meal on a day,
            the remaining days are regenerated automatically.
          </p>
        </div>
        <div className="heroArt" aria-hidden="true" />
      </div>

      <div id="planner" className="grid">
        <div className="noPrint">
          <WeeklyPlanForm onResponse={setResponse} />
        </div>

        <div id="results" className="card">
          <div className="sectionTitleRow">
            <h3 className="sectionTitle">Your Plan</h3>
            <div style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
              {isWeekly ? (
                <>
                  <button type="button" className="btn btnSecondary" onClick={jumpToDay1}>Jump to Day 1</button>
                  <button type="button" className="btn btnSecondary" onClick={printPlan}>Print</button>
                </>
              ) : null}
              {isWeekly && response?.user_id ? <div className="badge">User: {response.user_id}</div> : null}
            </div>
          </div>
          <p className="hint">Weekly plans render as cards; raw JSON is shown below.</p>

          {isWeekly ? <DayOnePlan weekDoc={response} /> : null}

          {isWeekly ? <WeekView weekDoc={response} /> : null}

          {isWeekly ? <GroceryList weekDoc={response} /> : null}

          <div className="output noPrint">
            <div className="outputTitle">Raw Response</div>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{raw || 'No response yet.'}</pre>
          </div>
        </div>
      </div>
    </div>
  )
}
