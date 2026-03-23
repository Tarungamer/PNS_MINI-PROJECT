import joblib
from pathlib import Path
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"


def load_model():
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            return None
    return None


def predict_scores(model, feature_matrix):
    if model is None:
        # fallback
        return feature_matrix.sum(axis=1)
    return model.predict(feature_matrix)
