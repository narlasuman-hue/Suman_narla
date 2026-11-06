# ServiceNow Incident Assistant

When a user raises an incident or request, this tool checks ServiceNow for
**previously resolved tickets describing the same problem** and returns the
**steps that fixed them**, so the agent (or the user) can try the known fix first.

## How it works

1. **Read the ticket** – `lookup INC0012345` fetches the ticket's short description,
   description, category and CI. `search "..."` takes a free-text problem instead.
2. **Find candidates** – queries resolved/closed records via the REST Table API using
   ServiceNow's keyword index (`123TEXTQUERY321`), widening from 6 to 3 to 2 keywords
   if nothing comes back.
   - `incident`: state Resolved (6) or Closed (7)
   - `sc_req_item`: state Closed Complete (3)
   - also supported: `sc_request`, `problem`
3. **Decide "same issue"** – re-ranks candidates locally with TF‑IDF cosine similarity
   (with IT synonyms such as *pwd → password*, *login → logon*, *outlook → email*).
   Tickets below `--min-score` (default `0.3`) are ignored.
4. **Extract steps** – parses each match's `close_notes` (numbered/bulleted lists or
   prose), drops admin lines like *"User confirmed, closing ticket"*, and falls back to
   the latest work notes if the close notes are empty.
5. **Merge** – combines steps across the top matches, keeps their order, and shows how
   many of the similar tickets used each step.

## Setup

```bash
pip install requests
export SERVICENOW_INSTANCE=acme                # or https://acme.service-now.com
export SERVICENOW_TOKEN=...                    # OAuth bearer token, or:
export SERVICENOW_USERNAME=svc_incident_reader
export SERVICENOW_PASSWORD=...
```

Use a **read-only** integration user with the `itil` role (or read ACLs on
`incident`, `sc_req_item` and `sys_journal_field`). The tool only performs `GET`
requests. HTTPS is required.

## Usage

```bash
# Steps for an existing ticket
python -m src.servicenow_assist lookup INC0012345

# Steps for a problem the user just described
python -m src.servicenow_assist search "VPN keeps disconnecting on my laptop"

# Only look at catalog requests, JSON output for integrations
python -m src.servicenow_assist --tables sc_req_item --json search "access to shared drive"
```

Example output:

```
Problem: INC0012345: VPN keeps disconnecting on laptop

Same issue was resolved before in 2 ticket(s). Suggested steps:

  1. Uninstall AnyConnect  [used in 2/2]
  2. Install AnyConnect 5.1 from Software Center  [used in 2/2]
  3. Reboot the laptop  [used in 1/2]
  4. Clear the DNS cache with ipconfig /flushdns  [used in 1/2]

Based on:
  - INC0000101 (high match, 0.82, Solved (Permanently), resolved 2026-09-01): VPN keeps disconnecting on laptop
  - INC0000102 (high match, 0.71, Solved (Permanently), resolved 2026-09-10): VPN disconnects frequently on laptop
```

Exit codes: `0` steps found, `1` no similar resolved ticket, `2` error (config, auth, network).

| Option | Default | Meaning |
|---|---|---|
| `--min-score` | `0.3` | Similarity (0–1) needed to count as the same issue |
| `--max-matches` | `5` | Similar tickets to draw steps from |
| `--tables` | own table / `incident sc_req_item` | Tables to search |
| `--no-work-notes` | off | Use close notes only (fewer API calls) |
| `--json` | off | Machine-readable output |

## Using it from Python

```python
from src.servicenow_assist import IncidentAssistant, ServiceNowClient, ServiceNowConfig

assistant = IncidentAssistant(ServiceNowClient(ServiceNowConfig.from_env()))
rec = assistant.recommend_for_ticket("INC0012345")
for step in rec.steps:
    print(step.text, step.sources)
```

## Tips

- Results are only as good as the close notes. Encourage resolvers to write the fix as
  numbered steps.
- Raise `--min-score` (e.g. `0.5`) if unrelated tickets show up; lower it if nothing does.
