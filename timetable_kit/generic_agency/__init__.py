# generic_agency/__init__.py
# Part of timetable_kit
# Copyright 2021, 2022 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
This contains generic code which should be used for agencies which don't have their own subpackages.
This defines an interface; each agency needs to provide the same interface
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable

from gtfs_kit import Feed

from timetable_kit.feed_enhanced import FeedEnhanced
from timetable_kit.generic_agency.access import AgencyAccessibilityInfo
from timetable_kit.generic_agency.gtfs import AgencyGTFSHandler
from timetable_kit.generic_agency.station_info import AgencyStationInfo
from timetable_kit.generic_agency.vehicle_info import AgencyVehicleInfo

module_location = Path(__file__).parent


# TODO: Pass the feed to the information classes so they don't have to recreate it so many damn times...
class Agency:
    """
    Contains agency-specific calls and information.

    Default implementation gets info from the GTFS.
    """

    # Surely there's a better way to do these... FIXME
    name: str = ""
    input_dir: Path = Path()
    published_name: Optional[str] = None
    published_names_or: Optional[str] = None
    published_names_and: Optional[str] = None
    published_website: str = (  # these could be an empty string I suppose
        "https://www.railpassengers.org/"
    )
    published_gtfs_url: str = "https://www.railpassengers.org"
    css_class: str = "amtrak-special-css"
    canonical_gtfs_url: str = published_gtfs_url
    gtfs_zip_local_path = module_location / "GTFS.zip"
    gtfs_unzipped_local_path = module_location / "gtfs"

    def __init__(self, feed: Feed | FeedEnhanced):
        self.feed = feed
        self.stop_name_dict = dict(zip(feed.stops["stop_id"], feed.stops["stop_name"]))
        self.route_name_dict = dict(
            zip(feed.routes["route_id"], feed.routes["route_long_name"])
        )

        self.published_name = (
            self.name if self.published_name is None else self.published_name
        )
        self.published_names_or = (
            self.published_name
            if self.published_names_or is None
            else self.published_names_or
        )
        self.published_names_and = (
            self.published_name
            if self.published_names_and is None
            else self.published_names_and
        )

    # This defines what class to use to handle vehicle information
    _vehicle_info_class: type = AgencyVehicleInfo
    _vehicle_info: AgencyVehicleInfo = None

    @property
    def vehicle_info(self) -> _vehicle_info_class:
        """
        Returns a special data class, initialized.
        Recreating the class each time doesn't really matter (it's not loading external info),
        but the @property groundwork is here for if/when that's necessary.
        """
        self._vehicle_info = self._vehicle_info_class()
        return self._vehicle_info

    # This defines what class to use to handle accessibility information
    # TODO Maybe this could be part of the station info, because it is about the stations...
    _accessibility_info_class: type = AgencyAccessibilityInfo
    _accessibility_info: AgencyAccessibilityInfo = None

    @property
    def accessibility(self) -> _accessibility_info_class:
        """
        Returns the accessibility info handler, which can then preload relevant information on init.
        This handler is also then saved to the class, so it can be returned again.
        """
        if self._accessibility_info is None:
            self._accessibility_info = self._accessibility_info_class(self)
        return self._accessibility_info

    # This defines what class to use to handle station information
    _station_info_class: type = AgencyStationInfo
    _station_info: AgencyStationInfo = None

    @property
    def station_info(self) -> _station_info_class:
        """
        Returns the accessibility info handler, which can then preload relevant information on init.
        This handler is also then saved to the class, so it can be returned again.
        """
        if self._station_info is None:
            self._station_info = self._station_info_class(self)
        return self._station_info

    _gtfs_handler_class = AgencyGTFSHandler

    @classmethod
    def gtfs_handler(cls) -> _gtfs_handler_class:
        """Returns a GTFS handler, which must be initialized like this
        because the url and paths can change in implementing classes"""
        return cls._gtfs_handler_class(
            gtfs_url=cls.canonical_gtfs_url,
            unzip_path=cls.gtfs_unzipped_local_path,
            zip_path=cls.gtfs_zip_local_path,
        )

    def get_route_name(self, route_id: str) -> str:
        """Given a route_id, return a route_long_name from GTFS"""
        return self.route_name_dict[route_id]

    def get_stop_name(self, stop_id: str) -> str:
        """Given a stop id, get the full name of the stop"""
        return self.stop_name_dict[stop_id]

    @staticmethod
    def get_all_connecting_services(stations: Iterable[str]) -> list[str]:
        """
        Given a list of station codes, return a list of services which connect
        (with no duplicates)
        """
        raise NotImplementedError(
            "Generic agency has no connecting services functionality."
        )
