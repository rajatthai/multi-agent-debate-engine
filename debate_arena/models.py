import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


@dataclass(frozen=True)
class ModelOption:
    id: str
    name: str


def default_model_for() -> str:
    return os.getenv("OPENROUTER_MODEL_DEBATER_1", "nvidia/nemotron-3-nano-30b-a3b:free")


def default_model_against() -> str:
    return os.getenv("OPENROUTER_MODEL_DEBATER_2", "nvidia/nemotron-3-super-120b-a12b:free")


def default_model_judge() -> str:
    return os.getenv("OPENROUTER_MODEL_JUDGE", "moonshotai/kimi-k2.6:free")


def default_model_ids() -> Dict[str, str]:
    return {
        "for": default_model_for(),
        "against": default_model_against(),
        "judge": default_model_judge(),
    }


def fallback_models_from_env() -> List[ModelOption]:
    seen = set()
    models: List[ModelOption] = []
    for model_id in default_model_ids().values():
        if model_id not in seen:
            seen.add(model_id)
            models.append(ModelOption(id=model_id, name=model_id))
    return models


def fetch_free_text_models(timeout: int = 30) -> Tuple[List[ModelOption], Optional[str]]:
    try:
        response = requests.get(
            OPENROUTER_MODELS_URL,
            params={
                "min_price": 0,
                "max_price": 0,
                "input_modalities": "text",
                "output_modalities": "text",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return fallback_models_from_env(), f"Could not load OpenRouter models: {exc}"

    models: List[ModelOption] = []
    for item in payload.get("data", []):
        model_id = item.get("id")
        if not model_id:
            continue
        architecture = item.get("architecture") or {}
        input_modalities = architecture.get("input_modalities") or []
        output_modalities = architecture.get("output_modalities") or []
        if input_modalities != ["text"] or output_modalities != ["text"]:
            continue
        models.append(ModelOption(id=model_id, name=item.get("name") or model_id))

    if not models:
        return fallback_models_from_env(), "OpenRouter returned no free text models."

    return models, None


def resolve_default_index(models: List[ModelOption], preferred_id: str) -> int:
    model_ids = [model.id for model in models]
    if preferred_id in model_ids:
        return model_ids.index(preferred_id)
    return 0


def model_name_map(models: List[ModelOption]) -> Dict[str, str]:
    return {model.id: model.name for model in models}
