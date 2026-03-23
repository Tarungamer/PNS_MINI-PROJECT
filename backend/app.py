from flask import Flask, request, jsonify
import os
import json
from pathlib import Path
from datetime import date, datetime, timedelta
import random
import hashlib
import re
import math

from backend.utils import (
    compute_bmi,
    analyze_health_risk,
    calculate_nutrition_targets,
    filter_foods,
    score_foods,
    optimize_meals,
    apply_cheat_adjustment,
    load_users_from_csv,
)
from backend.adaptive_engine import WeeklyAdaptationEngine

DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "users.json"
WEEKLY_PLANS_FILE = DATA_DIR / "weekly_plans.json"

# If a built frontend exists at ../frontend/dist, serve it as static files from Flask
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="/")
else:
    app = Flask(__name__)

DATA_DIR.mkdir(parents=True, exist_ok=True)
if not USERS_FILE.exists():
    USERS_FILE.write_text("[]")

if not WEEKLY_PLANS_FILE.exists():
    WEEKLY_PLANS_FILE.write_text("{}")



def load_users():
    # keep existing JSON file for registered users
    return json.loads(USERS_FILE.read_text())


def save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2))


def load_weekly_plans():
    try:
        return json.loads(WEEKLY_PLANS_FILE.read_text())
    except Exception:
        return {}


def save_weekly_plans(plans):
    WEEKLY_PLANS_FILE.write_text(json.dumps(plans, indent=2))


def _parse_start_date(start_date_str: str | None) -> date:
    if not start_date_str:
        return date.today()
    try:
        return datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except Exception:
        return date.today()


def _stable_variant(*parts: str, mod: int = 3) -> int:
    raw = "|".join([str(p or "") for p in parts]).encode("utf-8")
    h = hashlib.md5(raw).hexdigest()
    return int(h[:8], 16) % max(1, int(mod))


def _title_case(s: str) -> str:
    s = re.sub(r"\s+", " ", str(s or "").strip())
    return s[:1].upper() + s[1:] if s else s


def _normalize_cuisines(user: dict | None) -> list[str]:
    if not user or not isinstance(user, dict):
        return []
    raw = user.get("cuisines")
    if raw is None:
        raw = user.get("cuisine")
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = _title_case(x)
        if not s:
            continue
        if s.lower() in {"any", "none", "all"}:
            continue
        out.append(s)
    # de-dupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for s in out:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(s)
    return deduped


def _pick_cuisine(user: dict | None, seed_key: str) -> str | None:
    cuisines = _normalize_cuisines(user)
    if not cuisines:
        return None
    v = _stable_variant(seed_key, *cuisines, mod=len(cuisines))
    return cuisines[v]


def _infer_food_kind(food_name: str, food: dict) -> str:
    n = str(food_name or "").lower()
    if any(k in n for k in ["juice", "smoothie", "shake", "lassi", "buttermilk"]):
        return "drink"
    if any(k in n for k in ["curry", "soup", "omelette", "salad", "bowl", "khichdi", "upma", "poha", "dosa", "idli", "pulao", "biriyani", "biryani", "wrap", "sandwich", "stir", "fried", "roast", "grilled"]):
        return "dish"
    if any(k in n for k in ["egg", "chicken", "fish", "salmon", "mutton", "prawn"]):
        return "protein"
    if any(k in n for k in ["oats", "quinoa", "millet", "rice", "bread", "roti", "chapati", "pasta", "noodles", "potato", "sweet potato", "lentils", "chickpeas", "beans"]):
        return "grain"
    if any(k in n for k in ["apple", "banana", "papaya", "mango", "orange", "berries", "grapes"]):
        return "fruit"
    # macro-based fallback
    try:
        protein = float(food.get("protein_g") or 0)
        carbs = float(food.get("carbs_g") or 0)
        if protein >= 18:
            return "protein"
        if carbs >= 30:
            return "grain"
    except Exception:
        pass
    return "veg"


def _make_recipe_for_food(food: dict, meal: str, user: dict | None = None) -> dict:
    name = str(food.get("food_name") or "").strip()
    diet = str((user or {}).get("diet_type") or food.get("diet_type") or "Veg")
    meal = str(meal or "").strip().lower()

    cuisine = _pick_cuisine(user, seed_key=f"{name}|{meal}|{diet}")

    kind = _infer_food_kind(name, food)
    v = _stable_variant(name, meal, diet, mod=4)

    # If the dataset already looks like a full dish, keep the name and add a recipe scaffold.
    base = _title_case(name)

    cuisine_templates: dict[str, dict[str, list[str]]] = {
        "Indian": {
            "breakfast": [
                "{base} Masala Bowl",
                "Spiced {base} Breakfast Bowl",
                "{base} Chaat-Style Bowl",
            ],
            "lunch": [
                "{base} Tikka Bowl",
                "{base} Masala Plate",
                "{base} Curry Bowl",
            ],
            "dinner": [
                "Grilled {base} Tandoori",
                "{base} Curry Bowl",
                "{base} Masala Skillet",
            ],
        },
        "Mediterranean": {
            "breakfast": [
                "Greek-Style {base} Bowl",
                "Lemon {base} Breakfast Bowl",
            ],
            "lunch": [
                "Lemon Herb {base} Plate",
                "{base} Mediterranean Bowl",
                "{base} Olive Oil Salad Bowl",
            ],
            "dinner": [
                "Grilled Lemon Herb {base}",
                "{base} Mediterranean Skillet",
            ],
        },
        "Italian": {
            "breakfast": [
                "{base} Basil Breakfast Bowl",
                "{base} Caprese Bowl",
            ],
            "lunch": [
                "{base} Pesto Bowl",
                "{base} Marinara Plate",
            ],
            "dinner": [
                "Grilled {base} with Herbs",
                "{base} Pesto Skillet",
            ],
        },
        "Mexican": {
            "breakfast": [
                "{base} Salsa Breakfast Bowl",
                "Spiced {base} Breakfast Bowl",
            ],
            "lunch": [
                "{base} Taco Bowl",
                "{base} Lime-Cilantro Plate",
            ],
            "dinner": [
                "Grilled {base} Fajita Plate",
                "{base} Chili-Lime Skillet",
            ],
        },
        "Chinese": {
            "breakfast": [
                "{base} Ginger Bowl",
                "{base} Sesame Breakfast Bowl",
            ],
            "lunch": [
                "{base} Stir-Fry Bowl",
                "{base} Garlic Soy Plate",
            ],
            "dinner": [
                "Grilled {base} with Garlic Soy",
                "{base} Sesame Stir-Fry",
            ],
        },
        "South Indian": {
            "breakfast": [
                "{base} Coconut Bowl",
                "{base} Curry Leaf Breakfast Bowl",
            ],
            "lunch": [
                "{base} Pepper Fry Bowl",
                "{base} Curry Leaf Plate",
            ],
            "dinner": [
                "Grilled {base} Pepper Fry",
                "{base} South Indian Skillet",
            ],
        },
    }

    # If the dataset already looks like a full dish, keep the name and add a recipe scaffold.
    if kind == "dish":
        dish_name = _title_case(name)
    elif kind in {"fruit", "drink"}:
        base = _title_case(name)
        if kind == "drink":
            options = [
                "{base}",
                "{base} Refresh",
                "{base} Cooler",
            ]
        else:
            # Fruit should never become grilled/plates; keep breakfast-style dishes.
            options = [
                "{base} Fruit Bowl",
                "{base} Yogurt Parfait",
                "{base} Smoothie Bowl",
                "{base} Chia Bowl",
            ]
        dish_name = options[v % len(options)].format(base=base)
    else:
        templates_for_cuisine = cuisine_templates.get(cuisine or "", {})
        options = templates_for_cuisine.get(meal) if templates_for_cuisine else None
        if not options:
            if meal == "breakfast":
                options = [
                    "{base} Power Bowl",
                    "{base} Yogurt Parfait",
                    "{base} Breakfast Smoothie Bowl",
                    "{base} Overnight Bowl",
                ]
            elif meal == "lunch":
                options = [
                    "{base} Salad Bowl",
                    "{base} Grain Bowl",
                    "{base} Protein Plate",
                    "{base} Wrap Bowl",
                ]
            else:
                options = [
                    "Grilled {base} Plate",
                    "{base} Stir-Fry Plate",
                    "{base} Curry Bowl",
                    "{base} Spiced Skillet",
                ]

        dish_name = options[v % len(options)].format(base=base)

    # Build a simple, realistic ingredient list (whole-dish style)
    common = ["salt", "black pepper", "lemon", "olive oil"]
    cuisine_flavors = {
        "Indian": ["cumin", "turmeric", "ginger", "garlic", "garam masala"],
        "Mediterranean": ["oregano", "olive oil", "lemon", "garlic"],
        "Italian": ["basil", "olive oil", "garlic"],
        "Mexican": ["cumin", "paprika", "lime", "cilantro"],
        "Chinese": ["soy sauce", "ginger", "garlic", "sesame oil"],
        "South Indian": ["curry leaves", "mustard seeds", "coconut"],
    }
    veg_addons = ["cucumber", "tomato", "onion", "capsicum", "carrot", "spinach", "coriander"]
    veg_protein = ["paneer", "chickpeas", "curd", "tofu", "lentils"]
    nonveg_protein = ["egg", "chicken", "fish"]
    grain_addons = ["brown rice", "quinoa", "millet", "whole wheat bread"]

    # Drinks: avoid grains/protein templates and provide a simple beverage recipe.
    if kind == "drink":
        ingredients = [
            _title_case(name),
            "Water",
            "Lemon",
            "Mint",
            "Ice (optional)",
        ]
        steps = [
            "Chill all ingredients.",
            "Mix/blend and adjust sweetness/salt to taste.",
            "Serve cold.",
        ]
        return {
            "title": dish_name,
            "base_food": _title_case(name),
            "cuisine": cuisine,
            "diet_type": diet,
            "meal": meal,
            "ingredients": ingredients,
            "steps": steps,
            "time_minutes": 6 + (v * 2),
        }

    # Fruit: keep it as bowls/parfaits/smoothies with relevant ingredients.
    if kind == "fruit":
        fruit_addons = ["Curd", "Yogurt", "Chia seeds", "Nuts", "Cinnamon"]
        ingredients = [_title_case(name), fruit_addons[v % len(fruit_addons)], fruit_addons[(v + 2) % len(fruit_addons)], "Honey (optional)"]
        # Remove duplicates while preserving order
        seen = set()
        ingredients = [x for x in ingredients if not (x.lower() in seen or seen.add(x.lower()))]
        steps = [
            "Wash and chop the fruit.",
            "Combine with yogurt/curd and toppings.",
            "Serve immediately or chill for 10 minutes.",
        ]
        return {
            "title": dish_name,
            "base_food": _title_case(name),
            "cuisine": cuisine,
            "diet_type": diet,
            "meal": meal,
            "ingredients": ingredients,
            "steps": steps,
            "time_minutes": 8 + (v * 2),
        }

    addons = []
    if kind in {"veg", "fruit"}:
        addons.extend([veg_addons[(v + 0) % len(veg_addons)], veg_addons[(v + 2) % len(veg_addons)]])
        addons.append((veg_protein if diet.lower().startswith("veg") else nonveg_protein)[v % (len(veg_protein) if diet.lower().startswith("veg") else len(nonveg_protein))])
        if meal in {"lunch", "dinner"}:
            addons.append(grain_addons[v % len(grain_addons)])
    elif kind == "grain":
        addons.extend([veg_addons[(v + 1) % len(veg_addons)], veg_addons[(v + 4) % len(veg_addons)]])
        addons.append((veg_protein if diet.lower().startswith("veg") else nonveg_protein)[(v + 1) % (len(veg_protein) if diet.lower().startswith("veg") else len(nonveg_protein))])
    else:  # protein
        addons.extend([veg_addons[(v + 3) % len(veg_addons)], veg_addons[(v + 5) % len(veg_addons)]])
        if meal == "breakfast" and diet.lower().startswith("veg"):
            addons.append("curd")
        else:
            addons.append(grain_addons[(v + 2) % len(grain_addons)])

    flavors = cuisine_flavors.get(cuisine or "", [])
    flavor_pick = []
    if flavors:
        flavor_pick = [flavors[v % len(flavors)]]
        if len(flavors) > 2:
            flavor_pick.append(flavors[(v + 2) % len(flavors)])

    ingredients = [_title_case(name)] + [_title_case(x) for x in addons] + [_title_case(x) for x in flavor_pick] + [_title_case(x) for x in common[:2]]
    # Remove duplicates while preserving order
    seen = set()
    ingredients = [x for x in ingredients if not (x.lower() in seen or seen.add(x.lower()))]

    steps = []
    if "grilled" in dish_name.lower():
        steps = [
            f"Season {_title_case(name)} with spices/herbs and a squeeze of lemon.",
            "Grill or pan-sear on medium heat until cooked through.",
            "Add chopped veggies on the side and finish with pepper.",
        ]
    elif "salad" in dish_name.lower() or "bowl" in dish_name.lower():
        steps = [
            "Wash and chop vegetables and herbs.",
            f"Prepare {_title_case(name)} as needed (cook/steam/roast) and cool slightly.",
            "Mix everything in a bowl and season with lemon, salt, and pepper.",
            "Add a light drizzle of oil and toss well.",
        ]
    elif "curry" in dish_name.lower():
        steps = [
            "Lightly sauté onions/tomatoes with spices in a pan.",
            f"Add {_title_case(name)} and cook until flavors combine.",
            "Adjust consistency with water and simmer for 6–10 minutes.",
            "Serve hot with a grain side.",
        ]
    else:
        steps = [
            f"Prep {_title_case(name)} (cook/steam/roast) based on the ingredient.",
            "Sauté veggies with light seasoning.",
            "Combine in a bowl/plate and finish with lemon and pepper.",
        ]

    return {
        "title": dish_name,
        "base_food": _title_case(name),
        "cuisine": cuisine,
        "diet_type": diet,
        "meal": meal,
        "ingredients": ingredients,
        "steps": steps,
        "time_minutes": 12 + (v * 4),
    }


def _pick_meals_for_day(
    scored_foods: list,
    targets: dict,
    seed: int,
    used_ids: set[str],
    user: dict | None = None,
    max_items: dict[str, int] | None = None,
):
    # shuffle with a deterministic seed to introduce variety day-to-day
    rnd = random.Random(seed)
    shuffled = list(scored_foods)
    rnd.shuffle(shuffled)

    # Keep best foods near the front by mixing shuffle + rank.
    # This preserves score ordering bias but avoids identical daily picks.
    mixed = sorted(enumerate(shuffled), key=lambda t: (t[0] // 8, ))
    candidates = [t[1] for t in mixed]

    def _name_key(food_name: str | None) -> str:
        return f"name:{str(food_name or '').strip().lower()}"

    def _safe_calories(v) -> float:
        try:
            x = float(v)
        except Exception:
            return 0.0
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return max(0.0, x)

    if not max_items:
        max_items = {"breakfast": 3, "lunch": 3, "dinner": 3}

    def pick(limit: float):
        picked = []
        total = 0
        # first pass: avoid repeats
        for food in candidates:
            fid = food.get("food_id")
            name_key = _name_key(food.get("food_name"))
            if (fid and fid in used_ids) or (name_key in used_ids):
                continue
            c = food.get("calories", 0) or 0
            if total + c <= limit or not picked:
                picked.append({
                    "food_id": fid,
                    "food_name": food.get("food_name"),
                    "dish_name": _make_recipe_for_food(food, meal_name="", user=None).get("title") if False else None,
                    "calories": c,
                })
                if fid:
                    used_ids.add(fid)
                used_ids.add(name_key)
                total += c
            if total >= limit:
                break

        # fallback: if nothing picked (tiny dataset), allow repeats
        if not picked:
            for food in candidates:
                c = food.get("calories", 0) or 0
                picked.append({
                    "food_id": food.get("food_id"),
                    "food_name": food.get("food_name"),
                    "calories": c,
                })
                if c >= limit:
                    break
        return picked

    cal = targets.get("calories", 2000)
    def pick_with_recipe(meal_name: str, limit: float):
        picked = []
        total = 0

        # first pass: avoid repeats
        for food in candidates:
            fid = food.get("food_id")
            name_key = _name_key(food.get("food_name"))
            if (fid and fid in used_ids) or (name_key in used_ids):
                continue
            c = _safe_calories(food.get("calories", 0) or 0)
            # skip zero-calorie/missing entries to avoid runaway lists
            if c <= 0 and picked:
                continue
            if total + c <= limit or not picked:
                recipe = _make_recipe_for_food(food, meal=meal_name, user=user)
                picked.append({
                    "food_id": fid,
                    "food_name": food.get("food_name"),
                    "dish_name": recipe.get("title"),
                    "recipe": recipe,
                    "calories": c,
                })
                if fid:
                    used_ids.add(fid)
                used_ids.add(name_key)
                total += c
            if len(picked) >= max_items.get(meal_name, 3):
                break
            if total >= limit:
                break

        # fallback: if nothing picked (tiny dataset), allow repeats
        if not picked:
            local_names: set[str] = set()
            # pass 1: still try to avoid previously used names
            for food in candidates:
                fid = food.get("food_id")
                name_key = _name_key(food.get("food_name"))
                if (fid and fid in used_ids) or (name_key in used_ids):
                    continue
                if name_key in local_names:
                    continue
                c = _safe_calories(food.get("calories", 0) or 0)
                if c <= 0:
                    continue
                recipe = _make_recipe_for_food(food, meal=meal_name, user=user)
                picked.append({
                    "food_id": fid,
                    "food_name": food.get("food_name"),
                    "dish_name": recipe.get("title"),
                    "recipe": recipe,
                    "calories": c,
                })
                if fid:
                    used_ids.add(fid)
                used_ids.add(name_key)
                local_names.add(name_key)
                if len(picked) >= max_items.get(meal_name, 3):
                    break
                if c >= limit:
                    break

            # pass 2: if still nothing, allow repeats but keep the list small and sensible
            if not picked:
                for food in candidates:
                    fid = food.get("food_id")
                    name_key = _name_key(food.get("food_name"))
                    if name_key in local_names:
                        continue
                    c = _safe_calories(food.get("calories", 0) or 0)
                    if c <= 0:
                        continue
                    recipe = _make_recipe_for_food(food, meal=meal_name, user=user)
                    picked.append({
                        "food_id": fid,
                        "food_name": food.get("food_name"),
                        "dish_name": recipe.get("title"),
                        "recipe": recipe,
                        "calories": c,
                    })
                    if fid:
                        used_ids.add(fid)
                    used_ids.add(name_key)
                    local_names.add(name_key)
                    if len(picked) >= max_items.get(meal_name, 3):
                        break
                    if c >= limit:
                        break
        return picked

    return {
        "daily_calories": cal,
        "breakfast": pick_with_recipe("breakfast", cal * 0.30),
        "lunch": pick_with_recipe("lunch", cal * 0.40),
        "dinner": pick_with_recipe("dinner", cal * 0.30),
    }


def _apply_picks_to_meals(
    meals: dict,
    picks: dict,
    scored_foods: list,
    targets: dict,
    used_ids: set[str],
    user: dict | None = None,
    max_items: dict[str, int] | None = None,
):
    """Inject 1-2 user-picked recipes per meal (if provided) and fill remaining slots.
    Picks are applied only when food_id exists in the candidate list.
    """
    if not picks or not isinstance(picks, dict):
        return meals

    cal = targets.get("calories", 2000)
    limits = {
        "breakfast": cal * 0.30,
        "lunch": cal * 0.40,
        "dinner": cal * 0.30,
    }

    by_id = {f.get("food_id"): f for f in (scored_foods or []) if f.get("food_id")}

    def _name_key(food_name: str | None) -> str:
        return f"name:{str(food_name or '').strip().lower()}"

    def put_picks(meal_name: str):
        chosen = []
        chosen_ids: set[str] = set()
        total = 0
        raw = picks.get(meal_name) or []
        if not isinstance(raw, list):
            raw = []
        for fid in raw[:2]:
            if fid and fid in chosen_ids:
                continue
            f = by_id.get(fid)
            if not f:
                continue
            c = f.get("calories", 0) or 0
            if total + c <= limits[meal_name] or not chosen:
                recipe = _make_recipe_for_food(f, meal=meal_name, user=user)
                chosen.append({
                    "food_id": fid,
                    "food_name": f.get("food_name"),
                    "dish_name": recipe.get("title"),
                    "recipe": recipe,
                    "calories": c,
                })
                if fid:
                    chosen_ids.add(fid)
                used_ids.add(fid)
                used_ids.add(_name_key(f.get("food_name")))
                total += c
            if max_items and len(chosen) >= max_items.get(meal_name, 99):
                break

        # top-up with existing meal picks if needed
        for it in meals.get(meal_name) or []:
            fid = it.get("food_id")
            # Don't filter against used_ids here.
            # These items were already added to used_ids during day generation,
            # and skipping them would incorrectly empty the meal.
            if fid and fid in chosen_ids:
                continue
            c = it.get("calories", 0) or 0
            if total + c <= limits[meal_name] or not chosen:
                # ensure existing items have dish_name/recipe
                if not it.get("recipe"):
                    src = by_id.get(fid) or {"food_name": it.get("food_name"), "diet_type": None}
                    recipe = _make_recipe_for_food(src, meal=meal_name, user=user)
                    it = dict(it)
                    it.setdefault("dish_name", recipe.get("title"))
                    it.setdefault("recipe", recipe)
                chosen.append(it)
                if fid:
                    chosen_ids.add(fid)
                    used_ids.add(fid)
                used_ids.add(_name_key(it.get("food_name")))
                total += c
            if max_items and len(chosen) >= max_items.get(meal_name, 99):
                break
            if total >= limits[meal_name]:
                break

        meals[meal_name] = chosen

    put_picks("breakfast")
    put_picks("lunch")
    put_picks("dinner")
    return meals


def _enrich_meals_with_recipes(meals: dict, scored_foods: list, user: dict | None = None) -> dict:
    """Ensure each meal item includes recipe-style fields.

    This keeps API responses consistent across endpoints:
    - Adds `dish_name` (recipe title)
    - Adds `recipe` (ingredients/steps + cuisine when provided)
    """
    if not meals or not isinstance(meals, dict):
        return meals

    by_id = {f.get("food_id"): f for f in (scored_foods or []) if isinstance(f, dict) and f.get("food_id")}

    def enrich_list(meal_name: str, items: list) -> list:
        if not isinstance(items, list):
            return []
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            fid = it.get("food_id")
            src = by_id.get(fid) if fid else None
            if not src:
                src = {"food_name": it.get("food_name"), "diet_type": (user or {}).get("diet_type")}
            recipe = _make_recipe_for_food(src, meal=meal_name, user=user)
            enriched = dict(it)
            enriched.setdefault("dish_name", recipe.get("title"))
            enriched.setdefault("recipe", recipe)
            out.append(enriched)
        return out

    for meal_name in ("breakfast", "lunch", "dinner"):
        if meal_name in meals:
            meals[meal_name] = enrich_list(meal_name, meals.get(meal_name) or [])

    return meals


def get_user_by_id(user_id: str):
    # prefer the CSV dataset if present
    csv_user = load_users_from_csv(user_id)
    if csv_user:
        return csv_user
    # fallback to registered users
    users = load_users()
    return next((u for u in users if u.get("user_id") == user_id), None)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the built frontend if present. Otherwise return a simple JSON status.
    """
    if FRONTEND_DIST.exists():
        # If file exists in dist, serve it; otherwise serve index.html for SPA routing
        target = FRONTEND_DIST / path
        if path and target.exists():
            return app.send_static_file(path)
        return app.send_static_file('index.html')
    return jsonify({"status": "backend only - frontend not built"})


@app.route("/register", methods=["POST"])
def register():
    payload = request.get_json()
    if not payload or "user_id" not in payload:
        return jsonify({"error": "user_id required"}), 400
    users = load_users()
    # Overwrite or append
    users = [u for u in users if u.get("user_id") != payload["user_id"]]
    users.append(payload)
    save_users(users)
    return jsonify({"status": "ok", "user_id": payload["user_id"]})


@app.route("/recommend", methods=["POST"])
def recommend():
    payload = request.get_json() or {}
    user_id = payload.get("user_id")
    cheat_meal = payload.get("cheat_meal")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    # Compute BMI
    user["bmi"] = compute_bmi(user.get("height_cm"), user.get("weight_kg"))

    # Analyze risk
    user["health_risk"] = analyze_health_risk(user)

    # Nutrition targets
    targets = calculate_nutrition_targets(user)

    # Apply cheat meal adjustment
    if cheat_meal:
        targets = apply_cheat_adjustment(targets, cheat_meal)

    # Filter foods
    foods = filter_foods(user)

    # Score foods
    scored = score_foods(user, foods)

    # Optimize into meals
    meals = optimize_meals(scored, targets)
    meals = _enrich_meals_with_recipes(meals, scored, user=user)

    response = {
        "user_id": user_id,
        "targets": targets,
        "meals": meals,
    }
    return jsonify(response)


@app.route("/substitute", methods=["POST"])
def substitute():
    """Replace a disliked food in the user's plan with a similar alternative.
    Accepts JSON: { user_id: str, disliked_food_id: str }
    Returns: { substitute: {...}, meals: {...} }
    """
    payload = request.get_json() or {}
    user_id = payload.get("user_id")
    disliked_food_id = payload.get("disliked_food_id")
    if not user_id or not disliked_food_id:
        return jsonify({"error": "user_id and disliked_food_id required"}), 400

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    # recompute BMI and targets
    user["bmi"] = compute_bmi(user.get("height_cm"), user.get("weight_kg"))
    targets = calculate_nutrition_targets(user)

    # Rebuild candidate list excluding the disliked food
    all_foods = filter_foods(user)
    candidates = [f for f in all_foods if f.get("food_id") != disliked_food_id]

    # Score candidates and optimize meals
    scored = score_foods(user, candidates)
    new_meals = optimize_meals(scored, targets)
    new_meals = _enrich_meals_with_recipes(new_meals, scored, user=user)

    # Find one suggested substitute (best-scoring replacement)
    substitute_food = None
    if scored:
        substitute_food = scored[0]

    if isinstance(substitute_food, dict) and substitute_food.get("food_name"):
        r = _make_recipe_for_food(substitute_food, meal="lunch", user=user)
        substitute_food = dict(substitute_food)
        substitute_food.setdefault("dish_name", r.get("title"))
        substitute_food.setdefault("recipe", r)

    return jsonify({"substitute": substitute_food, "meals": new_meals})


@app.route("/weekly-update", methods=["POST"])
def weekly_update():
    payload = request.get_json() or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    engine = WeeklyAdaptationEngine()
    engine.adapt(user, payload)

    # save user changes if any
    users = load_users()
    users = [u for u in users if u.get("user_id") != user_id]
    users.append(user)
    save_users(users)

    return jsonify({"status": "ok"})


@app.route("/weekly-plan", methods=["POST"])
def weekly_plan():
    """Workflow endpoint:
    - Generate a full week plan for a user
    - If a cheat meal is reported for a given day, regenerate remaining days

    Payload supports either:
      { user_id: str, start_date?: 'YYYY-MM-DD', days?: int, cheat?: {day:int, cheat_meal:{...}} }
    or:
      { user: {...full profile...}, start_date?:..., days?:..., cheat?:... }
    """
    payload = request.get_json() or {}
    days = int(payload.get("days") or 7)
    days = max(1, min(days, 14))

    # allow direct user profile input (no predefined dataset needed)
    inline_user = payload.get("user")
    user_id = payload.get("user_id") or (inline_user or {}).get("user_id")

    if inline_user:
        user = dict(inline_user)
        if not user_id:
            user_id = "user_input"
            user["user_id"] = user_id
    else:
        if not user_id:
            return jsonify({"error": "user_id or user required"}), 400
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "user not found"}), 404

    start = _parse_start_date(payload.get("start_date"))

    # compute user derived fields + base targets
    user["bmi"] = compute_bmi(user.get("height_cm"), user.get("weight_kg"))
    user["health_risk"] = analyze_health_risk(user)
    base_targets = calculate_nutrition_targets(user)

    # fetch candidate foods + score once
    foods = filter_foods(user)
    scored = score_foods(user, foods)

    # Dynamically cap items per meal to reduce repeats.
    # Veg data has only ~26 unique foods; without a cap, repeats are inevitable.
    unique_names = {
        str(f.get("food_name") or "").strip().lower()
        for f in (scored or [])
        if str(f.get("food_name") or "").strip()
    }
    # Try to keep the plan mostly unique by food_name across the requested range.
    # Cap at 3, but shrink if the unique pool is small.
    per_meal_cap = 3
    try:
        denom = max(1, days * 3)
        per_meal_cap = max(1, min(3, len(unique_names) // denom))
    except Exception:
        per_meal_cap = 1
    max_items = {"breakfast": per_meal_cap, "lunch": per_meal_cap, "dinner": per_meal_cap}

    picks = payload.get("picks") or None

    cheat = payload.get("cheat") or None
    cheat_day = None
    remaining_targets = base_targets
    if cheat and isinstance(cheat, dict):
        try:
            cheat_day = int(cheat.get("day"))
        except Exception:
            cheat_day = None
        cheat_meal = cheat.get("cheat_meal")
        if cheat_day and cheat_meal:
            # after a cheat day, remaining days should be stricter
            remaining_targets = apply_cheat_adjustment(dict(base_targets), cheat_meal)

    plans = load_weekly_plans()
    existing = plans.get(user_id)

    # if cheat day provided and an existing plan exists with same start date, update remaining days
    if cheat_day and existing and existing.get("start_date") == start.isoformat():
        week = existing.get("week") or []
        used_ids = set()
        for d in week:
            for meal in (d.get("meals") or {}).values():
                for item in meal or []:
                    fid = item.get("food_id")
                    if fid:
                        used_ids.add(fid)
                    nm = item.get("food_name")
                    if nm:
                        used_ids.add(f"name:{str(nm).strip().lower()}")

        for i in range(len(week)):
            day_number = int(week[i].get("day") or (i + 1))
            if day_number <= cheat_day:
                continue
            meals = _pick_meals_for_day(scored, remaining_targets, seed=day_number, used_ids=used_ids, user=user, max_items=max_items)
            # Apply picks only to the very next day after cheat (keeps variety)
            if picks and day_number == (cheat_day + 1):
                meals = _apply_picks_to_meals(meals, picks, scored, remaining_targets, used_ids, user=user, max_items=max_items)
            week[i]["targets"] = remaining_targets
            week[i]["meals"] = meals

        existing["week"] = week
        existing["last_update"] = datetime.utcnow().isoformat() + "Z"
        existing["cheat"] = cheat
        plans[user_id] = existing
        save_weekly_plans(plans)
        return jsonify(existing)

    # else: create a brand new weekly plan
    used_ids: set[str] = set()
    week = []
    for i in range(days):
        day_number = i + 1
        d = start + timedelta(days=i)
        targets = base_targets
        if cheat_day and day_number > cheat_day:
            targets = remaining_targets

        meals = _pick_meals_for_day(scored, targets, seed=day_number, used_ids=used_ids, user=user, max_items=max_items)
        # Apply picks only on the first day (keeps the rest varied)
        if picks and day_number == 1:
            meals = _apply_picks_to_meals(meals, picks, scored, targets, used_ids, user=user, max_items=max_items)
        week.append({
            "day": day_number,
            "date": d.isoformat(),
            "targets": targets,
            "meals": meals,
        })

    doc = {
        "user_id": user_id,
        "start_date": start.isoformat(),
        "days": days,
        "cheat": cheat,
        "week": week,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_update": datetime.utcnow().isoformat() + "Z",
    }

    plans[user_id] = doc
    save_weekly_plans(plans)
    return jsonify(doc)


@app.route("/foods", methods=["POST"])
def foods_for_user():
    """Return recipe cards for the UI.
    Accepts { user: {...} } or { user_id: "..." }.
    Returns top scored foods after applying user constraints.
    """
    payload = request.get_json() or {}
    inline_user = payload.get("user")
    user_id = payload.get("user_id") or (inline_user or {}).get("user_id")

    if inline_user:
        user = dict(inline_user)
        if not user_id:
            user_id = "user_input"
            user["user_id"] = user_id
    else:
        if not user_id:
            return jsonify({"error": "user_id or user required"}), 400
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "user not found"}), 404

    user["bmi"] = compute_bmi(user.get("height_cm"), user.get("weight_kg"))
    foods = filter_foods(user)
    scored = score_foods(user, foods)

    limit = int(payload.get("limit") or 30)
    limit = max(5, min(limit, 120))

    cards = []
    for f in (scored[:limit] if scored else []):
        cards.append({
            "food_id": f.get("food_id"),
            "food_name": f.get("food_name"),
            "diet_type": f.get("diet_type"),
            "calories": f.get("calories"),
            "protein_g": f.get("protein_g"),
            "carbs_g": f.get("carbs_g"),
            "fat_g": f.get("fat_g"),
        })

    return jsonify({"user_id": user_id, "foods": cards})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
