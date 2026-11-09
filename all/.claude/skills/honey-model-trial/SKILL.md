---
name: honey-model-trial
description: Try a candidate model (GGUF, quant, drafter, newer llama.cpp) on Honey against Aura via llama-swap. Safe pre-flight, build and download without touching Aura, then a gated load window, measurement and restore. Use when asked whether a model can run on Honey or to compare one with Aura on DSH.
---

# Honey model trial

Use this when someone wants a candidate model (a new GGUF, quant, drafter or llama.cpp build)
tried on Honey, usually against Aura on DSH report writing. The long-form reasoning is in
`~/DotCortex/agents-skills-honey.org` ("Reference: trialling a candidate model on Honey").
Read `honey-host` and `llm-benchmark` first; this skill adds only the sequencing.

## The rule

Aura is the operator's production model on one shared memory pool (about 40.5 of 54 GiB GTT).
A candidate cannot sit beside her. Everything before the load is safe and should just be done;
the load takes Aura out, so it needs Tiago's go-ahead and a stated window. Never stop or
restart `gille-llama-swap` or Aura's `llama-server` on your own say-so.

## Do without asking (does not touch Aura)

1. Find the real repo (the linked one is often the BF16 training release) and get sha256 from
   the Hugging Face API; download with `curl -C -`, rename only on a hash match, `nice`/`ionice`.
2. Read the GGUF header by a 32 MB range request, `truncate -s <size>`, parse with gguf-py
   (a Python with numpy). Check architecture, per-layer arrays, tensor types.
3. Check support in a fresh llama.cpp checkout, not a stale `origin/master` (`git fetch` for real).
4. Build in a separate clone, Vulkan, low priority. Never rebuild `~/src/llama.cpp-vulkan`.
5. Do the memory arithmetic from the header (KV per token from the non-zero `head_count_kv`
   layers) and size the recipe to Honey, not to the vendor card's target hardware.

## Ask first

6. Window and go-ahead. Say what stops: Aura chats, web UI, the mail-wake lane.
7. Back up `~/src/llama-swap/config.yaml`, add a candidate entry to the exclusive `chat` group
   with its own runtime path, restart llama-swap, load the candidate alone, read the load log.
8. Measure candidate and Aura on the same synthetic tasks, cold and warm, TTFT, tok/s, total.
9. Restore: Aura back, answering through `:8090`, GTT near 40 GiB. A failed load means Aura
   goes straight back up, then report.

## Never

Read Secret Vault or clinical material for a benchmark. Use real client data. Edit the live
Aura entry's arguments as part of a trial. Treat a warm replay as a headline number.
