# Frontend (React) Integration Notes

This folder contains a minimal React frontend to interact with the backend API.

Suggested components:

- `UserForm` — collects `UserProfile` fields and POSTs to `/register`.
- `CheatMealForm` — optional cheat meal input and POSTs to `/recommend`.
- `WeeklyFeedbackForm` — collects weekly metrics and POSTs to `/weekly-update`.

API endpoints:

- `POST /register` — body: full `UserProfile` JSON
- `POST /recommend` — body: `{ user_id: string, cheat_meal?: {...} }` returns meal plan JSON
- `POST /weekly-update` — body: weekly feedback JSON

Example request using `fetch`:

```js
fetch("http://localhost:5000/recommend", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ user_id: "user_1" }),
})
  .then((r) => r.json())
  .then((data) => console.log(data));
```

Local dev (Vite):

1. From this folder run:

```cmd
cd frontend
npm install
npm run dev
```

2. Open the displayed `localhost` URL in the browser and use the forms to interact with the Flask backend running on port 5000.

# Frontend (React) Integration Notes

This folder contains guidance for implementing a React frontend to interact with the backend API.

Suggested components:

- `UserForm` — collects `UserProfile` fields, multi-select for `allergies`, checkboxes for conditions, activity level selector. POST to `/register`.
- `CheatMealForm` — optional cheat meal input. POST to `/recommend` with `user_id` and `cheat_meal`.
- `WeeklyFeedbackForm` — collects weekly metrics, POST to `/weekly-update`.

API endpoints:

- `POST /register` — body: full `UserProfile` JSON
- `POST /recommend` — body: `{ user_id: string, cheat_meal?: {...} }` returns meal plan JSON
- `POST /weekly-update` — body: weekly feedback JSON

Example request using `fetch`:

```js
fetch("http://localhost:5000/recommend", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ user_id: "user_1" }),
})
  .then((r) => r.json())
  .then((data) => console.log(data));
```
