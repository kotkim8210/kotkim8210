"""
captions.py — Whisper(faster-whisper) 기반 동기화 자막.

음성 파일에서 단어 단위 타임스탬프를 뽑아, 화면에 보기 좋은 짧은 청크(구간)로 묶는다.
각 청크 = {start, end, text} (세그먼트 오디오 기준 상대 시간).

config voice.backend 와 무관하게, 최종 음성 파일만 있으면 동작.
captions.mode = "whisper" 일 때 사용. "static"이면 segment.caption 한 장을 통째로 표시.
"""

_MODEL = None


def _get_model(model_size="small", device="cpu", compute_type="int8"):
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel   # pip install faster-whisper
        _MODEL = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _MODEL


def whisper_chunks(audio_path, cfg):
    """음성 → 동기화 자막 청크 리스트 반환.
    cfg(dict): model_size, device, compute_type, language,
               max_chars(청크당 최대 글자), max_gap(초, 이 간격 넘으면 끊기),
               max_dur(청크 최대 길이초)
    """
    model = _get_model(cfg.get("model_size", "small"),
                       cfg.get("device", "cpu"),
                       cfg.get("compute_type", "int8"))
    segments, _ = model.transcribe(
        audio_path, language=cfg.get("language", "ko"),
        word_timestamps=True, vad_filter=cfg.get("vad", True),
    )
    words = []
    for s in segments:
        for w in (s.words or []):
            tok = w.word.strip()
            if tok:
                words.append((tok, w.start, w.end))

    if not words:
        return []

    max_chars = cfg.get("max_chars", 18)   # 한 줄로 읽기 편한 한국어 글자수
    max_gap = cfg.get("max_gap", 0.6)
    max_dur = cfg.get("max_dur", 3.0)

    chunks, cur, c_start, c_end = [], "", None, None
    for tok, ws, we in words:
        if c_start is None:
            cur, c_start, c_end = tok, ws, we
            continue
        gap = ws - c_end
        cand = (cur + " " + tok).strip()
        too_long = len(cand.replace(" ", "")) > max_chars
        too_far = gap > max_gap
        too_dur = (we - c_start) > max_dur
        if too_long or too_far or too_dur:
            chunks.append({"start": c_start, "end": c_end, "text": cur})
            cur, c_start, c_end = tok, ws, we
        else:
            cur, c_end = cand, we
    if cur:
        chunks.append({"start": c_start, "end": c_end, "text": cur})
    return chunks
