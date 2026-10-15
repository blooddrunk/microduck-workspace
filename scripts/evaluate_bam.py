#!/usr/bin/env python3
"""Check the pinned FTServo BAM models and optionally compare CPU dynamics.

The script never edits either upstream checkout and never opens a serial port.
Run it with the Python 3.12 environment from the pinned HD1910 fork for the
MuJoCo comparison. All generated reports and curves go to a new output folder.
"""
from __future__ import annotations

import argparse
import csv
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "upstreams" / "sources.json"
MOTOR_DIR = Path("bam/params/feetech_hd1910_7_4V")
VARIANTS = tuple(f"m{i}" for i in range(1, 7))
BASE_FIELDS = {
    "kt", "R", "armature", "q_offset", "command_delay",
    "friction_base", "friction_viscous",
}
MODEL_FIELDS = {
    "m1": set(),
    "m2": {"friction_stribeck", "dtheta_stribeck", "alpha"},
    "m3": {"load_friction_base"},
    "m4": {
        "friction_stribeck", "load_friction_base", "load_friction_stribeck",
        "dtheta_stribeck", "alpha",
    },
    "m5": {
        "friction_stribeck", "load_friction_motor", "load_friction_external",
        "load_friction_motor_stribeck", "load_friction_external_stribeck",
        "dtheta_stribeck", "alpha",
    },
    "m6": {
        "friction_stribeck", "load_friction_motor", "load_friction_external",
        "load_friction_motor_stribeck", "load_friction_external_stribeck",
        "load_friction_motor_quad", "load_friction_external_quad",
        "dtheta_stribeck", "alpha",
    },
}


class EvaluationError(RuntimeError):
    """A pinned-source or model-contract check failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_catalog() -> dict[str, dict[str, Any]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {item["name"]: item for item in payload["sources"]}


def git_value(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if result.returncode:
        raise EvaluationError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def verify_checkout(repo: Path, source_name: str, catalog: dict[str, dict[str, Any]]) -> dict[str, str]:
    if source_name not in catalog:
        raise EvaluationError(f"{source_name} is missing from {CATALOG.relative_to(ROOT)}")
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise EvaluationError(f"Not a Git checkout: {repo}")
    head = git_value(repo, "rev-parse", "HEAD")
    expected = catalog[source_name]["sha"]
    if head != expected:
        raise EvaluationError(f"{source_name} SHA mismatch: expected {expected}, got {head}")
    dirty = git_value(repo, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise EvaluationError(f"{source_name} checkout is dirty; refusing to use it")
    return {"path": str(repo), "sha": head, "status": "clean"}


def validate_payload(data: Any, variant: str) -> None:
    """Validate the pinned HD1910 JSON shape and basic physical bounds."""
    if variant not in VARIANTS:
        raise ValueError(f"Unsupported model variant: {variant}")
    if not isinstance(data, dict):
        raise ValueError(f"{variant}: JSON root must be an object")
    expected = BASE_FIELDS | MODEL_FIELDS[variant] | {"model", "actuator"}
    if set(data) != expected:
        missing = sorted(expected - set(data))
        extra = sorted(set(data) - expected)
        raise ValueError(f"{variant}: field mismatch; missing={missing}, extra={extra}")
    if data["model"] != variant:
        raise ValueError(f"{variant}: model field must equal {variant!r}")
    if data["actuator"] != "hd1910":
        raise ValueError(f"{variant}: actuator field must equal lowercase 'hd1910'")
    for name in expected - {"model", "actuator"}:
        value = data[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{variant}.{name}: expected a JSON number")
        if not math.isfinite(value):
            raise ValueError(f"{variant}.{name}: value must be finite")
    for name in ("kt", "R", "armature"):
        if data[name] <= 0:
            raise ValueError(f"{variant}.{name}: value must be positive")
    if not 0 <= data["command_delay"] <= 0.05:
        raise ValueError(f"{variant}.command_delay: expected a value in [0, 0.05] seconds")
    if abs(data["q_offset"]) > 0.1:
        raise ValueError(f"{variant}.q_offset: value is outside the BAM loader's +/-0.1 rad range")
    for name in expected - {"model", "actuator", "kt", "R", "armature", "q_offset", "command_delay", "dtheta_stribeck", "alpha"}:
        if data[name] < 0:
            raise ValueError(f"{variant}.{name}: friction coefficient must be non-negative")
    for name in ("dtheta_stribeck", "alpha"):
        if name in data and data[name] <= 0:
            raise ValueError(f"{variant}.{name}: value must be positive")


def _finite_scalar(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise EvaluationError(f"{label} is not a scalar number") from exc
    if not math.isfinite(result):
        raise EvaluationError(f"{label} is not finite")
    return result


def load_models(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if sys.version_info[:2] != (3, 12):
        raise EvaluationError(
            f"BAM source requires Python 3.12; current interpreter is {sys.version.split()[0]}"
        )
    bam_root = repo.resolve()
    sys.path.insert(0, str(bam_root))
    try:
        from bam.actuators import actuators
        from bam.model import load_model, load_model_from_dict
    except Exception as exc:
        raise EvaluationError(f"Could not import pinned BAM checkout: {exc}") from exc

    results: dict[str, Any] = {}
    loaded: dict[str, Any] = {}
    params_dir = bam_root / MOTOR_DIR
    for variant in VARIANTS:
        path = params_dir / f"{variant}.json"
        if not path.is_file():
            raise EvaluationError(f"Missing model file: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvaluationError(f"Cannot parse {path}: {exc}") from exc
        validate_payload(data, variant)

        actuators.pop("hd1910", None)
        try:
            load_model(motor_name="feetech_hd1910_7_4V", model=variant)
            stock = {"status": "PASS", "exception": None}
        except Exception as exc:
            stock = {"status": "FAIL", "exception": f"{type(exc).__name__}: {exc}"}
            if not isinstance(exc, KeyError) or exc.args != ("hd1910",):
                raise EvaluationError(f"{variant}: unexpected stock-load exception: {stock['exception']}") from exc

        # Verify that the class exported by the vendor is reachable under its
        # documented spelling, then provide the lowercase JSON alias in-process.
        upper_payload = dict(data, actuator="HD1910")
        upper_model = load_model_from_dict(upper_payload)
        actuators["hd1910"] = actuators["HD1910"]
        model = load_model(json_file=str(path))
        if model.name != variant or model.actuator_name != "hd1910":
            raise EvaluationError(f"{variant}: loaded model identity does not match JSON")

        parameters = model.get_parameters()
        unknown = sorted(set(data) - {"model", "actuator"} - set(parameters))
        if unknown:
            raise EvaluationError(f"{variant}: loader ignores unrecognized parameters: {unknown}")
        loaded_values: dict[str, float] = {}
        for name in set(data) - {"model", "actuator"}:
            parameter = parameters[name]
            value = _finite_scalar(parameter.value, f"{variant}.{name}")
            lower = _finite_scalar(parameter.min, f"{variant}.{name}.min")
            upper = _finite_scalar(parameter.max, f"{variant}.{name}.max")
            if not lower <= value <= upper:
                raise EvaluationError(
                    f"{variant}.{name}={value} is outside loader bounds [{lower}, {upper}]"
                )
            loaded_values[name] = value

        def one_step_after_reset() -> dict[str, float]:
            model.reset()
            control = model.actuator.compute_control(0.15, 0.0, 0.0, 0.005)
            torque = model.actuator.compute_torque(control, True, 0.0, 0.0)
            friction, damping = model.compute_frictions(torque, -0.05, 0.0)
            return {
                "voltage_command_v": _finite_scalar(control, f"{variant}.control"),
                "motor_torque_nm": _finite_scalar(torque, f"{variant}.torque"),
                "friction_budget_nm": _finite_scalar(friction, f"{variant}.friction"),
                "viscous_damping_nm_per_rad_s": _finite_scalar(damping, f"{variant}.damping"),
            }

        one_step = one_step_after_reset()
        repeated_step = one_step_after_reset()
        reset_repeatable = all(
            math.isclose(one_step[key], repeated_step[key], rel_tol=0.0, abs_tol=1e-12)
            for key in one_step
        )
        if not reset_repeatable:
            raise EvaluationError(f"{variant}: reset did not reproduce a finite one-step result")
        file_sha = sha256_file(path)
        results[variant] = {
            "json_sha256": file_sha,
            "actuator_json": data["actuator"],
            "stock_loader": stock,
            "uppercase_registry_load": "PASS",
            "process_local_lowercase_alias_load": "PASS",
            "parameter_count": len(loaded_values),
            "parameters": loaded_values,
            "reset": "PASS",
            "reset_repeatable": reset_repeatable,
            "single_step_finite": one_step,
        }
        loaded[variant] = model
        # Keep the explicitly demonstrated uppercase loader out of the report's
        # live state; it is only a registration-case check.
        del upper_model
    return results, loaded


def _mjcf() -> str:
    return """<mujoco model=\"microduck_hd1910_single_joint\">
  <option timestep=\"0.005\" gravity=\"0 0 -9.80665\"/>
  <worldbody>
    <body name=\"pendulum\">
      <joint name=\"hinge\" type=\"hinge\" axis=\"0 1 0\"/>
      <geom name=\"arm\" type=\"capsule\" size=\"0.005\" fromto=\"0 0 0 0 0 -0.15\" mass=\"0.03\" contype=\"0\" conaffinity=\"0\"/>
      <body name=\"payload\" pos=\"0 0 -0.15\">
        <geom name=\"load\" type=\"sphere\" size=\"0.01\" mass=\"0.5\" contype=\"0\" conaffinity=\"0\"/>
      </body>
    </body>
  </worldbody>
  <actuator><motor name=\"motor\" joint=\"hinge\" gear=\"1\" ctrllimited=\"false\"/></actuator>
</mujoco>"""


def _target(time_s: float) -> float:
    return 0.25 if 0.1 <= time_s < 0.8 else 0.0


def _new_model(mujoco: Any) -> tuple[Any, Any]:
    model = mujoco.MjModel.from_xml_string(_mjcf())
    model.opt.timestep = 0.005
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def _run_provisional(mujoco: Any, hd_repo: Path) -> dict[str, list[float]]:
    sys.path.insert(0, str((hd_repo / "src").resolve()))
    from mjlab_microduck.actuator.hd1910 import Hd1910CpuController, PERF, SIM

    model, data = _new_model(mujoco)
    joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")
    dof = int(model.jnt_dofadr[joint])
    model.dof_armature[dof] = SIM["armature_kg_m2"]
    model.dof_frictionloss[dof] = SIM["coulomb_nm"]
    model.dof_damping[dof] = SIM["viscous_nm_s_per_rad"]
    rated_torque = float(PERF[-1]["rated_nm"])
    model.actuator_forcelimited[0] = 1
    model.actuator_forcerange[0] = (-rated_torque, rated_torque)
    controller = Hd1910CpuController(model, data, voltage=7.4, delay=4)

    rows = {key: [] for key in ("time_s", "target_rad", "position_rad", "velocity_rad_s", "torque_nm")}
    for step in range(400):
        time_s = step * 0.005
        target = _target(time_s)
        controller.q_target[:] = target
        controller.update()
        mujoco.mj_step(model, data)
        rows["time_s"].append(float(data.time))
        rows["target_rad"].append(target)
        rows["position_rad"].append(float(data.qpos[0]))
        rows["velocity_rad_s"].append(float(data.qvel[0]))
        rows["torque_nm"].append(float(data.ctrl[0]))
    return rows


def _run_bam(mujoco: Any, model_cfg: Any, delay_steps: int = 4) -> dict[str, list[float]]:
    from bam.mujoco import MujocoController

    model, data = _new_model(mujoco)
    controller = MujocoController(model_cfg, "motor", model, data)
    pending = deque([0.0] * delay_steps)
    rows = {key: [] for key in ("time_s", "target_rad", "position_rad", "velocity_rad_s", "torque_nm")}
    for step in range(400):
        time_s = step * 0.005
        target = _target(time_s)
        pending.append(target)
        controller.set_q_target("motor", pending.popleft())
        mujoco.mj_forward(model, data)
        controller.update()
        mujoco.mj_step(model, data)
        rows["time_s"].append(float(data.time))
        rows["target_rad"].append(target)
        rows["position_rad"].append(float(data.qpos[0]))
        rows["velocity_rad_s"].append(float(data.qvel[0]))
        rows["torque_nm"].append(float(data.ctrl[0]))
    return rows


def _metrics(rows: dict[str, list[float]]) -> dict[str, float | bool]:
    import numpy as np

    position = np.asarray(rows["position_rad"], dtype=float)
    velocity = np.asarray(rows["velocity_rad_s"], dtype=float)
    torque = np.asarray(rows["torque_nm"], dtype=float)
    target = np.asarray(rows["target_rad"], dtype=float)
    finite = bool(np.isfinite(position).all() and np.isfinite(velocity).all() and np.isfinite(torque).all())
    if not finite:
        raise EvaluationError("CPU dynamics produced NaN or Inf")
    return {
        "finite": finite,
        "position_rmse_rad": float(np.sqrt(np.mean(np.square(position - target)))),
        "final_position_rad": float(position[-1]),
        "peak_abs_position_rad": float(np.max(np.abs(position))),
        "peak_abs_speed_rad_s": float(np.max(np.abs(velocity))),
        "peak_abs_torque_nm": float(np.max(np.abs(torque))),
    }


def run_comparison(
    bam_results: dict[str, Any],
    loaded_models: dict[str, Any],
    hd_repo: Path,
    output_dir: Path,
) -> dict[str, Any]:
    import mujoco
    import numpy as np

    provisional = _run_provisional(mujoco, hd_repo)
    trajectories = {"provisional_pd": provisional}
    metrics = {"provisional_pd": _metrics(provisional)}
    for variant in VARIANTS:
        # The JSON delay is identification metadata. The A/B applies the same
        # four-physics-step (20 ms) target delay to both backends and records the
        # fitted vendor value separately; it is not added a second time here.
        model = loaded_models[variant]
        model.actuator.kp = 32
        model.actuator.error_gain = 0.163
        model.actuator.max_pwm = 0.97
        model.actuator.vin = 7.4
        model.actuator.max_current = None
        rows = _run_bam(mujoco, model, delay_steps=4)
        trajectories[variant] = rows
        metrics[variant] = _metrics(rows)
        bam_results[variant]["ab_metrics"] = metrics[variant]

    csv_path = output_dir / "single_servo_curves.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        header = ["time_s", "target_rad"]
        for name in trajectories:
            header.extend([f"{name}_position_rad", f"{name}_velocity_rad_s", f"{name}_torque_nm"])
        writer.writerow(header)
        for index, time_s in enumerate(provisional["time_s"]):
            row = [time_s, provisional["target_rad"][index]]
            for name, series in trajectories.items():
                row.extend([
                    series["position_rad"][index],
                    series["velocity_rad_s"][index],
                    series["torque_nm"][index],
                ])
            writer.writerow(row)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plot_path = output_dir / "single_servo_curves.png"
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(provisional["time_s"], provisional["target_rad"], "k--", label="command")
    for name, series in trajectories.items():
        axes[0].plot(series["time_s"], series["position_rad"], label=name)
    axes[0].set_ylabel("Position (rad)")
    axes[0].legend(ncol=2, fontsize=8)
    for name, series in trajectories.items():
        axes[1].plot(series["time_s"], series["torque_nm"], label=name)
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Motor torque (N m)")
    axes[1].legend(ncol=2, fontsize=8)
    fig.suptitle("Single-joint CPU sensitivity test: provisional PD vs FTServo BAM M1-M6")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=140)
    plt.close(fig)

    return {
        "status": "PASS",
        "scope": "CPU numerical A/B sensitivity test; not an empirical accuracy or robot-behavior result",
        "conditions": {
            "geometry": "single pendulum: 0.50 kg tip load, 0.03 kg, 0.15 m arm",
            "gravity_m_s2": 9.80665,
            "physics_dt_s": 0.005,
            "control_target": "0 rad, step to 0.25 rad at 0.10 s, return to 0 rad at 0.80 s",
            "duration_s": 2.0,
            "initial_position_rad": 0.0,
            "initial_velocity_rad_s": 0.0,
            "target_delay_steps": 4,
            "target_delay_s": 0.02,
            "voltage_v": 7.4,
            "bam_kp": 32,
            "bam_error_gain": 0.163,
            "bam_max_pwm": 0.97,
            "bam_max_current_a": None,
            "bam_command_delay_policy": "reported from JSON but not separately applied; shared 20 ms delay is applied to both models",
            "provisional_pd_gain_nm_per_rad": 0.55,
            "provisional_torque_cap_nm": 0.36284605,
        },
        "metrics": metrics,
        "artifacts": {
            "curves_csv": csv_path.name,
            "curves_png": plot_path.name,
            "curves_csv_sha256": sha256_file(csv_path),
            "curves_png_sha256": sha256_file(plot_path),
        },
    }


def _new_output_dir(path: Path) -> Path:
    path = path.resolve()
    if path.exists() and any(path.iterdir()):
        raise EvaluationError(f"Output folder is not empty; refusing to overwrite: {path}")
    path.mkdir(parents=True, exist_ok=True)
    for name in ("report.json", "single_servo_curves.csv", "single_servo_curves.png"):
        if (path / name).exists():
            raise EvaluationError(f"Output already exists; refusing to overwrite: {path / name}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("load-only", "compare"), default="compare",
                        help="load-only checks M1-M6; compare also runs the CPU single-joint A/B")
    parser.add_argument("--bam-repo", type=Path, default=ROOT / ".upstreams/ftservo-bam",
                        help="clean checkout at the SHA pinned in upstreams/sources.json")
    parser.add_argument("--hd1910-repo", type=Path, default=ROOT / ".upstreams/hd1910-rl",
                        help="clean checkout at the SHA pinned in upstreams/sources.json")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="new private output folder, normally under .evidence/s4-simulation/")
    args = parser.parse_args(argv)

    output_dir = _new_output_dir(args.output_dir)
    report: dict[str, Any] = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": ["scripts/evaluate_bam.py", *(argv if argv is not None else sys.argv[1:])],
        "python": sys.version.split()[0],
        "status": "RUNNING",
        "checks": {},
        "exceptions": [],
    }
    try:
        catalog = read_catalog()
        source_info = {
            "ftservo_bam": verify_checkout(args.bam_repo, "ftservo-bam", catalog),
            "hd1910_rl": verify_checkout(args.hd1910_repo, "hd1910-rl", catalog),
        }
        lock = args.hd1910_repo / "uv.lock"
        source_info["hd1910_rl"]["uv_lock_sha256"] = sha256_file(lock)
        report["sources"] = source_info
        license_path = args.bam_repo / "LICENSE"
        if not license_path.is_file() or "Apache License" not in license_path.read_text(encoding="utf-8"):
            raise EvaluationError("Pinned ftservo-bam LICENSE file is missing or not Apache-2.0")
        report["license"] = {
            "spdx": "Apache-2.0",
            "file_sha256": sha256_file(license_path),
        }
        model_results, loaded_models = load_models(args.bam_repo)
        report["models"] = model_results
        stock_failures = [name for name, item in model_results.items() if item["stock_loader"]["status"] != "PASS"]
        report["checks"]["json_and_parameter_validation"] = "PASS"
        report["checks"]["m1_m6_alias_load_reset_single_step"] = "PASS"
        report["checks"]["stock_loader_case_compatibility"] = (
            {"status": "FAIL", "variants": stock_failures}
            if stock_failures else {"status": "PASS", "variants": []}
        )
        if args.mode == "compare":
            report["cpu_comparison"] = run_comparison(model_results, loaded_models, args.hd1910_repo, output_dir)
            report["checks"]["cpu_single_joint_ab_finite"] = "PASS"
        report["status"] = "PARTIAL" if stock_failures else "PASS"
        report["interpretation"] = (
            "The stock vendor loader fails because lowercase JSON actuator names do not match the uppercase registry key. "
            "All six models load after a process-local lowercase alias. CPU A/B curves are model sensitivity evidence only; "
            "they do not identify which model matches a physical HD1910."
            if stock_failures else
            "All selected checks passed; simulation is still not hardware validation."
        )
        exit_code = 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["exceptions"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        exit_code = 1

    report["output_dir"] = str(output_dir)
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "output_dir": str(output_dir),
        "checks": report["checks"],
        "exceptions": report["exceptions"],
    }, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
