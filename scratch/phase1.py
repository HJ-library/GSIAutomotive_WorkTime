import re

with open('logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove pandas import and add openpyxl
content = content.replace('import pandas as pd', 'from openpyxl import Workbook, load_workbook\nfrom openpyxl.styles import PatternFill, Font, Alignment')

# 2. Rewrite get_yearly_overtime_summary
yearly_old = '''def get_yearly_overtime_summary(user_id):
    if not user_id:
        return []
        
    conn = get_connection()
    query = """
        SELECT strftime('%Y-%m', date) as month, SUM(overtime_earned) as total
        FROM work_logs
        WHERE user_id = ? AND date >= date('now', '-1 year')
        GROUP BY month
        ORDER BY month DESC
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df.to_dict('records')'''

yearly_new = '''def get_yearly_overtime_summary(user_id):
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
    return [dict(row) for row in rows]'''

content = content.replace(yearly_old, yearly_new)

# 3. Rewrite generate_import_template
gen_old = '''def generate_import_template(filepath):
    data = {
        '일자': ['2026-04-01', '2026-04-02'],
        '근무형태': ['정상 근무', '공휴일 (현충일)'],
        '출근': ['08:30', '08:30'],
        '퇴근': ['17:30', '17:30'],
        '비근무시간': ['00:00', '00:00'],
        '휴게시간': ['00:00', '00:00'],
        '실근무시간': ['08:00', '08:00'],
        '발생연장근로': [None, None],
        '사용연장근로': [None, None]
    }
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    return True'''

gen_new = '''def generate_import_template(filepath):
    wb = Workbook()
    ws = wb.active
    ws.title = "근무기록_양식"
    
    headers = ['일자', '근무형태', '출근', '퇴근', '비근무시간', '휴게시간', '실근무시간', '발생연장근로', '사용연장근로']
    ws.append(headers)
    
    ws.append(['2026-04-01', '정상 근무', '08:30', '17:30', '00:00', '00:00', '08:00', None, None])
    ws.append(['2026-04-02', '공휴일 (현충일)', '08:30', '17:30', '00:00', '00:00', '08:00', None, None])
    
    wb.save(filepath)
    return True'''

content = content.replace(gen_old, gen_new)

with open('logic.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Phase 1 done')
