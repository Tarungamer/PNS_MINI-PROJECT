import pandas as pd
from pathlib import Path
import numpy as np
from backend import ml_engine
from typing import Dict, Any

DATA_DIR = Path(__file__).resolve().parent / "data"
# Prefer the full master dataset when present
FOODS_MASTER = DATA_DIR / "food_nutrition_master_500.csv"
FOODS_CSV = DATA_DIR / "foods.csv"
USERS_MASTER = DATA_DIR / "user_health_profile_1000.csv"
PERSONALIZED_PLANS = DATA_DIR / "personalized_diet_plan.csv"


def compute_bmi(height_cm, weight_kg):
    try:
        h = float(height_cm) / 100.0
        w = float(weight_kg)
        if h <= 0:
            return None
        return round(w / (h * h), 2)
    except Exception:
        return None


def analyze_health_risk(user: Dict[str, Any]) -> int:
    risk = 0
    if user.get("diabetes"):
        risk += 2
    if user.get("blood_pressure") == "High":
        risk += 2
    if user.get("cholesterol") == "High":
        risk += 2
    if user.get("oxygen_level") is not None and user.get("oxygen_level") < 95:
        risk += 1
    if user.get("hemoglobin") == "Low":
        risk += 1
    return risk


def calculate_nutrition_targets(user: Dict[str, Any]) -> Dict[str, Any]:
    weight = user.get("weight_kg", 70)
    base_calories = 22 * weight
    activity = user.get("activity_level", "Medium")
    if activity == "Low":
        base_calories -= 200
    if activity == "High":
        base_calories += 300

    goal = str(user.get("goal") or user.get("weight_goal") or "").strip().lower()
    if goal in {"lose fat", "cut", "weight loss", "lose weight"}:
        base_calories -= 300
    elif goal in {"build muscle", "bulk", "muscle gain", "gain muscle"}:
        base_calories += 250

    carbs_ratio = 0.50
    protein_ratio = 0.25
    fat_ratio = 0.25

    if user.get("diabetes"):
        carbs_ratio -= 0.15
        protein_ratio += 0.10

    if user.get("bmi") and user.get("bmi") > 30:
        carbs_ratio -= 0.10
        protein_ratio += 0.10

    return {
        "calories": int(base_calories),
        "carbs_ratio": round(carbs_ratio, 2),
        "protein_ratio": round(protein_ratio, 2),
        "fat_ratio": round(fat_ratio, 2),
    }


def apply_cheat_adjustment(targets: Dict[str, Any], cheat_meal: Dict[str, Any]) -> Dict[str, Any]:
    if not cheat_meal:
        return targets
    c = cheat_meal.get("calories", 0)
    sugar = cheat_meal.get("sugar_g", 0)
    if c > 600:
        targets["calories"] = max(1200, int(targets["calories"] - c * 0.5))
    if sugar > 30:
        targets["carbs_ratio"] = max(0.2, round(targets.get("carbs_ratio", 0.5) - 0.1, 2))
        targets["protein_ratio"] = min(0.5, round(targets.get("protein_ratio", 0.25) + 0.1, 2))
    return targets


def load_foods_df():
    # prefer master file if present
    path = FOODS_MASTER if FOODS_MASTER.exists() else FOODS_CSV
    if not path.exists():
        cols = [
            "food_id",
            "food_name",
            "diet_type",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
            "sugar_g",
            "sodium_mg",
            "iron_mg",
            "potassium_mg",
            "cholesterol_mg",
            "glycemic_index",
        ]
        return pd.DataFrame(columns=cols)
    return pd.read_csv(path)


def load_users_from_csv(user_id: str = None):
    """Load user profile(s) from the master CSV when available.
    If `user_id` provided, return single user dict or None.
    Otherwise return full list of dicts.
    """
    if not USERS_MASTER.exists():
        return None if user_id else []
    df = pd.read_csv(USERS_MASTER)
    # Normalize column names for compatibility
    df.columns = [c.strip() for c in df.columns]
    if user_id:
        row = df[df.get("user_id") == user_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()
    return df.to_dict(orient="records")


def filter_foods(user: Dict[str, Any]):
    df_all = load_foods_df()
    df = df_all

    # Filter by diet type (fallback: if no foods exist for diet, keep all diets)
    diet = user.get("diet_type") or "Veg"
    try:
        df_diet = df[df["diet_type"].str.lower() == str(diet).lower()]
        if not df_diet.empty:
            df = df_diet
    except Exception:
        pass

    # Remove allergies (fallback: if everything gets removed, ignore allergies)
    allergies = user.get("allergies") or []
    df_no_allergy = df
    try:
        for a in allergies:
            if not a:
                continue
            df_no_allergy = df_no_allergy[~df_no_allergy["food_name"].str.contains(a, case=False, na=False)]
        if not df_no_allergy.empty:
            df = df_no_allergy
    except Exception:
        pass

    # Diabetes constraint (fallback: relax threshold, then drop if still empty)
    if user.get("diabetes"):
        try:
            df_gi = df[df["glycemic_index"] < 55]
            if df_gi.empty:
                df_gi = df[df["glycemic_index"] < 70]
            if not df_gi.empty:
                df = df_gi
        except Exception:
            pass

    # High blood pressure -> sodium filter (fallback: relax threshold)
    if user.get("blood_pressure") == "High":
        try:
            df_s = df[df["sodium_mg"] < 140]
            if df_s.empty:
                df_s = df[df["sodium_mg"] < 250]
            if df_s.empty:
                df_s = df[df["sodium_mg"] < 400]
            if not df_s.empty:
                df = df_s
        except Exception:
            pass

    # High cholesterol (fallback: relax threshold)
    if user.get("cholesterol") == "High":
        try:
            df_c = df[df["cholesterol_mg"] < 50]
            if df_c.empty:
                df_c = df[df["cholesterol_mg"] < 150]
            if not df_c.empty:
                df = df_c
        except Exception:
            pass

    # Prioritize iron if oxygen low (only if it leaves at least some foods)
    try:
        if user.get("oxygen_level") is not None and user.get("oxygen_level") < 95 and not df.empty:
            median_iron = df["iron_mg"].median()
            df_iron = df.sort_values(by=["iron_mg"], ascending=False)
            df_iron = df_iron[df_iron["iron_mg"] >= median_iron]
            if not df_iron.empty:
                df = df_iron
    except Exception:
        pass

    # Last resort: if something went wrong and df is empty, return the whole dataset
    if df is None or getattr(df, "empty", False):
        df = df_all

    return df.to_dict(orient="records")


def normalize_series(arr):
    a = np.array(arr, dtype=float)
    mi = np.nanmin(a)
    ma = np.nanmax(a)
    if ma - mi == 0:
        return np.ones_like(a)
    return (a - mi) / (ma - mi)


def _truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v) != 0.0
    s = str(v).strip().lower()
    return s in {"true", "1", "yes", "y", "t"}


def _encode_activity(level: Any) -> int:
    mapping = {"low": 0, "medium": 1, "high": 2}
    if level is None:
        return 1
    return mapping.get(str(level).strip().lower(), 1)


def _encode_gender(g: Any) -> int:
    if g is None or (isinstance(g, float) and np.isnan(g)):
        return 0
    gs = str(g).strip().lower()
    return 1 if gs.startswith("f") else 0


def _make_model_feature_vector(user: Dict[str, Any], food: Dict[str, Any]) -> list[float]:
    """Must match the feature order in `backend/train_model.py` make_fv()."""
    bmi = user.get("bmi") or 0
    oxygen = user.get("oxygen_level") or 0

    bp = user.get("blood_pressure")
    chol = user.get("cholesterol")

    return [
        food.get("calories", 0) or 0,
        food.get("protein_g", 0) or 0,
        food.get("carbs_g", 0) or 0,
        food.get("fat_g", 0) or 0,
        food.get("fiber_g", 0) or 0,
        food.get("sugar_g", 0) or 0,
        food.get("sodium_mg", 0) or 0,
        food.get("iron_mg", 0) or 0,
        food.get("potassium_mg", 0) or 0,
        food.get("glycemic_index", 0) or 0,
        food.get("cholesterol_mg", 0) or 0,
        bmi,
        oxygen,
        1 if _truthy(user.get("diabetes")) else 0,
        1 if str(bp).lower().startswith("h") else 0,
        1 if str(chol).lower().startswith("h") else 0,
        1 if _truthy(user.get("heart_disease")) else 0,
        1 if _truthy(user.get("thyroid")) else 0,
        1 if _truthy(user.get("pcos")) else 0,
        _encode_activity(user.get("activity_level")),
        _encode_gender(user.get("gender")),
        user.get("avg_weight", 0) or 0,
        user.get("avg_sugar_level", 0) or 0,
        user.get("avg_cheat_calories", 0) or 0,
    ]


def score_foods(user: Dict[str, Any], foods: list) -> list:
    """Heuristic scorer - positive weights for protein and fiber, negative for sugar and sodium.
    In a production system this calls an ML model that takes the feature vector and returns a score."""
    if not foods:
        return []

    # Attempt to use trained ML model
    model = ml_engine.load_model()
    if model is not None:
        rows = [_make_model_feature_vector(user, f) for f in foods]
        X = np.array(rows, dtype=float)

        # If the model expects a different number of features, pad/truncate safely
        expected = getattr(model, "n_features_in_", None)
        if isinstance(expected, (int, np.integer)) and expected > 0 and X.shape[1] != int(expected):
            exp = int(expected)
            if X.shape[1] < exp:
                pad = np.zeros((X.shape[0], exp - X.shape[1]), dtype=float)
                X = np.concatenate([X, pad], axis=1)
            else:
                X = X[:, :exp]

        try:
            preds = ml_engine.predict_scores(model, X)
            scored = list(zip(preds.tolist(), foods))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s[1] for s in scored]
        except Exception:
            # fall through to heuristic if model fails
            pass

    # Fallback heuristic scorer
    protein = [f.get("protein_g", 0) for f in foods]
    fiber = [f.get("fiber_g", 0) for f in foods]
    sugar = [f.get("sugar_g", 0) for f in foods]
    sodium = [f.get("sodium_mg", 0) for f in foods]
    gly = [f.get("glycemic_index", 0) for f in foods]

    p_n = normalize_series(protein)
    f_n = normalize_series(fiber)
    s_n = normalize_series(sugar)
    so_n = normalize_series(sodium)
    g_n = normalize_series(gly)

    # Base weights - adjust if user has diabetes or high cholesterol
    w_protein = 0.4
    w_fiber = 0.25
    w_sugar = -0.2
    w_sodium = -0.15
    w_gly = -0.1

    if user.get("diabetes"):
        w_sugar += -0.05
        w_gly += -0.1

    if user.get("cholesterol") == "High":
        w_sodium += -0.05

    scores = []
    for i, f in enumerate(foods):
        score = (
            w_protein * p_n[i]
            + w_fiber * f_n[i]
            + w_sugar * s_n[i]
            + w_sodium * so_n[i]
            + w_gly * g_n[i]
        )
        scores.append((score, f))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scores]


def optimize_meals(scored_foods: list, targets: Dict[str, Any]) -> Dict[str, Any]:
    # Simple greedy selection: pick top foods while within calorie budget per meal
    cal = targets.get("calories", 2000)
    breakfast_limit = cal * 0.30
    lunch_limit = cal * 0.40
    dinner_limit = cal * 0.30

    used_ids = set()

    def pick_for_limit(limit):
        picked = []
        total = 0
        for food in scored_foods:
            fid = food.get("food_id")
            if fid and fid in used_ids:
                continue
            c = food.get("calories", 0) or 0
            if total + c <= limit or not picked:
                picked.append({
                    "food_id": fid,
                    "food_name": food.get("food_name"),
                    "calories": c,
                })
                if fid:
                    used_ids.add(fid)
                total += c
            if total >= limit:
                break
        return picked

    breakfast = pick_for_limit(breakfast_limit)
    lunch = pick_for_limit(lunch_limit)
    dinner = pick_for_limit(dinner_limit)

    return {
        "daily_calories": cal,
        "breakfast": breakfast,
        "lunch": lunch,
        "dinner": dinner,
    }


def get_food_by_id(food_id: str):
    df = load_foods_df()
    if df.empty:
        return None
    row = df[df.get("food_id") == food_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def find_substitute(user: Dict[str, Any], disliked_food_id: str, max_calorie_diff_pct: float = 0.2):
    """Find a substitute food for `disliked_food_id` that matches user's diet and
    is nutritionally similar (calories within `max_calorie_diff_pct` and close by
    nutrient vector distance). Returns the substitute food dict or None.
    """
    disliked = get_food_by_id(disliked_food_id)
    if not disliked:
        return None

    # Load candidate foods filtered for user constraints
    candidates = load_foods_df()
    if candidates.empty:
        return None
    # Same diet type
    diet = user.get("diet_type") or disliked.get("diet_type")
    candidates = candidates[candidates["diet_type"].str.lower() == str(diet).lower()]

    # Remove allergies
    allergies = user.get("allergies") or []
    for a in allergies:
        if not a:
            continue
        candidates = candidates[~candidates["food_name"].str.contains(a, case=False, na=False)]

    # Exclude the disliked food itself
    candidates = candidates[candidates["food_id"] != disliked_food_id]

    if candidates.empty:
        return None

    # Calorie window
    cal = disliked.get("calories") or 0
    low = cal * (1 - max_calorie_diff_pct)
    high = cal * (1 + max_calorie_diff_pct)
    cal_candidates = candidates[(candidates["calories"] >= low) & (candidates["calories"] <= high)]
    if cal_candidates.empty:
        cal_candidates = candidates

    # Compute simple distance on a subset of nutrients
    nutrients = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g"]
    def vec(row):
        return np.array([row.get(n, 0) for n in nutrients], dtype=float)

    disliked_vec = vec(disliked)
    best = None
    best_dist = float("inf")
    for _, r in cal_candidates.iterrows():
        v = vec(r)
        # Euclidean distance
        dist = np.linalg.norm(disliked_vec - v)
        # Prioritize lower glycemic index for diabetics
        if user.get("diabetes") and r.get("glycemic_index", 100) > 70:
            dist *= 1.2
        if dist < best_dist:
            best_dist = dist
            best = r.to_dict()

    return best
