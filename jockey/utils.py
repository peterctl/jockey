import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generator, Optional, List
from jockey.juju_types import ObjectType


def print_table(objs: List[Any], columns: List[str], headers: bool = True):
    # Check max size for each column
    col_lens: Dict[str, int] = { col: len(col) for col in columns }
    for obj in objs:
        for col in columns:
            col_len = len(str(getattr(obj, col)))
            if col_len > col_lens.get(col, 0):
                col_lens[col] = col_len

    # Display the headers
    if headers:
        for col in columns:
            print(col.upper().ljust(col_lens[col] + 2), end="")
        print()

    # Display each row
    for obj in objs:
        for col in columns:
            print(str(getattr(obj, col)).ljust(col_lens[col] + 2), end="")
        print()

JujuStatus = Dict[str, Any]


class FilterMode(Enum):
    EQUALS = "="
    CONTAINS = "~"
    NOT_EQUALS = "^="
    NOT_CONTAINS = "^~"


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


@dataclass
class JockeyFilter:
    obj_type: ObjectType
    mode: FilterMode
    content: str


def parse_filter_string(
    filter_str: str,
) -> JockeyFilter:
    """
    Parse a filter string down into its object type, filter mode, and content.

    Arguments
    =========
    filter_str (str)
        The filter string.

    Returns
    =======
    jockey_filter (JockeyFilter)
        The constructed JockeyFilter object
    """

    filter_code_pattern = re.compile(r"[=^~]+")

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

    return JockeyFilter(obj_type=object_type, mode=filter_mode, content=content)


def check_filter_match(jockey_filter: JockeyFilter, value: str) -> bool:
    """
    Check if a value satisfied a Jockey filter.

    Arguments
    =========
    jockey_filter (JockeyFilter)
        A single Jockey filter
    value (str)
        A string to test against the filter

    Returns
    =======
    is_match (bool)
        True if value satisfies jockey_filter, else False
    """
    filter_map = {
        FilterMode.EQUALS: lambda c, v: c == v,
        FilterMode.NOT_EQUALS: lambda c, v: c != v,
        FilterMode.CONTAINS: lambda c, v: c in v,
        FilterMode.NOT_CONTAINS: lambda c, v: c not in v,
    }
    action = filter_map[jockey_filter.mode]
    return action(jockey_filter.content, value)


def pretty_print_keys(data: JujuStatus, depth: int = 1) -> None:
    """Print a dictionary's keys in a heirarchy."""
    if depth < 1:
        return

    for key, value in data.items():
        print(" |" * depth + key)

        if isinstance(value, dict):
            pretty_print_keys(data[key], depth=depth - 1)


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


def subordinate_unit_to_principal_unit(
    status: JujuStatus, unit_name: str
) -> str:
    """
    Given a unit name, get its principal unit.  If the given unit is principal,
    it will be returned as-is.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.

    Returns
    =======
    unit_name (str)
        The name of the unit to check.
    """
    app = unit_to_application(status, unit_name)
    app_data = status["applications"]

    if is_app_principal(status, app):
        return unit_name

    for p_app in app_data[app]["subordinate-to"]:

        if not is_app_principal(status, p_app):
            continue

        for p_unit in app_data[p_app]["units"]:
            if unit_name in app_data[p_app]["units"][p_unit]["subordinates"]:
                return p_unit


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
    principal_unit_name = subordinate_unit_to_principal_unit(status, unit_name)
    app = unit_to_application(status, principal_unit_name)

    return status["applications"][app]["units"][principal_unit_name]["machine"]


def machine_to_units(
    status: JujuStatus, machine: str
) -> Generator[str, None, None]:
    """
    Given an machine id, get all of its units, as a generator.  If no matching
    units are found, the generator will be empty.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
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
    status (JujuStatus)
        The current Juju status in json format.
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
    status (JujuStatus)
        The current Juju status in json format.
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
    status (JujuStatus)
        The current Juju status in json format.
    machine (str)
        The ID of the machine to use.

    Returns
    =======
    hostname (str)
        The machine's hostname.
    """
    if "lxd" in machine:
        physical_machine, _, container_id = machine.split("/")
        return status["machines"][physical_machine]["containers"][machine][
            "hostname"
        ]
    return status["machines"][machine]["hostname"]


def hostname_to_machine(status: JujuStatus, hostname: str) -> str:
    """
    Given a hostname, get that machine's ID.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
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


def filter_units(
    status: JujuStatus, filters: List[JockeyFilter]
) -> Generator[str, None, None]:
    """
    Get all units from a Juju status that match a list of filters.

    Arguments
    =========
    status (JujuStatus)
        The current Juju status in json format.
    filters (List[JockeyFilter])
        A list of parsed filters, provided to the CLI.

    Returns
    =======
    units (Generator[str])
        All matching units, as a generator.
    """

    charm_filters = [f for f in filters if f.obj_type == ObjectType.CHARM]
    app_filters = [f for f in filters if f.obj_type == ObjectType.APP]
    unit_filters = [f for f in filters if f.obj_type == ObjectType.UNIT]
    machine_filters = [f for f in filters if f.obj_type == ObjectType.MACHINE]
    ip_filters = [f for f in filters if f.obj_type == ObjectType.IP]
    hostname_filters = [f for f in filters if f.obj_type == ObjectType.HOSTNAME]

    for unit in get_units(status):
        # Check unit filters
        if not all(
            check_filter_match(u_filter, unit) for u_filter in unit_filters
        ):
            continue

        if app_filters or charm_filters:
            # Check application filters
            app = unit_to_application(status, unit)
            if not all(
                check_filter_match(a_filter, app) for a_filter in app_filters
            ):
                continue

            # Check charm filters
            charm = application_to_charm(status, app)
            if not all(
                check_filter_match(c_filter, charm)
                for c_filter in charm_filters
            ):
                continue

        # If there aren't any machine, IP, or hostname filters, just yield
        if not any((machine_filters, ip_filters, hostname_filters)):
            yield unit
            continue

        # pdb.set_trace()
        # Check machine filters
        machine = unit_to_machine(status, unit)
        if not all(
            check_filter_match(m_filter, machine)
            for m_filter in machine_filters
        ):
            continue

        # Check hostname filters
        hostname = machine_to_hostname(status, machine)
        if not all(
            check_filter_match(h_filter, hostname)
            for h_filter in hostname_filters
        ):
            continue

        # Check IP filters
        ips = machine_to_ips(status, machine)
        if not all(
            any(check_filter_match(i_filter, ip) for ip in ips)
            for i_filter in ip_filters
        ):
            continue

        yield unit
