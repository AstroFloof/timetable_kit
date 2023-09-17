# via/station_info.py
# Part of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.

"""
Utility routines to style VIA station names as HTML or text.

Also, routines to move from stop_id to and from station_code, and get station names.

Also, accessibility info.

Exported:
get_station_name_pretty
stop_id_to_stop_code
stop_code_to_stop_id

station_has_accessible_platform
station_has_inaccessible_platform
"""

# Find the HTML for a specific connecting agency's logo
from timetable_kit.connecting_services import get_connecting_service_logo_html
from timetable_kit.debug import debug_print
from timetable_kit.generic_agency import AgencyStationInfo


# Map from station codes to connecting service names (matching those in timetable_kit.connecting_services)
from timetable_kit.via.connecting_services_data import connecting_services_dict


# "Major stations".  This is for timetable styling: making them bigger and bolder.
# This should really be per-timetable but this is a start
# This list started as stations which VIA boldfaces on their website
# Plus a few US stations, since VIA didn't boldface any of them

# Station code reference: https://cptdb.ca/wiki/index.php/VIA_Rail_Canada_stations
# This is missing US stations though, and Hamilton (!)

major_stations_list = (
    # Atlantic Canada
    "HLFX",  # Halifax
    "MCTN",  # Moncton
    "MIRA",  # Miramichi
    "TRUR",  # Truro
    # Quebec
    "GASP",  # Gaspe (closed)
    "JONQ",  # Jonquiere
    "MTRL",  # Montreal
    "PERC",  # Perce (closed)
    "SFOY",  # Sainte-Foy (for Quebec City) -- I added this one
    "QBEC",  # Quebec (City)
    "RMSK",  # Rimouski
    "SENN",  # Senneterre
    "HERV",  # Hervey -- added for the JONQ/SENN split
    # Ontario
    "BLVL",  # Belleville
    "CWLL",  # Cornwall
    "HAML",  # Hamilton
    "KGON",  # Kingston
    "KITC",  # Kitchener
    "LNDN",  # London
    "NIAG",  # Niagara Falls
    "OTTW",  # Ottawa
    "SARN",  # Sarnia
    "TRTO",  # Toronto
    "WDON",  # Windsor
    # Western Ontario -- I added these for the Canadian
    "CAPR",  # Capreol
    "HNPN",  # Hornepayne
    "SLKT",  # Sioux Lookout
    # Western Ontario -- I added these for the Sudbury-White River train
    "SUDB",  # Sudbury -- VIA has this one boldfaced
    "CART",  # Cartier
    "CHAP",  # Chapleau
    "WHTR",  # White River
    # Manitoba
    "CHUR",  # Churchill
    "GILL",  # Gillam - I added
    "THOM",  # Thompson - I added
    "TPAS",  # The Pas
    "CANO",  # Canora - I added
    "WNPG",  # Winnipeg
    # Saskatchewan
    "SASK",  # Saskatoon
    # Alberta
    "EDMO",  # Edmonton
    "JASP",  # Jasper
    # British Columbia
    "KAMN",  # Kamloops North
    "PGEO",  # Prince George
    "PRUP",  # Prince Rupert
    "VCVR",  # Vancouver
    # US Stations
    "BUFX",  # Buffalo - Exchange
    "ALBY",  # Albany
    "NEWY",  # New York City
)


class VIARailStationInfo(AgencyStationInfo):
    # Initialization code.  We build the stop_code_to_stop_id and stop_id_to_stop_code dicts
    # from the GTFS.
    # These start blank and are filled in by initialization code on first use (memoized)
    stop_code_to_stop_id_dict = None
    stop_id_to_stop_code_dict = None
    stop_code_to_stop_name_dict = None

    def _gather_station_info(self):
        """
        Prepare the dicts for:
        stop_code_to_stop_id
        stop_id_to_stop_code
        stop_code_to_stop_name

        These depend on a previously established feed.
        """
        debug_print(1, "Preparing stop_code / stop_id dicts")

        patched_feed = self._agency.gtfs_handler().patch_feed(self._agency.feed)
        # ideally, the feed should already be patched... FIXME maybe?
        assert (
            patched_feed is not self._agency.feed
        )  # it shouldn't be, as patch_feed should return a patched COPY

        # Now extract the dicts from the feed
        stop_codes = patched_feed.stops["stop_code"].to_list()
        stop_ids = patched_feed.stops["stop_id"].to_list()
        stop_names = patched_feed.stops["stop_name"].to_list()

        self.stop_code_to_stop_id_dict = dict(zip(stop_codes, stop_ids))
        self.stop_id_to_stop_code_dict = dict(zip(stop_ids, stop_codes))
        self.stop_code_to_stop_name_dict = dict(zip(stop_codes, stop_names))

    def is_major_station(self, stop_id: str) -> bool:
        return stop_id in major_stations_list

    def get_all_connecting_services(self, station_list: list[str]) -> list:
        from connecting_services_data import get_all_connecting_services

        return get_all_connecting_services(station_list)

    def stop_code_to_stop_id(self, stop_code: str) -> str:
        """Given a VIA stop_code, return a VIA stop_id"""
        # Memoized

        return self.stop_code_to_stop_id_dict[stop_code]

    def stop_id_to_stop_code(self, stop_id: str) -> str:
        """Given a VIA stop_id, return a VIA stop_code"""
        # Memoized
        return self.stop_id_to_stop_code_dict[stop_id]

    def stop_code_to_stop_name(self, stop_code: str) -> str:
        """Given a VIA stop_code, return a VIA stop_name -- raw"""
        # This is unique to VIA, does it get called outside? If so, should be in AgencyStationInfo. TODO find out.
        # Memoized
        return self.stop_code_to_stop_name_dict[stop_code]

    def get_station_name_pretty(
        self, stop_code: str, doing_multiline_text=False, doing_html=False
    ) -> str:
        """Given a VIA stop_code, return a suitable station name for plaintext, multiline text, or HTML"""

        # First, get the raw station name: Memoized
        stop_name_raw = self.stop_code_to_stop_name(stop_code)
        # Is it major?
        major = self.is_major_station(stop_code)

        # Default to no facility name
        facility_name = None
        # Default to no connections from the name (this is unused)
        connections_from_name = []

        # Several stations have (EXO) in parentheses: one has (exo).  Get rid of this.
        # Some have GO Bus or GO as suffixes.  Get rid of this.
        # Clarify the confusing Niagara Falls situation.
        # This can be used to autogenerate connecting data, but isn't currently.  TODO
        if stop_name_raw.endswith(" (EXO)") or stop_name_raw.endswith(" (exo)"):
            stop_name_clean = stop_name_raw.removesuffix(" (EXO)").removesuffix(
                " (exo)"
            )
            facility_name = "EXO station"
            connections_from_name.append("exo")
        elif stop_name_raw.endswith(" GO Bus"):
            stop_name_clean = stop_name_raw.removesuffix(" GO Bus")
            facility_name = "GO Bus station"
        elif stop_name_raw.endswith(" GO"):
            stop_name_clean = stop_name_raw.removesuffix(" GO")
            facility_name = "GO station"
            connections_from_name.append("go_transit")
        elif stop_name_raw.endswith(" Bus"):
            stop_name_clean = stop_name_raw.removesuffix(" Bus")
            facility_name = "Bus station"
        elif stop_name_raw == "Niagara Falls Station":
            stop_name_clean = "Niagara Falls, NY"
        elif stop_name_raw == "Niagara Falls":
            stop_name_clean = "Niagara Falls, ON"
        else:
            stop_name_clean = stop_name_raw

        if stop_name_clean == "Sainte-Foy":
            # Explain where St. Foy station is
            facility_name = "for Quebéc City"
        elif stop_name_clean == "Quebéc":
            # Distinguish from other Quebec City stations
            facility_name = "Gare du Palais"
        elif stop_name_clean in ["Montreal", "Montréal"]:  # remember accented e
            # Two stations here too
            facility_name = "Central Station"
        elif stop_name_clean in ["Anjou", "Sauvé"]:  # remember accented e
            # On the Senneterre timetable,
            # "EXO station" blows out a line which we need for Montreal
            facility_name = ""
        elif stop_name_clean == "Ottawa":
            # Make it clear which LRT station this goes with
            facility_name = "Tremblay"
        elif stop_name_clean == "Toronto":
            # Just for clarity
            facility_name = "Union Station"
        elif stop_name_clean == "Vancouver":
            # There ARE two train stations in Vancouver
            facility_name = "Pacific Central Station"

        # We actually want to add the province to every station,
        # but VIA doesn't provide that info.  It's too much work.
        # FIXME

        # Uppercase major stations
        if major:
            stop_name_styled = stop_name_clean.upper()
        else:
            stop_name_styled = stop_name_clean

        # Default facility_name_addon to nothing...
        facility_name_addon = ""
        if doing_html:
            # There is some duplication of code between here and the Amtrak module.
            # Hence the misleading use of "city_state_name".  FIXME by pulling out common code
            city_state_name = stop_name_clean

            if major:
                enhanced_city_state_name = "".join(
                    ["<span class=major-station >", city_state_name, "</span>"]
                )
            else:
                enhanced_city_state_name = "".join(
                    ["<span class=minor-station >", city_state_name, "</span>"]
                )

            enhanced_station_code = "".join(
                ["<span class=station-footnotes>(", stop_code, ")</span>"]
            )

            if facility_name:
                facility_name_addon = "".join(
                    [
                        "<br>",
                        "<span class=station-footnotes>",
                        " - ",
                        facility_name,
                        "</span>",
                    ]
                )

            connection_logos_html = ""
            connecting_services = connecting_services_dict.get(stop_code, [])
            for connecting_service in connecting_services:
                # Note, this is "" if the agency is not found (but a debug error will print)
                # Otherwise it's a complete HTML code for the agency & its icon
                this_logo_html = get_connecting_service_logo_html(connecting_service)
                if this_logo_html:
                    # Add a space before the logo... if it exists at all
                    connection_logos_html += " "
                    connection_logos_html += this_logo_html

            cooked_station_name = "".join(
                [
                    enhanced_city_state_name,
                    " ",
                    enhanced_station_code,
                    facility_name_addon,  # Has its own space or <br> before it
                    connection_logos_html,  # Has spaces or <br> before it as needed
                ]
            )

        elif doing_multiline_text:
            # Multiline text. "Toronto (TRTO)\nSuffix"
            if facility_name:
                facility_name_addon = "\n - " + facility_name
            cooked_station_name = "".join(
                [stop_name_styled, " (", stop_code, ")", facility_name_addon]
            )
        else:
            # Single Line text: "Toronto - Suffix (TRTO)"
            if facility_name:
                facility_name_addon = " - " + facility_name
            cooked_station_name = "".join(
                [stop_name_styled, facility_name_addon, " (", stop_code, ")"]
            )

        return cooked_station_name


# TODO move testing to via/__init__.py because that's where these objects are initialized
# ### TESTING
# if __name__ == "__main__":
#     set_debug_level(2)
#     station_info = VIARailStationInfo()
#     print(
#         "Toronto stop id is:",
#         station_info.stop_code_to_stop_id("TRTO"),
#     )
