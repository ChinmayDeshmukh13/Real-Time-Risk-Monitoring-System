# engine/nse_calendar.py
# Calculates real NSE option expiry dates
# NSE monthly expiry = last Thursday of each month

from datetime import date, timedelta


def last_thursday(year: int, month: int) -> date:
    """Returns the last Thursday of a given month."""
    # Start from last day of month and go backwards
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # Thursday = weekday 3
    days_back = (last_day.weekday() - 3) % 7
    return last_day - timedelta(days=days_back)


def get_expiry_days(months_ahead: int = 0) -> int:
    """
    Returns calendar days until NSE expiry.

    months_ahead=0 → current month expiry
    months_ahead=1 → next month expiry
    months_ahead=2 → month after next
    """
    today = date.today()
    year  = today.year
    month = today.month + months_ahead

    # Handle year rollover
    while month > 12:
        month -= 12
        year  += 1

    expiry = last_thursday(year, month)

    # If current month expiry already passed, use next month
    if months_ahead == 0 and expiry <= today:
        return get_expiry_days(months_ahead=1)

    days = (expiry - today).days
    return max(days, 1)  # minimum 1 day


def get_all_expiries() -> dict:
    """Returns days to next 3 NSE expiries."""
    return {
        'near':   get_expiry_days(0),   # current month
        'mid':    get_expiry_days(1),   # next month
        'far':    get_expiry_days(2),   # month after
    }


if __name__ == "__main__":
    expiries = get_all_expiries()
    today = date.today()
    print(f"Today: {today}")
    print(f"Near expiry  : {expiries['near']} days")
    print(f"Mid expiry   : {expiries['mid']} days")
    print(f"Far expiry   : {expiries['far']} days")