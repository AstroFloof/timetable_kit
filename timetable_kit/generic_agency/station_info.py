from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from gtfs_kit import Feed

if TYPE_CHECKING:
    from timetable_kit.generic_agency import Agency


# TODO should access be merged into this? Should baggage be broken back out? Hmmmmm...
class AgencyStationInfo:
    """
    Class used to break out the functions for station information into a plug-and-play interface.
    Station information includes the status of checked baggage, station conditions, and formatting in a timetable.
    """

    def __init__(self, parent: Agency):
        self._agency = parent
        self._gather_station_info()

    def _gather_station_info(self):
        # Maybe this should be a warning
        raise NotImplementedError(
            "Station information not available for generic Agency"
        )

    def station_has_checked_baggage(self, stop_id: str) -> bool:
        """Does this station have checked baggage?
        Default implementation: False"""
        return False

    def has_shelter(self, station_code: str) -> bool:
        """
        Does this train station have a building, or does this bus stop have a building?
        Default implementation: False
        """
        return False

    def is_train_station(self, station_code: str) -> bool:
        """
        Is this a train station (not a bus station)?
        Default implementation: True
        """
        return True

    def is_major_station(self, stop_id: str) -> bool:
        """
        Return whether the station is major (should be emphasized).
        Default implementation: False.
        """
        return False

    def get_all_connecting_services(self, station_list: list[str]) -> list:
        """
        Given a list of station codes, return a list of services which connect
        (with no duplicates)
        Default implementation: []
        """
        return []

    def station_name_to_multiline_text(self, station_name: str, major=False) -> str:
        """
        Produce pretty station name for plaintext -- multi-line.
        Default implementation defaults to the single line function.
        """
        return self.station_name_to_single_line_text(station_name, major)

    def station_name_to_single_line_text(self, station_name: str, major=False) -> str:
        """
        Produce pretty station name for plaintext -- single line.
        Default implementation capitalizes the station name if major.
        """
        return station_name.upper() if major else station_name

    def station_name_to_html(
        self, station_name: str, major=False, show_connections=True
    ) -> str:
        """
        Produce pretty station name for HTML -- potentially multiline, and complex.
        Default implementation is to call the plaintext function.
        """
        return self.station_name_to_single_line_text(station_name, major)

    def get_station_name_pretty(
        self, station_code: str, doing_multiline_text=False, doing_html=False
    ) -> str:
        """
        Switch on which method should be used to prettify a station name based on whether
        multiline and html are necessary
        """
        prettyprint_station_name: Callable[[str, bool], str]
        if doing_html:
            # Note here that show_connections is on by default.
            # There is no mechanism for turning it off.
            prettyprint_station_name = self.station_name_to_html
        elif doing_multiline_text:
            prettyprint_station_name = self.station_name_to_multiline_text
        else:
            prettyprint_station_name = self.station_name_to_single_line_text

        from timetable_kit.amtrak.json_stations import get_station_name

        raw_station_name = get_station_name(station_code)
        major = self.is_major_station(station_code)
        cooked_station_name = prettyprint_station_name(raw_station_name, major)

        return cooked_station_name

    # These are do-nothings for Amtrak, but
    # quite significant for VIA Rail

    def stop_code_to_stop_id(self, stop_code: str) -> str:
        return stop_code

    def stop_id_to_stop_code(self, stop_id: str) -> str:
        return stop_id
