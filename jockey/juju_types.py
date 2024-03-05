from enum import Enum
from dataclasses import dataclass
from typing import Optional


@dataclass
class Application:
    app: str
    charm: str
    charm_rev: int


@dataclass
class Machine:
    machine: str
    hostname: str
    base: str
    hardware: str


@dataclass
class Unit:
    unit: str
    machine: str
    hostname: str
    app: str
    charm: str
    workload: str
    agent: str
    ip: str
    leader: bool
    subordinate: bool
    subordinate_to: Optional[str] = None


class ObjectType(Enum):
    CHARM = ("charms", "charm", "c")
    APP = ("app", "apps", "application", "applications", "a")
    UNIT = ("units", "unit", "u")
    MACHINE = ("machines", "machine", "m")
    IP = ("address", "addresses", "ips", "ip", "i")
    HOSTNAME = ("hostnames", "hostname", "host", "hosts", "h")
