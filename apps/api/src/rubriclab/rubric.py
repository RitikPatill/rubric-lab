"""Rubric YAML loader for RubricLab."""
from __future__ import annotations
from pathlib import Path
import yaml


def load_rubric(path: str | Path) -> dict:
    """Load a rubric YAML file.

    Returns a dict with two keys:
      - "dimensions": list[dict]  — each has id, name, description, weight
      - "pass_threshold": float
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return {
        "dimensions": [
            {
                "id": d["id"],
                "name": d.get("name", d["id"]),
                "description": d.get("description", ""),
                "weight": float(d.get("weight", 1.0)),
            }
            for d in data.get("dimensions", [])
        ],
        "pass_threshold": float(data.get("pass_threshold", 0.5)),
    }
