import sqlite3

with open('logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. save_work_log
old_save = "if log_type in ['holiday', 'annual_leave', 'public_leave', 'sick_leave', 'replacement_leave']:"
new_save = "if log_type in ['holiday', 'annual_leave', 'public_leave', 'sick_leave', 'replacement_leave', 'public_leave_half']:"
content = content.replace(old_save, new_save)

# 2. t_names in export_monthly_excel
old_tnames = '''            t_names = {
                "normal": "정상근무", "morning_half": "오전 반차", "afternoon_half": "오후 반차", 
                "holiday": "공휴일", "annual_leave": "연차", "public_leave": "공가", "sick_leave": "병가",
                "replacement_leave": "연장근로 시간 사용"
            }'''
new_tnames = '''            t_names = {
                "normal": "정상근무", "morning_half": "오전 반차", "afternoon_half": "오후 반차", 
                "holiday": "공휴일 / 특별휴가", "annual_leave": "연차", "public_leave": "공가", "sick_leave": "병가",
                "replacement_leave": "휴무", "public_leave_half": "반공가 + 반차"
            }'''
content = content.replace(old_tnames, new_tnames)

# 3. generate_import_template
old_gen = "ws.append(['2026-04-02', '공휴일 (현충일)', '08:30', '17:30', '00:00', '00:00', '08:00', None, None])"
new_gen = "ws.append(['2026-04-02', '공휴일 / 특별휴가 (현충일)', '08:30', '17:30', '00:00', '00:00', '08:00', None, None])"
content = content.replace(old_gen, new_gen)

# 4. import_excel mapping
old_import = '''            if "반차" in type_str:
                base_type = "morning_half" if "오전" in type_str else "afternoon_half"
            elif "연차" in type_str: base_type = "annual_leave"
            elif "공가" in type_str: base_type = "public_leave"
            elif "병가" in type_str: base_type = "sick_leave"
            elif "연장" in type_str or "replacement" in type_str: base_type = "replacement_leave"
            elif "공휴일" in type_str or "기념일" in type_str or "휴무" in type_str:
                base_type = "holiday"'''

new_import = '''            if "반공가" in type_str: base_type = "public_leave_half"
            elif "반차" in type_str:
                base_type = "morning_half" if "오전" in type_str else "afternoon_half"
            elif "연차" in type_str: base_type = "annual_leave"
            elif "공가" in type_str: base_type = "public_leave"
            elif "병가" in type_str: base_type = "sick_leave"
            elif "휴무" in type_str or "연장" in type_str or "replacement" in type_str: base_type = "replacement_leave"
            elif "공휴일" in type_str or "특별휴가" in type_str or "기념일" in type_str:
                base_type = "holiday"'''

content = content.replace(old_import, new_import)

with open('logic.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Logic replacements done.")
