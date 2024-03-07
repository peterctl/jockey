#!/bin/python3

# Jockey is a CLI utility that facilitates quick retrieval of Juju objects that
# match given filters.
# Author: Connor Chamberlain

import pdb
import argparse
import json
from jockey import collectors, filters, status_keeper
from jockey.types import ObjectType


def main(args: argparse.Namespace):
    # Perform any requested cache refresh
    if args.refresh:
        status_keeper.cache_juju_status()

    # Get status
    if args.file:
        status = json.load(args.file)
    else:
        status = status_keeper.get_juju_status()

    if args.object in ObjectType.APP.value:
        objects = collectors.get_applications(status)
    elif args.object in ObjectType.MACHINE.value:
        objects = collectors.get_machines(status)
    elif args.object in ObjectType.UNIT.value:
        objects = collectors.get_units(status)
    else:
        raise KeyError(f"Unknown object type: {args.object}")

    # fs = filters.parse_filters(args.filters)
    for obj in objects:
        if all([f(obj) for f in args.filters]):
            print(obj)


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

    return parser


if __name__ == "__main__":
    parser = argument_parser()
    args = parser.parse_args()
    main(args)
