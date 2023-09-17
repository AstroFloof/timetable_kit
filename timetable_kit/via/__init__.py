# via/__init.py__
# Init file for via subpackage of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
timetable_kit.via module

VIA-specific functions for timetable_kit.

This defines an interface; Amtrak and others need to provide the same interface.
"""
from pathlib import Path
from typing import Iterable

from timetable_kit.generic_agency import Agency
from timetable_kit.via.access import VIARailAccessibilityInfo

# Patch errors in the feed
from timetable_kit.via.gtfs import VIARailGTFSHandler

# How to title the routes at the top of the column
from timetable_kit.via.route_names import get_route_name

# For colorizing columns
from timetable_kit.via.vehicle_info import VIARailVehicleInfo

# Routine to pretty-print a station name
# (including subtitles, connecting agency logos, etc.)
from timetable_kit.via.station_info import VIARailStationInfo

module_location = Path(__file__).parent


class VIARail(Agency):
    # Published agency name
    name = "VIA Rail"
    input_dir = Path("specs_via")

    # Published agency website, for printing.
    # Does not include the https:// and should be capitalized for print.
    published_website = "ViaRail.ca"

    # CSS class for special modifications to the output.
    # Currently only used to change the header bar color. TODO do the stuff :)
    css_class = "via-special-css"
    _station_info_class = VIARailStationInfo
    _accessibility_info_class = VIARailAccessibilityInfo
    _vehicle_info_class = VIARailVehicleInfo
    _gtfs_handler_class = VIARailGTFSHandler

    # Where we should download the GTFS from.
    # Found at www.viarail.ca/en/developer-resources
    #
    canonical_gtfs_url = "https://www.viarail.ca/sites/all/files/gtfs/viarail.zip"

    # This is the URL we should publish at the bottom of the timetable as the
    # source for GTFS data.  This should probably be a transit.land or similar
    # reference, in case the canonical url changes.
    published_gtfs_url = "https://www.transit.land/feeds/f-f-viarail~traindecharlevoix"

    gtfs_zip_local_path = module_location / "GTFS.zip"
    gtfs_unzipped_local_path = module_location / "gtfs"

    @staticmethod
    def get_all_connecting_services(stations: Iterable[str]) -> list[str]:
        from timetable_kit.via.connecting_services_data import (
            get_all_connecting_services,
        )

        return get_all_connecting_services(stations)
