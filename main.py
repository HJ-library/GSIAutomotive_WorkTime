import webview
import os
import sys

class DummyFile:
    def write(self, x): pass
    def flush(self): pass

if sys.stdout is None:
    sys.stdout = DummyFile()
if sys.stderr is None:
    sys.stderr = DummyFile()

import json
from datetime import datetime, timedelta
import logic
from database import init_db

class Api:
    def __init__(self):
        self.window = None

    def get_users(self):
        return logic.get_users()
        
    def add_user(self, name):
        return logic.add_user(name)
        
    def delete_user(self, user_id):
        return logic.delete_user(user_id)

    def get_logs(self, user_id, start_date, end_date):
        return logic.get_work_logs(user_id, start_date, end_date)

    def save_log(self, data):
        try:
            user_id = data.get('user_id')
            date_str = data.get('date')
            log_type = data.get('type')
            clock_in = data.get('clock_in')
            clock_out = data.get('clock_out')
            description = data.get('description', '')
            
            try:
                non_work_time = int(data.get('non_work_time', 0) or 0)
            except ValueError:
                non_work_time = 0
                
            try:
                overtime_used = int(data.get('overtime_used', 0) or 0)
            except ValueError:
                overtime_used = 0
            
            logic.save_work_log(user_id, date_str, log_type, clock_in, clock_out, non_work_time, overtime_used, description)
            return {"status": "success"}
        except Exception as e:
            print(f"Error in save_log: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def get_suggested_filename(self, user_id, month_str):
        from database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT name FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        conn.close()
        user_name = row[0] if row else "Unknown"
        return f"{user_name}_근무기록_{month_str}.xlsx"

    def get_weekly_summary(self, user_id, date_str):
        if not user_id:
            return {"start": "", "end": "", "total_minutes": 0}
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days_to_monday = dt.weekday()
        start_dt = dt - timedelta(days=days_to_monday)
        end_dt = start_dt + timedelta(days=6)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        
        total_minutes = logic.get_weekly_work_time(user_id, start_str, end_str)
        return {
            "start": start_str,
            "end": end_str,
            "total_minutes": total_minutes
        }

    def get_monthly_summary(self, user_id, month_str):
        return logic.get_monthly_summary(user_id, month_str)

    def get_yearly_summary(self, user_id):
        return logic.get_yearly_overtime_summary(user_id)

    def export_excel(self, user_id, month_str, filepath):
        try:
            print(f"Exporting excel for user {user_id}, month {month_str} to {filepath}")
            success = logic.export_monthly_excel(user_id, month_str, filepath)
            if success:
                return {"status": "success"}
            return {"status": "error", "message": "해당 월에 데이터가 없습니다."}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    # A helper method to allow file dialog
    def save_file_dialog(self, default_filename):
        if self.window:
            try:
                result = self.window.create_file_dialog(
                    webview.SAVE_DIALOG, 
                    directory=os.getcwd(), 
                    save_filename=default_filename,
                    file_types=('Excel Files (*.xlsx)', 'All Files (*.*)')
                )
                if result:
                    return result[0]
            except Exception as e:
                print(f"File dialog error: {e}")
        return None

    def generate_template(self, filepath):
        success = logic.generate_import_template(filepath)
        if success:
            return {"status": "success"}
        return {"status": "error"}

    def import_excel(self, user_id):
        if self.window:
            try:
                result = self.window.create_file_dialog(
                    webview.OPEN_DIALOG,
                    allow_multiple=False,
                    directory=os.getcwd(),
                    file_types=('Excel Files (*.xlsx;*.xls)', 'All Files (*.*)')
                )
                if result:
                    filepath = result[0]
                    success, msg = logic.import_excel(user_id, filepath)
                    if success:
                        return {"status": "success"}
                    else:
                        return {"status": "error", "message": msg}
            except Exception as e:
                print(f"Import error: {e}")
        return {"status": "error", "message": "창 초기화 오류 또는 취소됨"}

    def get_vault_details(self, user_id):
        if not user_id:
            return []
        return logic.get_vault_details(user_id)

    def extend_overtime(self, user_id, vault_id, admin_pw):
        success, msg = logic.extend_overtime(user_id, vault_id, admin_pw)
        if success:
            return {"status": "success"}
        else:
            return {"status": "error", "message": msg}

    def auto_fill_missing(self, user_id):
        if user_id:
            logic.auto_fill_missing_days(user_id)
        return {"status": "success"}

if __name__ == '__main__':
    init_db()
    api = Api()
    
    import sys
    # Resolve absolute path for HTML
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(__file__)
        
    html_path = os.path.join(base_dir, 'web', 'index.html')
    
    window = webview.create_window(
        'GSI Automotive 근태 관리 - Made by 주형진', 
        html_path, 
        js_api=api,
        width=1200,
        height=800,
        text_select=False
    )
    api.window = window
    webview.start()
