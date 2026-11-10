"""Arrival window estimation."""

from datetime import datetime, timedelta

WINDOW = timedelta(hours=2)


# bondstone: SBB-eta-service
def arrival_window(last_event_at: datetime, route_p50: timedelta) -> tuple[datetime, datetime]:
    """Two-hour window centred on the median remaining travel time for the route."""
    centre = last_event_at + route_p50
    return centre - WINDOW / 2, centre + WINDOW / 2
