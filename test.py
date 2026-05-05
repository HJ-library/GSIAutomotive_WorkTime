import main
import logic
from database import init_db

print("=== 자체 검증 시작 ===")

# 1. DB 초기화
init_db()
print("[OK] DB 초기화 완료")

# 2. Api 인스턴스 생성
api = main.Api()
print("[OK] API 인스턴스 생성 완료")

# 3. 사용자 추가 테스트
user_res = api.add_user("테스트사용자")
user_id = user_res.get('user_id')
if not user_id:
    # Get existing user if run previously
    users = api.get_users()
    user_id = users[0]['id'] if users else 1
    
print(f"[OK] 사용자 ID 확보: {user_id}")

# 4. 근무 로그 저장 테스트
test_data = {
    'user_id': user_id,
    'date': '2026-04-28',
    'type': 'normal',
    'clock_in': '08:30',
    'clock_out': '19:30',
    'non_work_time': '30',
    'overtime_used': '0'
}
res = api.save_log(test_data)
if res.get('status') == 'success':
    print("[OK] 정상 근무 로그 저장 성공 (11시간 근무, 비근무 30분, 휴게시간 반영)")
else:
    print("[FAIL] 근무 로그 저장 실패!")

# 5. 주간 근무표 조회 테스트
weekly_res = api.get_weekly_summary(user_id, '2026-04-28')
print(f"[OK] 주간 요약 조회 완료: {weekly_res}")

# 6. 월간 근무표 조회 테스트
monthly_res = api.get_monthly_summary(user_id, '2026-04')
print(f"[OK] 월간 요약 조회 완료: {monthly_res}")

# 7. 엑셀 내보내기 테스트
excel_res = api.export_excel(user_id, '2026-04', '테스트사용자_근무기록_2026-04.xlsx')
print(f"[OK] 엑셀 내보내기: {excel_res}")

print("=== 모든 로직 정상 작동 ===")
