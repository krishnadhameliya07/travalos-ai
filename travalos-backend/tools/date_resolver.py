import re
from datetime import datetime, timedelta
from core.schemas import ResolvedDates

# Anchored strictly to current runtime
RUNTIME_NOW = datetime(2026, 9, 23)

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12
}

def resolve_travel_dates(raw_text: str) -> ResolvedDates:
    low = raw_text.lower()
    
    # 1. Parse Duration
    days = 1
    d_match = re.search(r'(\d+)\s*(?:day|days)', low)
    if d_match:
        days = int(d_match.group(1))
    elif "3-day" in low or "three day" in low:
        days = 3
    elif "4-day" in low or "four day" in low:
        days = 4
    elif "5-day" in low or "five day" in low:
        days = 5
    elif "weekend" in low:
        days = 3

    nights = max(0, days - 1)

    # 2. Check for Named Months (e.g. "in December", "in October", "next month")
    for m_name, m_num in MONTH_MAP.items():
        if re.search(rf'\b(?:in|for|during)?\s*{m_name}\b', low):
            year = 2026 if m_num >= RUNTIME_NOW.month else 2027
            # If specific day is requested in that month
            day_match = re.search(rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of)?\s*{m_name}\b|\b{m_name}\s*(\d{{1,2}})\b', low)
            if day_match:
                start_day = int(day_match.group(1) or day_match.group(2))
                dep = datetime(year, m_num, start_day)
            else:
                # Default start of trip window for named month
                dep = datetime(year, m_num, 10)
            
            ret = dep + timedelta(days=days - 1) if days > 1 else None
            label = f"{dep.strftime('%d')}–{ret.strftime('%d %b %Y')} ({days} Days, {nights} Nights)" if ret else dep.strftime("%d %b %Y")
            return ResolvedDates(
                departure_date=dep.strftime("%Y-%m-%d"),
                return_date=ret.strftime("%Y-%m-%d") if ret else None,
                display_label=label,
                duration_days=days,
                nights_count=nights,
                is_ambiguous=False
            )

    if "next month" in low:
        dep = datetime(2026, 10, 15)
        ret = dep + timedelta(days=days - 1) if days > 1 else None
        label = f"{dep.strftime('%d')}–{ret.strftime('%d %b %Y')} ({days} Days, {nights} Nights)" if ret else dep.strftime("%d %b %Y")
        return ResolvedDates(
            departure_date=dep.strftime("%Y-%m-%d"),
            return_date=ret.strftime("%Y-%m-%d") if ret else None,
            display_label=label,
            duration_days=days,
            nights_count=nights,
            is_ambiguous=False
        )

    # 3. Ambiguous relative keywords check
    if "next week" in low and not any(w in low for w in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        return ResolvedDates(
            departure_date="",
            display_label="Next Week",
            is_ambiguous=True,
            clarification_prompt="Which day next week would you like to depart?"
        )

    # 4. Standard Relatives (anchored to 2026-09-23)
    dep = RUNTIME_NOW
    if "tomorrow" in low:
        dep = RUNTIME_NOW + timedelta(days=1)
    elif "this weekend" in low:
        dep = RUNTIME_NOW + timedelta(days=2) # Friday Sep 25
        days = 3
    elif "next weekend" in low:
        dep = RUNTIME_NOW + timedelta(days=9) # Friday Oct 2
        days = 3
    elif "saturday" in low:
        dep = RUNTIME_NOW + timedelta(days=3)

    nights = max(0, days - 1)
    ret = dep + timedelta(days=days - 1) if days > 1 else None
    label = f"{dep.strftime('%d')}–{ret.strftime('%d %b %Y')} ({days} Days, {nights} Nights)" if ret else dep.strftime("%a, %d %b %Y")

    return ResolvedDates(
        departure_date=dep.strftime("%Y-%m-%d"),
        return_date=ret.strftime("%Y-%m-%d") if ret else None,
        display_label=label,
        duration_days=days,
        nights_count=nights,
        is_ambiguous=False
    )