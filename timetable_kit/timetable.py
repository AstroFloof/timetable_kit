#! /usr/bin/env python3
# timetable.py
# Part of timetable_kit
# Copyright 2021, 2022 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.

"""
Generate timetables

timetable.py is the main program for generating timetables and related things
timetable.py --help gives documentation
"""

# Other people's packages
import argparse

from pathlib import Path
import os  # for os.getenv
import os.path  # for os.path abilities
import sys  # Solely for sys.path and solely for debugging
import shutil  # To copy files
import json

import pandas as pd
import gtfs_kit as gk
from weasyprint import HTML as weasyHTML
from weasyprint import CSS as weasyCSS

# My packages: Local module imports
# Note namespaces are separate for each file/module
# Also note: python packaging is really sucky for direct script testing.
from timetable_kit.errors import (
    GTFSError,
    NoStopError,
    TwoStopsError,
    NoTripError,
    TwoTripsError,
    InputError,
)
from timetable_kit.debug import set_debug_level, debug_print
from timetable_kit.timetable_argparse import make_tt_arg_parser

# This one monkey-patches gk.Feed (sneaky) so must be imported early
from timetable_kit import feed_enhanced

# To intialize the feed -- does type changes
from timetable_kit.initialize import initialize_feed

# For reversing the type changes to output GTFS again
from timetable_kit import gtfs_type_cleanup

from timetable_kit import amtrak  # so we don't have to say "timetable_kit.amtrak"

# To make it easier to isolate Amtrak dependencies in the main code, we always explicitly call:
# amtrak.special_data
# amtrak.json_stations

from timetable_kit import text_presentation
from timetable_kit import icons

# This is the big styler routine, lots of CSS; keep out of main namespace
from timetable_kit.timetable_styling import (
    get_time_column_stylings,
    style_timetable_for_html,
    finish_html_timetable,
)

from timetable_kit.amtrak.station_name_styling import (
    amtrak_station_name_to_html,
    amtrak_station_name_to_multiline_text,
    amtrak_station_name_to_single_line_text,
)
from timetable_kit.tsn import (
    make_trip_id_to_tsn_dict,
    find_tsn_dupes,
    make_tsn_to_trip_id_dict,
    stations_list_from_tsn,
)

### tt-spec loading and parsing code

### Constant set for the special column names.
### These should not be interpreted as trip_short_names or train numbers.
special_column_names = {
    "",
    "station",
    "stations",
    "services",
    "timezone",
}


def load_tt_aux(filename):
    """Load a tt-aux file in JSON format"""
    path = Path(filename)
    if path.is_file():
        with open(path, "r") as f:
            auxfile_str = f.read()
            aux = json.loads(auxfile_str)
            debug_print(1, "tt-aux file loaded")
            return aux
        print("Shouldn't get here, file load failed.")
    else:
        # Make it blank, basically
        debug_print(1, "No tt-aux file.")
        return {}


def load_tt_spec(filename):
    """Load a tt-spec from a CSV file"""
    tt_spec = pd.read_csv(filename, index_col=False, header=None, dtype=str)
    return tt_spec


def augment_tt_spec(raw_tt_spec, *, feed, date):
    """
    Fill in the station list for a tt-spec if it has a key code.

    Cell 0,0 is normally blank.
    If it is "Stations of 59", then (a) assume there is only one tt-spec row;
    (b) get the stations for 59 and fill the rows in from that

    Requires a feed and a date (the reference date; the train may change by date).

    Note that this tucks on the end of the tt_spec.  A "second row" for column-options
    will therefore be unaffected.  Other second rows may result in confusing results.
    """
    if pd.isna(raw_tt_spec.iloc[0, 0]):
        # No key code, nothing to do
        return raw_tt_spec
    key_code = str(raw_tt_spec.iloc[0, 0])
    debug_print(3, "Key code: " + key_code)
    if key_code.startswith("stations of "):
        key_train_name = key_code[len("stations of ") :]
        # Filter the feed down to a single date...
        today_feed = feed.filter_by_dates(date, date)
        # And pull the stations list
        stations_df = stations_list_from_tsn(today_feed, key_train_name)
        new_tt_spec = raw_tt_spec.copy()  # Copy entire original spec
        new_tt_spec.iloc[0, 0] = float("nan")  # Blank out key_code
        newer_tt_spec = pd.concat([new_tt_spec, stations_df])  # Yes, this works
        # The problem is that it leads to duplicate indices (ugh!)
        # So fully reset the index
        newest_tt_spec = newer_tt_spec.reset_index(drop=True)
        debug_print(1, newest_tt_spec)
        return newest_tt_spec

    raise InputError("Key cell must be blank or 'stations of xxx', was ", key_code)


def stations_list_from_tt_spec(tt_spec):
    """Given a tt_spec dataframe, return the station list as a list of strings"""
    stations_df = tt_spec.iloc[1:, 0]
    stations_list_raw = stations_df.to_list()
    stations_list_strings = [str(i) for i in stations_list_raw]
    stations_list = [i.strip() for i in stations_list_strings if i.strip() != ""]
    return stations_list


def trains_list_from_tt_spec(tt_spec):
    """Given a tt_spec dataframe, return the trains list as a list of strings"""
    trains_df = tt_spec.iloc[0, 1:]
    trains_list_raw = trains_df.to_list()
    trains_list_strings = [str(i) for i in trains_list_raw]
    trains_list = [i.strip() for i in trains_list_strings]
    return trains_list


def get_column_options(tt_spec):
    """
    Given a tt_spec dataframe with column-options in row 2, return a data structure for the column options.

    This data structure is a list (indexed by column number) wherein each element is a list.
    These inner lists are either empty, or a list of options.

    Options are free-form; currently only "reverse" is defined.  More will be defined later.
    Blank columns lead to a spurious "nan", but as long as we don't check for a "nan" option, who cares?
    (Possibly fix this later.)

    The column options are specified in row 2 of the table.  If they're not there, don't call this.
    """

    def nan_to_blank(s):
        if pd.isna(s):
            return ""
        return s

    if str(tt_spec.iloc[1, 0]).lower() not in ["column-options", "column_options"]:
        column_count = tt_spec.shape[1]
        # What, there weren't any?  Make a list containing blank lists:
        column_options = [[]] * column_count
        return column_options
    # Now for the main version
    column_options_df = tt_spec.iloc[1, 0:]  # second row, all of it
    column_options_raw_list = column_options_df.to_list()
    column_options_clean_list = [nan_to_blank(s) for s in column_options_raw_list]
    column_options_nested_list = [str(i).split() for i in column_options_clean_list]
    debug_print(1, column_options_nested_list)
    return column_options_nested_list


def split_trains_spec(trains_spec):
    """
    Given a string like "59 / 174 / 22", return a structured list:

    [["59, "174", "22"], True]

    Used to separate specs for multiple trains in the same timetable column.
    A single "59" will simply give {"59"}.

    A leading minus sign (-) means the column is reversed (read bottom to top);
    this is stripped by this method.
    """
    # Remove leading whitespace and possible leading minus sign
    clean_trains_spec = trains_spec.lstrip()

    raw_list = clean_trains_spec.split("/")
    clean_list = [item.strip() for item in raw_list]  # remove whitespace again
    return clean_list


def flatten_trains_list(trains_list):
    """
    Take a nested list of trains and make a flast list of trains.

    Take a list of trains as specified in a tt_spec such as [NaN,'174','178/21','stations','23/1482']
    and make a flat list of all trains involved ['174','178','21','23','1482']
    without the special keywords like "station".
    """
    flattened_trains_list = []
    for ts in trains_list:
        tsns = split_trains_spec(ts)  # Separates at the "/"
        flattened_trains_list = [*flattened_trains_list, *tsns]
    flattened_trains_set = set(flattened_trains_list)
    flattened_trains_set = flattened_trains_set - special_column_names
    return flattened_trains_set


#### Subroutines for fill_tt_spec


def service_dates_from_trip_id(feed, trip_id):
    """
    Given a single trip_id, get the associated service dates by looking up the service_id in the calendar

    Returns an ordered pair (start_date, end_date)
    """
    # FIXME: The goal is to get the latest start date and earliest end date
    # for all trains in a list.  Do this in a more "pandas" fashion.
    service_id = feed.trips[feed.trips.trip_id == trip_id]["service_id"].squeeze()

    calendar_row = feed.calendar[feed.calendar.service_id == service_id]

    start_date = (calendar_row.start_date).squeeze()
    end_date = (calendar_row.end_date).squeeze()

    return [start_date, end_date]


def get_timepoint_from_trip_id(feed, trip_id, station_code):
    """
    Given a single trip_id, station_code, and a feed, extract a single timepoint.

    This returns the timepoint (as a Series) taken from the stop_times GTFS feed.

    Throw TwoStopsError if it stops here twice.

    Return "None" if it doesn't stop here.  This is not an error.
    (Used to throw NoStopError if it doesn't stop here.  Too common.)
    """
    # Old, slower code:
    # stop_times = feed.filter_by_trip_ids([trip_id]).stop_times # Unsorted
    # timepoint_df = stop_times.loc[stop_times['stop_id'] == station_code]
    # The following is MUCH faster -- cuts test case from 35 secs to 20 secs:
    timepoint_df = feed.stop_times[
        (feed.stop_times["trip_id"] == trip_id)
        & (feed.stop_times["stop_id"] == station_code)
    ]
    if timepoint_df.shape[0] == 0:
        return None
    if timepoint_df.shape[0] > 1:
        # This is a bail-out error, it can afford to be slow:
        # Note: the train number lookup only works if the feed is limited to one day,
        # thus making the reverse lookup unique.
        # It will throw an error otherwise.
        trip_id_to_tsn_dict = make_trip_id_to_tsn_dict(feed)
        tsn = trip_id_to_tsn_dict[trip_id]
        raise TwoStopsError(
            " ".join(
                [
                    "Train number",
                    tsn,
                    "with trip id",
                    trip_id,
                    "stops at station code",
                    station_code,
                    "more than once",
                ]
            )
        )
    timepoint = timepoint_df.iloc[0]  # Pull out the one remaining row
    return timepoint


def get_dwell_secs(today_feed, trip_id, station_code):
    """
    Gets dwell time in seconds for a specific trip_id at a specific station

    today_feed: a feed
    trip_id: relevant trip_id
    station_code: station code

    Used primarily to determine whether to put both arrival and departure times
    in the timetable for this station.
    """
    timepoint = get_timepoint_from_trip_id(today_feed, trip_id, station_code)

    if timepoint is None:
        # If the train doesn't stop there, the dwell time is zero;
        # and we need thie behavior for make_stations_max_dwell_map
        return 0

    # There's a catch!  If this station is "discharge only" or "receive only",
    # it effectively has no official dwell time, and should not get two lines
    if timepoint.drop_off_type == 1 or timepoint.pickup_type == 1:
        return 0

    # Normal case:
    departure_secs = gk.timestr_to_seconds(timepoint.departure_time)
    arrival_secs = gk.timestr_to_seconds(timepoint.arrival_time)
    dwell_secs = departure_secs - arrival_secs
    return dwell_secs


def make_stations_max_dwell_map(
    today_feed, tt_spec, dwell_secs_cutoff, trip_from_tsn_fn
):
    """
    Return a dict from station_code to True/False, based on the trains in the tt_spec.

    This is used to decide whether a station should get a "double line" or "single line" format in the timetable.

    today_feed: a feed filtered to a single date (so tsns are unique)
    tt_spec: the tt_spec
    dwell_secs_cutoff: below this, we don't bother to list arrival and departure times both
    trip_from_tsn_fn: a function which maps tsn to trip_id and provides error raising

    Expects a feed already filtered to a single date.
    The feed *may* be restricted to the relevant trains (but must contain all relevant trains).

    First we extract the list of stations and the list of train names from the tt_spec.

    If any train in tsns has a dwell time of dwell_secs or longer at a station,
    then the dict returns True for that station_code; otherwise False.
    """
    # First get stations and trains list from tt_spec.
    stations_list = stations_list_from_tt_spec(tt_spec)
    trains_list = trains_list_from_tt_spec(tt_spec)  # Note still contains "/" items
    flattened_trains_set = flatten_trains_list(trains_list)

    # Prepare the dict to return
    stations_dict = {}
    for station_code in stations_list:
        max_dwell_secs = 0
        for tsn in flattened_trains_set:
            debug_print(3, "debug dwell map:", tsn, station_code)
            trip_id = trip_from_tsn_fn(tsn).trip_id
            max_dwell_secs = max(
                max_dwell_secs, get_dwell_secs(today_feed, trip_id, station_code)
            )
        if max_dwell_secs >= dwell_secs_cutoff:
            stations_dict[station_code] = True
        else:
            stations_dict[station_code] = False
    return stations_dict


def raise_error_if_not_one_row(trips):
    """
    Given a PANDAS DataFrame, raise an error if it has either 0 or more than 1 rows.

    The error text is based on the assumption that this is a GTFS trips frame.
    This returns nothing if successful; it is solely sanity-check code.

    For speed we have to work with trips directly rather than modifying the feed,
    which is why this is needed for fill_tt_spec, rather than merely in feed_enhanced.
    """
    num_rows = trips.shape[0]
    if num_rows == 0:
        raise NoTripError(
            "Expected single trip: no trips in filtered trips table", trips
        )
    if num_rows > 1:
        print(trips)
        raise TwoTripsError(
            "Expected single trip: too many trips in filtered trips table", trips
        )
    return


def fill_tt_spec(
    tt_spec,
    *,
    today_feed,
    doing_html=False,
    box_time_characters=False,
    doing_multiline_text=True,
    is_major_station="standard",
    is_ardp_station="dwell",
    dwell_secs_cutoff=300,
):
    """
    Fill a timetable from a tt-spec template using GTFS data

    The tt-spec must be complete (run augment_tt_spec first)
    today_feed: GTFS feed to work with.  Mandatory.
        This should be filtered to a single representative date.  This is not checked.
        This *may* be filtered to relevant trains only.  It must contain all relevant trains.
    date: Reference date to get timetable for.  Default passed at command line. FIXME

    doing_html: Produce HTML timetable.  Default is false (produce plaintext timetable).
    box_time_characters: Box every character in the time in an HTML box to make them line up.
        For use with fonts which don't have tabular nums.
        Default is False.  Avoid if possible; fragile.
    doing_multiline_text: Produce multiline text in cells.  Ignored if doing_html.
        Default is True.
        If False, stick with single-line text (and never print arrival times FIXME)
    is_major_station: pass a function which says whether a station should be "major";
        "False" means false for all
        "standard" means a standard list of Amtrak major stations
        Defaults to "standard"
    is_ardp_station: pass a function which says whether a station should have arrival times;
        "False" means false for all; "True" means true for all
        Default is "dwell" (case sensitive), which uses dwell_secs_cutoff.
    dwell_secs_cutoff: Show arrival & departure times if dwell time is this many seconds
        or higher for some train in the tt_spec
        Defaults to 300, meaning 5 minutes.
        Probably don't want to ever make it less than 1 minute.
    """
    # We have a filtered feed.  We're going to have to map from tsns to trip_ids, repeatedly.
    # This was the single slowest step in earlier versions of the code, using nearly all the runtime.
    # So we generate a dict for it.
    tsn_to_trip_id = make_tsn_to_trip_id_dict(today_feed)
    # Create an inner function to get the trip from the tsn, using the dict we just made
    # Also depends on the today_feed
    def trip_from_tsn_local(tsn: str) -> str:
        try:
            my_trip_id = tsn_to_trip_id[tsn]
        except KeyError as e:
            raise InputError("No trip_id for ", tsn) from e
        my_trips = today_feed.trips[today_feed.trips.trip_id == my_trip_id]
        raise_error_if_not_one_row(my_trips)
        my_trip = my_trips.iloc[0]
        return my_trip

    # Extract a list of column options, if provided in the spec
    # This must be in the second row (row 1) and first column (column 0)
    # It ends up as a list (indexed by column number) of lists of options.
    column_options = get_column_options(tt_spec)
    if str(tt_spec.iloc[1, 0]).lower() in ["column-options", "column_options"]:
        # Delete the problem line before further work.
        # This drops by index and not by actual row number, irritatingly
        # Thankfully they're currently the same
        tt_spec = tt_spec.drop(1, axis="index")

    # Load variable function for station name printing
    prettyprint_station_name = None
    if doing_html:
        prettyprint_station_name = amtrak_station_name_to_html
    elif doing_multiline_text:
        prettyprint_station_name = amtrak_station_name_to_multiline_text
    else:
        prettyprint_station_name = amtrak_station_name_to_single_line_text
    if not callable(prettyprint_station_name):
        raise TypeError(
            "Received prettyprint_station_name which is not callable: ",
            prettyprint_station_name,
        )

    # Load variable functions for is_ardp_station and is_major_station
    if is_major_station is False:
        is_major_station = lambda station_code: False
    elif is_major_station == "standard":
        is_major_station = amtrak.special_data.is_standard_major_station
    if not callable(is_major_station):
        raise TypeError(
            "Received is_major_station which is not callable: ", is_major_station
        )

    if is_ardp_station is False:
        is_ardp_station = lambda station_code: False
    elif is_ardp_station is True:
        is_ardp_station = lambda station_code: True
    elif is_ardp_station == "dwell":
        # Prep max dwell map.  This is the second-slowest part of the program.
        stations_max_dwell_map = make_stations_max_dwell_map(
            today_feed=today_feed,
            tt_spec=tt_spec,
            dwell_secs_cutoff=dwell_secs_cutoff,
            trip_from_tsn_fn=trip_from_tsn_local,
        )
        is_ardp_station = lambda station_code: stations_max_dwell_map[station_code]
        debug_print(1, "Dwell map prepared.")
    if not callable(is_ardp_station):
        raise TypeError(
            "Received is_ardp_station which is not callable: ", is_ardp_station
        )

    # We used to do deep copies here.  Really we just want to copy the STRUCTURE.
    # tt = tt_spec.copy()  # "deep" copy
    [row_index, column_index] = tt_spec.axes
    tt = pd.DataFrame(
        index=row_index.copy(deep=True), columns=column_index.copy(deep=True)
    )
    # styler_t = tt_spec.copy()  # another "deep" copy, parallel
    styler_t = pd.DataFrame(
        index=row_index.copy(deep=True), columns=column_index.copy(deep=True)
    )
    debug_print(1, "Copied tt-spec.")

    # Go through the columns to get an ardp columns map -- cleaner than current implementation
    # FIXME.

    # Base CSS for every data cell.  We probably shouldn't do this but it tests that the styler works.
    base_cell_css = ""

    # NOTE, border variations not implemented yet FIXME
    # borders_final_css="border-bottom-heavy"
    # borders_initial_css="border-top-heavy"
    # Have to add "initial" and "final" with heavy borders

    # Pick out the agency timezone (which is based on the train number, the route, etc.)
    # TODO FIXME, brutal hack, assume it's Eastern since Amtrak is eastern and one
    # dataset is not allowed by GTFS to have multiple agency timezones!
    agency_tz = "America/New_York"

    # Now for the main routine, which is a giant double loop, and therefore quite slow.
    [row_count, column_count] = tt_spec.shape

    header_replacement_list = []  # list, will fill in as we go
    header_styling_list = []  # list, to match column numbers.  Will fill in as we go
    for x in range(1, column_count):  # First (0) column is the station code
        train_nums_str = str(tt_spec.iloc[0, x]).strip()  # row 0, column x

        if train_nums_str.lower() in ["station", "stations"]:
            station_column_header = text_presentation.get_station_column_header(
                doing_html=doing_html
            )
            header_replacement_list.append(station_column_header)
            header_styling_list.append("")  # could include background color
        elif train_nums_str.lower() in ["services"]:
            services_column_header = text_presentation.get_services_column_header(
                doing_html=doing_html
            )  # in a span
            header_replacement_list.append(services_column_header)
            header_styling_list.append("")  # could include background color;
        elif train_nums_str.lower() in ["timezone"]:
            timezone_column_header = text_presentation.get_timezone_column_header(
                doing_html=doing_html
            )  # in a span
            header_replacement_list.append(timezone_column_header)
            header_styling_list.append("")  # could include background color;
        else:  # it's actually a train
            # Check column options for reverse, days, ardp:
            reverse = "reverse" in column_options[x]
            use_daystring = "days" in column_options[x]
            long_days_box = "long-days-box" in column_options[x]
            short_days_box = "short-days-box" in column_options[x]
            this_column_gets_ardp = "ardp" in column_options[x]

            # Separate train numbers by "/"
            tsns = split_trains_spec(train_nums_str)
            tsn = tsns[0]
            if len(tsns) > 1:
                raise InputError("Two trains in one column not implemented")
            time_column_header = text_presentation.get_time_column_header(
                tsn, doing_html=doing_html
            )
            header_replacement_list.append(time_column_header)
            if doing_html:
                time_column_stylings = get_time_column_stylings(tsn)
                header_styling_list.append(time_column_stylings)
            else:  # plaintext
                header_styling_list.append("")

            train_has_checked_baggage = amtrak.train_has_checked_baggage(tsn)

        for y in range(1, row_count):  # First (0) row is the header
            station_code = tt_spec.iloc[y, 0]  # row y, column 0
            # Reset the styler string:
            cell_css_list = [base_cell_css]

            # Consider, here, whether to build parallel tables.
            # This allows for the addition of extra rows.
            if pd.isna(station_code):
                # Line which has no station code -- freeform line.
                # No times or station names here!
                cell_css_list.append("special-cell")
                if pd.isna(tt_spec.iloc[y, x]):
                    # Make sure blanks become *string* blanks in this line.
                    tt.iloc[y, x] = ""
                else:
                    # This is probably special text like "to Chicago".
                    # Copy the handwritten text over.
                    tt.iloc[y, x] = tt_spec.iloc[y,x]
            elif station_code.lower() == "route-name":
                # Special line for route names.
                cell_css_list.append("route-name-cell")
                if train_nums_str in special_column_names:
                    tt.iloc[y, x] = ""
                else:
                    my_trip = trip_from_tsn_local(tsn)
                    route_id = my_trip.route_id
                    # Clean this interface up later.  For now highly Amtrak-specific FIXME
                    route_name = amtrak.get_route_name(today_feed, route_id)
                    styled_route_name = text_presentation.style_route_name_for_column(
                        route_name, doing_html=doing_html
                    )
                    tt.iloc[y, x] = styled_route_name
                    cell_css_list.append(
                        get_time_column_stylings(tsn, output_type="class")
                    )
            elif station_code.lower() == "updown":
                # Special line just to say "Read Up" or "Read Down"
                cell_css_list.append("updown-cell")
                if train_nums_str in special_column_names:
                    tt.iloc[y, x] = ""
                else:
                    tt.iloc[y, x] = text_presentation.style_updown(
                        reverse, doing_html=doing_html
                    )
            elif station_code.lower() in ["days", "days-of-week"]:
                # Days of week -- best for a train which doesn't run across midnight
                cell_css_list.append("days-of-week-cell")
                if train_nums_str in special_column_names:
                    tt.iloc[y, x] = ""
                else:
                    my_trip = trip_from_tsn_local(tsn)
                    # We can only show the days for one station.
                    # So get the reference stop_id / station code to use; user-specified
                    reference_stop_id = tt_spec.iloc[y, x]
                    if pd.isna(reference_stop_id) or reference_stop_id == "":
                        # No reference stop?  Maybe this should be blank.
                        # Useful if one train runs across midnight.
                        tt.iloc[y, x] = ""
                    else:
                        timepoint = get_timepoint_from_trip_id(
                            today_feed, my_trip.trip_id, reference_stop_id
                        )
                        # Pull out the timezone for the reference_stop_id (should precache as dict, TODO)
                        stop_df = today_feed.stops[
                            today_feed.stops.stop_id == reference_stop_id
                        ]
                        stop_tz = stop_df.iloc[0].stop_timezone
                        zonediff = text_presentation.get_zonediff(stop_tz, agency_tz)
                        # Get the day change for the reference stop (format is explained in text_presentation)
                        departure = text_presentation.explode_timestr(
                            timepoint.departure_time, zonediff
                        )
                        offset = departure.day
                        # Finally, get the calendar (must be unique)
                        calendar = today_feed.calendar[
                            today_feed.calendar.service_id == my_trip.service_id
                        ]
                        # And fill in the actual string
                        daystring = text_presentation.day_string(
                            calendar, offset=offset
                        )
                        # TODO: add some HTML styling here
                        tt.iloc[y, x] = daystring
                    # Color this cell
                    cell_css_list.append(
                        get_time_column_stylings(tsn, output_type="class")
                    )
            elif not pd.isna(tt_spec.iloc[y, x]):
                # Line led by a station code, but cell already has a value.
                cell_css_list.append("special-cell")
                # This is probably special text like "to Chicago".
                # Copy the handwritten text over.
                tt.iloc[y, x] = tt_spec.iloc[y,x]
            else:
                # Normal line led by a station code.
                # Blank cell to be filled in -- the usual case.

                # TODO, check station code validity here!

                # Pick out the stop timezone -- TODO, precache this as a dict
                stop_df = today_feed.stops[today_feed.stops.stop_id == station_code]
                stop_tz = stop_df.iloc[0].stop_timezone

                if train_nums_str.lower() in [
                    "station",
                    "stations",
                ]:  # Column for station names
                    cell_css_list.append("station-cell")
                    station_name_raw = amtrak.get_station_name(station_code)
                    major = amtrak.special_data.is_standard_major_station(station_code)
                    station_name_str = prettyprint_station_name(station_name_raw, major)
                    tt.iloc[y, x] = station_name_str
                elif train_nums_str.lower() in [
                    "services"
                ]:  # Column for station services codes
                    cell_css_list.append("services-cell")
                    services_str = ""
                    debug_print(
                        1,
                        station_code,
                        amtrak.station_has_accessible_platform(station_code),
                    )
                    if amtrak.station_has_accessible_platform(station_code):
                        services_str += icons.get_accessible_icon_html()
                    elif amtrak.station_has_inaccessible_platform(station_code):
                        services_str += icons.get_inaccessible_icon_html()
                    tt.iloc[y, x] = services_str
                elif train_nums_str in ["timezone"]:  # Column for time zone codes
                    cell_css_list.append("timezone-cell")
                    tt.iloc[y, x] = text_presentation.get_zone_str(
                        stop_tz, doing_html=doing_html
                    )
                else:
                    # It's a train number.
                    # For a slashed train spec ( 549 / 768 ) pull the *first* train's times,
                    # then the second train's times *if the first train doesn't stop there*
                    # If the first train terminates and the second train starts, we need to
                    # somehow make it an ArDp station with double lines... tricky, not done yet
                    #
                    debug_print(
                        3, "".join(["Trains: ", str(tsns), "; Station:", station_code])
                    )

                    # Extract calendar, timepoint
                    my_trip = trip_from_tsn_local(tsn)
                    debug_print(2, "debug trip_id:", tsn, my_trip.trip_id)

                    timepoint = get_timepoint_from_trip_id(
                        today_feed, my_trip.trip_id, station_code
                    )

                    calendar = None  # if not use_daystring, save time
                    if use_daystring:
                        calendar = today_feed.calendar[
                            today_feed.calendar.service_id == my_trip.service_id
                        ]

                    if train_has_checked_baggage:
                        has_baggage = amtrak.station_has_checked_baggage(station_code)
                    else:
                        has_baggage = False

                    # Need to insert complicated for loop here for multiple trains
                    # TODO FIXME

                    # MUST figure first_stop and last_stop
                    # ...which means we need to make earlier passes through the table FIXME

                    # Only assign the stylings if the train hasn't ended.  Tricky!  Dunno how to do it!
                    # Probably requires that earlier pass through the table.
                    if timepoint is None:
                        # This train does not stop at this station
                        # Blank cell -- need to be cleverer about this FIXME
                        tt.iloc[y, x] = ""
                        cell_css_list.append("blank-cell")
                        # Confusing: we want to style some of these and not others.  Woof.
                        cell_css_list.append(
                            get_time_column_stylings(tsn, output_type="class")
                        )
                    else:
                        cell_css_list.append("time-cell")
                        cell_css_list.append(
                            get_time_column_stylings(tsn, output_type="class")
                        )

                        cell_text = text_presentation.timepoint_str(
                            timepoint,
                            stop_tz=stop_tz,
                            agency_tz=agency_tz,
                            doing_html=doing_html,
                            box_time_characters=box_time_characters,
                            reverse=reverse,
                            two_row=is_ardp_station(station_code),
                            use_ar_dp_str=this_column_gets_ardp,
                            use_daystring=use_daystring,
                            calendar=calendar,
                            long_days_box=long_days_box,
                            short_days_box=short_days_box,
                            use_baggage_str=train_has_checked_baggage,
                            has_baggage=has_baggage,
                        )
                        tt.iloc[y, x] = cell_text
            # Fill the styler.  We MUST overwrite every single cell of the styler.
            styler_t.iloc[y, x] = " ".join(cell_css_list)

    # Now we have to delete the placeholder left column
    tt = tt.drop(labels=0, axis="columns")
    styler_t = styler_t.drop(labels=0, axis="columns")

    # And the placeholder top row
    tt = tt.drop(labels=0, axis="rows")
    styler_t = styler_t.drop(labels=0, axis="rows")

    # And now we have to rename the headers.  This is kind of ugly!
    # This is quite fragile and should be checked regularly.
    # It depends on having removed the placeholder column already.
    #
    # We have to do the styler and the tt at the same time,
    # or the styler will fail.
    tt.columns = header_replacement_list
    styler_t.columns = header_replacement_list

    return (tt, styler_t, header_styling_list)


def produce_timetable(
    *,
    do_csv,
    do_html,
    do_pdf,
    master_feed,
    author,
    command_line_reference_date,
    input_dirname,
    spec_file,
    output_dirname,
):
    """
    Produce a single timetable HTML file.  Assumes setup has been done.

    Intended to allow multiple timetables to be processed at once.
    do_csv: produce a CSV timetable
    do_html: produce an HTML timetable
    do_pdf: produce a PDF timetable
    master_feed: initialized master GTFS feed
    author: author name
    command_line_reference_date: reference date passed at command line, might be None
    input_dirname: find the spec_name.tt-spec and spec_name.tt-aux files here
    spec_file: root of filename for the tt-spec and tt-aux files specifying the timetable
    output_dirname: Put the output timetables here
    """
    # Accept the spec name with or without .tt-spec, for convenience
    spec_filename_base = spec_file.removesuffix(".tt-spec").removesuffix(".tt-aux")
    tt_spec_filename = spec_filename_base + ".tt-spec"
    tt_aux_filename = spec_filename_base + ".tt-aux"

    if input_dirname:
        input_dir = Path(input_dirname)
        tt_spec_path = input_dir / tt_spec_filename
        tt_aux_path = input_dir / tt_aux_filename
    else:
        # Might be None, if it wasn't passed at the command line
        tt_spec_path = tt_spec_filename
        tt_aux_path = tt_aux_filename
    debug_print(1, "tt_spec_path", tt_spec_path, "/ tt_aux_path", tt_aux_path)

    # Load the .tt-aux file first, as it determines high-level stuff
    aux = load_tt_aux(tt_aux_path)

    if output_dirname:
        output_dir = Path(output_dirname)
    else:
        output_dir = Path(".")

    if "output_subdir" in aux:
        output_subdir = aux["output_subdir"]
        output_dir = output_dir / output_subdir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    if "output_filename" in aux:
        # The aux file may specify the output filename
        output_filename_base = aux["output_filename"]
    else:
        # Or, make it the same as the input filename
        output_filename_base = spec_filename_base

    if "for_rpa" in aux:
        for_rpa = aux["for_rpa"]
    else:
        for_rpa = False

    # Copy the icons and fonts to the output dir.
    # This is memoized so it won't duplicate work if you do multiple tables.
    copy_supporting_files_to_output_dir(output_dir, for_rpa)

    if command_line_reference_date:
        reference_date = int(command_line_reference_date)
    elif "reference_date" in aux:
        # We're currently converting GTFS dates to ints; FIXME
        reference_date = int(aux["reference_date"])
    else:
        raise InputError("No reference date in .tt-aux or at command line!")
    debug_print(1, "Working with reference date ", reference_date, ".", sep="")

    # Now we're ready to load the .tt-spec file, finally
    tt_spec_raw = load_tt_spec(tt_spec_path)
    tt_spec = augment_tt_spec(tt_spec_raw, feed=master_feed, date=reference_date)
    debug_print(1, "tt-spec", spec_filename_base, "loaded and augmented")

    # Filter the feed to the relevant day.  Required.
    today_feed = master_feed.filter_by_dates(reference_date, reference_date)
    debug_print(1, "Feed filtered by reference date.")

    # Reduce the feed, by eliminating stuff from other trains.
    # By reducing the stop_times table to be much smaller,
    # this hopefully makes each subsequent search for a timepoint faster.
    # This cuts a testcase runtime from 23 seconds to 20.
    trains_list = trains_list_from_tt_spec(tt_spec)  # Note still contains "/" items
    flattened_trains_set = flatten_trains_list(trains_list)
    reduced_feed = today_feed.filter_by_trip_short_names(flattened_trains_set)
    debug_print(1, "Feed filtered by trip_short_name.")

    # Uniqueness sanity check -- check for two rows in reduced_feed.trips with the same tsn.
    # This will make it impossible to map from tsn to trip_id.
    # HOWEVER, Amtrak has some weird duplicates with duplicate trip_ids and identical timings,
    # so this might not be a fatal error.
    if find_tsn_dupes(reduced_feed):
        debug_print(
            1,
            "Warning, tsn duplicates!  Random trip will be picked!  Usually a bad idea!",
        )

    # Print the calendar for debugging
    debug_print(1, reduced_feed.calendar)

    # Debugging for the reduced feed.  Seems to be fine.
    # with open( Path("./dump-stop-times.csv"),'w') as outfile:
    #    print(reduced_feed.stop_times.to_csv(index=False), file=outfile)

    # Collect pairs of validity dates.
    # Note that the feed has been filtered by tsns,
    # so will *only* include relevant tsns in the calendar!
    start_dates = reduced_feed.calendar["start_date"]
    latest_start_date = start_dates.max()
    end_dates = reduced_feed.calendar["end_date"]
    earliest_end_date = end_dates.min()

    debug_print(1, "Believed valid from", latest_start_date, "to", earliest_end_date)

    # This will eventually get used, but for now just emit it as a debug message

    # Note that due to the inline images issue we may need to run
    # a completely separate HTML version for weasyprint.  We avoid this so far.
    # TODO
    # Consider using the SpartanTT font to handle this.  We can make the font
    # quasi-legit for screen readers by using correct Unicode code points.

    if do_csv:
        (timetable, styler_table, header_styling) = fill_tt_spec(
            tt_spec,
            today_feed=reduced_feed,
            is_major_station=amtrak.special_data.is_standard_major_station,
            is_ardp_station="dwell",
        )
        # NOTE, need to add the header
        path_for_csv = output_dir / Path(output_filename_base + ".csv")
        timetable.to_csv(path_for_csv, index=False, header=True)
        debug_print(1, "CSV done")

    if do_html or do_pdf:
        # Main timetable, same for HTML and PDF
        (timetable, styler_table, header_styling_list) = fill_tt_spec(
            tt_spec,
            today_feed=reduced_feed,
            is_major_station=amtrak.special_data.is_standard_major_station,
            is_ardp_station="dwell",
            doing_html=True,
            box_time_characters=False,
        )
        timetable_styled_html = style_timetable_for_html(timetable, styler_table)
        debug_print(1, "HTML styled")

    if do_html or do_pdf:
        # Produce the final complete page...
        timetable_finished_html = finish_html_timetable(
            timetable_styled_html,
            header_styling_list,
            author=author,
            aux=aux,
            box_time_characters=False,
            start_date=str(latest_start_date),
            end_date=str(earliest_end_date),
        )
        path_for_html = output_dir / Path(output_filename_base + ".html")
        with open(path_for_html, "w") as outfile:
            print(timetable_finished_html, file=outfile)
        debug_print(1, "Finished HTML done")

    if do_pdf:
        # Pick up already-created HTML, convert to PDF
        weasy_html_pathname = str(path_for_html)
        html_for_weasy = weasyHTML(filename=weasy_html_pathname)
        path_for_weasy = output_dir / Path(output_filename_base + ".pdf")
        html_for_weasy.write_pdf(path_for_weasy)
        debug_print(1, "Weasy done")


# This is a module-level global
prepared_output_dirs = []
prepared_output_dirs_for_rpa = []


def copy_supporting_files_to_output_dir(output_dirname, for_rpa=False):
    """
    Copy supporting files (icons, fonts) to the output directory.

    Necessary for Weasyprint, and for the HTML to display right.
    """
    # Copy the image files to the destination directory.
    # Necessary for weasyprint to work right!

    output_dir = Path(output_dirname)

    # Note!  If we do multiple timetables with output_subdir,
    # we would like to save trouble by caching the fact that we've done it.
    # for_rpa adds an extra file (a superset of the other version)
    global prepared_output_dirs_for_rpa
    global prepared_output_dirs
    if str(output_dir) in prepared_output_dirs_for_rpa:
        return
    if not for_rpa and str(output_dir) in prepared_output_dirs:
        return

    source_dir = Path(__file__).parent

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.samefile(source_dir, output_dir):
        debug_print(1, "Working in module directory, not copying fonts and icons")
        return

    icons_dir = output_dir / "icons"
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
    icon_filenames = ["accessible.svg", "inaccessible-ncn.svg", "baggage-ncn.svg"]
    if for_rpa:
        icon_filenames.append("rpa-logo.svg")
    for icon_filename in icon_filenames:
        icon_file_source_path = source_dir / "icons" / icon_filename
        icon_file_dest_path = icons_dir / icon_filename
        # Note, this overwrites
        shutil.copy2(icon_file_source_path, icon_file_dest_path)

    fonts_dir = output_dir / "fonts"
    if not os.path.exists(fonts_dir):
        os.makedirs(fonts_dir)
    # Each font has its own directory
    font_subdir_names = ["SpartanTT"]
    for font_subdir_name in font_subdir_names:
        font_subdir = fonts_dir / font_subdir_name
        if not os.path.exists(font_subdir):
            os.makedirs(font_subdir)
    # And font files within the directory
    font_filenames = ["SpartanTT/SpartanTT-Bold.ttf", "SpartanTT/SpartanTT-Medium.ttf"]
    for font_filename in font_filenames:
        font_file_source_path = source_dir / "fonts" / font_filename
        font_file_dest_path = fonts_dir / font_filename
        # Note, this overwrites
        shutil.copy2(font_file_source_path, font_file_dest_path)

    debug_print(1, "Fonts and icons copied to", output_dir)
    if for_rpa:
        prepared_output_dirs_for_rpa.append(str(output_dir))
    prepared_output_dirs.append(str(output_dir))
    return


##########################
#### NEW MAIN PROGRAM ####
##########################
if __name__ == "__main__":

    debug_print(3, "Dumping sys.path for clarity:", sys.path)

    my_arg_parser = make_tt_arg_parser()
    args = my_arg_parser.parse_args()

    set_debug_level(args.debug)

    output_dirname = args.output_dirname
    if not output_dirname:
        output_dirname = os.getenv("TIMETABLE_KIT_OUTPUT_DIR")
    if not output_dirname:
        output_dirname = "."
    debug_print(1, "Using output_dir", output_dirname)

    input_dirname = args.input_dirname
    if not input_dirname:
        input_dirname = os.getenv("TIMETABLE_KIT_INPUT_DIR")
    debug_print(1, "Using input_dir", input_dirname)

    gtfs_filename = args.gtfs_filename
    master_feed = initialize_feed(gtfs=gtfs_filename)

    author = args.author
    if not author:
        author = os.getenv("TIMETABLE_KIT_AUTHOR")
    if not author:
        author = os.getenv("AUTHOR")
    if not author:
        print("--author is mandatory!")
        sys.exit(1)

    command_line_reference_date = args.reference_date  # Does not default, may be None

    spec_file_list = args.tt_spec_files

    # Quick hack to speed up testing cycle:
    # implement this properly later TODO
    do_csv = False
    do_html = True
    do_pdf = True

    for spec_file in spec_file_list:
        debug_print(1, "Producing timetable for", spec_file)
        produce_timetable(
            do_csv=do_csv,
            do_html=do_html,
            do_pdf=do_pdf,
            master_feed=master_feed,
            author=author,
            command_line_reference_date=command_line_reference_date,
            input_dirname=input_dirname,
            spec_file=spec_file,
            output_dirname=output_dirname,
        )
        debug_print(1, "Done producing timetable for", spec_file)
    sys.exit(0)
