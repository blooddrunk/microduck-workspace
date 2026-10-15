#!/usr/bin/env python3
"""Record a safe S4 host, source, dependency, CUDA, and ONNX preflight.

This check does not start training, open a simulator viewer, change upstreams,
or access hardware. It is a preflight only; GUI variables do not prove that a
viewer can render, and a valid ONNX output does not prove policy behavior.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "Mjlab-Velocity-Flat-MicroDuck-HD1910"
SNAPSHOT = ROOT / ".upstreams/hd1910-rl/models/hd1910-walking-iter-2000"
PROBE = r'''import importlib, json, sys
result = {"python": sys.version.split()[0], "modules": {}, "cuda": {"available": False}}
for name in ("torch", "mujoco", "mujoco_warp", "warp", "onnx", "onnxruntime", "mjlab"):
    try:
        module = importlib.import_module(name)
        result["modules"][name] = getattr(module, "__version__", "available")
    except Exception as exc:
        result["modules"][name] = f"UNAVAILABLE: {type(exc).__name__}: {exc}"
try:
    import torch
    result["cuda"] = {"available": bool(torch.cuda.is_available()),
                      "torch": torch.__version__, "runtime": torch.version.cuda,
                      "device_count": torch.cuda.device_count()}
except Exception as exc:
    result["cuda"] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
try:
    import mjlab.tasks
    from mjlab.tasks.registry import list_tasks
    result["task_registered"] = "''' + TASK_ID + r'''" in list_tasks()
except Exception as exc:
    result["task_registered"] = False
    result["task_error"] = f"{type(exc).__name__}: {exc}"
try:
    import numpy as np
    import onnxruntime as ort
    from pathlib import Path
    p = Path(sys.argv[1])
    session = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
    inputs, outputs = session.get_inputs(), session.get_outputs()
    shape = lambda value: [int(x) if isinstance(x, int) else str(x) for x in value]
    result["onnx"] = {"inputs": len(inputs), "outputs": len(outputs),
                      "input_shape": shape(inputs[0].shape) if inputs else None,
                      "output_shape": shape(outputs[0].shape) if outputs else None,
                      "input_type": inputs[0].type if inputs else None,
                      "output_type": outputs[0].type if outputs else None}
    valid = (len(inputs) == len(outputs) == 1 and
             len(inputs[0].shape) == len(outputs[0].shape) == 2 and
             inputs[0].shape[-1] == 61 and outputs[0].shape[-1] == 14 and
             inputs[0].type == outputs[0].type == "tensor(float)")
    if valid:
        sample = np.zeros((1, 61), dtype=np.float32)
        output = session.run(None, {inputs[0].name: sample})[0]
        result["onnx"]["inference_output_shape"] = list(output.shape)
        result["onnx"]["zero_vector_output_finite"] = bool(np.isfinite(output).all())
        valid = output.shape == (1, 14) and result["onnx"]["zero_vector_output_finite"]
    result["onnx"]["contract_valid"] = bool(valid)
except Exception as exc:
    result["onnx"] = {"contract_valid": False,
                       "error": f"{type(exc).__name__}: {exc}"}
print("S4_PROBE_JSON=" + json.dumps(result))
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_snapshot_manifest(snapshot: Path) -> dict[str, Any]:
    manifest = snapshot / "SHA256SUMS"
    if not manifest.is_file():
        return {"status": "FAIL", "error": "SHA256SUMS is missing"}
    failures = []
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            expected, name = line.split(None, 1)
            path = snapshot / name.lstrip(" *")
        except ValueError:
            failures.append(f"malformed manifest line: {line!r}")
            continue
        checked += 1
        if not path.is_file():
            failures.append(f"missing file: {path.name}")
        elif sha256_file(path) != expected:
            failures.append(f"hash mismatch: {path.name}")
    return {"status": "PASS" if checked and not failures else "FAIL",
            "checked_files": checked, "failures": failures}


def run(command: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        result = subprocess.run(command, text=True, capture_output=True,
                                check=False, timeout=timeout, cwd=ROOT)
        return {"command": command, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "returncode": None,
                "error": f"{type(exc).__name__}: {exc}"}


def _new_output_dir(path: Path) -> Path:
    path = path.resolve()
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"Output folder is not empty; refusing to overwrite: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if (path / "report.json").exists():
        raise ValueError(f"Output already exists; refusing to overwrite: {path / 'report.json'}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hd1910-python", type=Path,
                        default=ROOT / ".upstreams/hd1910-rl/.venv/bin/python",
                        help="Python in the pinned HD1910 fork environment")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="new private report folder under .evidence/s4-simulation/")
    args = parser.parse_args(argv)
    output = _new_output_dir(args.output_dir)
    report: dict[str, Any] = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": ["scripts/check_s4_environment.py", *(argv if argv is not None else sys.argv[1:])],
        "host_python": sys.version.split()[0],
        "status": "RUNNING",
        "checks": {},
        "exceptions": [],
        "boundaries": ["preflight only", "no GUI render attempted", "no GPU training attempted",
                       "no hardware access", "zero-vector ONNX inference is not behavior validation"],
    }
    try:
        root_head = run(["git", "rev-parse", "HEAD"])
        root_dirty = run(["git", "status", "--porcelain", "--untracked-files=all"])
        uv = run(["uv", "--version"])
        nvidia = run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], timeout=10)
        report["repository"] = {
            "head": root_head.get("stdout"),
            "dirty": bool(root_dirty.get("stdout")),
            "status": ("FAIL" if root_head.get("returncode") != 0 else
                       "PARTIAL" if root_dirty.get("stdout") else "PASS"),
        }
        report["uv"] = {"status": "PASS" if uv.get("returncode") == 0 else "BLOCKED",
                         "version": uv.get("stdout"), "error": uv.get("error") or uv.get("stderr")}
        report["gui_hint"] = {
            "display_variable_present": bool(os.environ.get("DISPLAY")),
            "wayland_variable_present": bool(os.environ.get("WAYLAND_DISPLAY")),
            "x11_socket_present": Path("/tmp/.X11-unix/X0").exists(),
            "status": "PARTIAL" if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) else "BLOCKED",
        }
        report["nvidia_smi"] = nvidia

        try:
            from sync_upstreams import read_catalog
            catalog = {item["name"]: item for item in read_catalog()["sources"]}
            sources = {}
            for name in ("hd1910-rl", "ftservo-bam"):
                repo = ROOT / ".upstreams" / name
                head = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
                dirty = run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"])
                expected = catalog[name]["sha"]
                sources[name] = {"expected_sha": expected, "actual_sha": head.get("stdout"),
                                 "clean": not bool(dirty.get("stdout")),
                                 "status": "PASS" if head.get("stdout") == expected and not dirty.get("stdout") else "FAIL"}
            report["sources"] = sources
            report["checks"]["pinned_clean_sources"] = "PASS" if all(v["status"] == "PASS" for v in sources.values()) else "FAIL"
        except Exception as exc:
            report["exceptions"].append({"stage": "pinned sources", "type": type(exc).__name__, "message": str(exc)})
            report["checks"]["pinned_clean_sources"] = "FAIL"

        python = args.hd1910_python
        if not python.is_absolute():
            python = ROOT / python
        if not python.is_file():
            report["checks"]["locked_python_environment"] = "BLOCKED"
            report["environment"] = {"python": str(python), "error": "environment interpreter is missing"}
        else:
            lock = ROOT / ".upstreams/hd1910-rl/uv.lock"
            report["environment"] = {"interpreter": str(python),
                                      "uv_lock_sha256": sha256_file(lock) if lock.is_file() else None}
            probe = run([str(python), "-c", PROBE, str(SNAPSHOT / "policy.onnx")], timeout=60)
            report["environment"]["probe_returncode"] = probe.get("returncode")
            if probe.get("returncode") == 0:
                marker = next((line[len("S4_PROBE_JSON="):]
                               for line in probe["stdout"].splitlines()
                               if line.startswith("S4_PROBE_JSON=")), None)
                if marker is None:
                    raise ValueError("environment probe emitted no JSON result marker")
                details = json.loads(marker)
                report["environment"].update(details)
                report["checks"]["locked_python_environment"] = "PASS"
                report["checks"]["task_registered"] = "PASS" if details.get("task_registered") else "FAIL"
                report["checks"]["onnx_cpu_contract_and_finite_inference"] = (
                    "PASS" if details.get("onnx", {}).get("contract_valid") else "FAIL")
                cuda_available = bool(details.get("cuda", {}).get("available"))
                report["checks"]["cuda"] = "PASS" if cuda_available else "BLOCKED"
                report["checks"]["gpu_smoke"] = "NOT_EXECUTED" if cuda_available else "BLOCKED"
            else:
                report["environment"]["probe_stderr"] = probe.get("stderr") or probe.get("error")
                report["checks"]["locked_python_environment"] = "FAIL"
                report["checks"]["task_registered"] = "BLOCKED"
                report["checks"]["onnx_cpu_contract_and_finite_inference"] = "BLOCKED"
                report["checks"]["cuda"] = "BLOCKED"
                report["checks"]["gpu_smoke"] = "BLOCKED"

        manifest = SNAPSHOT / "SHA256SUMS"
        checksums = verify_snapshot_manifest(SNAPSHOT)
        report["snapshot"] = {"manifest": str(manifest), "manifest_check": checksums,
                               "status": checksums["status"],
                               "checkpoint_present": (SNAPSHOT / "model_2000.pt").is_file(),
                               "note": "this is a published checkpoint; this preflight did not train one"}
        report["checks"]["published_snapshot_checksums"] = report["snapshot"]["status"]
        report["checks"]["new_training_checkpoint"] = "NOT_EXECUTED"
        report["status"] = "PARTIAL"
    except Exception as exc:
        report["status"] = "FAIL"
        report["exceptions"].append({"stage": "preflight", "type": type(exc).__name__,
                                     "message": str(exc), "traceback": traceback.format_exc()})
        exit_code = 1
    else:
        exit_code = 0

    report["output_dir"] = str(output)
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output_dir": str(output),
                      "checks": report["checks"], "exceptions": report["exceptions"]},
                     indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
