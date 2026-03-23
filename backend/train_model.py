"""Train model from the provided datasets, enriching user features with
health-condition flags, weekly feedback aggregates and cheat logs.
Performs a small randomized hyperparameter search and saves the best model
to `backend/model.pkl`.
"""
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV

BASE = Path(__file__).resolve().parent
FOODS = BASE / "data" / "food_nutrition_master_500.csv"
USERS = BASE / "data" / "user_health_profile_1000.csv"
PLANS = BASE / "data" / "personalized_diet_plan.csv"
WEEKLY = BASE / "data" / "weekly_health_feedback.csv"
CHEAT = BASE / "data" / "cheat_meal_log.csv"


def encode_activity(level):
    mapping = {"Low": 0, "Medium": 1, "High": 2}
    return mapping.get(level, 1)


def encode_gender(g):
    if pd.isna(g):
        return 0
    g = str(g).lower()
    return 1 if g.startswith("f") else 0


def aggregate_weekly():
    if not WEEKLY.exists():
        return pd.DataFrame()
    df = pd.read_csv(WEEKLY)
    # Normalize column names: support alternate names
    col_map = {}
    # blood sugar variants
    for cand in ["avg_sugar_level", "avg_blood_sugar", "sugar_level", "blood_sugar", "avg_glucose"]:
        if cand in df.columns:
            col_map[cand] = "avg_sugar_level"
            break
    # ensure other expected columns exist or use fallbacks
    if "avg_weight" not in df.columns and "weight" in df.columns:
        col_map["weight"] = "avg_weight"
    if "avg_oxygen" not in df.columns and "oxygen" in df.columns:
        col_map["oxygen"] = "avg_oxygen"
    if "cheat_frequency" not in df.columns and "cheats" in df.columns:
        col_map["cheats"] = "cheat_frequency"

    if col_map:
        df = df.rename(columns=col_map)

    # Aggregate available columns, using only those present
    agg_cols = {}
    if "avg_weight" in df.columns:
        agg_cols["avg_weight"] = "mean"
    if "avg_sugar_level" in df.columns:
        agg_cols["avg_sugar_level"] = "mean"
    if "avg_oxygen" in df.columns:
        agg_cols["avg_oxygen"] = "mean"
    if "cheat_frequency" in df.columns:
        agg_cols["cheat_frequency"] = "mean"
    if not agg_cols:
        return pd.DataFrame()

    agg = df.groupby("user_id").agg(agg_cols).reset_index()
    return agg


def aggregate_cheat():
    if not CHEAT.exists():
        return pd.DataFrame()
    df = pd.read_csv(CHEAT)
    # Support columns like `cheat_calories` as well
    col_map = {}
    if "cheat_calories" in df.columns and "calories" not in df.columns:
        col_map["cheat_calories"] = "calories"
    if col_map:
        df = df.rename(columns=col_map)

    agg_cols = {}
    if "calories" in df.columns:
        agg_cols["calories"] = "mean"
    if "sugar_g" in df.columns:
        agg_cols["sugar_g"] = "mean"
    if "fat_g" in df.columns:
        agg_cols["fat_g"] = "mean"
    if not agg_cols:
        return pd.DataFrame()

    agg = df.groupby("user_id").agg(agg_cols).reset_index()
    agg = agg.rename(columns={"calories": "avg_cheat_calories", "sugar_g": "avg_cheat_sugar", "fat_g": "avg_cheat_fat"})
    return agg


def build_training_data():
    # Load datasets if present
    if not FOODS.exists() or not USERS.exists():
        print("Food or user master dataset not found. Cannot train.")
        return None, None

    foods = pd.read_csv(FOODS)
    users = pd.read_csv(USERS)

    weekly = aggregate_weekly()
    cheat = aggregate_cheat()

    # Merge weekly and cheat aggregates into users
    if not weekly.empty:
        users = users.merge(weekly, on="user_id", how="left")
    else:
        users["avg_weight"] = np.nan
        users["avg_sugar_level"] = np.nan
        users["avg_oxygen"] = np.nan
        users["cheat_frequency"] = np.nan

    if not cheat.empty:
        users = users.merge(cheat, on="user_id", how="left")
    else:
        users["avg_cheat_calories"] = np.nan
        users["avg_cheat_sugar"] = np.nan
        users["avg_cheat_fat"] = np.nan

    # Helper to build feature vector for a (user, food) pair
    def make_fv(u, f):
        fv = [
            f.get("calories", 0),
            f.get("protein_g", 0),
            f.get("carbs_g", 0),
            f.get("fat_g", 0),
            f.get("fiber_g", 0),
            f.get("sugar_g", 0),
            f.get("sodium_mg", 0),
            f.get("iron_mg", 0),
            f.get("potassium_mg", 0),
            f.get("glycemic_index", 0),
            f.get("cholesterol_mg", 0),
            u.get("bmi", 0),
            u.get("oxygen_level", 0),
            1 if u.get("diabetes") else 0,
            1 if str(u.get("blood_pressure")).lower().startswith("h") else 0,
            1 if str(u.get("cholesterol")).lower().startswith("h") else 0,
            1 if u.get("heart_disease") else 0,
            1 if u.get("thyroid") else 0,
            1 if u.get("pcos") else 0,
            encode_activity(u.get("activity_level")),
            encode_gender(u.get("gender")),
            u.get("avg_weight", 0) if "avg_weight" in u else 0,
            u.get("avg_sugar_level", 0) if "avg_sugar_level" in u else 0,
            u.get("avg_cheat_calories", 0) if "avg_cheat_calories" in u else 0,
        ]
        return fv

    # If personalized plans exist, use them to create supervised pairs
    if PLANS.exists():
        plans = pd.read_csv(PLANS)
        rows = []
        for _, r in plans.iterrows():
            uid = r.get("user_id")
            fid = r.get("food_id")
            if pd.isna(uid) or pd.isna(fid):
                continue
            u = users[users.get("user_id") == uid]
            f = foods[foods.get("food_id") == fid]
            if u.empty or f.empty:
                continue
            u = u.iloc[0].to_dict()
            f = f.iloc[0].to_dict()
            fv = make_fv(u, f)
            y = r.get("suitability") if "suitability" in r else None
            rows.append((fv, y))

        if rows:
            X = np.array([r[0] for r in rows])
            ys = [r[1] for r in rows]
            if all([v is None for v in ys]):
                y = X[:, 1] * 0.4 + X[:, 4] * 0.2 - X[:, 5] * 0.2
            else:
                y = np.array([float(v) if v is not None else 0.0 for v in ys])
            return X, y
        else:
            print("personalized_diet_plan.csv present but not in (user_id,food_id) format; falling back to synthetic training")

    # Otherwise synthesize training examples by random pairing, enriched with aggregated features
    n = min(5000, len(users) * 5)
    rng = np.random.default_rng(42)
    rows_x = []
    rows_y = []
    for _ in range(n):
        u = users.sample(1).iloc[0].to_dict()
        f = foods.sample(1).iloc[0].to_dict()
        fv = make_fv(u, f)
        y = fv[1] * 0.4 + fv[4] * 0.2 - fv[5] * 0.2 + rng.normal(0, 1)
        rows_x.append(fv)
        rows_y.append(y)

    X = np.array(rows_x)
    y = np.array(rows_y)
    return X, y


def train_and_save():
    X, y = build_training_data()
    if X is None:
        print("No training data available.")
        return

    param_dist = {
        "n_estimators": [50, 100, 200],
        "max_depth": [5, 10, 20, None],
        "min_samples_split": [2, 5, 10],
    }

    base = RandomForestRegressor(random_state=42)
    search = RandomizedSearchCV(base, param_distributions=param_dist, n_iter=8, cv=3, random_state=42, n_jobs=1)
    print("Starting hyperparameter search (this will be brief)...")
    search.fit(X, y)
    best = search.best_estimator_
    joblib.dump(best, BASE / "model.pkl")
    print(f"Saved best model to {BASE / 'model.pkl'} (score={search.best_score_})")


if __name__ == "__main__":
    train_and_save()
