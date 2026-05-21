# Plugin Sandbox Boundary

WeiTesting currently uses process-level plugin isolation. It is useful for operational guardrails, but it is not a container, VM, or malicious-code security boundary.

## Current Boundary

- Plugins run through a child Python process with a dedicated temporary working directory.
- The runner strips token, secret, password, and key-like environment variables before execution.
- The child process uses sandbox-local `TEMP`, `TMP`, `HOME`, and `USERPROFILE`.
- Built-in external calls require `CALL_EXTERNAL`, `networkMode=ALLOWLIST`, and matching `allowedHosts`.
- Payload size and runtime timeout are enforced before and during execution.

## What This Does Not Guarantee

- It does not provide OS-level filesystem isolation.
- It does not block every absolute path access by kernel policy.
- It does not create a network namespace or firewall rule.
- It does not apply cgroups, seccomp, AppArmor, SELinux, Windows Job Object hardening, or VM isolation.
- It does not make arbitrary untrusted code safe to execute.

## Policy Contract

- `permissions` must explicitly include the capability the entry point needs.
- `CALL_EXTERNAL` is required before any network operation.
- `allowedHosts` must be populated when `networkMode=ALLOWLIST`.
- Legacy loose sandbox configs can be read for diagnostics but should not be treated as executable production policy.

## Production Hardening Path

For third-party or untrusted plugins, move execution into a container, VM, or microVM with:

- read-only root filesystem and mounted input/output directories
- non-root user
- CPU, memory, process, and disk quotas
- network deny by default with an allowlist
- signed plugin packages or pinned images
- audited artifact handoff back into WeiTesting
