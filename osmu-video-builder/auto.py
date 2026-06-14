#!/usr/bin/env python3
"""
auto.py — OSMU 제작 전(全) 과정을 명령 1개로. (run_all.py의 후속/통합)

설계 철학: "자동 실행 + 사람 게이트". 할 수 있는 건 전부 자동, 사람만 할 수 있는
두 가지(이미지/음성 준비, 사실 검증)는 게이트로 남겨 슬롭·정책 리스크를 막는다.

한 번 실행하면:
  [1] factcheck   — 고증 검출 + factcheck_todo.json(Claude 작업목록) 생성
  [2] ttsfix      — config.tts.json(읽기용 tts_text)
  [3] promptgen   — 이미지 프롬프트 16:9 + 9:16 + image_manifest.json
  [4] images      — (선택) images.backend 설정 시 빠진 이미지 자동 생성
  [*] STATUS BOARD— 세그먼트별 이미지/음성 준비 현황 + 남은 할 일 출력
  [5] build       — (--build & 자산 준비 & 고증 통과 시) 본편+클립+자막 조립

idempotent: 산출물이 config보다 최신이면 해당 단계는 건너뜀(--force로 강제).

사용:
  python auto.py config.json --era 17c            # 준비 단계 + 현황판
  python auto.py config.json --era 17c --build     # 자산 준비됐으면 영상까지
  python auto.py config.json --status              # 현황판만
  옵션: --force(전 단계 재실행) --yes(고증 게이트 자동통과) --skip-factcheck --skip-ttsfix
"""
import argparse
import json
import os
import subprocess
import sys

from osmu_common import config_root, load_config, resolve, segment_images

HERE = os.path.dirname(os.path.abspath(__file__))
GREEN, RED, DIM, BOLD, END = "\033[92m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"


def run(mod, args, title):
    print(f"\n{'='*56}\n[{title}]\n{'='*56}")
    r = subprocess.run([sys.executable, os.path.join(HERE, mod)] + args)
    if r.returncode != 0:
        print(f"  ✗ {mod} 실패 (코드 {r.returncode})")
        sys.exit(r.returncode)


def newer(out_path, cfg_path):
    """out_path가 cfg_path보다 최신이면 True(=재실행 불필요)."""
    return os.path.exists(out_path) and os.path.getmtime(out_path) >= os.path.getmtime(cfg_path)


def pending_factcheck(root):
    p = os.path.join(root, "factcheck_todo.json")
    if not os.path.exists(p):
        return None
    data = json.load(open(p, encoding="utf-8"))
    return [t for t in data.get("items", []) if t.get("status") == "pending"]


def asset_status(cfg, root):
    backend = cfg.get("voice", {}).get("backend", "files")
    rows = []
    for s in cfg["segments"]:
        imgs = segment_images(s, cfg)
        have = [p for p in imgs if os.path.exists(resolve(root, p))]
        aud = resolve(root, s["audio"])
        rows.append({
            "id": s["id"],
            "images": imgs, "img_have": len(have), "img_total": len(imgs),
            "miss_img": [p for p in imgs if not os.path.exists(resolve(root, p))],
            "audio": s["audio"],
            "audio_ok": (backend != "files") or os.path.exists(aud),
            "audio_needed": backend == "files",
        })
    return rows


def print_board(cfg, root):
    rows = asset_status(cfg, root)
    pend = pending_factcheck(root)
    print(f"\n{BOLD}{'─'*56}\n 제작 현황판\n{'─'*56}{END}")
    miss_img, miss_aud = [], []
    for r in rows:
        ok = r["img_have"] == r["img_total"]
        ic = f"{GREEN}✅{END}" if ok else f"{RED}❌{END}"
        if r["audio_needed"]:
            ac = f"{GREEN}✅{END}" if r["audio_ok"] else f"{RED}❌{END}"
        else:
            ac = f"{DIM}auto{END}"
        print(f"  {r['id']:<5} 이미지 {ic} {r['img_have']}/{r['img_total']}장   음성 {ac} {r['audio'] if r['audio_needed'] else ''}")
        miss_img += r["miss_img"]
        if r["audio_needed"] and not r["audio_ok"]:
            miss_aud.append(r["audio"])

    print(f"\n{BOLD} 남은 할 일{END}")
    if pend is None:
        print(f"  · 고증: {DIM}factcheck 미실행{END}")
    elif pend:
        print(f"  · {RED}고증 검증 {len(pend)}건 대기{END} → Claude가 web_search로 해결해야 함 (factcheck_todo.json)")
        for t in pend[:8]:
            print(f"      - [{t['type']}] {t['sid']}: {t['detail']}")
    else:
        print(f"  · 고증: {GREEN}전부 검증 완료{END}")
    if miss_img:
        print(f"  · 이미지 {len(miss_img)}개 필요 → {BOLD}image_prompts.16x9.md{END} 프롬프트로 만들어 파일명대로 저장")
    if miss_aud:
        print(f"  · 음성 {len(miss_aud)}개 필요 → {BOLD}voice_script.md{END} 열어서 브루에 복붙(파일명까지 표시됨)")
    if miss_img or miss_aud:
        print(f"  · {BOLD}👉 human_tasks.md{END} 한 장에 할 일·체크박스 전부 정리돼 있음")
    if not miss_img and not miss_aud and (pend == [] or pend is None):
        print(f"  · {GREEN}자산 준비 완료 — python auto.py {os.path.basename(sys.argv[1] if len(sys.argv)>1 else 'config.json')} --build{END}")
    return miss_img, miss_aud, (pend or [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--era", default="17c")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--status", action="store_true", help="현황판만 출력")
    ap.add_argument("--force", action="store_true", help="모든 준비 단계 강제 재실행")
    ap.add_argument("--yes", action="store_true", help="고증 게이트 자동통과")
    ap.add_argument("--skip-factcheck", action="store_true")
    ap.add_argument("--skip-ttsfix", action="store_true")
    a = ap.parse_args()

    cfg_path = os.path.abspath(a.config)
    root = config_root(cfg_path)
    cfg = load_config(cfg_path)
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)

    if a.status:
        print_board(cfg, root)
        return

    # [1] factcheck
    if not a.skip_factcheck:
        run("factcheck.py", [cfg_path, "--era", a.era], "1/5 고증 자가검토 (factcheck)")

    # [2] ttsfix (idempotent)
    if not a.skip_ttsfix:
        if a.force or not newer(os.path.join(root, "config.tts.json"), cfg_path):
            run("ttsfix.py", [cfg_path], "2/5 TTS 친화 대본 (ttsfix)")
        else:
            print("\n[2/5 ttsfix] 최신 → 건너뜀 (--force로 재실행)")

    # [3] promptgen 16:9 + 9:16 (idempotent)
    if a.force or not newer(os.path.join(root, "image_prompts.16x9.md"), cfg_path):
        run("promptgen.py", [cfg_path], "3/5 이미지 프롬프트 16:9")
        run("promptgen.py", [cfg_path, "--ar", "9x16"], "3/5 이미지 프롬프트 9:16")
    else:
        print("\n[3/5 promptgen] 최신 → 건너뜀")

    # [3.5] handoff — 사람용 음성 대본 + 체크리스트
    run("handoff.py", [cfg_path], "3/5 사람용 대본·체크리스트 (handoff)")

    # [4] images (선택적 자동 생성)
    if cfg.get("images", {}).get("backend", "prompts") != "prompts":
        print(f"\n{'='*56}\n[4/5 이미지 자동 생성 (images.backend={cfg['images']['backend']})]\n{'='*56}")
        import images as imgmod
        pj = os.path.join(root, "image_prompts.16x9.json")
        prompts = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {}
        made = imgmod.ensure_images(cfg, root, prompts, force=a.force)
        print(f"  생성: {made or '없음(이미 존재)'}")

    # [*] 현황판
    miss_img, miss_aud, pend = print_board(cfg, root)

    if not a.build:
        return

    # [5] build — 게이트 통과 검사
    blocked = False
    if pend and not a.yes:
        print(f"\n{RED}✗ 조립 중단: 고증 검증 대기 {len(pend)}건. Claude가 먼저 해결하거나 --yes 로 강제.{END}")
        blocked = True
    if miss_img or miss_aud:
        print(f"\n{RED}✗ 조립 중단: 자산 부족(이미지 {len(miss_img)} / 음성 {len(miss_aud)}).{END}")
        blocked = True
    if blocked:
        sys.exit(1)
    run("build.py", [cfg_path], "5/5 영상 조립 (build)")
    print(f"\n{GREEN}✅ 전체 체인 완료 → {os.path.join(root, cfg.get('out_dir','out'))}{END}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python auto.py config.json [--era 17c] [--build] [--status]")
        sys.exit(1)
    main()
