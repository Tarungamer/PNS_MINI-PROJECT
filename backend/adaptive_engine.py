from typing import Dict, Any


class WeeklyAdaptationEngine:
    def __init__(self):
        pass

    def adapt(self, user: Dict[str, Any], weekly_feedback: Dict[str, Any]):
        # Simple rules-based adaptations per spec
        avg_weight = weekly_feedback.get("avg_weight")
        if avg_weight is not None:
            try:
                if avg_weight > user.get("weight_kg", avg_weight):
                    # reduce calorie target by 5%
                    user.setdefault("adaptations", {})
                    user["adaptations"]["calorie_adj_pct"] = user["adaptations"].get("calorie_adj_pct", 0) - 5
                elif avg_weight < user.get("weight_kg", avg_weight):
                    user.setdefault("adaptations", {})
                    user["adaptations"]["calorie_adj_pct"] = user["adaptations"].get("calorie_adj_pct", 0) + 2
            except Exception:
                pass

        sugar = weekly_feedback.get("avg_sugar_level")
        if sugar is None:
            sugar = weekly_feedback.get("avg_blood_sugar")
        if sugar is not None:
            try:
                sugar_val = float(sugar)
            except Exception:
                sugar_val = None

            if sugar_val is not None and sugar_val > 140:
                user.setdefault("adaptations", {})
                user["adaptations"]["carb_strictness"] = user["adaptations"].get("carb_strictness", 0) + 1

        if weekly_feedback.get("cheat_frequency") and weekly_feedback.get("cheat_frequency") > 2:
            user.setdefault("adaptations", {})
            user["adaptations"]["strictness"] = user["adaptations"].get("strictness", 0) + 1

        # In a real system, we'd feed feedback into ML model training here.
