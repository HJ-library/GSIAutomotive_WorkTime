from datetime import datetime, date, timedelta
import calendar

def get_missing_days(month_str):
    year, month = map(int, month_str.split('-'))
    num_days = calendar.monthrange(year, month)[1]
    
    start_date = date(year, month, 1)
    end_date = min(date(year, month, num_days), date.today() - timedelta(days=1))
    
    days_to_fill = []
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5: # Monday = 0, Friday = 4
            days_to_fill.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return days_to_fill

print(get_missing_days('2026-05'))
