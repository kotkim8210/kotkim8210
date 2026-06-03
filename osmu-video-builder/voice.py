"""
voice.py — 나레이션(목소리) 백엔드. "한 번 등록 → 이후 대본만 넣으면 내 목소리로 발성".

지원 백엔드 (config의 voice.backend 로 선택):
  - "elevenlabs": 클라우드 보이스 클론 (가장 쉬움, 유료/무료한도)
       준비: 대시보드에서 내 목소리 1회 클론 → voice_id 발급 → config에 입력
       설치: pip install elevenlabs / 환경변수 ELEVENLABS_API_KEY
  - "xtts":      로컬 오픈소스 클론 (무료·무제한, 한국어 지원, 셋업 무거움·GPU 권장)
       준비: 내 목소리 참조 wav(약 6초 이상) 1개 → config의 voice.reference_wav 에 경로
       설치: pip install TTS
  - "files":     TTS 미사용. 세그먼트별로 직접 녹음한 오디오 제공(또는 테스트용).
       config의 각 segment에 "audio": "경로" 를 넣으면 그대로 사용.

공통 인터페이스: synth(text, out_path, voice_cfg) -> out_path 에 오디오 파일 생성
"""
import os
import shutil


def synth(text: str, out_path: str, voice_cfg: dict, segment_audio: str | None = None) -> str:
    backend = voice_cfg.get("backend", "files")
    if backend == "files":
        return _files(segment_audio, out_path)
    if backend == "elevenlabs":
        return _elevenlabs(text, out_path, voice_cfg)
    if backend == "xtts":
        return _xtts(text, out_path, voice_cfg)
    raise ValueError(f"알 수 없는 voice.backend: {backend}")


def _files(segment_audio, out_path):
    if not segment_audio or not os.path.exists(segment_audio):
        raise FileNotFoundError(
            f"backend=files 인데 segment의 'audio' 파일이 없습니다: {segment_audio}"
        )
    shutil.copy(segment_audio, out_path)
    return out_path


def _elevenlabs(text, out_path, voice_cfg):
    """클라우드 보이스 클론. 내 목소리는 대시보드에서 1회 클론 → voice_id 사용."""
    from elevenlabs.client import ElevenLabs  # pip install elevenlabs
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("환경변수 ELEVENLABS_API_KEY 가 필요합니다.")
    client = ElevenLabs(api_key=api_key)
    voice_id = voice_cfg["voice_id"]                 # ← 한 번 클론하고 받은 내 목소리 ID
    model_id = voice_cfg.get("model_id", "eleven_multilingual_v2")
    audio = client.text_to_speech.convert(
        voice_id=voice_id, model_id=model_id, text=text, output_format="mp3_44100_128"
    )
    with open(out_path, "wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)
    return out_path


def _xtts(text, out_path, voice_cfg):
    """로컬 무료 클론(Coqui XTTS v2). 참조 wav 한 개로 내 목소리를 복제."""
    from TTS.api import TTS  # pip install TTS
    ref = voice_cfg["reference_wav"]                 # ← 내 목소리 참조 wav (약 6초+)
    lang = voice_cfg.get("language", "ko")
    model = voice_cfg.get("model", "tts_models/multilingual/multi-dataset/xtts_v2")
    tts = TTS(model).to(voice_cfg.get("device", "cpu"))
    tts.tts_to_file(text=text, speaker_wav=ref, language=lang, file_path=out_path)
    return out_path
