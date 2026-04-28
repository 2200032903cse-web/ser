import gc
from threading import Lock


MODEL_NAME = "superb/wav2vec2-base-superb-er"
MAX_AUDIO_SECONDS = 5
LABEL_MAP = {
    "hap": "happy",
    "happy": "happy",
    "sad": "sad",
    "ang": "angry",
    "angry": "angry",
    "neu": "neutral",
    "neutral": "neutral",
}

_classifier = None
_classifier_lock = Lock()


def get_classifier():
    global _classifier

    if _classifier is None:
        with _classifier_lock:
            if _classifier is None:
                import torch
                from transformers import pipeline

                torch.set_num_threads(1)
                _classifier = pipeline(
                    "audio-classification",
                    model=MODEL_NAME,
                    device=-1,
                    top_k=1,
                )

    return _classifier


def _load_first_seconds(audio_path: str) -> dict:
    try:
        import torchaudio

        info = torchaudio.info(audio_path)
        max_frames = int(info.sample_rate * MAX_AUDIO_SECONDS)
        waveform, sample_rate = torchaudio.load(audio_path, num_frames=max_frames)

        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0)
        else:
            waveform = waveform.squeeze(0)

        audio_array = waveform.cpu().numpy()
    except ImportError:
        import soundfile as sf

        with sf.SoundFile(audio_path) as audio_file:
            sample_rate = audio_file.samplerate
            max_frames = int(sample_rate * MAX_AUDIO_SECONDS)
            audio_array = audio_file.read(frames=max_frames, dtype="float32", always_2d=False)

        if len(audio_array.shape) > 1:
            audio_array = audio_array.mean(axis=1)

    return {
        "array": audio_array,
        "sampling_rate": sample_rate,
    }


def predict_emotion(audio_path: str) -> dict:
    import torch

    classifier = get_classifier()
    audio_input = _load_first_seconds(audio_path)

    with torch.inference_mode():
        output = classifier(audio_input)

    prediction = output[0][0] if isinstance(output[0], list) else output[0]
    raw_label = prediction["label"].lower()
    emotion = LABEL_MAP.get(raw_label, raw_label)
    confidence = round(float(prediction["score"]), 4)

    del audio_input, output
    gc.collect()

    return {
        "emotion": emotion,
        "confidence": confidence,
    }
