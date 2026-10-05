# Reproducing the experiments

## Environment

The benchmark parsers are Linux x86_64 executables. The recorded runs used
CPython 3.10.20 for learning, PyPy 3.10.16 / 7.3.19 for the upstream evaluator,
and system Python 3.12.3 with Expat 2.6.1 for the XML oracle.

Setup requires Git, make, and [uv](https://docs.astral.sh/uv/). These commands
set up the artifacts and Python environments, run the tests, and verify the
saved results:

```sh
make setup
make test
make verify-results
```

Setup fetches XVada at `af167eb842ae79dacbe415bb32fcb62d9f4aa619` and
TreeVada at `44fb606bdc97e9145f7f730ca951ba24a15052f8`. It applies the
included setup-only patch to XVada. Older result metadata identifies the
same upstream revision plus this patch as `1b38aaf4`. The patch adjusts
imports and optional-client initialization; it does not change inference.

Python packages are installed in local environments. An import stub rejects
any attempted LLM use, so no API key is needed. Artifacts and environments
are not committed.

The XML worker defaults to `python3` on PATH. `GI_ORACLE_PYTHON` selects
an alternative interpreter linked to Expat 2.6.1:

```sh
export GI_ORACLE_PYTHON=/path/to/python-with-expat-2.6.1
```

The worker checks for Expat 2.6.1 to match the recorded oracle environment.

## Inspecting and replaying the XML result

Recorded files are under `results/`. Commands below create new output under
`runs/` and refuse to overwrite completed directories.

```sh
.venv/bin/python scripts/trace_xml_generalization.py oracle-check --verify
.venv/bin/python scripts/replay_xml_decisions.py causal-xml-control replay
.venv/bin/python scripts/analyze_causal_xml.py --output-dir runs/recorded-analysis
```

The first command checks all 70,829 recorded oracle answers, including
evaluation calls. The replay restores each saved call's grammar and random
state. The analysis checks the common trace prefix and recomputes paired
gains and losses.

The checkpoint and grammar files use Python pickle, which can execute code
when loaded. Readable grammar files and JSON verdicts are also provided.

## Full XML inference

```sh
.venv/bin/python scripts/trace_xml_generalization.py causal-xml-control
.venv/bin/python scripts/trace_xml_generalization.py causal-xml-one-decision \
  --allow-context generalize_letters_in_rule:15
.venv/bin/python scripts/trace_xml_generalization.py causal-xml-final-expansion \
  --allow-context expand_tokens:2
.venv/bin/python scripts/trace_xml_generalization.py causal-xml-repair-all \
  --allow-context all

for run in causal-xml-control causal-xml-one-decision causal-xml-final-expansion causal-xml-repair-all; do
  .venv/bin/python scripts/eval_causal_xml.py "$run"
done
.venv/bin/python scripts/analyze_causal_xml.py \
  --runs-dir runs --output-dir runs/new-analysis
```

Call identifiers refer to this artifact revision and seed set; other
subjects or revisions may assign them differently. The analysis checks
that the one-call and final-pass runs follow the control's trace until
their respective interventions begin.

The worker-backed learning runs took roughly 3–5 minutes each on my
machine. Evaluation has a 3 GiB address-space limit and a 10-second per-input
limit. These limits are reported separately from grammar rejection.

## Benchmark reproduction and overlap

```sh
bash scripts/run_xvada.sh xml-baseline \
  artifacts/xvada/experiments/xml/parse_xml \
  artifacts/xvada/experiments/xml/xml-train \
  artifacts/xvada/experiments/xml/xml-test

bash scripts/run_treevada.sh treevada-xml \
  artifacts/xvada/experiments/xml/parse_xml \
  artifacts/xvada/experiments/xml/xml-train \
  artifacts/xvada/experiments/xml/xml-test

.venv/bin/python scripts/check_benchmarks.py
.venv/bin/python scripts/recall_split.py results/repro-xml-r1/search.log \
  artifacts/xvada/experiments/xml/xml-train \
  artifacts/xvada/experiments/xml/xml-test
```

The runners accept an executable oracle and input directories. The same
command format applies to other benchmark subjects. Upstream inference launches a
process per oracle query and can take much longer than the worker-backed
XML experiment. The TreeVada lisp precision run is incomplete.

## JSON uniqueness and parser comparisons

Mini-XML and the parser comparisons additionally require a C compiler, Go,
a JDK, Node, Ruby with REXML, Perl with JSON::PP, jq, and system Python with
lxml. The additional setup and checks are:

```sh
make setup-all
.venv/bin/python scripts/validate_checkers.py
.venv/bin/python scripts/check_json_pilot.py
```

Setup builds Mini-XML at `0d5afc4278d7a336d554602b951c2979c3f8f296` and the
Go/Java checkers. Validation replays the input batches saved in `results/`
and stops if any verdict differs. Parser versions and defaults can affect
the answers even when the inputs are identical.

The JSON uniqueness run adds a duplicate-key check to the benchmark oracle:

```sh
bash scripts/run_xvada.sh json-unique \
  subjects/oracle_json_uniqkeys.py \
  artifacts/xvada/experiments/json/json-train \
  artifacts/xvada/experiments/json/json-test
```

The oracle retains the benchmark verdict when Python cannot parse a
benchmark-accepted input. The pilot's recall uses the 994 inputs without
duplicate keys. `check_json_pilot.py` computes this filtered score; the
runner reports recall on all 1,000 benchmark inputs.

Parser comparisons accept either a saved grammar or an existing input batch:

```sh
.venv/bin/python scripts/diff_probe_batch.py results/swap-xmlseeds-expat/search.log \
  --kind xml -n 500 --out runs/xml-differential
.venv/bin/python scripts/diff_probe_batch.py \
  --inputs results/parser-differential/inputs/json-mut-s1.jsonl \
  --kind json --out runs/json-mutations
```

Each output contains every verdict and a summary. The main XML set uses
namespace-aware Expat; plain Expat and Mini-XML are additional columns.
Known parser extensions are not harness failures. Missing answers, malformed
responses, unavailable tools, and abnormal checker exits stop the comparison.

## Recorded results and validation

Run metadata records the settings and script hashes used for each saved
measurement. [validation.json](results/validation.json) records the checks
I repeated with the scripts in this repository: full inference and
evaluation for the XML control and final-pass intervention, 16 decision
replays, all 70,829 reference oracle answers, and 17 parser-comparison batches.
The one-call and full-learning intervention results are also included, but
were not part of those full inference reruns.

The scripts stop on a missing oracle answer, unavailable checker, or worker
failure. Evaluation timeouts and memory limits are recorded separately from
grammar rejection.

`results/` contains the saved measurements, grammars, query traces, and
metadata. New runs write their output under `runs/`, which is gitignored.

The local-document study includes summary numbers only. Its corpus and
derived grammars are not included, so that study cannot be rerun from
this repository.
