from dataclasses import dataclass


@dataclass
class DeviceRule:
    name: str
    layout: str
    variant: str = ""
    match: str = "exact"


@dataclass
class GeneralConfig:
    default_layout: str = "es"
    default_variant: str = "nodeadkeys"
    poll_interval: int = 2
