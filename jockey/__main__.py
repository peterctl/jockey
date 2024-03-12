#!/bin/python3

# Jockey is a CLI utility that facilitates quick retrieval of Juju objects that
# match given filters.
# Author: Connor Chamberlain

import pdb
import argparse
import json
from jockey import collectors, filters, juju_types, status_keeper
from jockey.utils import print_table


def main(args: argparse.Namespace):
    # Perform any requested cache refresh
    if args.refresh:
        status_keeper.cache_juju_status()

    # Get status
    if args.file:
        status = json.load(args.file)
    else:
        status = status_keeper.get_juju_status()

    if args.object in juju_types.ObjectType.APP.value:
        objects = collectors.get_applications(status)
        headers = juju_types.Application.__annotations__.keys()
    elif args.object in juju_types.ObjectType.MACHINE.value:
        objects = collectors.get_machines(status)
        headers = juju_types.Machine.__annotations__.keys()
    elif args.object in juju_types.ObjectType.UNIT.value:
        objects = collectors.get_units(status)
        headers = juju_types.Unit.__annotations__.keys()
    else:
        raise KeyError(f"Unknown object type: {args.object}")

    filtered_objects = [obj for obj in objects if all([f(obj) for f in args.filters])]
    print_table(filtered_objects, columns=args.columns or headers, headers=True)


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Jockey - All your Juju objects at your fingertips."
    )

    # Add cache refresh flag
    parser.add_argument(
        "--refresh", action="store_true", help="Force a cache update"
    )

    # Add object type argument
    parser.add_argument(
        "object",
        choices=[
            abbrev for object_type in juju_types.ObjectType for abbrev in object_type.value
        ],
        nargs="?",
        help="Choose an object type to seek",
    )

    # Add filters as positional arguments
    filters_help = (
        "Specify filters for the query. Each filter should be in the format"
        "`key operator value`. Supported operators: = != ~."
        "For example:"
        "  app==nova-compute hostname~ubun"
    )
    parser.add_argument(
        "filters", type=filters.parse_filter, nargs="*", help=filters_help
    )

    # Optional import from a json file
    parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        help="Use a local Juju status JSON file",
    )

    parser.add_argument(
        "-c",
        dest="columns",
        nargs="*",
        help="Select which columns to show",
    )

    return parser


if __name__ == "__main__":
    parser = argument_parser()
    args = parser.parse_args()
    main(args)
