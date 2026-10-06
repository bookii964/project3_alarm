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

## PowerShell 주의
`python -c "..."` 에 SQL이나 따옴표가 들어가면 PowerShell이 먼저 해석해
깨진다 (`*`, `'`, `$` 등). 확인용 쿼리도 src/ 에 파일로 만들어 실행할 것.

## Day 3 | 날짜 체계 정리
- 세 종류의 날짜가 공존한다:
  - 작업일: 실제 개발한 날 (worklog 기준)
  - batch_date: 배치 실행일. 작업일과 동일하며 raw/mart의 파티션 키
  - 논리 날짜: 원본 이벤트 날짜(2025-09-02~12-02). 재생기가 자동 계산
- CLI 인자 `--date` 는 batch_date 를 받는다 (논리 날짜 아님)
- 대시보드 축: 품질 지표는 batch_date, 매출 추이는 order_date 기준

## Neon 브랜치

| 브랜치 | 용도 | 엔드포인트 |
|---|---|---|
| main (default) | 운영 | ep-____ |
| dev | 실험 | ep-____ |

- 브랜치를 새로 만들면 **엔드포인트와 비밀번호가 새로 생긴다.**
  만든 즉시 `.env` 를 갱신할 것
- Connect 창에서 **브랜치 드롭다운을 확인**할 것.
  대시보드 첫 화면은 기본 브랜치 주소만 보여준다
- 주소 형식: `postgresql+psycopg://...?sslmode=require`
  (`&channel_binding=require` 는 제거)
- 무료 플랜: 브랜치 10개까지. 브랜치는 데이터를 복사하지 않고
  변경분만 저장하므로 추가 용량 부담이 거의 없다
- 접속 확인: `python src/test_conn.py`

## 개발 중 초기화
```powershell
python src/run_sql.py dev sql/maintenance/99_truncate_all.sql
```
되돌릴 수 없으니 대상이 dev 인지 반드시 확인할 것.

## 코드 붙여넣은 뒤 확인
```powershell
python -c "import ast,pathlib; ast.parse(pathlib.Path('src/파일명.py').read_text(encoding='utf-8')); print('문법 OK')"
```

IndentationError 가 나는데 눈으로는 맞아 보이면 탭/공백 혼용이다.
VS Code: Ctrl+Shift+P → Convert Indentation to Spaces

## 파이썬 실행 시 -B 옵션

```powershell
python -B src/load.py dev
```

`-B` 는 컴파일 캐시(__pycache__)를 만들지도 읽지도 않는다.
파일을 통째로 덮어썼는데 수정 내용이 반영되지 않고 예전 오류가
그대로 나오면 캐시 문제이므로, 이 프로젝트에서는 항상 -B 를 붙인다.

캐시 수동 삭제:
```powershell
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force -Directory | Remove-Item -Recurse -Force

## 작업 시작할 때

```powershell
cd C:\Users\SAMSUNG\Desktop\project\project_3
.\.venv\Scripts\Activate.ps1
```

VS Code 내장 터미널을 쓰면 cd 가 불필요하다.
명령 실행 전 프롬프트 경로를 한 번 확인할 것.
```

## PowerShell 인코딩 UTF-8로 설정
```powershell
chcp 65001
```

VS Code 내장 터미널을 쓰면 cd 가 불필요하다.
명령 실행 전 프롬프트 경로를 한 번 확인할 것.
```