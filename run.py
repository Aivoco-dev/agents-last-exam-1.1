import argparse
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from bootstrap import REPO, ensure_env, require_tools, checkout, clean_environment, result_directory
from cl_adapter import bridge, load_key, read_env

URL = "https://github.com/rdi-berkeley/agents-last-exam"
REVISION = "2e91edd3cd26baa35a38127c90c8e5241dfbe62f"


def run_task(task, key, output, upstream, environment, env):
    task_dir = output.joinpath(*task.split("/"))
    task_dir.mkdir(parents=True)
    agent = task_dir / "agent.yaml"
    config = task_dir / "experiment.yaml"
    with bridge(key, limit=600) as (url, token, vision):
        agent.write_text(json.dumps({
            "harness": "ale_claw", "executor": "local", "model": "openai/vispark/vision-large",
            "config": {
                "base_url": url, "api_key": "${env:VISION_ADAPTER_TOKEN}", "max_turns": 500,
                "disable_delegate_gui": True, "disabled_tools": ["delegate_general", "web_search", "web_fetch"],
            },
        }, indent=2))
        task_file = task_dir / "tasks.txt"
        task_file.write_text(task + "\n")
        config.write_text(json.dumps({
            "name": "vision-cl-" + task.rsplit("/", 1)[-1],
            "agents": [str(agent)], "environment": str(environment), "tasks": str(task_file),
            "output": {"root": str(task_dir / "run")}, "concurrency": 1,
            "wall_time_s": 18000, "auto_resume": False, "max_attempts": 1, "cleanup_mode": "delete",
        }, indent=2))
        try:
            with (task_dir / "runner.log").open("w") as log:
                result = subprocess.run(
                    ["uv", "run", "--no-sync", "python", str(REPO / "ale_entry.py"), "run", str(config)],
                    cwd=upstream, env=env | {"VISION_ADAPTER_TOKEN": token},
                    stdout=log, stderr=subprocess.STDOUT,
                )
            print(f"{task} | ALE runner exit {result.returncode}", flush=True)
            if result.returncode or not vision.report()["calls"]:
                return None
            for path in (task_dir / "run").rglob("eval_result.json"):
                evaluation = json.loads(path.read_text())
                score = evaluation.get("score")
                if evaluation.get("eval_status") == "success" and isinstance(score, (int, float)) and math.isfinite(score):
                    return score
            return None
        finally:
            (task_dir / "vision-usage.json").write_text(json.dumps(vision.report(), indent=2) + "\n")


def main():
    settings = read_env(REPO)
    parser = argparse.ArgumentParser(description="Agents’ Last Exam v1.1 with ale_run and Vision continual learning")
    parser.add_argument("--workers", type=int, default=settings.get("BENCH_WORKERS") or "1")
    parser.add_argument("--task", action="append", help="Published task ID, including its domain if listed")
    parser.add_argument("--environment", default=settings.get("ALE_ENVIRONMENT") or None, help="Path to an official ALE environment YAML")
    parser.add_argument("--prepare", action="store_true", help="Download the pinned release and install its dependencies")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    official = [line for line in (REPO / "tasks.txt").read_text().splitlines() if line and not line.startswith("#")]
    selected = args.task or official
    if len(set(official)) != 122:
        raise RuntimeError("Expected the 122-task ALE v1.1 manifest")
    if args.workers < 1 or len(set(selected)) != len(selected) or not set(selected) <= set(official):
        parser.error("Use positive workers and unique published task IDs")
    if args.plan:
        print(json.dumps({
            "release": "v1.1", "harness": "ale_run / ALE-Claw + Vision CL",
            "workers": args.workers, "task_count": len(selected), "tasks": selected,
        }, indent=2))
        return 0
    if not args.prepare:
        ensure_env()
        key = load_key(REPO)
        if not args.environment:
            parser.error("Set ALE_ENVIRONMENT in this repo's .env or pass --environment")
    require_tools("git", "uv")
    env = clean_environment()
    source = checkout(URL, REVISION)
    subprocess.run(["uv", "sync", "--all-packages", "--locked"], cwd=source, env=env, check=True)
    if args.prepare:
        print(f"Official environment examples: {source / 'configs' / 'environments'}")
        return 0
    environment = (REPO / os.path.expanduser(args.environment)).resolve()
    if not environment.is_file():
        parser.error(f"Environment file does not exist: {environment}")
    output = result_directory(
        benchmark="Agents' Last Exam", harness="ale_run / ALE-Claw + Vision CL",
        release="v1.1", tasks=selected, workers=args.workers, revision=REVISION,
        wall_time_s=18000, environment=environment.name,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        outcomes = list(executor.map(lambda task: run_task(task, key, output, source, environment, env), selected))
    scores = [score for score in outcomes if score is not None]
    summary = {
        "planned": len(selected), "graded": len(scores),
        "ungraded": [task for task, score in zip(selected, outcomes) if score is None],
        "mean_rubric_score": sum(scores) / len(selected),
        "strict_pass_rate": sum(score == 1.0 for score in scores) / len(selected),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return int(len(scores) != len(selected))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Benchmark startup or run failed: {error}", file=sys.stderr)
        raise SystemExit(1)
