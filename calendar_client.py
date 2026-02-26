# calendar_client.py — local khal vdir calendar client
#
# Reads and writes events as individual .ics files in a local directory,
# compatible with khal's vdir format (one VCALENDAR/VEVENT per file).
#
# KHAL_CALENDAR_DIR is read from config.py (default: ~/.local/share/khal/calendars/personal).
#
# Public API (same signatures as the former caldav_client.py):
#   connect()                    — checks dir exists, returns (None, dir_path)
#   get_events(start, end)       — scan all .ics files, filter by date range
#   add_event(title, start_dt, end_dt, description, location) — write {uid}.ics, return uid
#   get_upcoming_events(days=7)  — convenience wrapper around get_events

import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

import config


def connect():
    """
    Verify that KHAL_CALENDAR_DIR exists and is a directory.

    Returns (None, dir_path_str) to mirror caldav_client's (client, calendar) tuple.
    Raises FileNotFoundError if the directory is missing.
    """
    cal_dir = Path(config.KHAL_CALENDAR_DIR)
    if not cal_dir.exists():
        raise FileNotFoundError(
            f"khal calendar directory not found: {cal_dir}\n"
            f"Create it with: mkdir -p {cal_dir}"
        )
    if not cal_dir.is_dir():
        raise NotADirectoryError(f"KHAL_CALENDAR_DIR is not a directory: {cal_dir}")
    return None, str(cal_dir)


def get_events(start: datetime, end: datetime) -> list:
    """
    Return events whose DTSTART falls within [start, end].

    Scans all *.ics files in KHAL_CALENDAR_DIR.  Skips files that cannot
    be parsed.  Returns a list of dicts:
        {uid, title, start, end, description, location, attendees}
    """
    from icalendar import Calendar

    connect()  # validate dir
    cal_dir = Path(config.KHAL_CALENDAR_DIR)
    results = []

    for ics_file in cal_dir.glob("*.ics"):
        try:
            cal = Calendar.from_ical(ics_file.read_bytes())
        except Exception as e:
            print(f"[calendar_client] Skipping {ics_file.name}: {e}")
            continue

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            try:
                dtstart_prop = component.get("DTSTART")
                if dtstart_prop is None:
                    continue
                dtstart = dtstart_prop.dt

                # Normalise date → datetime for range comparison
                if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                    dtstart = datetime.combine(dtstart, time.min)

                if not (start <= dtstart <= end):
                    continue

                uid         = str(component.get("UID") or ics_file.stem)
                summary     = component.get("SUMMARY")
                title       = str(summary) if summary else "No title"
                dtend_prop  = component.get("DTEND")
                dtend       = dtend_prop.dt if dtend_prop else None
                desc        = str(component.get("DESCRIPTION") or "")
                loc         = str(component.get("LOCATION") or "")

                # Extract attendee emails from ATTENDEE properties
                attendees = []
                for att in component.get("ATTENDEE", []) if isinstance(
                    component.get("ATTENDEE"), list
                ) else ([component.get("ATTENDEE")] if component.get("ATTENDEE") else []):
                    addr = str(att).replace("mailto:", "").strip()
                    if "@" in addr:
                        attendees.append(addr.lower())

                results.append({
                    "uid":         uid,
                    "title":       title,
                    "start":       dtstart_prop.dt,
                    "end":         dtend,
                    "description": desc,
                    "location":    loc,
                    "attendees":   attendees,
                })
            except Exception as e:
                print(f"[calendar_client] Error parsing event in {ics_file.name}: {e}")

    return results


def add_event(
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    location: str = "",
) -> str:
    """
    Write a new VEVENT to KHAL_CALENDAR_DIR as {uid}.ics.

    Returns the event UID string.
    """
    from icalendar import Calendar, Event

    connect()  # validate dir

    uid = str(uuid.uuid4())

    cal = Calendar()
    cal.add("prodid", "-//MolluskAI//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("uid",     uid)
    event.add("summary", title)
    event.add("dtstart", start_dt)
    event.add("dtend",   end_dt)
    event.add("dtstamp", datetime.utcnow())
    if description:
        event.add("description", description)
    if location:
        event.add("location", location)

    cal.add_component(event)

    ics_path = Path(config.KHAL_CALENDAR_DIR) / f"{uid}.ics"
    ics_path.write_bytes(cal.to_ical())

    return uid


def get_upcoming_events(days: int = 7) -> list:
    """Return events from now through now + days. Convenience wrapper."""
    now = datetime.now()
    return get_events(start=now, end=now + timedelta(days=days))
