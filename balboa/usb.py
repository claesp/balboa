"""Render USBGuard rules that apply to approved USB models."""

import re


CATEGORIES = {"audio", "cameras", "hubs", "keyboards", "network", "other", "pointers", "storage"}
ID = re.compile(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{4}")
INTERFACE = re.compile(r"[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}")


def model_rules(devices):
    if not isinstance(devices, dict) or set(devices) - CATEGORIES:
        raise ValueError("The usb_devices field requires an object with supported USB categories.")

    rules = set()
    for category, models in devices.items():
        if not isinstance(models, list):
            raise ValueError(f"The usb_devices.{category} field requires a list of models.")
        if category == "storage" and models:
            raise ValueError("The CIS profile disables USB storage. Leave usb_devices.storage empty.")

        for model in models:
            if not isinstance(model, dict) or set(model) != {"id", "interfaces"}:
                raise ValueError("Each USB model requires only id and interfaces.")
            identity = model["id"]
            if not isinstance(identity, str) or not ID.fullmatch(identity):
                raise ValueError("Each USB model requires an exact vendor and product ID, such as 1234:5678.")
            interfaces = model["interfaces"]
            if not isinstance(interfaces, list) or not interfaces or any(
                not isinstance(interface, str) or not INTERFACE.fullmatch(interface) for interface in interfaces
            ):
                raise ValueError("Each USB model requires exact interface codes, such as 03:01:01.")
            if any(interface.startswith("08:") for interface in interfaces):
                raise ValueError("The CIS profile disables USB storage. Remove USB models with storage interfaces.")
            rules.add((identity.lower(), tuple(sorted(interface.lower() for interface in interfaces))))

    lines = [f"allow id {identity} with-interface equals {{ {' '.join(interfaces)} }}"
             for identity, interfaces in sorted(rules)]
    return "\n".join([*lines, "block", ""])
