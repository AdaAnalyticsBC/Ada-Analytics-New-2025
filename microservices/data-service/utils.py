from enum import Enum
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# ----- D A T A   T Y P E S ----- #
class Timespan(str, Enum):
    minute = "minute"
    hour = "hour"
    day = "day"
    week = "week"
    month = "month"
    quarter = "quarter"
    year = "year"

# ----- H E L P E R S ----- #
def calculate_dates(multiplier: int, timespan: str):
    end = date.today()

    delta_map = {
        "minute": timedelta(minutes=multiplier),
        "hour": timedelta(hours=multiplier),
        "day": timedelta(days=multiplier),
        "week": timedelta(weeks=multiplier),
        "month": relativedelta(months=multiplier),
        "quarter": relativedelta(months=multiplier * 3),
        "year": relativedelta(years=multiplier),
    }

    if timespan not in delta_map:
        raise ValueError(f"Unsupported timespan: {timespan}")
    
    delta = delta_map[timespan]
    start = end - delta

    return start.isoformat(), end.isoformat()