import re

with open('logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_old = '''def import_excel(user_id, filepath):
    if not user_id:
        return False, "사용자를 선택해주세요."
    try:
        df = pd.read_excel(filepath)
        
        def hm_to_mins(hm_str):
            if pd.isna(hm_str) or not hm_str: return 0
            try:
                parts = str(hm_str).strip().split(':')
                return int(parts[0])*60 + int(parts[1])
            except:
                return 0
                
        for _, row in df.iterrows():
            date_val = str(row['일자'])[:10]
            if date_val == 'nan': continue
            
            type_str = str(row['근무형태']).strip()
            desc = ""
            base_type = "normal"
            
            # Map type back
            if "반차" in type_str:
                base_type = "morning_half" if "오전" in type_str else "afternoon_half"
            elif "연차" in type_str: base_type = "annual_leave"
            elif "공가" in type_str: base_type = "public_leave"
            elif "병가" in type_str: base_type = "sick_leave"
            elif "공휴일" in type_str or "기념일" in type_str or "휴무" in type_str:
                base_type = "holiday"
            
            # Extract description
            if "(" in type_str and ")" in type_str:
                desc = type_str.split("(")[1].split(")")[0]
            elif " - " in type_str:
                desc = type_str.split(" - ")[1]
            elif base_type == "holiday" and type_str != "공휴일":
                desc = type_str
                
            non_work = hm_to_mins(row.get('비근무시간', ''))
            
            used_hours = row.get('사용연장근로', 0)
            if pd.isna(used_hours): used_hours = 0
            try:
                used_mins = int(float(used_hours) * 60)
            except:
                used_mins = 0
            
            save_work_log(
                user_id,
                date_val,
                base_type,
                str(row['출근']).strip(),
                str(row['퇴근']).strip(),
                non_work,
                used_mins,
                desc
            )
        return True, "성공적으로 불러왔습니다."
    except Exception as e:
        return False, str(e)'''

import_new = '''def import_excel(user_id, filepath):
    if not user_id:
        return False, "사용자를 선택해주세요."
    try:
        wb = load_workbook(filepath, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows: return False, "데이터가 없습니다."
        
        headers = rows[0]
        try:
            date_idx = headers.index('일자')
            type_idx = headers.index('근무형태')
            in_idx = headers.index('출근')
            out_idx = headers.index('퇴근')
            nw_idx = headers.index('비근무시간')
            use_idx = headers.index('사용연장근로')
        except ValueError:
            return False, "양식이 올바르지 않습니다."
            
        def hm_to_mins(hm_str):
            if not hm_str: return 0
            try:
                parts = str(hm_str).strip().split(':')
                return int(parts[0])*60 + int(parts[1])
            except:
                return 0
                
        for row in rows[1:]:
            date_val = str(row[date_idx])[:10]
            if date_val == 'None' or not date_val.strip(): continue
            
            type_str = str(row[type_idx] or '').strip()
            desc = ""
            base_type = "normal"
            
            if "반차" in type_str:
                base_type = "morning_half" if "오전" in type_str else "afternoon_half"
            elif "연차" in type_str: base_type = "annual_leave"
            elif "공가" in type_str: base_type = "public_leave"
            elif "병가" in type_str: base_type = "sick_leave"
            elif "공휴일" in type_str or "기념일" in type_str or "휴무" in type_str:
                base_type = "holiday"
            
            if "(" in type_str and ")" in type_str:
                desc = type_str.split("(")[1].split(")")[0]
            elif " - " in type_str:
                desc = type_str.split(" - ")[1]
            elif base_type == "holiday" and type_str != "공휴일":
                desc = type_str
                
            non_work = hm_to_mins(row[nw_idx])
            
            used_hours = row[use_idx] if row[use_idx] is not None else 0
            try:
                used_mins = int(float(used_hours) * 60)
            except:
                used_mins = 0
            
            cin = str(row[in_idx] or '').strip()
            cout = str(row[out_idx] or '').strip()
            if cin == 'None': cin = ''
            if cout == 'None': cout = ''
            
            save_work_log(
                user_id,
                date_val,
                base_type,
                cin,
                cout,
                non_work,
                used_mins,
                desc
            )
        return True, "성공적으로 불러왔습니다."
    except Exception as e:
        return False, str(e)'''

content = content.replace(import_old, import_new)
with open('logic.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Phase 3 done')
