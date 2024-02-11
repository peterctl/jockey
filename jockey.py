#!/bin/python3
# Jockey is a CLI utility that facilitates quick retrieval of Juju objects that
# match given filters.
# Author: Connor Chamberlain

import argparse
import json
import re
from enum import Enum
from typing import Any, Dict, NamedTuple, Generator, Optional, List, Tuple

from status_keeper import (
    retrieve_juju_cache,
    cache_juju_status,
    read_local_juju_status_file,
)


JujuStatus = Dict[str, Any]


class FilterMode(Enum):
    EQUALS = "="
    NOT_EQUALS = "!="
    CONTAINS = "~"
    NOT_CONTAINS = "!~"


class ObjectType(Enum):
    CHARM = ("charms", "charm", "c")
    APP = ("app", "apps", "application", "applications", "a")
    UNIT = ("units", "unit", "u")
    MACHINE = ("machines", "machine", "m")
    IP = ("address", "addresses", "ips", "ip", "i")
    HOSTNAME = ("hostnames", "hostname", "host", "hosts", "h")


def pretty_print_keys(data: JujuStatus, depth: int = 1) -> None:
    """Print a dictionary's keys in a heirarchy."""
    if depth < 1:
        return

    for key, value in data.items():
        print(" |" * depth + key)

        if isinstance(value, dict):
            pretty_print_keys(data[key], depth=depth - 1)


def convert_object_abbreviation(abbrev: str) -> Optional[ObjectType]:
    """
    Convert an object type abbreviation into an ObjectType.  If the abbreviation
    is not a valid Juju object, None will be returned.

    Arguments
    =========
    abbrev (str)
        A possibly abbreviated object name.

    Returns
    =======
    object_type (ObjectType) [optional]
        The ObjectType corresponding with the given abbrevation, if any.
    """
    abbrev = abbrev.lower()
    return next(
        (obj_type for obj_type in ObjectType if abbrev in obj_type.value), None
    )


def parse_filter_string(
    filter_str: str,
) -> Tuple[str, FilterMode, str]:
    """
    Parse a filter string down into its object type, filter mode, and content.

    Arguments
    =========
    filter_str (str)
        The filter string.

    Returns
    =======
    object_type (str)
        The object type of the filter.  May be "charm", "application", "unit",
        "machine", "ip", or "hostname".
    mode (FilterMode)
        FilterMode of the filter.
    content (str)
        Content of the filter string, which may be any string that doesn't
        include blacklisted characters.
    """

    filter_code_pattern = re.compile(r"[=!~]+")

    filter_codes = filter_code_pattern.findall(filter_str)
    assert len(filter_codes) == 1, "Incorrect number of filter codes detected."

    match = filter_code_pattern.search(filter_str)

    object_type = convert_object_abbreviation(filter_str[: match.start()])
    assert object_type, "Invalid object type detected in filter string."

    filter_mode = next(
        (mode for mode in FilterMode if mode.value == match.group()), None
    )
    assert filter_mode, f"Invalid filter mode detected: {match.group()}."

    content = filter_str[match.end() :]
    assert content, "Empty content detected in filter string."

    char_blacklist = ("_", ":", ";", "\\", "\t", "\n", ",")
    assert not any(
        char in char_blacklist for char in content
    ), "Blacklisted characters detected in filter string content."

    return object_type, filter_mode, content


def is_app_principal(status: JujuStatus, app_name: str) -> bool:
    """
    Test if a given application is principal.  True indicates principal and
    False indicates subordinate.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    app_name (str)
        The name of the application to check.

    Returns
    =======
    is_principal (bool)
        Whether the indicated application is principal.
    """
    return "subordinate-to" not in status["applications"][app_name]


def get_principal_unit_for_subordinate(
    status: JujuStatus, unit_name: str
) -> str:
    """Get the name of a princpal unit for a given subordinate unit."""
    for app, data in status["applications"].items():

        # Skip other subordinate applications
        if not is_app_principal(status, app):
            continue

        # Check if given unit is a subordinate of any of these units
        for unit, unit_data in data["units"].items():
            if unit_name in unit_data["subordinates"]:
                return unit

    return ""


def get_applications(status: JujuStatus) -> Generator[str, None, None]:
    """
    Get all applications in the Juju status by name.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    application_names (Generator[str])
        All application names, in no particular order, as a generator.
    """
    for app in status["applications"]:
        yield app


def get_charms(status: JujuStatus) -> Generator[str, None, None]:
    """
    Get all charms in the Juju status by name.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    charm_names (Generator[str])
        All charms names, in no particular order, as a generator.
    """
    for app in get_applications(status):
        yield status["applications"][app]["charm"]


def get_units(status: JujuStatus) -> Generator[str, None, None]:
    """
    Get all units in the Juju status by name.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    unit_names (Generator[str])
        All unit names, in no particular order, as a generator.
    """
    for app in get_applications(status):

        # Skip subordinate applicaitons
        if not is_app_principal(status, app):
            continue

        for unit_name, data in status["applications"][app]["units"].items():
            # Generate principal unit
            yield unit_name

            # Check if subordinate units exist
            if "subordinates" not in data:
                continue

            # Generate subordinate units
            for subordinate_unit_name in data["subordinates"]:
                yield subordinate_unit_name


def get_machines(status: JujuStatus) -> Generator[str, None, None]:
    """
    Get all machines in the Juju model by index.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    machine_ids (Generator[str])
        All machine indices, in no particular order, as a generator.
    """
    for id in status["machines"].keys():
        yield id


def get_hostnames(status: JujuStatus) -> Generator[str, None, None]:
    """
    Get all machine hostnames in the Juju model.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    hostnames (Generator[str])
        All hostnames, in no particular order, as a generator.
    """
    for machine in status["machines"]:
        yield machine["hostname"]


def get_ips(status: JujuStatus) -> Generator[str, None, None]:
    """
    Get all machine ips in the Juju model.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    ips (Generator[str])
        All ips, in no particular order, as a generator.
    """
    for machine in status["machines"]:
        for address in machine["ip-addresses"]:
            yield address


def charm_to_applications(
    status: JujuStatus, charm_name: str
) -> Generator[str, None, None]:
    """
    Given a charm name, get all applications using it, as a generator. If no
    matching charm is found, the generator will be empty.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    charm_name (str)
        The name of the charm to find applications for.


    Returns
    =======
    applications (Generator[str])
        All applications that match the given charm name.
    """
    for application in status["applications"]:
        if application["charm"] == charm_name:
            yield application


def application_to_charm(status: JujuStatus, app_name: str) -> Optional[str]:
    """
    Given an application name, get the charm it is using, if any.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    app_name (str)
        The name of the applicaiton to find a charm for.

    Returns
    =======
    charm (str) [optional]
        The name of the charm, if the indicated application exists.
    """
    try:
        return status["applications"][app_name]["charm"]
    except KeyError:
        return


def application_to_units(
    status: JujuStatus, app_name: str
) -> Generator[str, None, None]:
    """
    Given an application name, get all of its untis, as a generator.  If no
    matching application is found, the generator will be empty.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    app_name (str)
        The name of the applicaiton to find a units for.

    Returns
    =======
    units (Generator[str])
        All units of the given application.
    """
    for application, data in status["applications"].items():

        if application != app_name:
            continue

        for unit_name in application["units"].keys():
            yield unit_name


def unit_to_application(status: JujuStatus, unit_name: str) -> Optional[str]:
    """
    Given a unit name, get its application name.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    unit_name (str)
        The name of the unit to find an application for.

    Returns
    =======
    application (str) [optional]
        The name of the corresponding application.
    """
    app_name = unit_name.split("/")[0]

    if app_name in status["applications"]:
        return app_name


def unit_to_machine(status: JujuStatus, unit_name: str) -> Optional[str]:
    """
    Given a unit name, get the ID of the machine it is running on, if any.
    Currently only works on units from principal applications.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    unit_name (str)
        The name of the unit.

    Returns
    =======
    machine_id (str) [optional]
        The ID of the corresponding machine.
    """
    app = unit_to_application(status, unit_name)

    if not is_app_principal(status, app):
        # TODO write a subordinate_to_principal function to get principal units
        raise NotImplemented

    return status["applications"][app]["units"][unit_name]["machine"]


def machine_to_units(
    status: JujuStatus, machine: str
) -> Generator[str, None, None]:
    """
    Given an machine id, get all of its units, as a generator.  If no matching
    units are found, the generator will be empty.

    Arguments
    =========
    machine (str)
        The ID of the machine to use.

    Returns
    =======
    units (Generator[str])
        All units on the given machine.
    """

    for unit in get_units(status):

        # Skip subordinate units
        app = unit_to_application(status, unit)
        if not is_app_principal(status, app):
            continue

        if unit_to_machine(status, unit) == machine:
            yield unit

            for subordinate_unit in status["applications"][app]["units"][unit][
                "subordinates"
            ]:
                yield subordinate_unit


def machine_to_ips(
    status: JujuStatus, machine: str
) -> Generator[str, None, None]:
    """
    Given an machine id, each of its IP addresses as a geneator.

    Arguments
    =========
    machine (str)
        The ID of the machine to use.

    Returns
    =======
    addresses (Generator[str])
        The IP addresses of the machine.
    """
    for ip in status["machines"][machine]["ip-addresses"]:
        yield ip


def ip_to_machine(status: JujuStatus, ip: str) -> str:
    """
    Given an ip, get the ID of the machine that owns it.

    Arguments
    =========
    address (str)
        The IP address in question.

    Returns
    =======
    machine ID (str)
        ID of the machine owning the given IP.
    """
    for machine in status["machines"]:
        if ip in status["machines"][machine]["ip-addresses"]:
            return machine


def machine_to_hostname(status: JujuStatus, machine: str) -> str:
    """
    Given an machine id, get its hostname.

    Arguments
    =========
    machine (str)
        The ID of the machine to use.

    Returns
    =======
    hostname (str)
        The machine's hostname.
    """
    return status["machines"][machine]["hostname"]


def hostname_to_machine(status: JujuStatus, hostname: str) -> str:
    """
    Given a hostname, get that machine's ID.

    Arguments
    =========
    hostname (str)
        The machine's hostname.

    Returns
    =======
    machine (str)
        The ID of the machine with the given hostname.
    """
    for machine in get_machines(status):
        if status["machines"][machine]["hostname"] == hostname:
            return machine


def main(args: argparse.Namespace):
    # Perform any requested cache refresh
    if args.refresh:
        cache_juju_status()

    # Get status
    status = (
        retrieve_juju_cache()
        if not args.file
        else read_local_juju_status_file(args.file)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Jockey - All your Juju objects at your fingertips."
    )

    # Add cache refresh flag
    parser.add_argument(
        "--refresh", action="store_true", help="Force a cache update"
    )

    # Add object type argument
    objectparser = parser.add_mutually_exclusive_group(required=True)
    objectparser.add_argument(
        "object",
        choices=[
            abbrev for object_type in ObjectType for abbrev in object_type.value
        ],
        nargs="?",
        help="Choose an object type to seek",
    )

    # Add filters as positional arguments
    filters_help = (
        "Specify filters for the query. Each filter should be in the format"
        "`key operator value`. Supported operators: = != ~."
        "For example:"
        "  app=nova-compute hostname~ubun"
    )
    parser.add_argument(
        "filters", type=parse_filter_string, nargs="*", help=filters_help
    )

    # Optional import from a json file
    parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        help="Use a local Juju status JSON file",
    )

    args = parser.parse_args()
    main(args)
