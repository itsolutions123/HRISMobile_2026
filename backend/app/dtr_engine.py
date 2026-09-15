from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional

def compute_daily_dtr(
    date_str: str,
    punches: List[Dict[str, Any]],
    shift_start_str: str = "08:00",
    shift_end_str: str = "17:00",
    break_duration_mins: int = 60,
    grace_period_mins: int = 15,
    overtime_approved: bool = False
) -> Dict[str, Any]:
    """
    Computes daily regular hours, late minutes, undertime minutes, and overtime hours.
    Expects punches as a list of dicts with 'punch_type' and 'timestamp' (datetime or ISO string).
    """
    parsed_punches = []
    for p in punches:
        ts = p["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        parsed_punches.append({
            "type": p["punch_type"].strip().upper(),
            "timestamp": ts
        })

    parsed_punches.sort(key=lambda x: x["timestamp"])

    clock_in = next((p["timestamp"] for p in parsed_punches if p["type"] == "CLOCK_IN"), None)
    clock_out = next((p["timestamp"] for p in reversed(parsed_punches) if p["type"] == "CLOCK_OUT"), None)

    if not clock_in or not clock_out:
        return {
            "date": date_str,
            "clock_in": clock_in.isoformat() if clock_in else None,
            "clock_out": clock_out.isoformat() if clock_out else None,
            "regular_hours": 0.0,
            "late_minutes": 0,
            "undertime_minutes": 0,
            "overtime_hours": 0.0,
            "status": "INCOMPLETE" if (clock_in or clock_out) else "ABSENT"
        }

    # Evaluate exact break duration if explicit break punches exist
    break_starts = [p["timestamp"] for p in parsed_punches if p["type"] == "BREAK_OUT"]
    break_ends = [p["timestamp"] for p in parsed_punches if p["type"] == "BREAK_IN"]
    
    break_seconds = 0.0
    if break_starts and break_ends:
        for b_start, b_end in zip(break_starts, break_ends):
            if b_end > b_start:
                break_seconds += (b_end - b_start).total_seconds()
    else:
        # Fallback to schedule's auto-deduct if no break punches are found
        break_seconds = break_duration_mins * 60.0

    target_date = clock_in.date()
    start_h, start_m = map(int, shift_start_str.split(":"))
    end_h, end_m = map(int, shift_end_str.split(":"))

    sched_start = datetime.combine(target_date, time(start_h, start_m))
    sched_end = datetime.combine(target_date, time(end_h, end_m))

    # Handle night shifts crossing midnight
    if sched_end <= sched_start:
        sched_end += timedelta(days=1)

    grace_deadline = sched_start + timedelta(minutes=grace_period_mins)
    late_minutes = 0
    if clock_in > grace_deadline:
        late_minutes = int((clock_in - sched_start).total_seconds() // 60)

    undertime_minutes = 0
    if clock_out < sched_end:
        undertime_minutes = int((sched_end - clock_out).total_seconds() // 60)

    total_worked_seconds = (clock_out - clock_in).total_seconds()
    net_worked_seconds = max(0.0, total_worked_seconds - break_seconds)
    net_worked_hours = round(net_worked_seconds / 3600.0, 2)

    sched_total_seconds = (sched_end - sched_start).total_seconds() - break_seconds
    standard_sched_hours = round(max(0.0, sched_total_seconds) / 3600.0, 2)

    regular_hours = min(net_worked_hours, standard_sched_hours)

    overtime_hours = 0.0
    if overtime_approved and clock_out > sched_end:
        ot_seconds = (clock_out - sched_end).total_seconds()
        overtime_hours = round(ot_seconds / 3600.0, 2)

    return {
        "date": date_str,
        "clock_in": clock_in.isoformat(),
        "clock_out": clock_out.isoformat(),
        "regular_hours": regular_hours,
        "late_minutes": late_minutes,
        "undertime_minutes": undertime_minutes,
        "overtime_hours": overtime_hours,
        "status": "PRESENT"
    }
