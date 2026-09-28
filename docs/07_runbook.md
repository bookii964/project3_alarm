	# 대응 절차

	## 용량 경고 시
- 원인: 순환 재생 2회차 이후 raw 누적
- 조치: python src/run_sql.py main sql/maintenance/90_retention.sql
- 항구 조치: daily.yml 마지막 단계에 위 명령 추가
- 확인: Neon 대시보드 → Monitoring → Database size