from functools import lru_cache

import torch
from transformers import pipeline


MODEL_NAME = "superb/wav2vec2-base-superb-er"
LABEL_MAP = {
    "hap": "happy",
    "happy": "happy",
    "sad": "sad",
    "ang": "angry",
    "angry": "angry",
    "neu": "neutral",
    "neutral": "neutral",
}


@lru_cache(maxsize=1)
def get_classifier():
    device = 0 if torch.cuda.is_available() else -1
    return pipeline(
        task="audio-classification",
        model=MODEL_NAME,
        device=device,
        top_k=1,
    )


classifier = get_classifier()


def predict_emotion(audio_path: str) -> dict:
    with torch.inference_mode():
        output = classifier(audio_path)

    prediction = output[0][0] if isinstance(output[0], list) else output[0]
    raw_label = prediction["label"].lower()
    emotion = LABEL_MAP.get(raw_label, raw_label)

    return {
        "emotion": emotion,
        "confidence": round(float(prediction["score"]), 4),
    }
