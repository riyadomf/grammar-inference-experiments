# Recorded evidence

These are the saved measurements behind the [research summary](../README.md).
They include grammars, query traces, checkpoints, and individual input verdicts,
not just the final scores. New runs write to the gitignored `runs/` directory
so they remain separate from this evidence.

| Directory | Contents |
| --- | --- |
| `repro-*`, `treevada-*` | Benchmark grammars, evaluation output, and run settings. TreeVada lisp evaluation is incomplete. |
| `swap-xmlseeds-*` | XML inference with the benchmark seeds and different parsers. |
| `causal-xml-control`, `causal-xml-one-decision`, `causal-xml-final-expansion`, `causal-xml-repair-all` | Controlled XML runs, query traces, saved decisions, and per-input evaluation. |
| `causal-xml-analysis`, `causal-xml-decision-replay`, `causal-xml-worker-check` | Paired comparisons, replay outcomes, and oracle validation. |
| `reference` | Historical strict XML oracle answers and grammar used to check the control. |
| `pilot-json-uniqkeys` | JSON uniqueness experiment and its baseline comparison. |
| `json-jq-lenient`, `json-py-strict` | JSON inference under alternative parsers. |
| `parser-differential` | Public input batches and complete parser verdicts. |

`local-corpus-aggregates.json` contains summary numbers from the local-document
study. The documents and grammars learned from them are not included.

Directory names are run identifiers, not claims about standards compliance.
In particular, `json-py-strict` used Python's default JSON settings, which
accept `NaN`. The Mini-XML `strict` wrapper rejects documents that produce
diagnostics; the `lenient` wrapper accepts them if Mini-XML returns a tree.
In the controlled XML runs, `strict` means unchanged Expat 2.6.1 with
namespace processing off, compared with the duplicate-name intervention.

Large traces are gzip-compressed. Grammar and checkpoint files use pickle
and should only be loaded from a trusted source. Original run metadata is
retained, including historical script hashes. Paths in exported text files
have been made relative; `provenance.json` records their original and exported
hashes. `checksums.json` covers the saved evidence files.
`validation.json` records the checks I repeated with this repository's scripts.

The reference oracle log contains 69,829 learning queries followed by 1,000
evaluation queries. The control trace records learning separately, so counts
from the two stages can be checked independently.

Run `make verify-results` to check the XML tables, differential counts, and
file hashes. See [REPRODUCING.md](../REPRODUCING.md) to rerun the experiments.
