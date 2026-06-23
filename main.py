import webview
import os
import sys
import io
import ctypes

# Hide console window immediately if running in console mode
if sys.platform == "win32":
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0 is SW_HIDE
    except Exception:
        pass

import traceback

# Safe redirection of standard streams for windowed mode
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import json
from datetime import datetime, timedelta
import logic
from database import init_db

class Api:
    def __init__(self):
        self._window = None

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
                over_used_raw = int(float(data.get('overtime_used', 0) or 0))
                overtime_used = (over_used_raw // 30) * 30
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

    def export_yearly_excel(self, year_str, user_id, user_name):
        try:
            filepath = self.save_file_dialog(f"{year_str}_연간근무표_{user_name}.xlsx")
            if not filepath:
                return {"status": "error", "message": "cancel"}
            success = logic.export_yearly_excel(year_str, user_id, filepath)
            if success:
                return {"status": "success"}
            return {"status": "error", "message": "데이터 내보내기에 실패했습니다."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def auto_fill_missing_days(self, user_id, month_str):
        try:
            count = logic.auto_fill_missing_days(user_id, month_str)
            return {"status": "success", "count": count}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # A helper method to allow file dialog
    def save_file_dialog(self, default_filename):
        if self._window:
            try:
                result = self._window.create_file_dialog(
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
        if self._window:
            try:
                result = self._window.create_file_dialog(
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

    def get_yearly_ledger(self, user_id, year_str):
        if not user_id:
            return []
        return logic.get_yearly_ledger(user_id, year_str)

    def extend_overtime(self, user_id, vault_id, admin_pw, new_expires_at):
        success, msg = logic.extend_overtime(user_id, vault_id, admin_pw, new_expires_at)
        if success:
            return {"status": "success"}
        else:
            return {"status": "error", "message": msg}

    def change_admin_password(self, old_pw, new_pw):
        success, msg = logic.change_admin_password(old_pw, new_pw)
        if success:
            return {"status": "success"}
        else:
            return {"status": "error", "message": msg}

    def get_overtime_usage_history(self, user_id, year_str):
        if not user_id:
            return []
        return logic.get_overtime_usage_history(user_id, year_str)


if __name__ == '__main__':
    try:
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
            height=800
        )
        api._window = window
        webview.start()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        with open('worktime_crash.txt', 'w', encoding='utf-8') as f:
            f.write(err_msg)
