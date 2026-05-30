# YouTube Shorts Creator Ultimate

해외 Creative Commons 쇼츠/짧은 영상을 한국·일본용으로 현지화·재유통하기 위한 최종 운영 스킬 패키지입니다.

이 버전은 최신 첨부본의 **경량 SKILL.md + workflow.md 분리 구조**를 메인으로 채택하고, 이전 최종판의 **템플릿·스크립트·품질 게이트·정책 노트·직장인 운영 루틴**을 병합했습니다.

## 핵심 구조

```text
youtube-shorts-creator-ultimate/
├─ SKILL.md
├─ README.md
├─ CHANGELOG.md
├─ references/
│  ├─ workflow.md
│  ├─ transformative-editing-guide.md
│  ├─ rights-safety-checklist.md
│  ├─ source-selection-scorecard.md
│  ├─ first-2-seconds-hook-playbook.md
│  ├─ korean-script-tone-guide.md
│  ├─ localization-jp.md
│  ├─ capcut-editing-guide.md
│  ├─ growth-ops-playbook.md
│  ├─ comment-mining-guide.md
│  ├─ quality-gates.md
│  ├─ policy-source-notes.md
│  ├─ part-time-operator-routine.md
│  └─ final-merge-audit.md
├─ assets/
│  ├─ templates/
│  └─ examples/
└─ scripts/
   ├─ new-project.ps1
   └─ new-project.sh
```

## 최종 운영 원칙

1. CC 확인 없으면 제작하지 않습니다.
2. CC여도 음원·초상권·제3자 저작물·로고·뉴스/사건성 리스크를 별도 점검합니다.
3. 원본 후보는 조회수만 보지 않고 100점 점수표로 평가합니다.
4. 댓글 클러스터를 통해 주제와 감정선을 결정합니다.
5. 한국어와 일본어 첫 2초 후킹을 따로 설계합니다.
6. 일본어판은 직역하지 않고 9항목 자가 리뷰 후 v2를 만듭니다.
7. CapCut 편집은 줌·크롭·반전의 목적을 타임코드로 명시합니다.
8. 실질 변형은 **필수군 C1~C3 중 2개 이상 + 전체 4개 이상**을 통과해야 합니다.
9. 같은 원본/같은 구조 반복은 채널 단위 리스크로 관리합니다.
10. 업로드 후 24h/72h/7d 지표로 Repeat / Modify / Kill 결정을 내립니다.

## 새 프로젝트 만들기

Windows PowerShell:

```powershell
.\scripts
ew-project.ps1 -Name "morning-routine-001"
```

macOS/Linux:

```bash
bash scripts/new-project.sh morning-routine-001
```

생성된 프로젝트에는 `assets/templates/`의 00~11 템플릿이 복사됩니다.

## 이번 최종 병합에서 보강한 점

- 최신 첨부본의 경량 SKILL.md 구조를 유지했습니다.
- 상세 Stage 절차는 `references/workflow.md`로 분리했습니다.
- 기존 최종판에 있던 템플릿 00~11과 자동 프로젝트 생성 스크립트를 복구했습니다.
- `quality-gates.md`와 `07-transformative-gate.md`를 새 C/S 가중치 구조로 업데이트했습니다.
- 공식 정책 확인 문서는 `policy-source-notes.md`로 분리했습니다.
- 반복 콘텐츠·D등급 소재·수익화 거절 복구·채널 단위 리스크를 최종 기준에 반영했습니다.
