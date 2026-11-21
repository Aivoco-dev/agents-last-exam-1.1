# Agents’ Last Exam v1.1

**122 tasks · ale_run and ALE-Claw · Vision Large with continual learning**

## Start

1. Install Python 3.9+, Git, uv, and the official ALE host dependencies on a supported Linux host. The launcher checks out the pinned release and installs the locked Python dependencies.
2. Set `VISPARK_LAB_API` in this repository’s `.env`. Copy `.env.example` if needed.
3. Set `ALE_ENVIRONMENT` in `.env` to an official ALE environment YAML. Run `./start --prepare` to download the pinned environment examples. Configure the provider using the upstream setup guide. Full runs need Linux, Windows, and GPU coverage.
4. Double-click `Start.command` or run `./start` to run all 122 tasks. Set `BENCH_WORKERS` in `.env` to change default concurrency.

```sh
./start --plan
./start --task visual_media/music_transcription
```

ALE provisions and grades each environment. Each task has a five-hour execution limit and a fresh Vision memory session.

## Results

Open `results/<run>/summary.json` for the mean rubric score, strict pass rate, and ungraded tasks. `run.json` records the release, settings, and task IDs. Each task directory contains the official evaluator output, runner log, and Vision usage.

[Official ALE v1.1 setup](https://github.com/rdi-berkeley/agents-last-exam/blob/main/docs/releases/v1.1.md)
