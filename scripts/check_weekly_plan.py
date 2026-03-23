import collections
import json
import urllib.request


def fetch_weekly_plan(days: int = 7) -> dict:
    payload = {
        "user": {
            "user_id": "demo_user",
            "age": 28,
            "gender": "Male",
            "height_cm": 172,
            "weight_kg": 74,
            "diet_type": "Veg",
            "activity_level": "Medium",
            "allergies": [],
            "diabetes": False,
            "blood_pressure": "Normal",
            "cholesterol": "Normal",
            "oxygen_level": 98,
            "hemoglobin": "Normal",
        },
        "days": days,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:5000/weekly-plan",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    resp = fetch_weekly_plan(7)
    week = resp["week"]

    print("days", len(week))
    for d in week:
        counts = {k: len(v) for k, v in d["meals"].items() if isinstance(v, list)}
        print("day", d["day"], counts)

    names = [
        (it.get("food_name") or "").strip().lower()
        for d in week
        for items in d["meals"].values()
        if isinstance(items, list)
        for it in items
        if (it.get("food_name") or "").strip()
    ]

    counter = collections.Counter(names)
    repeat_names = [name for name, count in counter.items() if count > 1]
    repeat_count = sum(count - 1 for count in counter.values() if count > 1)

    print("unique_names_used", len(counter), "total_items", len(names), "repeat_count", repeat_count)
    print("repeat_names", repeat_names[:20])


if __name__ == "__main__":
    main()
