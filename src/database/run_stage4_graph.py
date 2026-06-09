import argparse
import csv
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_local_env():
    for env_file in (REPO_ROOT / ".env", REPO_ROOT / ".env.local"):
        if not env_file.exists():
            continue
        for raw in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def redact(text):
    password = os.environ.get("NEO4J_PASSWORD", "")
    if password:
        text = text.replace(password, "[redacted]")
    return text


def parse_bolt_host_port(uri):
    value = uri.replace("bolt://", "").replace("neo4j://", "")
    host_port = value.split("/")[0]
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        return host or "localhost", int(port)
    return host_port or "localhost", 7687


def check_tcp(uri, timeout=3):
    host, port = parse_bolt_host_port(uri)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"{host}:{port}"
    except OSError as exc:
        return False, f"{host}:{port} refused or unavailable: {exc.__class__.__name__}"


def run_command(name, cmd, log_file, env):
    result = subprocess.run(cmd, cwd=REPO_ROOT, env=env, text=True, capture_output=True)
    log_file.write_text(redact((result.stdout or "") + (result.stderr or "")), encoding="utf-8")
    return {
        "name": name,
        "command": " ".join(str(part) for part in cmd),
        "exit_code": result.returncode,
        "log": str(log_file.relative_to(REPO_ROOT)),
        "ok": result.returncode == 0,
    }


def count_records(path):
    if not Path(path).exists():
        return ""
    if Path(path).suffix == ".jsonl":
        return sum(1 for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
    if Path(path).suffix == ".csv":
        with Path(path).open(newline="", encoding="utf-8", errors="replace") as f:
            return max(0, sum(1 for _ in csv.reader(f)) - 1)
    return ""


def write_manifest(run_dir, artifacts):
    with (run_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"])
        writer.writeheader()
        for artifact, path, notes in artifacts:
            path = Path(path)
            writer.writerow({
                "artifact": artifact,
                "path": str(path.relative_to(REPO_ROOT)) if path.exists() else str(path),
                "records": count_records(path),
                "bytes": path.stat().st_size if path.exists() else "",
                "sha256": sha256_file(path) if path.exists() else "",
                "notes": notes,
            })


def write_readme(run_dir, summary):
    lines = [
        "# Stage 4 Graph And Neo4j Run",
        "",
        f"- Valid: {summary['valid']}",
        f"- Neo4j status: `{summary['neo4j_status']}`",
        f"- Neo4j TCP: `{summary['neo4j_tcp_check']['detail']}`",
        f"- Input file: `{summary['input_file']}`",
        f"- Input SHA-256: `{summary['input_sha256']}`",
        f"- Promoted: {summary['promoted']}",
        f"- Preserve Neo4j: {summary['preserve_neo4j']}",
        "",
        "## Outputs",
        "",
    ]
    for name, path in summary["outputs"].items():
        lines.append(f"- {name}: `{path}`")
    lines.extend(["", "## Commands", ""])
    for command in summary["commands"]:
        lines.append(f"- {command['name']}: exit_code={command['exit_code']}, log=`{command['log']}`")
    (run_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Run Stage 4 graph analytics and optional Neo4j import.")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--skip-neo4j", action="store_true")
    parser.add_argument("--preserve-neo4j", action="store_true", help="Do not clear previously imported SMA KG nodes/relationships before import.")
    parser.add_argument("--input-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--opentargets-file", default="data/external/sma_gda_baseline.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    load_local_env()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"stage4_graph_database_{stamp}"
    outputs_dir = run_dir / "outputs"
    logs_dir = run_dir / "logs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    commands = []
    neo4j_status = "skipped"
    required = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]
    env_ready = {key: bool(env.get(key)) for key in required}
    tcp_ok = False
    tcp_detail = ""
    neo4j_import_summary = outputs_dir / "database" / "neo4j_import_summary.json"
    topology_metrics = outputs_dir / "evaluation" / "topology_metrics.json"
    snapshot_analytics = outputs_dir / "data" / "processed" / "analytics_metrics.csv"
    snapshot_viewer = outputs_dir / "docs" / "graph_viewer.html"
    for path in (neo4j_import_summary, topology_metrics, snapshot_analytics, snapshot_viewer):
        path.parent.mkdir(parents=True, exist_ok=True)

    if not args.skip_neo4j:
        if all(env_ready.values()):
            tcp_ok, tcp_detail = check_tcp(env["NEO4J_URI"])
            if tcp_ok:
                import_cmd = [
                    sys.executable,
                    "src/database/neo4j_importer.py",
                    "--fused-file",
                    args.input_file,
                    "--opentargets-file",
                    args.opentargets_file,
                    "--summary-file",
                    str(neo4j_import_summary),
                ]
                if not args.preserve_neo4j:
                    import_cmd.append("--clear-managed-graph")
                import_result = run_command(
                    "neo4j_import",
                    import_cmd,
                    logs_dir / "neo4j_import.log",
                    env,
                )
                commands.append(import_result)
                eval_result = run_command(
                    "topology_eval",
                    [
                        sys.executable,
                        "src/evaluation/topology_eval.py",
                        "--output-file",
                        str(topology_metrics),
                    ],
                    logs_dir / "topology_eval.log",
                    env,
                )
                commands.append(eval_result)
                neo4j_status = "ok" if import_result["ok"] and eval_result["ok"] else "failed"
            else:
                neo4j_status = "failed_service_unavailable"
        else:
            neo4j_status = "skipped_missing_env"

    commands.append(run_command(
        "graph_analytics",
        [
            sys.executable,
            "src/database/graph_analytics.py",
            "--input-file",
            args.input_file,
            "--opentargets-file",
            args.opentargets_file,
            "--output-file",
            str(snapshot_analytics),
        ],
        logs_dir / "graph_analytics.log",
        env,
    ))
    commands.append(run_command(
        "generate_pyvis",
        [
            sys.executable,
            "src/database/generate_pyvis.py",
            "--input-file",
            args.input_file,
            "--metrics-file",
            str(snapshot_analytics),
            "--opentargets-file",
            args.opentargets_file,
            "--output-file",
            str(snapshot_viewer),
        ],
        logs_dir / "generate_pyvis.log",
        env,
    ))

    local_graph_valid = all(command["ok"] for command in commands if command["name"] in {"graph_analytics", "generate_pyvis"})
    neo4j_valid = args.skip_neo4j or neo4j_status == "ok"
    all_valid = local_graph_valid and neo4j_valid

    summary = {
        "valid": all_valid,
        "neo4j_status": neo4j_status,
        "neo4j_env_ready": env_ready,
        "neo4j_tcp_check": {"ok": tcp_ok, "detail": tcp_detail},
        "input_file": args.input_file,
        "input_sha256": sha256_file(REPO_ROOT / args.input_file) if (REPO_ROOT / args.input_file).exists() else "",
        "opentargets_file": args.opentargets_file,
        "opentargets_sha256": sha256_file(REPO_ROOT / args.opentargets_file) if (REPO_ROOT / args.opentargets_file).exists() else "",
        "promoted": bool(args.promote and all_valid),
        "preserve_neo4j": bool(args.preserve_neo4j),
        "commands": commands,
        "outputs": {
            "analytics_metrics": str(snapshot_analytics.relative_to(REPO_ROOT)) if snapshot_analytics.exists() else "",
            "graph_viewer": str(snapshot_viewer.relative_to(REPO_ROOT)) if snapshot_viewer.exists() else "",
            "neo4j_import_summary": str(neo4j_import_summary.relative_to(REPO_ROOT)) if neo4j_import_summary.exists() else "",
            "topology_metrics": str(topology_metrics.relative_to(REPO_ROOT)) if topology_metrics.exists() else "",
        },
    }
    (run_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(run_dir, summary)
    write_manifest(
        run_dir,
        [
            ("validation_summary", run_dir / "validation_summary.json", f"neo4j_status={neo4j_status}"),
            ("analytics_metrics", snapshot_analytics, "stage4 run snapshot"),
            ("graph_viewer", snapshot_viewer, "stage4 run snapshot"),
            ("neo4j_import_summary", neo4j_import_summary, "stage4 Neo4j import counts"),
            ("topology_metrics", topology_metrics, "stage4 Neo4j topology metrics"),
        ],
    )
    if args.promote and all_valid:
        promote_pairs = [
            (snapshot_analytics, REPO_ROOT / "data" / "processed" / "analytics_metrics.csv"),
            (snapshot_viewer, REPO_ROOT / "docs" / "graph_viewer.html"),
        ]
        for source, dest in promote_pairs:
            if source.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)

    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
