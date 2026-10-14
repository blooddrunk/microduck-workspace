#!/usr/bin/env python3
"""Read-only Linux inventory: no UART/I2C opens, probes, configuration or motor commands."""
from __future__ import annotations
import argparse
from pathlib import Path
import platform
from evidence import Bundle, run, timestamp

# Fixed allowlist: no sudo, stty, i2cdetect, nmcli secrets, service start/stop or writes.
COMMANDS = {
    "kernel": ["uname", "-a"],
    "memory": ["free", "-b"],
    "storage": ["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS"],
    "root_space": ["df", "-h", "/"],
    "network_links": ["ip", "-brief", "link"],
    "network_addresses": ["ip", "-brief", "address"],
    "network_routes": ["ip", "route"],
    "failed_services": ["systemctl", "--failed", "--no-pager", "--plain", "--no-legend"],
    "boot_warnings": ["journalctl", "-b", "-p", "warning", "-n", "100", "--no-pager"],
    "kernel_log": ["dmesg", "--level=err,warn"],
}
ROBOTD = ["systemctl", "show", "robotd.service", "--no-pager",
          "--property=LoadState,ActiveState,SubState,UnitFileState,Result,MainPID,FragmentPath"]


def command_status(name, result):
    if result["returncode"] != 0:
        return "BLOCKED", "Command unavailable, permission denied, timeout or collection failure; see raw output"
    if name == "failed_services" and result["stdout"].strip():
        return "FAIL", "Failed units reported; inspect raw output before reboot/recovery"
    if result.get("stderr", "").strip():
        return "BLOCKED", "Collection emitted diagnostics; review stderr for incomplete visibility"
    if name in {"boot_warnings", "kernel_log"} and result["stdout"].strip() not in ("", "-- No entries --"):
        return "BLOCKED", "Warnings require review; not automatically classified as harmless"
    if name == "robotd" and "LoadState=not-found" in result["stdout"]:
        return "BLOCKED", "Optional robotd service not installed"
    return "PASS", "Read-only collection succeeded; does not establish electrical or runtime compatibility"


def occupancy(dev_root=Path('/dev'), proc_root=Path('/proc')):
    nodes = sorted({str(p) for pattern in ("ttyS*", "ttyUSB*", "ttyACM*", "ttyAMA*", "i2c-*")
                    for p in dev_root.glob(pattern)})
    opened = {node: [] for node in nodes}
    denied = 0
    for process in proc_root.iterdir():
        if not process.name.isdigit():
            continue
        try:
            for fd in (process / "fd").iterdir():
                try:
                    target = str(fd.resolve(strict=True))
                    if target in opened:
                        opened[target].append(process.name)
                except FileNotFoundError:
                    pass  # process/fd disappeared during observation
                except PermissionError:
                    denied += 1
        except FileNotFoundError:
            pass
        except PermissionError:
            denied += 1
    return dict(nodes=nodes, open_by_pid=opened, denied=denied,
                limit="snapshot only; kernel/console ownership and GPIO pin assignment require separate review")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="NEW private local directory")
    parser.add_argument("--robotd", action="store_true", help="Read optional service metadata only")
    args = parser.parse_args(argv)
    bundle = Bundle(args.output, "S1 Linux read-only collection; no bus communication, physical measurements or service mutation")
    if platform.system() != "Linux":
        bundle.add("platform", dict(command=["platform.system"], time_utc=timestamp()),
                   "BLOCKED", "Run this on the Radxa Linux board through SSH")
        return bundle.finish()
    for name, path in {"os_release": "/etc/os-release", "cpu": "/proc/cpuinfo",
                       "console": "/proc/cmdline", "board_model": "/proc/device-tree/model"}.items():
        result = run(["cat", path])
        bundle.add(name, result, *command_status(name, result))
    for name, command in {**COMMANDS, **({"robotd": ROBOTD} if args.robotd else {})}.items():
        result = run(command)
        bundle.add(name, result, *command_status(name, result))
    data = occupancy()
    bundle.add("device_occupancy", dict(command=["read /dev names and /proc/*/fd links"],
               time_utc=timestamp(), data=data), "BLOCKED" if data["denied"] or not data["nodes"] else "PASS",
               "Partial process visibility/no nodes" if data["denied"] or not data["nodes"] else "Snapshot collected; absence of owners does not prove UART free")
    bundle.add("hardware_acceptance", dict(command=["NOT_EXECUTED"], time_utc=timestamp()),
               "BLOCKED", "5V stability, heat, PCB identity, pin mux and reboot/storage health require board evidence and human review")
    return bundle.finish({"architecture": platform.machine()})


if __name__ == "__main__":
    raise SystemExit(main())
