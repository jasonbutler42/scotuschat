# Windows PostgreSQL 18 Setup — Evidence Record

**Date:** 2026-08-13
**Task:** Phase 46, Plan 02, Task 1 (blocking human-action checkpoint)
**Purpose:** Record the Windows-side configuration that makes the `postgresql-x64-18`
service reachable from WSL, satisfying D-02 (WSL-native code connects to a real
Windows Postgres service instead of the portable `pg_ctl`-managed instance).

## WSL-side network facts (recomputed at execution time, per Pattern 2 — never cached)

- `ip route show default | awk '{print $3}'` → `172.26.32.1` (Windows host / gateway IP)
- `ip -o -4 addr show eth0` → `172.26.44.149/20` → network `172.26.32.0/20`

These match the planning-time values recorded in 46-RESEARCH.md (`172.26.32.1` /
`172.26.32.0/20`) exactly — the WSL2 NAT subnet has not shifted since research time.

## Windows-side configuration (operator-executed, elevated PowerShell)

- **Service discovery:** `Get-Service -Name 'postgresql-x64-18'` → **Running**, StartType **Automatic**.
- **Data directory** (from `(Get-CimInstance Win32_Service -Filter "Name='postgresql-x64-18'").PathName`):
  `C:\Program Files\PostgreSQL\18\data`
  - This matches the generic install-path guidance in 46-RESEARCH.md's Assumption A1 —
    no deviation from the generic guides was found for this install.
- **`postgresql.conf`:** `listen_addresses = '*'` (uncommented, widened from the default
  `localhost`-only). Rationale recorded per the plan: pinning to the gateway IP would break
  startup after any NAT-subnet shift; access control is carried by the two gates below instead.
- **`pg_hba.conf`:** one host line added — `host    all    all    172.26.32.0/20    scram-sha-256`
  — the existing `127.0.0.1/32` and `::1/128` lines were left untouched.
- **Windows Firewall:** `New-NetFirewallRule -DisplayName 'PostgreSQL 5432 from WSL' -Direction Inbound -Protocol TCP -LocalPort 5432 -RemoteAddress 172.26.32.0/20 -Action Allow -Profile Any`
- **Service restart:** service restarted after the config edits to apply `listen_addresses`/`pg_hba.conf` changes.
- **Role/database creation:** `createuser`/`createdb` run for role `scotus`, databases `scotus`
  and `scotus_test` (owner `scotus`). Password chosen interactively by the operator via
  `createuser -W -P`; never shared with or recorded by Claude.
- **Windows-side verification:** `Test-NetConnection -ComputerName 172.26.32.1 -Port 5432` →
  `TcpTestSucceeded : True`.

## WSL-side verification (Claude-executed, this session)

```
timeout 5 bash -c 'cat < /dev/null > /dev/tcp/172.26.32.1/5432' && echo REACHABLE
```
→ **REACHABLE**

## Deviation from 46-RESEARCH.md's generic guidance

None found. The discovered data directory (`C:\Program Files\PostgreSQL\18\data`) matches
the standard PostgreSQL-on-Windows install layout that 46-RESEARCH.md's Assumption A1 assumed
but could not verify directly (that research session ran from WSL only). All three reachability
gates (`listen_addresses`, `pg_hba.conf`, Windows Firewall) were configured exactly as
46-RESEARCH.md's Pitfall 4 prescribes, scoped to the live WSL subnet CIDR in both the
`pg_hba.conf` host rule and the firewall rule's `-RemoteAddress` — both are narrowly scoped
to the WSL subnet recorded above, not to every address, not to a broad private-range default,
and not to a passwordless auth method.
