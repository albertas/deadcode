# DEP 7 - Support SARIF output

**Status**: Proposed

**Type**: Feature

**Created**: 2026-11-12

## Problem statement

`deadcode` currently has exactly one report format: the text renderer in `deadcode/actions/get_unused_names_error_message.py`.
It emits one `filename:line:column: CODE Message` line per finding and supports only the text modifiers `--count`, `--quiet`, and `--fix`/`--dry`.
There is no format selector and no structured output channel, so every consumer must scrape the human-readable stream.

As a result, findings cannot be consumed natively by linter aggregators or IDEs. The only interoperability guidance on `main` is the README advice to run
`deadcode` alongside `ruff`; the repository contains no SARIF implementation, documentation, issue comment, or pull request on `main`.
Issue #100 (`https://github.com/albertas/deadcode/issues/100`) requests native SARIF output so that these tools can integrate without an adapter.
`vulture`, the closest comparable tool, also lacks SARIF support, so native support would become a documented differentiator for `deadcode`.

Scope: this DEP covers SARIF 2.1.0 output for findings. It does not cover a language server, a new analyser rule, auto-fix reporting, severity modelling,
or a docs-site DEP page.

## Considered alternatives

Five designs were compared against issue #100. The last one is selected; the other four are recorded with the reason they were not chosen.

### 1. Keep the text renderer only (status quo)

Leave `get_unused_names_error_message` as the only output path and expect consumers to parse the `filename:line:column: CODE Message` lines.

**Rejected (D5):** it does not satisfy issue #100 and leaves aggregators and IDEs without a machine-readable report. Scraping human-readable lines is
fragile and gives consumers no rule metadata, no locations objects, and no document version to validate.

### 2. Add a neutral JSON format first, SARIF later

Introduce a `--output-format json` document shaped for `deadcode` itself, then add `sarif` in a follow-up release.

**Rejected (D5):** it creates two formats and two migrations for the consumer that was actually requested, and there is no second consumer that would
justify the generic schema. The requested target already has a standard, so a private intermediate document adds work without adding capability.

### 3. Third-party adapter or wrapper script

Ship a small external converter that runs `deadcode` in text mode and translates the lines to SARIF.

**Rejected (D5):** it is not native support, adds an install step to every consumer, and depends on unmaintained external code. Issue #100 asks for
native integration, and a wrapper would still have to reimplement the finding-to-result mapping this DEP already specifies.

### 4. Boolean `--sarif` flag

Add a bare `--sarif` switch that turns SARIF output on.

**Rejected (D5):** a boolean cannot express a third format and is inconsistent with the project's option style. A `--output-format` family extends to
future formats without a new flag for each one, and its argparse choices give a clear usage error for unknown values.

### 5. Built-in SARIF 2.1.0 emitter behind `--output-format {text,sarif}` (selected)

Add `--output-format {text,sarif}` with default `text`, and implement a native SARIF 2.1.0 emitter in a sibling module. This is the smallest design that
satisfies "native integration": one flag, one new renderer, no change to the analyser, no new dependency (`json` is in the standard library), and no
consumer-specific adapter. It matches how `ruff` and `bandit` ship SARIF and leaves room for future formats (D5, D18).

The sub-decisions of the selected emitter were also compared:

- **Destination: stdout, no output file (D6).** Stdout is the existing output channel and shell redirection creates a file.
  Rejected: always writing `results.sarif`, which is surprising in CI; and an `--output FILE` option now, which adds path, overwrite, and encoding
  questions that issue #100 does not ask for and can be added later without changing the format.
- **Artifact URIs: absolute `file://` URIs via `Path(...).resolve().as_uri()` (D13).** This matches GitHub's request for resolved paths and the VS Code
  extension's workspace reconciliation, and `as_uri()` handles spaces and non-ASCII characters.
  Rejected: the raw CLI path, which can be relative and is not a valid URI; a relative URI plus `uriBaseId`/`originalUriBaseIds`, whose base is ambiguous
  outside the workspace root; and a bare POSIX path, which violates `uri-reference` expectations.
- **Region: the reported name range, not the `code_parts` removal range (D11).** The tight name range highlights exactly what the result is about.
  Rejected: `code_parts`, which can span a whole statement, differs from the reported name, and overlaps between findings; that mapping belongs to future
  fix support. The removal range is documented as future work rather than conflated with highlighting.
- **Columns: Unicode code points, not UTF-16 code units (D11).** `columnKind: "unicodeCodePoints"` matches both named consumers.
  Rejected: `utf16CodeUnits`, which needs a second conversion from code points with no benefit, and mapping the zero-based UTF-8 byte offset directly,
  which is wrong for any line with non-ASCII text before the name.
- **`fixes`, `suppressions`, and `fingerprints` are out of v1 (D20).** None of them is required for a valid, displayable log, and each needs data the
  renderer does not have. Rejected: emitting SARIF `fixes`, which needs a `code_parts`-to-`artifactChanges` mapping; `suppressions`, which are removed
  during analysis; and `partialFingerprints`, because a finding identity of `ruleId + filename + name` would merge alerts for names that are not unique
  across files or scopes. GitHub can compute fingerprints during an upload when they are absent.

### Other rejected user-visible options

These options were considered and rejected before the selected design was fixed:

- **Emit SARIF by default (D5).** Rejected: it breaks every existing consumer and every golden output test, and it would change the default contract of
the command without a flag a user can see.
- **Overload `--count` or `--quiet` for structured output (D5, D16).** Rejected: both are output modifiers with established behavior and tests, and
overloading them would conflate output selection with rendering.
- **A separate `[tool.deadcode.output]` table (D7).** Rejected: a new configuration shape with no precedent; the existing `[tool.deadcode]` key
normalization already maps `output-format` to `Args.output_format`.
- **Depend on `sarif_om` or `jschema_to_python` (D18).** Rejected: new runtime dependencies for a small constant document, when the project has only
`tomli` and `json` covers serialization.
- **A consumer-specific adapter module per consumer, such as one for GitHub and one for VS Code (D5, D21).** Rejected: spec-conformant SARIF 2.1.0 is
accepted by both, so separate modules would duplicate the same emitter and split the format by vendor.

## Chosen solution

Add an opt-in output-format selector to the command line:

```text
deadcode --output-format {text,sarif} PATH...
```

The default is `text`. In `text` mode the command behaves exactly as it does today, byte-for-byte, including `--count`, `--quiet`, `--fix`, `--dry`, colors,
and the success banner. In `sarif` mode the command writes a SARIF 2.1.0 log to stdout and nothing else, so shell redirection is enough to produce a file:

```shell
deadcode --output-format sarif . > results.sarif
```

There is no output-file option in the first version (D6). The log goes to the existing stdout channel, and consumers that need a path can use shell
redirection.

### Configuration

`[tool.deadcode]` accepts the same option as the CLI:

```toml
[tool.deadcode]
output-format = "sarif"
```

The existing key normalization in `parse_arguments.py` strips leading `--` and converts `-` to `_`, so this key maps to `Args.output_format` without a new
configuration concept. The existing truthy-scalar merge means a value from `pyproject.toml` overwrites the CLI value, including a CLI `--output-format text`;
this DEP keeps and documents that precedence (D7).

### Compatibility and exit status

SARIF mode is incompatible with the text-only output modifiers. Each of the following is a command-line usage error: a message on stderr and exit status 2.

- `--output-format sarif` with `--fix` (D15).
- `--output-format sarif` with `--dry` (D15). `--fix --dry` keeps working in `text` mode.
- `--output-format sarif` with `--count` (D16).
- `--output-format sarif` with `--quiet` (D16).

Validation happens after the `pyproject.toml` merge, so a configuration value cannot silently disable the check. The valid choices are enforced by argparse
with `{text,sarif}`, and an unknown value is also a usage error with exit status 2.

Exit statuses are unchanged (D17): 0 when no findings are reported, 1 when findings exist, 2 for invalid CLI usage, and 1 for an unexpected error. In
`sarif` mode the success banner is not printed, because a human line before or after the document would make stdout unparseable. An empty report is still a
complete document with one run, the tool driver, the rule table, and `results: []`, and it exits 0.

### Conformance targets

Conformance means a valid SARIF 2.1.0 log that both named consumers accept without vendor-specific extensions (D21): GitHub code scanning and the VS Code
SARIF Viewer. A generic linter aggregator that accepts SARIF 2.1.0 is covered by the same document. GitHub and the VS Code extension are chosen because the
issue names no specific product, and these two document their SARIF requirements and accept a plain file path.

## Scope

The following are not part of this DEP's implementation:

- SARIF `fixes`, `suppressions`, `fingerprints`, or `partialFingerprints` in v1 (D20).
- A language server, IDE plugin, or aggregator-specific adapter (D5, D21).
- A new analyser rule or auto-fix reporting; this DEP changes reported output only (D5).
- Severity modelling beyond SARIF's default `warning` (D10).
- SARIF 2.0 or earlier, multiple runs, `runAutomationDetails`, or an output-file flag.
- Implementing SARIF output, the `--output-format` flag, or any Python, test, configuration, or workflow change in this task.
- Changes to the docs-site DEP process page `docs/dep.md` beyond publishing this DEP.

## Implementation notes

### CLI wiring

The change is additive and touches three small places:

1. `deadcode/data_types.py`: add `output_format: Literal['text', 'sarif'] = 'text'` to `Args`.
2. `deadcode/actions/parse_arguments.py`: declare `--output-format` with `choices=('text', 'sarif')` and `default='text'`, and validate incompatible
   combinations after the `pyproject.toml` merge, before returning `Args`. A parser error gives the documented stderr message and exit status 2.
3. `deadcode/cli.py`: after parsing, dispatch between the unchanged `get_unused_names_error_message` for `text` and the new `get_sarif_report` for
   `sarif`. The SARIF branch must not print the success banner. The existing `RunResult` contract remains: findings return the document as the message and
   exit status 1; an empty report returns the document and exit status 0.

The new module is `deadcode/actions/get_sarif_report.py`; `get_unused_names_error_message` is not changed (D18). The renderer accepts the same
`Iterable[CodeItem]` and `Args` as the text renderer, applies the same `--only` filtering with `deadcode.visitor.ignore._match`, and returns a `str` produced by
`json.dumps`. No new dependency is needed because `json` and `pathlib` are in the standard library. No schema file is bundled: the build ships only `**/*.py`,
and the document is generated in code (D18).

### Document shape

The emitter builds one dictionary and serializes it. The top level has `$schema` set to `https://json.schemastore.org/sarif-2.1.0.json`, `version` set to
`"2.1.0"`, and `runs` containing exactly one run (D8). The run contains:

- `tool.driver.name`: `"deadcode"`.
- `tool.driver.version`: `deadcode.__version__`, the package version read through `importlib.metadata`.
- `tool.driver.informationUri`: `https://github.com/albertas/deadcode`.
- `tool.driver.rules`: the static rule table below, in the order given.
- `results`: one entry per finding after `--only` filtering, or an empty array.
- `columnKind`: `"unicodeCodePoints"`.

The run deliberately omits `invocations`, `originalUriBaseIds`, `runAutomationDetails`, and `properties.metrics`; none is required for a valid, displayable
result and each adds consumer-specific behavior (D8). A minimal populated document looks like this:

```json
{
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "deadcode",
          "version": "2.6.1",
          "informationUri": "https://github.com/albertas/deadcode",
          "rules": [
            {
              "id": "DC01",
              "name": "Variable",
              "shortDescription": {"text": "A variable is defined but never used."},
              "helpUri": "https://deadcode.readthedocs.io/en/latest/rules.html"
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "DC01",
          "ruleIndex": 0,
          "message": {"text": "Variable `unused_name` is never used"},
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {"uri": "file:///workspace/pkg/module.py"},
                "region": {"startLine": 4, "startColumn": 5, "endLine": 4, "endColumn": 16}
              }
            }
          ]
        }
      ],
      "columnKind": "unicodeCodePoints"
    }
  ]
}
```

### Rule metadata

`tool.driver.rules` is built from `ERROR_TYPE_TO_ERROR_CODE` in `deadcode/constants.py`, preserving its insertion order so `ruleIndex` is stable (D9). Each
entry has `id` equal to the `DCxx` code, `name` equal to the type label with underscores replaced by spaces and capitalized, `shortDescription.text` as
below, and `helpUri` set to `https://deadcode.readthedocs.io/en/latest/rules.html`. Results carry both `ruleId` and `ruleIndex`.

| Index | `id` | `name` | `shortDescription.text` |
| --- | --- | --- | --- |
| 0 | `DC01` | Variable | A variable is defined but never used. |
| 1 | `DC02` | Function | A function is defined but never used. |
| 2 | `DC03` | Class | A class is defined but never used. |
| 3 | `DC04` | Method | A method is defined but never used. |
| 4 | `DC05` | Attribute | An attribute is assigned but never used. |
| 5 | `DC06` | Name | A name is defined but never used. |
| 6 | `DC07` | Import | An import is never used. |
| 7 | `DC08` | Property | A property is defined but never used. |
| 8 | `DC09` | Unreachable body | A function body is unreachable. |
| 9 | `DC11` | Unused file | A Python file is never imported. |
| 10 | `DC12` | Commented out code | A comment contains commented-out code. |
| 11 | `DC` | Ignore expression | An ignore expression is unused. |
| 12 | `DC13` | Unreachable code | A statement after control flow is unreachable. |

### Result mapping

Each `CodeItem` becomes one result after the `--only` filter. The mapping is:

| Result field | Source |
| --- | --- |
| `ruleId` | `item.error_code`, for example `DC01`. |
| `ruleIndex` | The index of `item.error_code` in the static rule table above. |
| `message.text` | `item.message` when set; otherwise `"<Type> `<name>` is never used"`, with the same type capitalization as the text renderer. |
| `level` | Omitted. SARIF's default severity is `warning`; no severity model is added (D10). |
| `locations` | Exactly one location. It always has `physicalLocation.artifactLocation.uri`; it has a `region` when the finding has a usable position. |
| `fixes`, `suppressions`, `fingerprints`, `partialFingerprints` | Omitted in v1 (D20). |

The message does not contain `filename:line:column:`, rule codes, or ANSI escape sequences (D14). `ruleId` carries the code, and `locations` carries the
position. Examples of existing explicit messages that are passed through unchanged are the empty-file, commented-out-code, and unreachable-variant messages.

### Artifact URIs

`artifactLocation.uri` is `Path(item.filename).resolve().as_uri()` (D13). This produces an absolute `file://` URI with percent-encoding, resolves symlinks,
and handles spaces and non-ASCII characters. The raw CLI path is never written as a bare path or a relative URI, and `uriBaseId`/`originalUriBaseIds` are
not used.

### Regions and column conversion

`startLine` is `item.name_line`. `item.name_column` is a zero-based UTF-8 byte offset, so it must be converted to the one-based code-point column that
`columnKind: "unicodeCodePoints"` promises (D11):

1. Read the source file as bytes and split it into lines. Select `name_line - 1`.
2. Take the first `name_column` bytes of that line and decode them as UTF-8.
3. Set `startColumn = len(decoded_prefix) + 1`.
4. Set `endLine = startLine` and `endColumn = startColumn + len(item.name)`, both in code points.

If the file cannot be read, the line is missing, the byte offset is invalid, or the prefix cannot be decoded as UTF-8, the result still gets its location but
no `region`; the emitter never guesses a column. A finding without `name_line` or `name_column` also emits only `physicalLocation.artifactLocation.uri`
(D12). This covers `unused_file` (`DC11`) and any future finding without a position. Positionless findings are kept rather than dropped, because dropping them
would silently lose results.

### Empty results

When there are no findings after filtering, the emitter still returns a complete document: `$schema`, `version`, one run with `tool.driver` (including the
rules array), `results: []`, and `columnKind`. `cli.run` returns that document with exit status 0 and suppresses the success banner (D17). Consumers thus
always receive parseable JSON, and CI can still rely on exit status 0.

### Fixes, suppressions, and fingerprints are future work

The following are explicitly out of the first version and each has a blocker (D20):

- **`fixes`**: mapping `code_parts` to SARIF `artifactChanges` requires handling overlapping parts, partial imports, and multi-line removals. That is a
  separate design, and it is why `--fix` and `--dry` are usage errors with `sarif` (D15).
- **`suppressions`**: suppressed findings are removed during analysis, so the renderer never sees them and cannot mark them as suppressed.
- **`fingerprints` and `partialFingerprints`**: a stable identity needs more than a bare name. `CodeItem` equality and hashing use only `name`, and names are
  not unique across files or scopes, so a synthetic fingerprint could merge unrelated alerts. GitHub attempts to compute fingerprints during an upload when
  they are absent.

### Test plan for the future implementation

The DEP defines behavior but does not add tests, because this task changes no Python. The implementation that follows this DEP should add:

- `tests/cli_args/test_output_format.py`: parse `--output-format`, default to `text`, accept both choices, reject unknown values with exit status 2, map
  `[tool.deadcode] output-format` through the existing normalization, cover the config-over-CLI precedence, and assert usage errors for `--fix`, `--dry`,
  `--count`, and `--quiet` combined with `sarif` (D19).
- `tests/cli/test_sarif_output.py`: run the CLI and parse stdout as JSON; assert `$schema`, `version`, one run, and `tool.driver` presence; assert one result
  per finding, stable `ruleId`/`ruleIndex`, the message wording, and absolute `file://` URIs; cover an ASCII line and a non-ASCII line before the name for the
  byte-to-code-point conversion; assert that an `unused_file` result has a location without a region; assert empty results with exit status 0; and assert that
  no banner or other non-JSON text appears (D19).

Existing text-output tests stay unchanged. The future code change must also add `--output-format` to the README option table, the argparse `--help` output, and
`docs/features.md`, because those surfaces are contract-tested (D19, and the research constraint that README and feature documentation are checked).

## References

- Issue #100, "Support SARIF output": <https://github.com/albertas/deadcode/issues/100>
- OASIS SARIF 2.1.0 specification: <https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html>
- OASIS SARIF 2.1.0 JSON schema: <https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json>
- GitHub code scanning SARIF support: <https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning>
- VS Code SARIF Viewer: <https://github.com/microsoft/sarif-vscode-extension>
- Text renderer: `deadcode/actions/get_unused_names_error_message.py`
- Finding data model: `deadcode/visitor/code_item.py`
- CLI argument parsing: `deadcode/actions/parse_arguments.py`
- Published rule page: `docs/rules.md`
