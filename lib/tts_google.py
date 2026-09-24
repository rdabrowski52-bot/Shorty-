"""
Google Cloud TTS - generowanie voiceover.
Setup: pip install google-cloud-texttospeech
export GOOGLE_APPLICATION_CREDENTIALS=/sciezka/do/klucza.json
"""
from google.cloud import texttospeech

VOICE_NAME = "en-US-Neural2-D"
LANGUAGE_CODE = "en-US"


def synthesize(text: str, out_path: str, speaking_rate: float = 1.0) -> str:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=LANGUAGE_CODE,
        name=VOICE_NAME,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(out_path, "wb") as f:
        f.write(response.audio_content)
    return out_path
