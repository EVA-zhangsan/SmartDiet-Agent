import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


def _build_synthetic_dataset(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    ages = rng.integers(18, 61, size=n)
    weights = rng.uniform(45, 120, size=n).round(1)
    heights = rng.uniform(150, 200, size=n).round(1)

    activity_levels = np.array([1.2, 1.375, 1.55, 1.725, 1.9])
    activity = rng.choice(activity_levels, size=n, replace=True)

    # 简化版 BMR（不区分性别；用于演示/模拟训练）
    bmr = 10 * weights + 6.25 * heights - 5 * ages + 5
    tdee = bmr * activity

    # 目标标签生成：tdee 越高越倾向维持/增肌，否则减脂
    target = np.where(tdee > 2800, "gain", np.where(tdee > 2500, "maintain", "lose"))

    df = pd.DataFrame(
        {
            "age": ages.astype(int),
            "weight": weights.astype(float),
            "height": heights.astype(float),
            "activity_level": activity.astype(float),
            "target": target.astype(str),
        }
    )
    return df


def main() -> int:
    df = _build_synthetic_dataset(n=1000, seed=42)

    X = df[["age", "weight", "height", "activity_level"]]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    acc = float(model.score(X_test, y_test))
    print(f"Test accuracy: {acc:.4f}")

    project_root = os.path.dirname(__file__)
    out_dir = os.path.join(project_root, "diet_planner", "ml_models")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "diet_model_v1.pkl")
    joblib.dump(model, out_path)
    print(f"Saved model to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
