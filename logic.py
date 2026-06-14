import math
import calendar
import sqlite3
from datetime import datetime, timedelta
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from database import get_connection

def get_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name FROM users ORDER BY name ASC')
    users = c.fetchall()
    conn.close()
    return [{"id": u[0], "name": u[1]} for u in users]

def add_user(name):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (name) VALUES (?)', (name,))
        conn.commit()
        user_id = c.lastrowid
        status = "success"
        msg = "User added"
    except sqlite3.IntegrityError:
        user_id = None
        status = "error"
        msg = "User already exists"
    conn.close()
    return {"status": status, "user_id": user_id, "message": msg}

def delete_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM work_logs WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "User deleted"}

def calculate_work_time(clock_in_str, clock_out_str, non_work_minutes):
    if not clock_in_str or not clock_out_str:
        return 0, 0
        
    fmt = "%H:%M"
    try:
        t_in = datetime.strptime(clock_in_str, fmt)
        t_out = datetime.strptime(clock_out_str, fmt)
    except ValueError:
        return 0, 0
        
    if t_out < t_in:
        t_out += timedelta(days=1)
        
    total_duration_minutes = int((t_out - t_in).total_seconds() / 60)
    target_duration = total_duration_minutes - non_work_minutes
    
    if target_duration > 540:
        base_work = 480
        base_break = 60
        extra_time = target_duration - 540
        extra_break = min(30, extra_time)
        extra_work = extra_time - extra_break
        
        W_extra = extra_work
        breaks_extra = 0
        while W_extra >= 240 * (breaks_extra + 1):
            W_extra -= 30
            breaks_extra += 1
            
        return base_work + W_extra, base_break + extra_break + (breaks_extra * 30)
    else:
        W = target_duration
        breaks = 0
        while W >= 240 * (breaks + 1):
            W -= 30
            breaks += 1
        return W, breaks * 30

def save_work_log(user_id, date_str, log_type, clock_in, clock_out, non_work_time, overtime_used=0, description=""):
    if not user_id:
        return
        
    conn = get_connection()
    c = conn.cursor()
    
    if log_type in ['holiday', 'annual_leave', 'public_leave', 'sick_leave', 'replacement_leave', 'public_leave_half']:
        work_minutes = 8 * 60
        break_minutes = 0
        clock_in = '08:30'
        clock_out = '17:30'
        non_work_time = 0
        if log_type == 'replacement_leave' and overtime_used == 0:
            overtime_used = 480
    elif log_type in ['morning_half', 'afternoon_half']:
        work_minutes = 4 * 60
        break_minutes = 0
        non_work_time = 0
        if log_type == 'morning_half':
            clock_in = '08:30'
            clock_out = '12:30'
        else:
            clock_in = '13:30'
            clock_out = '17:30'
    else:
        work_minutes, break_minutes = calculate_work_time(clock_in, clock_out, non_work_time)
        
    try:
        c.execute('''
            INSERT OR REPLACE INTO work_logs 
            (user_id, date, type, clock_in, clock_out, non_work_time, break_time, work_time, overtime_earned, overtime_used, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        ''', (user_id, date_str, log_type, clock_in, clock_out, non_work_time, break_minutes, work_minutes, overtime_used, description))
        conn.commit()
    except Exception as e:
        print(f"Error saving log: {e}")
        raise e
    finally:
        conn.close()
    
    recalculate_monthly_overtime(user_id, date_str[:7])

def recalculate_monthly_overtime(user_id, month_str):
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute('SELECT date, work_time, type FROM work_logs WHERE user_id = ? AND date LIKE ? ORDER BY date', (user_id, month_str + '%'))
        logs = c.fetchall()
        
        accumulated_raw_overtime = 0
        weekly_overtime = {}
        
        for row in logs:
            date_str = row[0]
            work_time = row[1]
            log_type = row[2]
            
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            is_weekend = dt.weekday() >= 5
            year, week_num, _ = dt.isocalendar()
            week_key = (year, week_num)
            
            if week_key not in weekly_overtime:
                weekly_overtime[week_key] = 0
            
            raw_earned = 0
            if is_weekend:
                raw_earned = work_time
            else:
                if work_time > 480:
                    raw_earned = work_time - 480
                    
            # 10분 단위로 내림(버림) 처리
            raw_earned = (raw_earned // 10) * 10
            
            if weekly_overtime[week_key] + raw_earned > 720:
                raw_earned = max(0, 720 - weekly_overtime[week_key])
                
            weekly_overtime[week_key] += raw_earned
                    
            earned = 0
            if raw_earned > 0:
                available_1x = max(0, 1200 - accumulated_raw_overtime)
                
                if raw_earned <= available_1x:
                    earned = raw_earned
                else:
                    portion_1x = available_1x
                    portion_15x = raw_earned - available_1x
                    earned = portion_1x + int(portion_15x * 1.5)
                    
                accumulated_raw_overtime += raw_earned
                
            c.execute('UPDATE work_logs SET overtime_earned = ? WHERE user_id = ? AND date = ?', (earned, user_id, date_str))
            
        conn.commit()
    except Exception as e:
        print(f"Error recalculating overtime: {e}")
    finally:
        conn.close()

def get_work_logs(user_id, start_date_str, end_date_str):
    if not user_id:
        return []
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM work_logs WHERE user_id = ? AND date >= ? AND date <= ? ORDER BY date', (user_id, start_date_str, end_date_str))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_monthly_summary(user_id, month_str):
    if not user_id:
        return {"carry_over": 0, "curr_earned": 0, "curr_used": 0, "expiring_soon": 0, "total_remaining": 0}
        
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('SELECT SUM(overtime_earned), SUM(overtime_used) FROM work_logs WHERE user_id = ? AND date < ?', (user_id, month_str + '-01'))
    row = c.fetchone()
    prev_earned = row[0] or 0
    prev_used = row[1] or 0
    carry_over = max(0, prev_earned - prev_used)
    
    c.execute('SELECT SUM(overtime_earned), SUM(overtime_used) FROM work_logs WHERE user_id = ? AND date LIKE ?', (user_id, month_str + '%'))
    row2 = c.fetchone()
    curr_earned = row2[0] or 0
    curr_used = row2[1] or 0
    
    total_remaining = carry_over + curr_earned - curr_used
    expiring_soon = carry_over
    
    conn.close()
    
    return {
        "carry_over": carry_over,
        "curr_earned": curr_earned,
        "curr_used": curr_used,
        "expiring_soon": expiring_soon,
        "total_remaining": total_remaining
    }

def get_weekly_work_time(user_id, start_date_str, end_date_str):
    if not user_id:
        return 0
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT SUM(work_time) FROM work_logs WHERE user_id = ? AND date >= ? AND date <= ?', (user_id, start_date_str, end_date_str))
    row = c.fetchone()
    conn.close()
    return row[0] or 0

def export_monthly_excel(user_id, month_str, filepath):
    if not user_id:
        return False
        
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM work_logs WHERE user_id = ? AND date LIKE ? ORDER BY date', (user_id, month_str + '%',))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            print(f"Export failed: No data for {user_id} in {month_str}")
            return False
            
        def mins_to_hm(mins):
            if not mins or mins == 0: return "00:00"
            mins = int(mins)
            return f"{mins//60:02d}:{mins%60:02d}"

        def mins_to_hours(mins):
            if not mins or mins == 0: return None
            return round(int(mins) / 60, 2)

        def format_type(row):
            t_names = {
                "normal": "정상근무", "morning_half": "오전 반차", "afternoon_half": "오후 반차", 
                "holiday": "공휴일 / 특별휴가", "annual_leave": "연차", "public_leave": "공가", "sick_leave": "병가",
                "replacement_leave": "휴무", "public_leave_half": "반공가 + 반차"
            }
            base_name = t_names.get(row['type'], row['type'])
            desc = row['description']
            if row['type'] == 'holiday' and desc:
                return f"{base_name} - {desc}"
            if desc and row['type'] != 'holiday':
                return f"{base_name} ({desc})"
            return base_name

        wb = Workbook()
        ws = wb.active
        
        headers = ['일자', '근무형태', '출근', '퇴근', '비근무시간', '휴게시간', '실근무시간', '발생연장근로', '사용연장근로']
        ws.append(headers)
        
        for r in rows:
            ws.append([
                r['date'],
                format_type(r),
                r['clock_in'],
                r['clock_out'],
                mins_to_hm(r['non_work_time']),
                mins_to_hm(r['break_time']),
                mins_to_hm(r['work_time']),
                mins_to_hours(r['overtime_earned']),
                mins_to_hours(r['overtime_used'])
            ])
            
        # Post-process with openpyxl to add styles and summary block
        try:
            yellow_fill = PatternFill(start_color="FEF08A", end_color="FEF08A", fill_type="solid")
            bold_font = Font(bold=True)
            center_align = Alignment(horizontal="center", vertical="center")
            
            # Format header
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = bold_font
                cell.fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
                cell.alignment = center_align
                
            for r_idx, r in enumerate(rows, start=2):
                if (r['overtime_earned'] or 0) > 0:
                    for c_idx in range(1, len(headers) + 1):
                        ws.cell(row=r_idx, column=c_idx).fill = yellow_fill
                        
            stats = get_monthly_summary(user_id, month_str)
            
            ws.cell(row=2, column=11, value="총 발생 연장근로").font = bold_font
            ws.cell(row=2, column=12, value=round(stats['curr_earned'] / 60, 2))
            
            ws.cell(row=3, column=11, value="총 사용 연장근로").font = bold_font
            ws.cell(row=3, column=12, value=round(stats['curr_used'] / 60, 2))
            
            ws.cell(row=4, column=11, value="이월된 연장근로").font = bold_font
            ws.cell(row=4, column=12, value=round(stats['carry_over'] / 60, 2))
            
            ws.cell(row=5, column=11, value="잔여 연장근로 시간").font = bold_font
            ws.cell(row=5, column=12, value=round(stats['total_remaining'] / 60, 2)).font = bold_font
            
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                    except: pass
                ws.column_dimensions[column].width = max_length + 2
                
            wb.save(filepath)
        except Exception as style_e:
            print(f"Excel styling failed (continuing): {style_e}")
            wb.save(filepath)
            
        return True
    except Exception as e:
        print(f"Logic export error: {e}")
        raise e

def get_yearly_overtime_summary(user_id):
    if not user_id:
        return []
        
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(overtime_earned) as total
        FROM work_logs
        WHERE user_id = ? AND date >= date('now', '-1 year')
        GROUP BY month
        ORDER BY month DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def generate_import_template(filepath):
    wb = Workbook()
    ws = wb.active
    ws.title = "근무기록_양식"
    
    headers = ['일자', '근무형태', '출근', '퇴근', '비근무시간', '휴게시간', '실근무시간', '발생연장근로', '사용연장근로']
    ws.append(headers)
    
    ws.append(['2026-04-01', '정상 근무', '08:30', '17:30', '00:00', '00:00', '08:00', None, None])
    ws.append(['2026-04-02', '공휴일 / 특별휴가 (현충일)', '08:30', '17:30', '00:00', '00:00', '08:00', None, None])
    
    wb.save(filepath)
    return True

def import_excel(user_id, filepath):
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
            
            if "반공가" in type_str: base_type = "public_leave_half"
            elif "반차" in type_str:
                base_type = "morning_half" if "오전" in type_str else "afternoon_half"
            elif "연차" in type_str: base_type = "annual_leave"
            elif "공가" in type_str: base_type = "public_leave"
            elif "병가" in type_str: base_type = "sick_leave"
            elif "휴무" in type_str or "연장" in type_str or "replacement" in type_str: base_type = "replacement_leave"
            elif "공휴일" in type_str or "특별휴가" in type_str or "기념일" in type_str:
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
                used_mins = (used_mins // 30) * 30
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
        return False, str(e)

def get_vault_details(user_id):
    if not user_id:
        return []
        
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT date, overtime_used
        FROM work_logs 
        WHERE user_id = ? AND overtime_used > 0
        ORDER BY date DESC
    ''', (user_id,))
    logs = c.fetchall()
    
    result = []
    for row in logs:
        date_str = row[0]
        used = row[1] or 0
        
        # Calculate running remaining balance up to this date
        c.execute('SELECT SUM(overtime_earned), SUM(overtime_used) FROM work_logs WHERE user_id = ? AND date <= ?', (user_id, date_str))
        run_row = c.fetchone()
        run_earned = run_row[0] or 0
        run_used = run_row[1] or 0
        remain = run_earned - run_used
                
        result.append({
            "id": date_str,
            "date": date_str,
            "earned_minutes": 0,
            "used_minutes": used,
            "remain_minutes": remain,
            "expires_at": "",
            "is_extended": 0
        })
        
    conn.close()
    return result

def extend_overtime(user_id, vault_id, admin_pw):
    return False, "Not implemented yet"

def auto_fill_missing_days(user_id):
    pass

def auto_fill_missing_days(user_id, month_str):
    if not user_id: return 0
    from datetime import datetime, date, timedelta
    import calendar
    import sqlite3
    
    year, month = map(int, month_str.split('-'))
    num_days = calendar.monthrange(year, month)[1]
    
    start_date = date(year, month, 1)
    end_date = min(date(year, month, num_days), date.today() - timedelta(days=1))
    
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT date FROM work_logs WHERE user_id = ? AND date LIKE ?', (user_id, month_str + '%'))
    existing_dates = set([row[0] for row in c.fetchall()])
    conn.close()
    
    curr = start_date
    count = 0
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        if curr.weekday() < 5 and d_str not in existing_dates: # 평일이고 기록이 없으면
            save_work_log(user_id, d_str, 'normal', '08:30', '17:30', 0, 0, '')
            count += 1
        curr += timedelta(days=1)
    return count

def export_yearly_excel(year_str, target_user_id, filepath):
    import sqlite3
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if target_user_id == 'all':
        c.execute('SELECT id, name FROM users ORDER BY name')
        users = c.fetchall()
    else:
        c.execute('SELECT id, name FROM users WHERE id = ?', (target_user_id,))
        users = c.fetchall()
        
    wb = Workbook()
    if not users:
        wb.save(filepath)
        conn.close()
        return True
        
    first_sheet = True
    
    for u in users:
        u_id = u['id']
        u_name = u['name']
        
        c.execute('SELECT * FROM work_logs WHERE user_id = ? AND date LIKE ? ORDER BY date', (u_id, year_str + '%'))
        rows = c.fetchall()
        
        if first_sheet:
            ws = wb.active
            ws.title = u_name
            first_sheet = False
        else:
            ws = wb.create_sheet(title=u_name)
            
        def mins_to_hm(mins):
            if not mins or mins == 0: return "00:00"
            mins = int(mins)
            return f"{mins//60:02d}:{mins%60:02d}"

        def mins_to_hours(mins):
            if not mins or mins == 0: return None
            return round(int(mins) / 60, 2)

        def format_type(row):
            t_names = {
                "normal": "정상근무", "morning_half": "오전 반차", "afternoon_half": "오후 반차", 
                "holiday": "공휴일 / 특별휴가", "annual_leave": "연차", "public_leave": "공가", "sick_leave": "병가",
                "replacement_leave": "휴무", "public_leave_half": "반공가 + 반차"
            }
            base_name = t_names.get(row['type'], row['type'])
            desc = row['description']
            if row['type'] == 'holiday' and desc: return f"{base_name} - {desc}"
            if desc and row['type'] != 'holiday': return f"{base_name} ({desc})"
            return base_name

        headers = ['일자', '근무형태', '출근', '퇴근', '비근무시간', '휴게시간', '실근무시간', '발생연장근로', '사용연장근로']
        ws.append(headers)
        
        for r in rows:
            ws.append([
                r['date'], format_type(r), r['clock_in'], r['clock_out'],
                mins_to_hm(r['non_work_time']), mins_to_hm(r['break_time']), mins_to_hm(r['work_time']),
                mins_to_hours(r['overtime_earned']), mins_to_hours(r['overtime_used'])
            ])
            
        try:
            yellow_fill = PatternFill(start_color="FEF08A", end_color="FEF08A", fill_type="solid")
            bold_font = Font(bold=True)
            center_align = Alignment(horizontal="center", vertical="center")
            
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = bold_font
                cell.fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
                cell.alignment = center_align
                
            for r_idx, r in enumerate(rows, start=2):
                if (r['overtime_earned'] or 0) > 0:
                    for c_idx in range(1, len(headers) + 1):
                        ws.cell(row=r_idx, column=c_idx).fill = yellow_fill
                        
            # Yearly summary
            c.execute("SELECT SUM(overtime_earned) as e, SUM(overtime_used) as u FROM work_logs WHERE user_id = ? AND date LIKE ?", (u_id, year_str + '%'))
            yearly_stats = c.fetchone()
            y_earned = yearly_stats['e'] if yearly_stats['e'] else 0
            y_used = yearly_stats['u'] if yearly_stats['u'] else 0
            
            ws.cell(row=2, column=11, value="년도 총 발생 연장근로").font = bold_font
            ws.cell(row=2, column=12, value=round(y_earned / 60, 2))
            
            ws.cell(row=3, column=11, value="년도 총 사용 연장근로").font = bold_font
            ws.cell(row=3, column=12, value=round(y_used / 60, 2))
            
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                    except: pass
                ws.column_dimensions[column].width = max_length + 2
        except Exception as style_e:
            pass

    wb.save(filepath)
    conn.close()
    return True
