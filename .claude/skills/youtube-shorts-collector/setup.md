# 세팅 가이드 (setup.md)

처음 한 번만 하면 됩니다. 어렵지 않아요.

---

## 1. Claude Code 설치 (이미 있으면 건너뛰기)

Claude Code가 설치돼 있어야 합니다. 없으면 먼저 설치:
- 공식 안내: https://docs.claude.com 에서 "Claude Code" 검색
- 설치 후 터미널에서 이 레포 폴더를 열면 `CLAUDE.md`가 자동 로드됩니다.

## 2. Python 확인

터미널에서:
```bash
python3 --version
```
- `Python 3.8` 이상이면 OK
- 없으면: macOS는 `brew install python3`, Windows는 python.org에서 설치

## 3. yt-dlp 설치 (핵심 도구)

```bash
pip install -U yt-dlp
```
- 권한 오류 나면: `pip install -U yt-dlp --user`
- `pip` 없다고 하면: `python3 -m pip install -U yt-dlp`

설치 확인:
```bash
yt-dlp --version
```
날짜 같은 버전 숫자가 나오면 성공 (예: `2026.07.04`).

## 4. (선택) ffmpeg 설치

영상을 실제로 **다운로드**까지 할 거면 필요. 데이터·댓글 수집만이면 없어도 됩니다.
- macOS: `brew install ffmpeg`
- Windows: `winget install ffmpeg` 또는 ffmpeg.org
- Linux: `sudo apt install ffmpeg`

## 5. 동작 테스트

이 레포 폴더에서:
```bash
python scripts/fetch_meta.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```
제목·조회수·라이선스 등이 뜨면 성공.

---

## 자주 나는 문제

| 증상 | 해결 |
|-----|-----|
| `yt-dlp: command not found` | `pip install -U yt-dlp` 다시. 또는 `python3 -m yt_dlp` |
| `ModuleNotFoundError: yt_dlp` | 같은 Python에 설치됐는지 확인. `python3 -m pip install -U yt-dlp` |
| 수집이 자꾸 실패 | 유튜브가 자주 바뀜. `pip install -U yt-dlp`로 최신화가 1순위 해결책 |
| 느림 | 정상. 댓글까지 긁으면 영상당 수십 초 걸릴 수 있음 |
| 특정 영상만 실패 | 연령제한·비공개·댓글차단 영상. 다른 영상으로 |

## yt-dlp를 최신으로 유지하세요

유튜브는 자주 구조를 바꿔서, 수집이 갑자기 안 되면 **거의 항상** 이걸로 해결됩니다:
```bash
pip install -U yt-dlp
```
