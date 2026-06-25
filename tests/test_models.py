import requests
from unittest.mock import patch

from debate_arena.models import (
    ModelOption,
    fallback_models_from_env,
    fetch_free_text_models,
    resolve_default_index,
)


def test_resolve_default_index_prefers_env_default():
    models = [
        ModelOption(id="alpha:free", name="Alpha"),
        ModelOption(id="beta:free", name="Beta"),
    ]
    assert resolve_default_index(models, "beta:free") == 1


def test_resolve_default_index_falls_back_to_first():
    models = [
        ModelOption(id="alpha:free", name="Alpha"),
        ModelOption(id="beta:free", name="Beta"),
    ]
    assert resolve_default_index(models, "missing:free") == 0


@patch("debate_arena.models.requests.get")
def test_fetch_free_text_models_filters_text_only(mock_get):
    mock_get.return_value.json.return_value = {
        "data": [
            {
                "id": "text-model:free",
                "name": "Text Model (free)",
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
            },
            {
                "id": "vision-model:free",
                "name": "Vision Model (free)",
                "architecture": {
                    "input_modalities": ["text", "image"],
                    "output_modalities": ["text"],
                },
            },
        ]
    }
    mock_get.return_value.raise_for_status.return_value = None

    models, error = fetch_free_text_models()

    assert error is None
    assert [model.id for model in models] == ["text-model:free"]


@patch("debate_arena.models.requests.get")
def test_fetch_free_text_models_falls_back_on_request_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("network down")

    models, error = fetch_free_text_models()

    assert error is not None
    assert models == fallback_models_from_env()
