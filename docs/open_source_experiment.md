---
orphan: true
---

# Running deadcode on large open source Python projects

This page describes a planned experiment that will run deadcode on popular and large open source Python projects. No results have been collected yet. Every result table on this page is a template to be filled after the experiment.

## Introduction

The experiment asks a simple question: how does deadcode behave when it is pointed at real, large codebases instead of small examples? The page records the repository selection, the metrics, the measurement procedure, and the reporting format, so the experiment can be repeated and compared later. Nothing on this page is a measured result.

## Why run this experiment

The experiment has two goals:

- Find deadcode limitations that only appear in realistic code, such as dynamic framework patterns, generated modules, and plugin systems.
- Turn useful findings into improvements in deadcode itself and, where a finding is confirmed, in the analysed projects.

The experiment is not meant to do the following:

- Automatically fix large amounts of upstream code.
- Compare deadcode with other analysers or rank tools against each other.
- Claim that a finding is a defect before a human has reviewed it.

## Experiment questions

1. Does runtime grow roughly linearly with lines of code, or does it grow faster on very large repositories?
2. Do findings per thousand lines differ by project type, such as a web framework, a data library, or a plugin-heavy application?
3. Do dynamic framework patterns produce more false positives than plain library code?
4. Do runs complete without crashes or unusable output on every candidate repository?

## How repositories are selected

Candidates are chosen with the following criteria:

- The repository is public.
- The licence is permissive or otherwise open enough to read, analyse, and quote small excerpts.
- The project supports at least one Python version that deadcode supports (`>=3.10`).
- The project is large or popular enough that a result matters to real users.
- The code can be analysed as files without importing the project or running its test suite.
- The sample mixes application styles so that size and project type can be told apart.

Size, stars, release age, and Python support are recorded at experiment time together with the pinned commit SHA, not guessed in advance.

## Candidate repositories

The starting sample is ten repositories: seven large or very large projects and three smaller controls.

| Repository | Tier | Why it is in the sample | Limitations it may expose |
|---|---|---|---|
| `django/django` | Very large | Widely used web framework with many internal packages and an app registry. | Dynamic app loading, settings references, and framework entry points. |
| `home-assistant/core` | Very large | Large application with many integration modules discovered at runtime. | Plugin discovery, dynamic imports, and string-based registration. |
| `apache/airflow` | Very large | Large orchestration project with operators, plugins, and entry points. | Metaclasses, entry-point loading, and generated or vendored code. |
| `pandas-dev/pandas` | Large | Widely used data library with generated APIs and extension modules. | Generated bindings, re-exports, and code that is hard to resolve statically. |
| `scikit-learn/scikit-learn` | Large | Widely used machine-learning library with Cython and estimator classes. | Generated or compiled-adjacent code, inheritance, and dynamic attributes. |
| `ansible/ansible` | Very large | Large automation project with a plugin loader and many modules. | Loader-based resolution, string references, and vendored collections. |
| `pytest-dev/pytest` | Large | Test tool with plugin hooks, fixtures, and dynamic collection. | Hooks, fixture registration, and code used only through plugins. |
| `pydantic/pydantic` | Large | Popular library that builds models and validators at runtime. | Metaclasses, generated models, and names used only at runtime. |
| `pallets/flask` | Medium control | Smaller, well-structured framework with familiar extension points. | A baseline for comparing framework overhead against the very large projects. |
| `psf/requests` | Medium control | Compact, popular library with a simpler static structure. | A baseline for checking whether a result scales with size or is project-specific. |

This list is a starting plan. The commit SHA and repository metadata are pinned before measurement, and a candidate is replaced only by recording why it could not be used.

## Experiment design

The diagram shows the run order that the measurement procedure will detail.

```text
Choose repositories
        |
        v
Pin commits and record metadata
        |
        v
Prepare a clean pinned environment
        |
        v
Run baseline measurement (neutral working directory)
        |
        v
Run project-config measurement (repository root)
        |
        v
Collect runtime, findings, memory, and parse failures
        |
        v
Review a sample of findings for false positives
        |
        v
Optionally run fixing on a disposable copy
        |
        v
Report the results in the template
```

## Metrics

Every metric below is collected for both configuration modes, and every value is reported with the mode it belongs to.

| Metric | Type | Unit | How it is collected |
|---|---|---|---|
| Wall-clock runtime | Primary | seconds | `/usr/bin/time -v` around the whole deadcode command; median of three warm runs, cold run reported separately |
| Finding count | Primary | findings | integer from `--count`, or number of finding lines in normal output; count after configured filtering; state the mode |
| Findings per thousand Python lines | Primary | findings per 1000 lines | `finding_count / analysed_python_lines * 1000` using the file list from `-v` |
| Rule distribution | Secondary | findings per `DCxx` rule | count finding lines by `DCxx` token using `--no-color` output; report absolute counts and shares |
| Analysed files and lines | Secondary | files, lines | count `.py` paths listed by `-v`; sum `wc -l` over those files |
| Parse failures | Secondary | count, share of analysed files | count `Failed to parse` error lines on stderr |
| Peak memory | Secondary | MiB | maximum resident set size from `/usr/bin/time -v` |
| Exit status | Secondary | status code | `0` no findings, `1` findings or unexpected error, `2` invalid usage |
| False-positive rate | Secondary | share of reviewed sample | `false_positive_count / reviewed_count` on a stratified sample of up to 30 findings per repository, two reviewers |
| Fix success rate | Secondary | share of fixing runs | on a disposable copy only: share of runs whose `Removed N` is greater than zero, whose edited files still parse, and whose rerun count is lower; record file deletions |

### Wall-clock runtime

Definition: the elapsed time in seconds from process start to process exit for one complete deadcode invocation.

Collection: wrap the command with `/usr/bin/time -v`, for example `/usr/bin/time -v deadcode <repository-path> -v --no-color`. Run the command once cold, immediately after boot or after clearing the file cache, and record that value separately. Then run it three times warm and report the median of the three warm values, not their mean. The same commands and the same machine are used for every repository.

### Finding count

Definition: the number of findings that deadcode reports after all configured filtering, in one configuration mode.

Collection: run `deadcode <repository-path> --count --no-color` and read the integer it prints. As a fallback, count the finding lines in normal output with `deadcode <repository-path> --no-color | grep -c 'DC[0-9][0-9]'`. Both forms must agree. Record which configuration mode produced the count, because an exclusion in `[tool.deadcode]` changes it.

### Findings per thousand Python lines

Definition: the finding count normalised for repository size, so repositories of different sizes can be compared.

Formula: `finding_count / analysed_python_lines * 1000`, where `analysed_python_lines` is the line count of the same files that deadcode analysed, not the line count of the whole checkout.

Collection: take the finding count from the previous metric, take the analysed file list from the `-v` output, and sum those files with `wc -l`. Report the result with two decimal places and the mode.

### Rule distribution

Definition: how the findings are spread across the individual rules, so a single rule cannot silently dominate a result.

Collection: from `--no-color` output, count the `DCxx` tokens per finding line, for example with `grep -oE 'DC[0-9]{2}' deadcode-output.txt | sort | uniq -c | sort -rn`. The codes are printed as `DC01` to `DC09` and `DC11` to `DC13`; the `DC` marker used to ignore a finding is not a finding and is not counted. Report absolute counts and shares per mode.

### Analysed files and lines

Definition: the number of Python files and Python lines that deadcode actually analysed in one run.

Collection: run `deadcode <repository-path> -v --no-color`; the verbose log on stderr lists the files to be checked, and the `.py` paths in that list are the analysed files. Count them, then sum their line counts with `wc -l`. Compare the file count with the repository's own Python file count and record every difference, including excluded and unparsable files.

### Parse failures

Definition: the number of files that deadcode could not parse and skipped.

Collection: capture stderr and count lines that match `Error: Failed to parse <filename> file, ignoring it.`, for example with `grep -c 'Error: Failed to parse' deadcode.stderr`. Report the count and its share of analysed files as `parse_failures / analysed_files`. A parse failure does not change the exit status, so it must be counted from the log rather than inferred from the status.

### Peak memory

Definition: the maximum resident set size of the deadcode process during one run.

Collection: read the `Maximum resident set size` line from the `/usr/bin/time -v` output of the timed runs. Convert kilobytes to MiB by dividing by 1024. Report the value from the same run whose runtime is reported, and report the cold run separately.

### Exit status

Definition: the process status code that deadcode returns for one invocation.

Collection: capture the status immediately with `echo $?` after the command. The values are `0` when no findings are reported, `1` when findings are reported or an unexpected error occurs, and `2` for invalid usage such as an unknown option. A parse failure alone does not change the status. Record the status for both modes, because findings in either mode are a result.

### False-positive rate

Definition: the share of reviewed findings that do not identify unused or dead code, or that the project intentionally keeps and documents.

Formula: `false_positive_count / reviewed_count` on the reviewed sample.

Collection: draw a stratified sample of up to 30 findings per repository, with the strata being the `DCxx` rules that occur in that repository. Two reviewers label each finding independently as true positive or false positive, then discuss disagreements and record the agreed labels. The reported value is the agreed false-positive share of the sample, with the sample size, and it applies to the sample, not to all findings.

### Fix success rate

Definition: the share of fixing runs that produced a plausible and still valid result.

Collection: run only on a separate disposable copy of the pinned checkout, for example `cp -a <repository-path> <copy-path>`, then `deadcode <copy-path> --fix --no-color` and capture the `Removed N` line. A run counts as successful only when `N` is greater than zero, every edited file still parses via `python -m compileall -q <copy-path>`, and a rerun of `deadcode <copy-path> --count --no-color` reports a lower count. Record every deleted file and every edit that fails to parse. Never run `--fix` on the recorded checkout, and delete the copy afterwards.

## Measurement procedure

The procedure below is the exact run order for every candidate repository. It uses only existing deadcode command line options and `[tool.deadcode]` settings.

1. Freeze the deadcode version and commit, the Python version, the operating system, the CPU, the memory, and the exact command lines.
2. Clone each candidate and check out the pinned commit. Record the commit SHA, licence, release tag, and default branch.
3. Create a clean environment with the pinned dependencies, install deadcode from the pinned source or wheel, and record `deadcode --version`.
4. Run the baseline mode from an empty temporary directory with `deadcode <repository-path> -v --no-color`, so no target `pyproject.toml` is read.
5. Run the project-config mode from the repository root with the same arguments, so `[tool.deadcode]` applies. Record the effective configuration.
6. For each mode, capture stdout, stderr, and the exit status. Run `--count` as a cross-check on the finding count.
7. Time one cold run and three warm runs per mode with `/usr/bin/time -v`, and report the median warm runtime and the peak memory.
8. Derive the finding count, rule distribution, analysed files and lines, findings per KLOC, and parse-failure share from the captured outputs.
9. Draw the false-positive sample, have two reviewers label it, discuss disagreements, and record the agreed labels.
10. On a separate disposable copy, run `--fix`, capture `Removed N`, validate the edited files with `python -m compileall` or `ast.parse`, and rerun `--count`.
11. Fill the reporting template, record anomalies and failed candidates, and keep the raw logs with the experiment record.

The two configuration modes are defined as follows. In baseline mode the working directory is an empty temporary directory, so deadcode reads no `pyproject.toml` from the analysed project. In project-config mode the working directory is the repository root, so `[tool.deadcode]` is applied exactly as a project user would see it. deadcode reads `pyproject.toml` only from the current working directory and has no `--config` option. The file walker includes vendored and generated directories because it has no `.gitignore` handling, so every exclusion must be explicit and recorded with `--exclude` or the equivalent `[tool.deadcode]` key.

## Fairness and reproducibility

The following controls keep the comparison fair and the result repeatable:

- Tool and repository versions are pinned, and the record names the deadcode version, the deadcode commit, and every repository commit.
- All runs happen on one documented machine with the recorded CPU, memory, and operating system.
- Every repository is analysed with the same Python version (3.12) and the same deadcode build.
- No other workload runs during a timed measurement.
- The first run is cold and is reported separately; the reported runtime is the median of the following three warm runs.
- The configuration mode is stated for every reported value, and both modes are reported for every repository.
- File discovery rules are identical across repositories, with no implicit skips.
- Every exclusion is explicit, recorded with its source, and applied in both modes or only in one mode with the reason recorded.

The file walker includes vendored and generated directories, so an exclusion that is not recorded would silently change the analysed file set and the findings per KLOC.

## Reporting template

Every table below is empty on purpose. To be completed after the experiment.

Table 1 records one row per candidate repository and configuration mode. `Baseline` is the neutral-directory mode and `Project config` is the repository-root mode.

| Repository | Commit | Mode | Runtime (s) | Findings | Findings per KLOC | Peak memory (MiB) | Parse failures | Reviewed false-positive rate | Exit status |
|---|---|---|---|---|---|---|---|---|---|
| `django/django` | - | Baseline | - | - | - | - | - | - | - |
| `django/django` | - | Project config | - | - | - | - | - | - | - |
| `home-assistant/core` | - | Baseline | - | - | - | - | - | - | - |
| `home-assistant/core` | - | Project config | - | - | - | - | - | - | - |
| `apache/airflow` | - | Baseline | - | - | - | - | - | - | - |
| `apache/airflow` | - | Project config | - | - | - | - | - | - | - |
| `pandas-dev/pandas` | - | Baseline | - | - | - | - | - | - | - |
| `pandas-dev/pandas` | - | Project config | - | - | - | - | - | - | - |
| `scikit-learn/scikit-learn` | - | Baseline | - | - | - | - | - | - | - |
| `scikit-learn/scikit-learn` | - | Project config | - | - | - | - | - | - | - |
| `ansible/ansible` | - | Baseline | - | - | - | - | - | - | - |
| `ansible/ansible` | - | Project config | - | - | - | - | - | - | - |
| `pytest-dev/pytest` | - | Baseline | - | - | - | - | - | - | - |
| `pytest-dev/pytest` | - | Project config | - | - | - | - | - | - | - |
| `pydantic/pydantic` | - | Baseline | - | - | - | - | - | - | - |
| `pydantic/pydantic` | - | Project config | - | - | - | - | - | - | - |
| `pallets/flask` | - | Baseline | - | - | - | - | - | - | - |
| `pallets/flask` | - | Project config | - | - | - | - | - | - | - |
| `psf/requests` | - | Baseline | - | - | - | - | - | - | - |
| `psf/requests` | - | Project config | - | - | - | - | - | - | - |

Table 2 records the rule distribution for the experiment as a whole. To be completed after the experiment.

| Rule | Findings | Share |
|---|---|---|
| `DC01` | - | - |
| `DC02` | - | - |
| `DC03` | - | - |
| `DC04` | - | - |
| `DC05` | - | - |
| `DC06` | - | - |
| `DC07` | - | - |
| `DC08` | - | - |
| `DC09` | - | - |
| `DC11` | - | - |
| `DC12` | - | - |
| `DC13` | - | - |

Results narrative: the experiment will report which repositories completed, which limitations appeared, and how the false-positive sample was judged. To be completed after the experiment.

## Threats to validity

- Repository selection is purposive rather than random, so the sample describes these projects and does not estimate a population average.
- A pinned commit is a snapshot of a moving project, and later commits may behave differently.
- Manual labels are subjective, and two reviewers can still share a blind spot.
- Wall-clock timing depends on hardware, operating-system state, and cache behaviour, so absolute seconds compare poorly across machines.
- `--fix` results show that the edited copy still parses; they do not prove that the project's own tests still pass.
- The results are descriptive and do not establish a general accuracy rate for deadcode.

## How results will be used

Findings become triaged issues for deadcode. Reproducible examples become regression tests. Confirmed false positives become documentation or configuration guidance, such as an ignore marker or a `[tool.deadcode]` exclusion. Confirmed true positives in a target project become a proposed upstream change after the maintainers have reviewed it.

## Out of scope

- Comparing deadcode with vulture or any other tool.
- Changing deadcode code as part of the experiment.
- Running upstream test suites.
- Opening upstream pull requests.
- Publishing raw third-party source or logs that are not licence-compatible.
