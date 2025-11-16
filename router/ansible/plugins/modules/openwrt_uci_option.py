#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple helper module to set UCI options idempotently on OpenWrt."""
from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: openwrt_uci_option
short_description: Set OpenWrt UCI options via the uci CLI
version_added: "1.0.0"
description:
  - Reads the current value of a UCI option and updates it only when a change is required.
  - Designed for lightweight OpenWrt hosts where relying on external collections is undesirable.
options:
  config:
    description:
      - Name of the UCI config (for example C(wireless)).
    type: str
    required: true
  section:
    description:
      - Section expression such as C(@wifi-device[0]) or a named section.
    type: str
    required: true
  option:
    description:
      - Option key to manage within the section.
    type: str
    required: true
  value:
    description:
      - Desired value for the option. The module does not quote or escape the value.
    type: str
    required: true
  uci_path:
    description:
      - Path to the C(uci) binary on the remote host.
    type: path
    default: uci
author:
  - Ionegulkin Router Automation (@ionegulkin)
notes:
  - The module never runs C(uci commit); trigger it via a handler once all changes are staged.
"""

EXAMPLES = r"""
- name: Enable first Wi-Fi device
  openwrt_uci_option:
    config: wireless
    section: "@wifi-device[0]"
    option: disabled
    value: "0"

- name: Update SSID of the first iface
  openwrt_uci_option:
    config: wireless
    section: "@wifi-iface[0]"
    option: ssid
    value: MyNetwork
"""

RETURN = r"""
current:
  description: Previously configured value (if present).
  returned: always
  type: str
  sample: "1"
desired:
  description: Value requested via the module parameters.
  returned: always
  type: str
  sample: "0"
changed:
  description: Whether the module updated the option.
  returned: always
  type: bool
"""


def main() -> None:
    argument_spec = dict(
        config=dict(type="str", required=True),
        section=dict(type="str", required=True),
        option=dict(type="str", required=True),
        value=dict(type="str", required=True),
        uci_path=dict(type="path", default="uci"),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    config = module.params["config"]
    section = module.params["section"]
    option = module.params["option"]
    value = str(module.params["value"])
    uci_path = module.params["uci_path"]

    key = f"{config}.{section}.{option}"

    rc, stdout, stderr = module.run_command([uci_path, "-q", "get", key], check_rc=False)
    if rc == 0:
        current_value = stdout.strip()
    elif rc == 1:
        current_value = None
    else:
        module.fail_json(msg=f"failed to read {key}", rc=rc, stderr=stderr)

    changed = current_value != value

    if module.check_mode or not changed:
        module.exit_json(changed=changed, current=current_value, desired=value)

    rc, _, stderr = module.run_command([uci_path, "set", f"{key}={value}"], check_rc=False)
    if rc != 0:
        module.fail_json(msg=f"failed to set {key}", rc=rc, stderr=stderr)

    module.exit_json(changed=True, current=current_value, desired=value)


if __name__ == "__main__":
    main()
