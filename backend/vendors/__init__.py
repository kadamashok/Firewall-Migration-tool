from .base import DeviceFacts, VendorAdapter
from .ciscoasa import CiscoAsaAdapter
from .checkpoint import CheckPointAdapter
from .fortinet import FortinetAdapter
from .paloalto import PaloAltoAdapter

VENDOR_ADAPTERS = [
    PaloAltoAdapter(),
    FortinetAdapter(),
    CiscoAsaAdapter(),
    CheckPointAdapter(),
]
