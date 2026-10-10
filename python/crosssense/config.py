"""Caricamento della configurazione minima del prototipo."""

import json
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path) -> dict:
    """Valida i soli campi consumati dalla diagnostica dello scaffold."""
    with path.open(encoding="utf-8") as source:
        config = json.load(source)
    if not isinstance(config, dict):
        raise ValueError("La configurazione deve essere un oggetto JSON")
    if config.get("schema_version") != 1:
        raise ValueError("schema_version deve essere 1")
    if config.get("mode") != "prototype":
        raise ValueError("Lo scaffold supporta soltanto mode=prototype")
    if config.get("outputs_enabled") is not False:
        raise ValueError("Le uscite devono restare disabilitate nello scaffold")
    interval = config.get("diagnostic_interval_s")
    if isinstance(interval, bool) or not isinstance(interval, (float, int)):
        raise ValueError("diagnostic_interval_s deve essere numerico")
    if not 0.1 <= interval <= 60:
        raise ValueError("diagnostic_interval_s deve essere tra 0.1 e 60")
    return config
