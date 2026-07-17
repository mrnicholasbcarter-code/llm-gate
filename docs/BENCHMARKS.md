# Benchmark methodology

This document defines how to collect comparable measurements. It intentionally
contains no latency claim or service-level objective. A result is meaningful
only with the commit, Python version, environment, fixture, and command recorded
alongside it.

## Measurements

1. **Contract normalization** — serialize/deserialize representative `TaskSpec`
   and `RoutingDecisionContract` payloads.
2. **Eligibility** — normalize a fixed catalog/runtime fixture and explain all
   candidates, including capability, freshness, quota, auth, and policy
   exclusions.
3. **Compatibility routing** — run `Gate.route` on a fixed prompt corpus with
   logging disabled or directed to a temporary path.
4. **Proxy overhead** — use a local stub upstream, measure request handling
   separately from upstream response time, and test both non-streaming and
   streaming payloads.
5. **Adapter failure behavior** — inject timeout, malformed, stale, and
   unavailable runtime responses; record state and readiness, not just elapsed
   time.

Provider network time, model generation quality, and local decision overhead
must not be mixed into one number. The proxy's upstream and model results are
external variables, so provider benchmarks must identify provider/model,
region, request shape, and sampling date.

## Protocol

- Pin the repository commit and Python version; record OS, CPU, memory, and
  dependency lockfile hash.
- Use fixed, checked-in fixtures and a fixed policy version for local routing
  measurements.
- Warm up before collecting samples; report sample count, median, p95, p99,
  minimum, maximum, and spread. Report units and whether serialization/logging
  are included.
- Run enough repetitions to show variance and repeat the complete run at least
  three times. Do not publish a single best run.
- Separate cold-start and warm-process results.
- For proxy tests, use a local deterministic stub and report stub response time
  independently from gateway overhead.
- Publish raw JSON/CSV alongside a rendered table, plus the exact command.
- Treat regression thresholds as proposed until a baseline exists; thresholds
  must be justified by repeated measurements rather than copied claims.

## Baseline command

The existing smoke benchmark is a local routing exercise:

```bash
.venv/bin/python benchmarks/test_throughput.py
```

It is not a production performance benchmark and does not measure a provider.
For a new result, capture the output with:

```bash
.venv/bin/python benchmarks/test_throughput.py | tee benchmark-results/<commit>.txt
```

Before publishing, add the environment manifest and fixture/policy versions to
the result file. Do not put API keys, raw prompts, completions, or authorization
headers in benchmark artifacts.

## Reporting template

```text
Commit:
Date (UTC):
Python:
OS / CPU / memory:
Dependency lockfile:
Fixture and policy version:
Command:
Warm-up / samples / repetitions:
Cold or warm process:
Logging enabled:
Upstream stub or provider (if any):
Results (unit, median, p95, p99, min, max):
Known limitations:
```
