# Grammar inference experiments and findings

## Overview

I explored [XVada](https://github.com/rifatarefin/xvada) and [TreeVada](https://github.com/rifatarefin/treevada), starting by reproducing benchmark results and checking the data. I then kept the XML training examples fixed and changed the parser used to answer XVada’s queries. When XML recall fell with Expat, I investigated how rejected queries affected the learned grammar. I also tested how requiring unique object keys affected JSON grammar inference and used learned grammars to generate inputs for comparing parsers.

The main finding was that a query could repeat an attribute name and be rejected, even though the proposed token was valid elsewhere. That rejection blocked a useful generalization. I replayed the learning step and changed duplicate-attribute handling at different stages to measure its effect on the final grammar.

This repository contains my scripts, grammars, query traces, and evaluations. [REPRODUCING.md](REPRODUCING.md) has the setup and commands; [results/README.md](results/README.md) maps the experiments to their saved files.

## Benchmark reproduction and data checks

Using XVada, I reproduced the reported XML and JSON precision and recall after rounding, and obtained 1.0 on both measures for while, turtle, and lisp. My TreeVada results were close to the reported values for JSON, XML, and turtle.

<b>Train-Test Overlap: </b> I checked all 17 test sets for exact duplicates. Each contained 1,000 distinct inputs. However, seven subjects included every training seed in the test set. Liquid had 12 overlapping inputs, and minic and tiny had one each.

To measure the effect, I computed recall again after excluding training inputs:

| XVada grammar | Full test set | Test set excluding seeds |
| --- | ---: | ---: |
| XML | 867/1,000 (86.70%) | 847/980 (86.43%) |
| JSON | 891/1,000 (89.10%) | 861/970 (88.76%) |

Removing the training examples changed recall by about 0.3 percentage points in these two runs. The effect is small, but the held-out score better reflects generalization to unseen inputs.

The [benchmark checks](scripts/check_benchmarks.py) and [recall calculation](scripts/recall_split.py) can be rerun on the saved grammars.

## XML inference with different parsers

The reproduction runs used the parsers supplied with the benchmark. I then compared the supplied XML parser with two XML parsing libraries, [Mini-XML](https://www.msweet.org/mxml/) and [Expat](https://libexpat.github.io/). I kept the same 20 training examples and changed the parser that accepted or rejected XVada’s generated queries.

| Parser used for learning | Recall on the 1,000 benchmark inputs | Precision against that parser |
| --- | ---: | ---: |
| Benchmark XML parser | 86.7% | 100.0% |
| Mini-XML, requiring a parsed document with no reported parsing errors | 100.0% | 40.5% |
| Expat, namespace processing off | 25.3% | 82.8% |

Precision here is the fraction of 1,000 generated samples accepted by the learning parser. Each row uses a different grammar and parser, so these scores do not share one definition of valid XML.

Expat's low recall was unexpected. Its learning log contained duplicate-attribute rejections. I wanted to find out whether these rejections blocked learning, rather than just appearing in the log.

The [parser-swap runs](results/README.md) contain the grammars and evaluations.

## Tracing the XML recall loss

### Replaying the generalization step

In the decision I investigated, one nonterminal, named `t6733` in the saved grammar, was used for attribute names, attribute values, and element text. XVada tried to broaden it to allow sequences of letters. Its replacement procedure put the same trial string into several selected positions.

A simplified example is:

```xml
<e FreshName="x" FreshName="y">FreshName</e>
```

Expat correctly rejects this document because `FreshName` occurs twice as an attribute name. But `FreshName` is a valid name by itself, and it is valid element text. The rejection comes from combining the replacements, not from the letter sequence alone.

<details>
<summary>Actual query from the saved decision</summary>

```xml
<e Uptiubqd="Uptiubqd" I="Uptiubqd" t="kRQFV" Uptiubqd="k"><b/></e>
```

</details>

I saved the grammar, trees, and random state before that generalization step, then reran it from that state. With unchanged Expat, it made 112 queries and found no generalization. When I renamed duplicate attributes before checking the document again, it made 420 queries and accepted a broader rule for sequences of letters. This change applied throughout that step, not just for one parser response.

The restriction also affected ordinary text. Expat accepts:

```xml
<e>FreshName</e>
```

The grammar learned with unchanged Expat rejects it, even though it has no attributes. Allowing duplicate-attribute repair during the final token-expansion pass (which broadens the rules for individual tokens) produced a grammar that accepts it. The shared nonterminal carried the restriction from attribute names into text.

### Measuring the effect on the final grammar

I compared four runs with the same seeds and learner settings. I used unchanged Expat to identify valid test inputs and check generated samples. I measured recall by checking how many valid held-out inputs each learned grammar could parse. Evaluation used Expat 2.6.1 with namespace processing disabled and no duplicate-attribute repair.

| Duplicate-name repair during learning | Valid held-out inputs accepted / 973 | Generated samples accepted by unchanged Expat / 1,000 |
| --- | ---: | ---: |
| None (control) | 234 | 828 |
| One saved generalization call | 310 | 885 |
| Final token-expansion pass | 842 | 803 |
| Throughout learning | 842 | 935 |

The 973-input set excludes 20 training examples and seven inputs rejected by Expat. Repair during the final token-expansion pass lets the grammar accept 608 additional inputs from this set. On the full 1,000-input benchmark, it gains 614 without losing any previously accepted inputs.

Changing only the final pass achieves the same recall as allowing repair throughout learning. This recovers much of the lost recall, but sampled precision falls from 82.8% to 80.3%. I used the repair to investigate the cause, not as a proposed fix.

<details>
<summary>Checks on the trace and replay</summary>

After adding query logging, I reran the unchanged experiment. It reproduced the same 69,829 learning queries, their answers, and the final grammar. The one-call and final-pass runs followed the control's trace until their respective interventions began. All 16 saved calls also reproduced their original outcomes without repair.

There were 187 duplicate-attribute rejections during learning, excluding cache hits. The separate evaluation queries are not included in this count.

</details>

### Checking for lost inputs

Allowing repair during just one generalization call revealed another problem. The resulting grammar accepted 150 benchmark inputs that the original grammar rejected, but rejected 85 that the original grammar accepted. It also accepted only seven of the 20 training examples, down from 18.

The trace showed a later alphanumeric expansion replacing the broader letter rule with a narrower one. For example, the original grammar accepts `<e>freshname</e>`, but the grammar from the single-step experiment rejects it. A successful generalization at one step did not guarantee that the final grammar would preserve previously accepted inputs.

The [comparison](results/causal-xml-analysis/summary.json) contains the gains, losses, and examples. [Decision replays](results/causal-xml-decision-replay/summary.json) record the individual calls.

## Follow-up experiments

### JSON with unique keys

To check whether the XML result extended to another format, I added a unique-key requirement to the benchmark JSON oracle and kept the same 30 training examples. This is an extra constraint, not a rule that every JSON parser enforces.

Both grammars (learned with and without the unique-key requirement) accepted 886 of the 994 benchmark inputs without duplicate keys. The XML recall loss did not repeat. This suggests that uniqueness alone does not explain the result; how the constraint interacts with the learner's queries also matters.

Sampled precision against the unique-key oracle fell from 99.5% to 94.3%. Each grammar nevertheless accepted all 500 samples generated by the other in a cross-check. This does not prove that they accept the same language, but it shows why a sampled precision difference needs further investigation.

The [JSON pilot](results/pilot-json-uniqkeys/cross.json) and [baseline evaluation](results/pilot-json-uniqkeys/baseline-cross.json) contain the measurements.

### Testing parsers with generated inputs

I also tested whether the learned grammars could produce useful inputs for comparing parsers. I generated 500 inputs from each grammar and counted cases where some parsers accepted an input while others rejected it. As a baseline, I made three batches of 500 inputs by inserting, deleting, or replacing one character in a seed.

For XML, I compared namespace-aware Expat, `lxml.etree`, Go’s `encoding/xml`, Java SAX, and Ruby’s REXML. For JSON, I compared Python’s `json`, Node’s `JSON.parse`, jq, Ruby’s `JSON`, Go’s `encoding/json`, and Perl’s `JSON::PP`.

| Input source | XML disagreements / 500 | JSON disagreements / 500 |
| --- | ---: | ---: |
| Expat-trained XML / jq-trained JSON grammar | 122 | 41 |
| One-character mutations, batch 1 | 8 | 18 |
| One-character mutations, batch 2 | 8 | 13 |
| One-character mutations, batch 3 | 10 | 19 |

For example, the jq-trained grammar generated `+2` and `04`. jq accepted both, while the other five JSON parsers rejected them. All 41 disagreements involved number syntax, not 41 separate bugs.

The XML results also depended on parser settings. Expat had namespace processing off during learning, but enabled in this cross-parser comparison. Of the 122 disagreement inputs, the learning oracle accepted 78, all involving namespace behavior. It rejected the remaining 44 for duplicate attributes. Some inputs had both problems.

Grammar samples produced disagreements more often than mutations, but did not reveal more kinds of disagreement. Learning also adds cost, so these counts do not establish an advantage under the same time or query budget. A disagreement alone does not establish a bug or security vulnerability.

The [saved parser verdicts](results/parser-differential/) include every tested input. The XML wrappers require one complete document, and a missing answer or checker failure stops the comparison rather than counting as rejection.


## Research question

I would like to explore how grammar inference can learn useful generalizations while respecting the constraints enforced by real parsers. The XML experiments raised a question I would like to investigate: when a parser rejects a query, how can the learner tell whether the proposed generalization is wrong or the query itself is poorly constructed?

Query construction would be one starting point, while keeping the parser’s answers unchanged. Possible approaches include trying different tokens in repeated positions or separating nonterminals used for attribute names from those used for element text. I am also interested in how the learner can preserve previously accepted inputs as the grammar changes.

I would evaluate these ideas across several seed sets and languages, measuring held-out recall, sampled precision, and query cost.

## Reproducing the experiments

The core experiments require Linux x86_64, Git, make, [uv](https://docs.astral.sh/uv/), and a Python interpreter linked to Expat 2.6.1.

```sh
make setup
make test
make verify-results
```

[REPRODUCING.md](REPRODUCING.md) contains the full commands and extra dependencies for parser comparisons.

## Experimental limitations

The controlled XML experiment uses one seed set. Renaming duplicate attributes helped isolate their effect on learning, but it is not a general repair strategy. It relies on Expat’s error messages, leaves DTD inputs (XML documents containing a document type definition) unchanged, and can alter a document’s meaning. A learner with only accept/reject feedback would need another way to identify why a query failed.

I estimated precision from 1,000 samples generated by each grammar, using the artifact’s sampling-depth rule. Since the samples differ between grammars, the scores reflect both the learned rules and how they were sampled. The different result in JSON also means that more languages and seed sets are needed to establish how widely the XML finding applies.
