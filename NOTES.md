# 작업 메모

## 작업 시작할 때

VS Code 내장 터미널(`Ctrl + ~`)을 열면 프로젝트 폴더에서 시작하므로 아래 한 줄만 실행:

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShell을 별도로 열었다면 이동부터:

```powershell
cd C:\Users\SAMSUNG\Desktop\project_3
.\.venv\Scripts\Activate.ps1
```

프롬프트에 `(.venv)`가 붙으면 준비 완료.

## 작업 중단할 때 (저장 절차)

```powershell
git status              # 1. 무엇이 변했는지 확인
git add .               # 2. 커밋 대상에 올리기
git status              # 3. .env 등이 섞이지 않았는지 재확인 ★
git commit -m "메시지"  # 4. 로컬에 기록
git push                # 5. GitHub에 업로드
```

★ 3번을 생략하지 말 것. `.env`, `.venv/`, `data/source/` 가 목록에 보이면 멈추고 원인 확인.

### 커밋 메시지 접두어
`feat:` 기능 추가 / `fix:` 오류 수정 / `docs:` 문서 / `chore:` 설정·잡무

### 중단 시 함께 할 것
- `docs/06_worklog.md` 에 한 일 / 막힌 것 / 다음 할 것 3줄 기록
- 선택이 있었다면 `docs/02_decision_log.md` 에 추가

## 자주 쓰는 확인

```powershell
git status          # 변경된 파일 확인
git log --oneline   # 커밋 이력
git remote -v       # GitHub 연결 주소
dir                 # 현재 폴더 내용
Get-Location        # 현재 위치
```

## 주의

- 명령 치기 전에 프롬프트 경로 확인 (홈 폴더에서 실행하면 엉킴)
- 여러 줄을 한꺼번에 붙여넣으면 출력 순서가 섞이므로 확인 명령은 한 줄씩
- `>>`가 나오면 입력 대기 상태 → `Ctrl + C`

## .gitignore 함정

`data/` 처럼 **폴더 자체**를 제외하면 안쪽 파일은 `!` 로 되살릴 수 없다.
Git이 제외된 폴더는 아예 들여다보지 않기 때문.

예외를 두려면 `data/*` 처럼 **내용물**을 제외해야 한다.

확인: `git check-ignore -v <파일>` → 출력이 없으면 포함되는 상태
진단: `git status --ignored <폴더>` → 무시된 대상이 폴더인지 파일인지 보임

`.gitignore` 를 고쳐도 반영이 안 되면 캐시를 비운다: