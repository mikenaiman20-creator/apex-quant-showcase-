from pathlib import Path

class HoldoutIntegrityError(Exception):
    pass

def load_holdout():
    manifest_path = Path("data/holdout")
    manifest_path.mkdir(parents=True, exist_ok=True)
    return True
