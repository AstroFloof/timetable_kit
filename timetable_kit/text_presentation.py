# text_presentation.py
# Part of timetable_kit
# Copyright 2021, 2022, 2023, 2024 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""Module for presenting small bits of text for the timetable.

This produces strings like "MoWeFr" and "Ar D11:49P". Some routines have HTML variants
and plaintext variants.

Most of the "character twiddling" operations are in here.  Some are in time.py and text_assembly.py.
"""
import pandas as pd

# These are mine
from timetable_kit.debug import debug_print
from timetable_kit.errors import InputError
from timetable_kit.icons import (
    get_baggage_icon_html,
    get_bus_icon_html,
    get_accessible_icon_html,
)
from timetable_kit.tsn import train_spec_to_tsn

# Time stuff
from timetable_kit.time import (
    TimeTuple,
    get_zonediff,
    explode_timestr,
    day_string,
    time_short_str_24,
    time_short_str_12,
)

# Safe version of <br>
from timetable_kit.text_assembly import SAFE_BR


# These work, but only at 120%.
thick_cell_substitution_map = {
    "blank": " ",
    "downarrow": '<div style="text-align: center; font-size: 120%;">&#x1f87b;</div>',
    "uparrow": '<div style="text-align: center; font-size: 120%;">&#x1f879;</div>',
    "rightarrow": '<div style="text-align: center; font-size: 120%;">&#x1f87a;</div>',
    "downrightarrow": '<div style="text-align: right; font-size: 120%;">&#x1f87e;</div>',
    "rightdownarrow": '<div style="text-align: left; font-size: 120%;">&#x1f87e;</div>',
    "uprightarrow": '<div style="text-align: right; font-size: 120%;">&#x1f87d;</div>',
    "rightuparrow": '<div style="text-align: left; font-size: 120%;">&#x1f87d;</div>',
}

# New, for the new version of SpartanTT
new_cell_substitution_map = {
    "blank": " ",
    "downarrow": '<div style="text-align: center; font-weight: bold;">&#x2193;</div>',
    "uparrow": '<div style="text-align: center; font-weight: bold;">&#x2191;</div>',
    "rightarrow": '<div style="text-align: center; font-weight: bold;">&#x2192;</div>',
    "downrightarrow": '<div style="text-align: right; font-weight: bold;">&#x2198;</div>',
    "rightdownarrow": '<div style="text-align: left; font-weight: bold;">&#x2198;</div>',
    "uprightarrow": '<div style="text-align: right; font-weight: bold;">&#x2197;</div>',
    "rightuparrow": '<div style="text-align: left; font-weight: bold;">&#x2197;</div>',
}


# Used with Noto arrows
# cell_substitution_map = thick_cell_substitution_map
# Used for Matt Bailey's new SpartanTT
cell_substitution_map = new_cell_substitution_map


def get_cell_substitution(cell_text: str) -> str | None:
    """Given special simple-substitution cell texts, provide the substitution.

    "blank" -> becomes a single space, for a white blank cell "downarrow" -> suitable
    downwards pointing arrow in HTML/Unicode "uparrow" -> suitable upwards pointing
    arrow in HTML/Unicode "downrightarrow" -> suitable downwards-then-right pointing
    arrow in HTML/Unicode "rightdownarrow" -> suitable right-then-down pointing arrow in
    HTML/Unicode "uprightarrow" -> suitable upwards-then-right pointing arrow in
    HTML/Unicode "rightuparrow" -> suitable right- then-up pointing arrow in
    HTML/Unicode "rightarrow" -> suitable right pointing arrow in HTML/Unicode

    Otherwise, return None.
    """
    cell_text = cell_text.strip()
    if cell_text not in cell_substitution_map:
        return None
    return cell_substitution_map[cell_text]


def get_rd_str(
    timepoint,
    doing_html=False,
    is_first_stop=False,
    is_last_stop=False,
    is_first_line=False,
    is_second_line=False,
    is_arrival_line=False,
    is_departure_line=False,
):
    """Return a single character (default " ") with receive-only / discharge- only
    annotation. "R" = Receive-only "D" = Discharge-only "L" = May leave early
    (unimplemented) "F" = Flag stop "*" = Not a regular passenger stop " " = Anything
    else.

    Subroutine of timepoint_str.

    doing_html determines whether to produce this letter as HTML (boldfaced) or not.
    is_first_stop suppresses the R for "receive only" is_last_stop suppresses the D for
    "discharge only"

    If you are producing a two-line string, is_first_line, is_second_line,
    is_arrival_line, and is_departure_line determine which line gets the letter (it
    looks ugly for both to get it). These should all be false when producing a one-line
    string.
    """
    # Important note: there's currently no way to identify the infamous "L",
    # which means the train or bus is allowed to depart ahead of time
    rd_str = " "  # NOTE the default is one blank space, for plaintext output.

    match [timepoint.drop_off_type, timepoint.pickup_type, "timepoint" in timepoint]:
        case [1, 0, _]:
            if not is_first_stop:  # This is obvious at the first station
                if not is_arrival_line:  # put on departure line
                    rd_str = "R"  # Receive passengers only
        case [0, 1, _]:
            if not is_last_stop:  # This is obvious at the last station
                if not is_departure_line:  # put on arrival line
                    rd_str = "D"  # Discharge passengers only
        case [1, 1, _]:
            if not is_second_line:  # it'll be on the first line
                rd_str = "*"  # Not for ordinary passengers (staff only, perhaps)
        case [2 | 3, _, _] | [_, 2 | 3, _]:
            if not is_second_line:  # it'll be on the first line
                rd_str = "F"  # Flag stop of some type
        case [_, _, True]:
            # If the "timepoint" column has been supplied
            # IMPORTANT NOTE: Amtrak has not implemented this yet.
            # FIXME: request that Alan Burnstine implement this if possible
            # This seems to be the only way to identify the infamous "L",
            # which means that the train or bus is allowed to depart ahead of time
            #
            # Obnoxiously, VIA Rail includes the column but it's blank,
            # which really means "all 1".  Handle this elsewhere!
            # print("timepoint column found")  # Should not happen with Amtrak data
            if timepoint.timepoint == 0:  # and it says times aren't exact
                print(
                    "Inexact timepoint found!"
                )  # Should not happen with Amtrak or VIA so far
                if not is_arrival_line:  # This goes on departure line, always
                    rd_str = "L"

    # Now: this is an utterly stupid hack used for HTML width testing:
    # Not for production code.  Enable if you need to recheck CSS span widths.
    # if (timepoint.stop_id=="CLF"):
    #    rd_str = "M"
    # if (timepoint.stop_id=="CVS"):
    #    rd_str = "M"

    if doing_html:
        if rd_str != " ":
            # Boldface it:
            rd_str = "".join(["<b>", rd_str, "</b>"])
        # Always wrap it in the span, even if it's a blank space:
        rd_str = "".join(['<span class="box-rd">', rd_str, "</span>"])
    return rd_str


baggage_box_prefix = '<span class="box-baggage">'
baggage_box_postfix = "</span>"


def get_baggage_str(doing_html=False):
    """Return a suitable string to indicate the presence of checked baggage.

    Currently, the HTML implementation references an external checked baggage icon.
    There are inline alternatives to this but Weasyprint isn't nice about them.
    """
    if not doing_html:
        return get_baggage_icon_html(doing_html=False)
    return "".join(
        [
            baggage_box_prefix,
            get_baggage_icon_html(doing_html=True),
            baggage_box_postfix,
        ]
    )


def get_blank_baggage_str(doing_html=False):
    """Return a suitable string to indicate the absence of checked baggage.

    The HTML implementation boxes it to line things up properly.
    """
    if not doing_html:
        return " "
    return "".join([baggage_box_prefix, baggage_box_postfix])


bus_box_prefix = '<span class="box-bus">'
bus_box_postfix = "</span>"


def get_bus_str(doing_html=False):
    """Return a suitable string to indicate that this is a bus.

    Currently, the HTML implementation references an external bus icon. There are inline
    alternatives to this but Weasyprint isn't nice about them.
    """
    if not doing_html:
        return get_bus_icon_html(doing_html=False)
    return "".join(
        [
            bus_box_prefix,
            get_bus_icon_html(doing_html=True),
            bus_box_postfix,
        ]
    )


def get_blank_bus_str(doing_html=False):
    """Return a suitable string to indicate that this is not a bus.

    The HTML implementation boxes it to line things up properly.
    """
    if not doing_html:
        return " "
    return "".join([bus_box_prefix, bus_box_postfix])


def timepoint_str(
    timepoint,
    stop_tz,
    agency_tz,
    reference_date,
    doing_html=False,
    box_time_characters=False,
    reverse=False,
    two_row=False,
    use_ar_dp_str=False,
    bold_pm=True,
    times_24h=False,
    use_daystring=False,
    long_days_box=False,
    short_days_box=False,
    calendar=None,
    is_first_stop=False,
    is_last_stop=False,
    use_baggage_icon=False,
    has_baggage=False,
    use_bus_icon=False,
    is_bus=False,
    no_rd=False,
):
    """Produces a text or HTML string for display in a timetable, showing the time of
    departure, arrival, and extra symbols.

    This is quite complex: I would have used tables-within-tables, but they're screen-reader-unfriendly.
    Trying to do it with fixed-width fonts was too ugly.

    So the the HTML version uses spans with inline-block layout.

    The CSS is elsewhere.

    The most excruciatingly complex variant looks like:
    Ar F 9:59P Daily
    Dp F10:00P WeFrSu

    Mandatory arguments:
    -- timepoint: a single row from stop_times.
    -- stop_tz: timezone for the stop
    -- agency_tz: timezone for the agency
    -- reference_date: reference date for time zone conversion (strictly speaking, needed only for Arizona)
    Options are many:
    -- two_row: This timepoint gets both arrival and departure rows (default is just one row)
    -- use_ar_dp_str: Use "Ar " and "Dp " or leave space for them (use only where appropriate)
    -- reverse: This piece of the timetable is running upward (departure time above arrival time)
    -- doing_html: output HTML (default is plaintext)
    -- box_time_characters: put each character in the time in an HTML box; default is False.
        For use with fonts which don't have tabular nums.  A nasty hack; best to use a font
        which does have tabular nums.
    -- times_24h: use 24-hour military time (default is 12 hour time with "A" and "P" suffix)
    -- bold_pm: make PM times bold (even in 24-hour time; only with doing_html)
    -- use_daystring: append a "MoWeFr" or "Daily" string.  Only used on infrequent services.
    -- long_days_box: Extra-long space for days, for SuMoTuWeTh five-day calendars.
    -- short_days_box: Extra-short space for days, for "Mo" one-day across-midnight trains.
    -- calendar: a calendar with a single row containing the correct calendar for the service.
           Required if use_daystring is True; pointless otherwise.
    -- is_first_stop: suppress "receive only" notation
    -- is_last_stop: suppress "discharge only" notation
    -- use_baggage_icon: True/False: leave space for baggage symbol
    -- has_baggage: True/False: does this stop have checked baggage?
        Ignored if use_baggage_icon is False.
    -- use_bus_icon: True/False: leave space for bus symbol
    -- is_bus: True/False: is this a bus?  Ignored if use_bus_icon is False.
    -- no_rd: Leave out the usual space for "R" or "D" notations. Used to save space.
    """

    if doing_html:
        linebreak = SAFE_BR
    else:
        linebreak = "\n"

    if not doing_html:
        box_time_characters = False

    # Pick function for the actual time printing
    if times_24h:
        time_str_func = time_short_str_24
    else:
        time_str_func = time_short_str_12

    zonediff = get_zonediff(stop_tz, agency_tz, reference_date)

    # Fill the TimeTuple and prep string for actual departure time
    if pd.isna(timepoint.departure_time):
        # Stupid finicky stuff for stops with *no specific time*
        # VIA Rail Winnipeg-Churchill has this
        departure_time_str = "---"
        is_pm = 0
    else:
        departure = explode_timestr(timepoint.departure_time, zonediff)
        departure_time_str = time_str_func(
            departure, box_time_characters=box_time_characters
        )
        is_pm = departure.pm
    if doing_html:
        if bold_pm and is_pm == 1:
            departure_time_str = "".join(["<b>", departure_time_str, "</b>"])
        if times_24h:
            departure_time_str = "".join(
                ['<span class="box-time24">', departure_time_str, "</span>"]
            )
        else:
            departure_time_str = "".join(
                ['<span class="box-time12">', departure_time_str, "</span>"]
            )

    # Fill the TimeTuple and prep string for actual time
    if pd.isna(timepoint.arrival_time):
        # Stupid finicky stuff for stops with *no specific time*
        # VIA Rail Winnipeg-Churchill has this
        arrival_time_str = "---"
        is_pm = 0
    else:
        arrival = explode_timestr(timepoint.arrival_time, zonediff)
        arrival_time_str = time_str_func(
            arrival, box_time_characters=box_time_characters
        )
        is_pm = arrival.pm
    if doing_html:
        if bold_pm and is_pm == 1:
            arrival_time_str = "".join(["<b>", arrival_time_str, "</b>"])
        if times_24h:
            arrival_time_str = "".join(
                ['<span class="box-time24">', arrival_time_str, "</span>"]
            )
        else:
            arrival_time_str = "".join(
                ['<span class="box-time12">', arrival_time_str, "</span>"]
            )

    # Need this for lines just containing "Ar" or "Dp"
    blank_rd_str = ""
    blank_time_str = ""
    if doing_html:
        blank_rd_str = "".join(['<span class="box-rd">', "", "</span>"])
        if times_24h:
            blank_time_str = "".join(['<span class="box-time24">', "", "</span>"])
        else:
            blank_time_str = "".join(['<span class="box-time12">', "", "</span>"])

    # Fill in the day strings, if we're using it
    departure_daystring = ""
    arrival_daystring = ""
    blank_daystring = ""
    if use_daystring:
        if long_days_box:
            days_box_class = "box-days-long"
        elif short_days_box:
            days_box_class = "box-days-short"
        else:
            days_box_class = "box-days"
        # Note that daystring is VARIABLE LENGTH, and is the only variable-length field
        # It must be last and the entire time field must be left-justified as a result
        if pd.isna(timepoint.departure_time):
            # No specified time
            departure_daystring = ""
        else:
            departure_daystring = day_string(calendar, offset=departure.day)
        if pd.isna(timepoint.arrival_time):
            # No specified time
            arrival_daystring = ""
        else:
            arrival_daystring = day_string(calendar, offset=arrival.day)
        if doing_html:
            departure_daystring = "".join(
                ['<span class="', days_box_class, '">', departure_daystring, "</span>"]
            )
            arrival_daystring = "".join(
                ['<span class="', days_box_class, '">', arrival_daystring, "</span>"]
            )
            blank_daystring = "".join(
                ['<span class="', days_box_class, '">', "", "</span>"]
            )
        else:
            # Add a necessary spacer: CSS does it for us in HTML
            departure_daystring = "".join([" ", departure_daystring])
            arrival_daystring = "".join([" ", arrival_daystring])
            blank_daystring = ""

    ar_str = ""  # If we are not adding the padding at all -- unwise with two_row
    dp_str = ""  # Again, if we are not adding the "Ar/Dp" at all
    if use_ar_dp_str:
        if doing_html:
            # I'd like to make this read better in screen readers,
            # but there is no clean way to do it.  FIXME.
            ar_str = '<span class="box-ardp">Ar</span>'
            dp_str = '<span class="box-ardp">Dp</span>'
        else:
            ar_str = "Ar "
            dp_str = "Dp "
            ardp_spacer = "   "

    # Determine whether we are looking at receive-only or discharge-only
    receive_only = False
    discharge_only = False
    if is_first_stop:
        receive_only = True
        # Logically speaking
    if is_last_stop:
        discharge_only = True
        # Logically speaking
    if timepoint.drop_off_type == 1 and timepoint.pickup_type == 0:
        receive_only = True
    elif timepoint.pickup_type == 1 and timepoint.drop_off_type == 0:
        discharge_only = True

    # One-row version: easier logic.  Returns early.
    if not two_row:
        rd_str = get_rd_str(
            timepoint,
            doing_html=doing_html,
            is_first_stop=is_first_stop,
            is_last_stop=is_last_stop,
        )

        ar_dp_str = ""  # If we are not adding the padding at all
        if use_ar_dp_str:
            if not doing_html:  # HTML spaces this using the boxes
                ar_dp_str = ardp_spacer  # Two spaces, like "Ar", on most stops
        if is_first_stop:
            ar_dp_str = dp_str  # Mark departure on first stop
        elif is_last_stop:
            ar_dp_str = ar_str  # Mark arrival on last stop

        if not use_baggage_icon:
            baggage_str = ""
        elif has_baggage:
            baggage_str = get_baggage_str(doing_html=doing_html)
        else:
            baggage_str = get_blank_baggage_str(doing_html=doing_html)

        # The bus string is dependent only on the train number.
        if not use_bus_icon:
            bus_str = ""
        elif is_bus:
            bus_str = get_bus_str(doing_html=doing_html)
        else:
            bus_str = get_blank_bus_str(doing_html=doing_html)

        # Each element joined herein includes HTML annotations, and is completely blank if unused
        complete_line_str = "".join(
            [
                ar_dp_str,
                "" if no_rd else rd_str,
                arrival_time_str if discharge_only else departure_time_str,
                arrival_daystring if discharge_only else departure_daystring,
                baggage_str,
                bus_str,
            ]
        )
        return complete_line_str

    # Two row version follows:
    else:  # two_row
        # Special handling for two-row stations with no dwell
        no_dwell = False
        if timepoint.departure_time == timepoint.arrival_time:
            no_dwell = True

        # Put baggage_str on line one, leave line two blank
        if not use_baggage_icon:
            arrival_baggage_str = ""
            departure_baggage_str = ""
            blank_baggage_str = ""
        else:
            blank_baggage_str = get_blank_baggage_str(doing_html=doing_html)
            departure_baggage_str = blank_baggage_str
            arrival_baggage_str = blank_baggage_str
            if has_baggage:
                if receive_only or (no_dwell and not discharge_only):
                    # On the only printed line
                    departure_baggage_str = get_baggage_str(doing_html=doing_html)
                elif discharge_only:
                    # On the only printed line
                    arrival_baggage_str = get_baggage_str(doing_html=doing_html)
                elif reverse:
                    # On the first of two printed lines
                    departure_baggage_str = get_baggage_str(doing_html=doing_html)
                else:
                    # On the first of two printed lines
                    arrival_baggage_str = get_baggage_str(doing_html=doing_html)

        # Put bus_str on line one, leave line two blank
        if not use_bus_icon:
            arrival_bus_str = ""
            departure_bus_str = ""
            blank_bus_str = ""
        else:
            blank_bus_str = get_blank_bus_str(doing_html=doing_html)
            departure_bus_str = blank_bus_str
            arrival_bus_str = blank_bus_str
            if is_bus:
                if receive_only or (no_dwell and not discharge_only):
                    # On the only printed line
                    departure_bus_str = get_bus_str(doing_html=doing_html)
                elif discharge_only:
                    # On the only printed line
                    arrival_bus_str = get_bus_str(doing_html=doing_html)
                elif reverse:
                    # On the first of two printed lines
                    departure_bus_str = get_bus_str(doing_html=doing_html)
                else:
                    # On the first of two printed lines
                    arrival_bus_str = get_bus_str(doing_html=doing_html)

        # Start assembling the two lines.
        if is_first_stop:
            # Don't include the "Ar" on a specified is_first_stop two_row.
            # On these, the full ArDp is probably present somewhere else;
            # just do the Dp.
            arrival_line_str = ""
        elif receive_only or (no_dwell and not discharge_only):
            # This just prints the "Ar" but does the alignment (hopefully)
            arrival_line_str = "".join(
                [
                    ar_str,
                    "" if no_rd else blank_rd_str,
                    blank_time_str,
                    blank_daystring,
                    blank_baggage_str,
                    blank_bus_str,
                ]
            )
        else:
            arrival_rd_str = get_rd_str(
                timepoint,
                doing_html=doing_html,
                is_first_stop=is_first_stop,
                is_last_stop=is_last_stop,
                is_first_line=(not reverse),  # arrival is first unless reversing
                is_second_line=reverse,
                is_arrival_line=True,
            )
            arrival_line_str = "".join(
                [
                    ar_str,
                    "" if no_rd else arrival_rd_str,
                    arrival_time_str,
                    arrival_daystring,
                    arrival_baggage_str,
                    arrival_bus_str,
                ]
            )
        if is_last_stop:
            # Don't include the "Dp" on a specified is_first_stop two_row.
            # On these, the full ArDp is probably present somewhere else;
            # just do the Ar.
            departure_line_str = ""
        elif discharge_only:
            # This just prints the "Dp" but does the alignment (hopefully)
            departure_line_str = "".join(
                [
                    dp_str,
                    "" if no_rd else blank_rd_str,
                    blank_time_str,
                    blank_daystring,
                    blank_baggage_str,
                    blank_bus_str,
                ]
            )
        else:
            departure_rd_str = get_rd_str(
                timepoint,
                doing_html=doing_html,
                is_first_stop=is_first_stop,
                is_last_stop=is_last_stop,
                is_second_line=reverse,  # departure is second unless reversing
                is_first_line=(not reverse),
                is_departure_line=True,
            )
            departure_line_str = "".join(
                [
                    dp_str,
                    "" if no_rd else departure_rd_str,
                    departure_time_str,
                    departure_daystring,
                    departure_baggage_str,
                    departure_bus_str,
                ]
            )

        # Patch the two rows together.
        if not reverse:
            complete_line_str = linebreak.join([arrival_line_str, departure_line_str])
        else:  # reverse
            complete_line_str = linebreak.join([departure_line_str, arrival_line_str])
        return complete_line_str

    # We should not reach here; we should have returned earlier.
    assert False


# Used for get_time_column_header
# This is the *complete* list of valid GTFS codes
# Amtrak only uses 2 and 3, but why not?
route_number_prefix_map = {
    1: "Tram #",
    2: "Train #",
    3: "Bus #",
    4: "Ferry #",
    5: "Cable Car #",
    6: "Gondola #",
    7: "Funicular #",
    11: "Trolleybus #",
    12: "Monorail Train #",
}


def get_time_column_header(
    train_specs: list[str],
    route_from_train_spec,
    doing_html=False,
    train_numbers_side_by_side=False,
) -> str:
    """Return the header for a column of times.

    train_specs: should be a list of train_specs (ordered).

    Each train_spec is a trip_short_name, possibly followed by a space and a lowercase day of the week.  Possibly followed by " noheader".

    route_from_train_spec: function taking train_spec and giving a route row from the GTFS routes table.
    train_numbers_side_by_side: List train numbers with a slash instead of on top of each other.
    """
    if not train_specs:
        raise InputError("No train_specs?")

    # Strip the "noheader" train specs; we don't mention them.
    fewer_train_specs = [ts for ts in train_specs if not ts.endswith("noheader")]

    # It's OK if stripping noheader train specs leads to no header.
    # In this case return blank.  Uniqueness of headers is handled later.
    if not fewer_train_specs:
        return ""

    if not doing_html:
        # For plaintext, keep it simple: just the train specs
        return " / ".join(fewer_train_specs)

    if train_numbers_side_by_side:
        # Old algorithm.  For Empire Builder, Lake Shore Limited.

        # Strip the " monday" type suffixes
        tsns = [train_spec_to_tsn(train_spec) for train_spec in fewer_train_specs]

        # For HTML, let's get FANCY... May change this later.
        # Route types: 2 is a train, 3 is a bus
        route_types = [
            int(route_from_train_spec(train_spec).route_type)
            for train_spec in fewer_train_specs
        ]
        match route_types:
            case [2]:
                time_column_prefix = "Train #"
            case [3]:
                time_column_prefix = "Bus #"
            case [3, 2]:
                time_column_prefix = "Bus/Train #s"
            case [2, 3]:
                time_column_prefix = "Train/Bus #s"
            case _:
                route_set = set(route_types)
                if route_set == {2}:
                    time_column_prefix = "Train #s"
                elif route_set == {3}:
                    time_column_prefix = "Bus #s"
                elif route_set == {2, 3}:
                    # This is three or more routes in the same column, yeechburgers
                    time_column_prefix = "Train/Bus #s"
                else:
                    # Not train or bus.  Does not occur on Amtrak.
                    time_column_prefix = "Trip #s"

        time_column_header = "".join(
            [
                "<small>",
                time_column_prefix,
                "</small>",
                SAFE_BR,
                "<strong>",
                " / ".join(tsns),  # Note! Works cleanly for single-element case
                "</strong>",
            ]
        )
        return time_column_header

    # New algorithm.
    # Numbers are stacked.
    # Putting slashes between the train and bus number has proven to make
    # overly-wide columns.  Aaargh!

    prefixed_route_numbers = [
        "".join(
            [
                "<small>",
                route_number_prefix_map[
                    int(route_from_train_spec(train_spec).route_type)
                ],
                "</small>",
                SAFE_BR,
                "<strong>",
                # Strip the " monday" type suffix
                # Special for CTrail: clean off the "CTrail" prefix
                # This is hacky; FIXME
                train_spec_to_tsn(train_spec).removeprefix("CTrail "),
                "</strong>",
            ]
        )
        for train_spec in fewer_train_specs
    ]
    time_column_header = "<hr>".join(prefixed_route_numbers)
    return time_column_header


def get_station_column_header(doing_html=False):
    """Return the header for a column of station names.

    Currently just the word "Station".
    """
    return "Station"

def get_mile_column_header(doing_html=False):
    """Return the header for a column of mileage integers.

    Currently just the word "Mile".
    """
    if doing_html:
        return '<div class="mile-header-text">Mile</div>'
    else:
        return "Mile"


def get_services_column_header(doing_html=False):
    """Return the header for a column of station services icons.

    Tricky because the column should be very narrow. Wraps with a special CSS div, so it
    can be rotated.
    """
    if doing_html:
        return '<div class="services-header-text">Station' + SAFE_BR + "Services</div>"
    else:
        return "Services"


def get_access_column_header(doing_html=False):
    """Return the header for a column of accessibility icons.

    Tricky because the column should be very narrow.

    Use the wheelchair icon. Wraps with a special CSS div, so it can be rotated.
    """
    if doing_html:
        accessible_icon_html = get_accessible_icon_html(doing_html=doing_html)
        return "".join(
            ['<div class="access-header-text">', " ", accessible_icon_html, "</div>"]
        )
    else:
        # Spell this one out for CSV production.
        return "Access"


def get_timezone_column_header(doing_html=False):
    """Return the header for a column of station time zones.

    Tricky because the column should be very narrow. Wraps with a special CSS div, so it
    can be rotated.
    """
    if doing_html:
        # return '<div class="timezone-header-text">Time' + SAFE_BR + 'Zone</div>'
        # Keep it one line, space is at a premium
        return '<div class="timezone-header-text">TZ</div>'
    else:
        return "Time Zone"


def style_route_name_for_column(route_name, doing_html=False):
    """Style a route name for HTML (or not) for a column header.

    This is largely a matter of whitespace.  And quite tricky.
    """
    if not doing_html:
        return route_name

    # "Route name words" / "Route name lines"
    rnw = route_name.split()
    debug_print(2, rnw)
    # Most VIA Rail route names are "City - City"
    if "-" in rnw:
        # Here, don't break the city names, do put one on top of the other
        rnw = route_name.split(" - ")
        # Should give us a length-two list, with both strings being
        # 4 or more characters, so will pass the next two tests
    # The following works well for Amtrak:
    # If four words, combine last two if one is really short
    if len(rnw) >= 4:
        if len(rnw[2]) <= 3 or len(rnw[3]) <= 3:
            rnw = [rnw[0], rnw[1], "".join([rnw[2], " ", rnw[3]]), *rnw[4:]]
    # Combine first two words if one is really short
    if len(rnw) >= 2:
        if len(rnw[0]) <= 3 or len(rnw[1]) <= 3:
            rnw = ["".join([rnw[0], " ", rnw[1]]), *rnw[2:]]

    linebroken_str = SAFE_BR.join(rnw)
    final_str = "".join(['<div class="box-route-name">', linebroken_str, "</div>"])
    return final_str


def style_updown(reverse: bool, doing_html=False) -> str:
    """Style "Read Up" or "Read Down" column subheader."""
    if reverse:
        text = "Read Up"
    else:
        text = "Read Down"

    if not doing_html:
        return text

    # doing_html

    # The added arrows are nice, but...
    # Silver Service doesn't have enough room for the arrows.
    # Have to flag this off of the aux / .toml file.
    using_arrows = False
    if doing_html and using_arrows:
        if reverse:
            arrow = "&#x2191;"  # Up arrow in SpartanTT font
        else:
            arrow = "&#x2193;"  # Down arrow in SpartanTT font
        # Put arrows on right and left, with spaces
        text = " ".join([arrow, text, arrow])

    text = "".join(["<b>", text, "</b>"])
    return text


def get_origin_destination_spacer(doing_html: bool) -> str:
    """Return an appropriate spacer to keep an 'origin' or 'destination' row the right height."""
    if not doing_html:
        return ""
    # Origin and destination are two lines; attempt to force this
    return "".join(["&nbsp;", SAFE_BR, "&nbsp;"])
