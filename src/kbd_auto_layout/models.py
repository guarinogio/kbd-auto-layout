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
    apply_retries: int = 5
    apply_retry_delay: float = 1.0
