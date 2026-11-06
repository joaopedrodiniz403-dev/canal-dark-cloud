def score(item):
    """Heuristica editorial; nao e previsao de viralizacao."""
    hook = item.get("hook", "").strip()
    scenes = item.get("scenes", [])
    words = len(" ".join(scenes).split())
    hook_points = 25 if 18 <= len(hook) <= 100 else 10
    structure = 25 if len(scenes) >= 3 else 10
    context = 20 if 25 <= words <= 95 else 8
    pace = 20 if all(15 <= len(s) <= 190 for s in scenes) else 8
    technical = 10 if item.get("source") else 0
    return min(100, hook_points + structure + context + pace + technical)
