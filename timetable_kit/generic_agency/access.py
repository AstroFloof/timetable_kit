from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from timetable_kit.generic_agency import Agency


class AgencyAccessibilityInfo:
    def __init__(self, parent: Agency):
        self._agency = parent
        self._gather_accessibility_info()

    def _gather_accessibility_info(self):
        """
        Initialization method for gathering accessibility information from GTFS or other data.
        Must be implemented per agency.
        """
        raise NotImplementedError(
            "Accessibility information is not implemented for this agency!"
        )

    def station_has_inaccessible_platform(self, stop_id: str) -> bool:
        """
        Does this station have an explicitly inaccessible platform?
        Default implementation: False
        """
        # FIXME: instead of having accessibility dicts as globals in access.py, have them in this class as part of the init
        return False

    def station_has_accessible_platform(self, stop_id: str) -> bool:
        """
        Does this station have an explicitly accessible platform?
        Default implementation: False
        """
        # FIXME: same as above
        return False
