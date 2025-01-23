#!/usr/bin/env python3
"""Jockey: a Juju query language to put all of your Juju objects at your fingertips."""
import logging
import os
from pkgutil import get_data
import sys
from typing import Optional, Sequence

from rich import print
from rich.console import Console
from rich.markdown import Markdown

from jockey.__args__ import parse_args
from jockey.core import query
from jockey.log import configure_logging


logger = logging.getLogger(__name__)


if "SNAP" in os.environ:
    os.environ["PATH"] += ":" + os.path.join(os.environ["SNAP"], "usr", "juju", "bin")


def info() -> Markdown:
    info_data = get_data("jockey", "info.md")
    info_decoded = info_data.decode("utf-8") if info_data else ""
    return Markdown(info_decoded)


def print_info(console: Optional[Console] = None) -> None:
    if not console:
        console = Console(width=120)

    console.print(info())


def main(argv: Optional[Sequence[str]] = None) -> int:
    # parse command-line arguments and configure logging
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    logger.debug("Parsed command-line arguments:\n%r", args)

    verbosity = args.verbose if "verbose" in args else 0
    configure_logging(verbosity)

    # check if OBJECT is requesting the informational message
    if args.object == "info":
        print_info()
        return 0

    filters = args.filters if "filters" in args else []
    print("\n".join(query(object_type=args.object, filter_strings=filters, file=args.file, model=args.model)))
    return 0


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
