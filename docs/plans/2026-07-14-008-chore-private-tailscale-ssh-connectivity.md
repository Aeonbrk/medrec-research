# Private Tailscale SSH Connectivity

## Goal

Establish a least-privilege Tailscale path using a private Windows relay host. Before any client enrollment, confirm whether the relay is an SSH jump host to an existing public SSH target or whether both endpoints must join the Tailnet. Keep all identifiers, credentials, Tailnet state, and SSH material outside Git.

## Scope

- Verify the local control host is authenticated to the intended Tailnet.
- Add only the relay for an SSH jump-host topology; add both endpoints only for an explicitly approved end-to-end Tailnet topology.
- For a jump-host topology, retain the target's existing public SSH endpoint and use `ProxyJump` over the relay's Tailscale address.
- For an end-to-end topology, prefer MagicDNS or a Tailscale IP for the target SSH host entry.
- Verify only Tailscale reachability, SSH host-key confirmation, and user identity.

## Non-Goals

- Do not access research data, repositories, GPUs, processes, or workloads.
- Do not add a subnet router, exit node, funnel, or broad ACL exception.
- Do not write keys, passwords, addresses, node IDs, or Tailnet metadata to this repository.

## Decision Required

Confirm the jump-host topology before installing or authorizing any additional Tailscale client. It requires the relay's Windows administrator access, its local SSH account, and its OpenSSH server configuration. An end-to-end topology requires administrative control of the actual Linux host rather than an unprivileged container shell.

## Verification

- Both new nodes appear online in the existing Tailnet.
- The relay reaches the target over its Tailscale address or MagicDNS name.
- SSH authenticates as the intended account through the private path.
- Existing public SSH configuration remains unchanged until the private path succeeds.

## Rollback

Remove only the two newly enrolled nodes from the Tailnet and remove the newly added private SSH host entry. Preserve all pre-existing Tailnet devices and SSH configuration.

## Outcome

The confirmed SSH jump-host topology completed. A dedicated client key authenticated to the relay, and the new local SSH alias reached the expected target account through that relay. No research data, source checkout, GPU state, or workload was accessed.
