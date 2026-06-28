---
name: <workflow-name>
description: >-
  <one line: what this workflow does and when to use it>
argument-hint: "<what the user should provide, e.g. a folder path>"
---

# <Workflow name>

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| User data | `input/` | material to process |

## Process
1. <step>
2. <step — mark any human gate explicitly>

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Result | `output/` | <format> |

## Gates
- <every destructive/irreversible step requires explicit user "yes">

## Run log
Append one line to `output/run-log.csv`: `timestamp,<workflow-name>,<action>,<result>`.
