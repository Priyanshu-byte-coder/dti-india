# Running on PARAM Shavak (Nirma)

PARAM Shavak replaces the earlier server (10.1.73.151, unreachable). Credentials are
issued by the faculty in charge and are never stored in this repo.

## Machine

| Item | Value |
|---|---|
| Host | `nirmashavak`, 10.1.73.225 (VPN: GlobalProtect `vpn.nirmauni.ac.in` or `vpn2.nirmauni.ac.in`; on campus Wi-Fi no VPN) |
| SSH | port 22, OpenSSH 7.4: add `-o KexAlgorithms=diffie-hellman-group14-sha256` if your client refuses |
| GPU | **Quadro GP100, 16 GB** (Pascal, compute 6.0) + Quadro P400 2 GB (display only, not used) |
| CPU / RAM / disk | 36 cores, 93 GB RAM, ~3.7 TB free on /home |
| OS | CentOS 7.3 (glibc 2.17, system gcc 4.8, system ld 2.25) |
| Scheduler | TORQUE/PBS 6.1, queue `batch` (`qsub`, `qstat -a`); `screen` available, no `tmux` |
| Internet | PyPI, Hugging Face, GitHub reachable; conda channels and ollama.com blocked |

## Why not vLLM

vLLM needs a Volta-or-newer GPU (compute ≥ 7.0) and a newer glibc. The GP100 is Pascal
and the OS is CentOS 7. Models therefore run as quantised GGUF files under **llama.cpp**,
compiled on the machine for compute 6.0. llama.cpp's server speaks the same
OpenAI-compatible API, so `dti score` is unchanged (same prompt, schema, output files).

## Layout (inside the shared account)

```
~/priyanshu/
  dti-env/        conda env, Python 3.10.18 (created offline from the account's package cache)
  dti-india/      this repo (PLFS data in data/raw/plfs/, git-ignored, mode 700)
  llama.cpp/      source + build/bin/llama-server (CUDA, sm_60)
  models/         GGUF files (scripts/shavak_models.sh)
  toolbin/        `ld` link to binutils 2.40 (the system ld 2.25 cannot link CUDA 12.2)
```

## One-time setup (already done once; repeat only on a fresh account)

```bash
source /opt/anaconda3/etc/profile.d/conda.sh
conda create -y -p ~/priyanshu/dti-env python=3.10.18 --offline
cd ~/priyanshu/dti-india
~/priyanshu/dti-env/bin/python -m pip install --prefer-binary -e ".[dev]"   # use the env's python: a different pip is first on PATH
# llama.cpp
cd ~/priyanshu && git clone --depth 1 https://github.com/ggml-org/llama.cpp && cd llama.cpp
module load gcc/9.1.0
export COMPILER_PATH=~/priyanshu/toolbin PATH=/usr/local/cuda-12.2/bin:$PATH CC=$(which gcc) CXX=$(which g++)
cmake -B build -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX -DCMAKE_CUDA_HOST_COMPILER=$CXX \
      -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=60 -DLLAMA_CURL=OFF -DGGML_CCACHE=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 12 --target llama-server llama-cli
```

## Models (16 GB GPU, one model at a time)

| Key | File | Size |
|---|---|---|
| `qwen14b` | Qwen2.5-14B-Instruct, 4-bit (Q4_K_M) | 9.0 GB |
| `llama8b_gguf` | Llama-3.1-8B-Instruct, 8-bit (Q8_0) | 8.5 GB |

Two model families, as before, so cross-model agreement (RQ1) stays available. The 32B
model does not fit in 16 GB.

```bash
conda activate ~/priyanshu/dti-env && cd ~/priyanshu/dti-india
bash scripts/shavak_models.sh            # downloads both into ../models
```

## Running

```bash
qsub -v STAGE=pilot scripts/shavak.pbs                      # 50 occupations, both rubrics, both models
qsub -v STAGE=full,MODEL=qwen14b scripts/shavak.pbs         # full corpus, one model per job
qsub -v STAGE=full,MODEL=llama8b_gguf scripts/shavak.pbs
qsub -v STAGE=onet,MODEL=qwen14b scripts/shavak.pbs
qstat -a                                                    # status; output in logs/pbs_<id>.out
```

`scripts/shavak_score.sh <model>` does one model directly (e.g. inside `screen`).
Everything is resumable. Expect the full NCO corpus (3,450 × 5 runs) to take on the order
of a day or more per model on this GPU; the pilot gives the actual rate.
