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

## 작업 저장할 때

```powershell
git add .
git commit -m "무엇을 했는지 한 줄"
git push
```

커밋 메시지 접두어: `feat:` 기능 / `fix:` 수정 / `docs:` 문서 / `chore:` 잡무

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