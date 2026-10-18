# Nirma GPU: SSH access so Claude can run and monitor the pipeline

Goal: Priyanshu spends about 15 minutes once. After that, Neal's Claude Code session logs
in over SSH, runs every GPU stage, watches progress and fixes failures, and Priyanshu does
nothing further.

## Priyanshu: one-time steps (on the Nirma server)

1. **Get the repo onto the server** (any directory you like):
   ```bash
   git clone https://github.com/Priyanshu-byte-coder/dti-india.git && cd dti-india
   ```
2. **Give Neal's key access**, in the account the jobs should run under:
   ```bash
   bash scripts/nirma_grant_access.sh
   ```
   This appends one public key (comment `neal-claude-nirma-dti`) to `~/.ssh/authorized_keys`
   and prints the user, host and addresses to send to Neal. A separate account for Neal,
   if the lab admin can create one, is cleaner than sharing yours; then run the script in
   that account.
3. **Tell Neal how the server is reached from outside campus**. One of:
   - it has a public address or port forward → just send host and port;
   - there is a **jump/bastion host** → send its address and ask for Neal's key to be
     added there too (same script);
   - access is **VPN only** → Neal needs VPN credentials from the lab or IT;
   - none of these → ask IT before setting up any tunnel (Tailscale, Cloudflare Tunnel,
     reverse SSH). Do not open one without their permission.
4. **Llama licence** (the second model is gated): accept it at
   https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct, create a read token at
   https://huggingface.co/settings/tokens, then on the server run `huggingface-cli login`
   once setup has installed it, or send the token to Neal privately.
5. **PLFS microdata**: copy the files onto the server under
   `data/raw/plfs/<round>/` (e.g. `data/raw/plfs/2022-23/`) together with each round's
   data layout and instruction manual. The data never goes to GitHub: `data/raw/plfs/` is
   ignored by git, and MoSPI's terms forbid redistribution.

That is all. If the server uses SLURM (you submit jobs with `sbatch` rather than running
on the machine directly), tell Neal: the jobs then go through `scripts/score.sbatch`.

## Neal's laptop (already done)

- Key pair: `~/.ssh/id_ed25519_nirma` (private, stays on the laptop) and
  `~/.ssh/id_ed25519_nirma.pub` (the key in `scripts/nirma_grant_access.sh`).
- Once Priyanshu sends the details, add to `~/.ssh/config`:
  ```
  Host nirma
      HostName <address from step 2>
      User <user from step 2>
      Port 22
      IdentityFile ~/.ssh/id_ed25519_nirma
      IdentitiesOnly yes
      ServerAliveInterval 60
      # ProxyJump <user>@<jump host>    # only if step 3 named a jump host
  ```
  Test with `ssh nirma nvidia-smi`.

## What Claude runs over SSH

| Step | Command (from the repo directory on the server) |
|---|---|
| Setup (once) | `bash scripts/nirma_setup.sh` → venv, GPU extras, tests, `logs/gpu_spec.txt` with the model pair |
| Pilot (HANDOFF step 2) | `bash scripts/nirma_run.sh pilot` → 50 occupations, both rubrics, both models |
| Full corpus (step 3) | `bash scripts/nirma_run.sh full` |
| O\*NET + gap (steps 4–5) | `bash scripts/nirma_run.sh onet` |
| Progress | `bash scripts/status.sh` → GPUs, running stages, records/failures per model, log tail, vLLM errors |
| PLFS (step 7) | edit `configs/plfs.yaml` against the files and manuals, then `dti plfs-build` and `dti analysis` |

Each stage runs detached (tmux, or nohup when tmux is missing), so it survives a dropped
connection, and rerunning a stage resumes it. The model pair is chosen from the GPUs:
about 80 GB in total → Qwen2.5-32B + Llama-3.1-8B, otherwise Qwen2.5-7B + Llama-3.1-8B
(see `scripts/nirma_models.sh`).

Results come back to the laptop with `rsync -a nirma:<repo>/reports/ reports/` (and
`data/processed/`, `data/llm/`). PLFS microdata and person-level files are not copied off
the server. Only the aggregated result tables are.

## Limits Claude keeps to on the server

- Works only inside the repo directory and `~/.cache/huggingface`; no `sudo`, no system
  packages, no changes to other users' files or jobs.
- Stops only processes it started (its own tmux sessions, pid files and vLLM servers).
- Checks free GPU memory before starting a stage, so it does not crowd out other lab jobs.
- Never commits PLFS or coder data; commits from the server go to a branch, not `main`.
