---
bundle:
  name: now
  version: 0.1.0
  description: Adds the `now` tool (current UTC time as ISO-8601) to a session.

# Thin bundle pattern (study guide Chapter 2 §2.6): include foundation, add
# only what foundation does not. Foundation provides orchestrator, context
# manager, providers, and the standard tool set; we just contribute one tool.
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

tools:
  - module: tool-now
    # Local source URI for development. In a published bundle this would be
    # `git+https://github.com/<owner>/amplifier-module-tool-now@<ref>`.
    # Source URI forms documented in Chapter 2 §2.5.
    source: file:///home/user/amplifier-universe/verification/reader-test/tool-now
---

# Now Tool

This bundle mounts a single tool, `now`, which returns the current UTC time as
ISO-8601. It is a minimal example of the thin-bundle pattern — everything
heavy comes from `foundation`, this bundle only adds a tool.

@foundation:context/shared/common-system-base.md
