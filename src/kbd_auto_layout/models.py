from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeviceRule:
    name: str
    layout: str
    variant: str = ""
    match: str = "exact"
    vendor_id: str = ""
    product_id: str = ""
    priority: int = 0


@dataclass
class KeyboardDevice:
    name: str
    connected: bool = True
    vendor_id: str = ""
    product_id: str = ""

    @property
    def hardware_id(self) -> str:
        if self.vendor_id and self.product_id:
            return f"{self.vendor_id}:{self.product_id}"
        return ""


@dataclass
class GeneralConfig:
    default_layout: str = "es"
    default_variant: str = "nodeadkeys"
    poll_interval: int = 2
    apply_retries: int = 5
    apply_retry_delay: float = 1.0
    backend: str = "auto"
    device_cache_ttl: float = 2.0
