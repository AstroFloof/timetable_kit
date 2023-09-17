# amtrak/__init.py__
# Init file for amtrak subpackage of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
timetable_kit.amtrak module

Amtrak-specific functions for timetable_kit.

This defines an interface; VIA rail and others need to provide the same interface.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from timetable_kit.amtrak.access import AmtrakAccessibilityInfo
from timetable_kit.amtrak.gtfs import AmtrakGTFSHandler

# How to title the routes at the top of the column
from timetable_kit.amtrak.route_names import get_route_name
from timetable_kit.amtrak.stations import AmtrakStationInfo
from timetable_kit.amtrak.vehicles import AmtrakVehicleInfo

# Routine to pretty-print a station name
# (including subtitles, connecting agency logos, etc.)
from timetable_kit.generic_agency import Agency

module_location = Path(__file__).parent


class Amtrak(Agency):
    name = "Amtrak"
    input_dir = Path("specs_amtrak")
    # Published agency website, for printing.
    # Does not include the https:// and should be capitalized for print.
    published_website = "Amtrak.com"
    # Found at transit.land.
    # Also at The Mobility Database on GitHub.  MobilityData/mobility-database
    # This is the URL we should download the GTFS from.
    canonical_gtfs_url = "https://content.amtrak.com/content/gtfs/GTFS.zip"

    # This is the URL we should publish at the bottom of the timetable as the
    # source for GTFS data.  This should probably be a transit.land or similar
    # reference, in case the canonical url changes.
    published_gtfs_url = "https://www.transit.land/feeds/f-9-amtrak~amtrakcalifornia~amtrakcharteredvehicle"
    # CSS class for special modifications to the output.
    # Currently only used to change the header bar color.
    css_class = "amtrak-special-css"

    gtfs_zip_local_path = module_location / "GTFS.zip"
    gtfs_unzipped_local_path = module_location / "gtfs"

    _vehicle_info_class = AmtrakVehicleInfo
    _accessibility_info_class = AmtrakAccessibilityInfo
    _station_info_class = AmtrakStationInfo
    _gtfs_handler_class = AmtrakGTFSHandler

    @staticmethod
    def get_all_connecting_services(stations: Iterable[str]) -> list[str]:
        from timetable_kit.amtrak.connecting_services_data import (
            get_all_connecting_services,
        )

        return get_all_connecting_services(stations)


if __name__ == "__main__":
    from timetable_kit.initialize import initialize_feed

    master_feed = initialize_feed(gtfs=Amtrak.gtfs_zip_local_path)
    my_agency = Amtrak(master_feed)
    # print(my_agency.get_stop_name("ALB"))
    # # This works but is ugly / undesirable
    # my_agency.get_station_name_pretty = amtrak.get_station_name_pretty
    # print(my_agency.get_station_name_pretty("ALB"))
    # print(my_agency.get_station_name_pretty("ALB", doing_multiline_text=True))
    # print(my_agency.get_station_name_pretty("ALB", doing_html=True))
    print(my_agency.get_stop_name("ALB"))
    print(my_agency.station_info.get_station_name_pretty("ALB"))
    print(
        my_agency.station_info.get_station_name_pretty("ALB", doing_multiline_text=True)
    )
    print(my_agency.station_info.get_station_name_pretty("ALB", doing_html=True))

    b = my_agency.station_info.station_has_checked_baggage("NYP")
    print(b)
