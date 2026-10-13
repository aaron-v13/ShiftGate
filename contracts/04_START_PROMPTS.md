# Start prompts (paste one into each laptop's agent chat)

## One-time setup by the human
1. Create the GitHub repo. Put these 5 files in `contracts/` and commit to `main`.
2. Laptop A: clone, `git checkout -b system1-pipeline`. Laptop B: clone, `git checkout -b system2-gate-app`.
3. Open the repo folder in the IDE on each laptop and start a fresh agent chat. Keep chats focused: if a chat gets long or confused, start a new one and paste the prompt again (the files hold all the state).
4. Day-one human tasks that do not need an agent: see `03_AMD_SETUP_AND_SMOKE_TEST.md`.

---

## Prompt for System 1 (AMD side, Laptop A)

```
You are building System 1 of the ShiftGate project.
Read contracts/00_SHARED_CONTRACT.md and contracts/01_SYSTEM1_PIPELINE_AMD.md completely, then also contracts/03_AMD_SETUP_AND_SMOKE_TEST.md (only the "Smoke test script" section matters to you).
Follow the working rules in the contract exactly. Edit only the folders System 1 owns.
Start at Stage 0. Do the setup, then ask me the three Stage 0 questions in one message and wait for my answer.
After each stage, run its CHECK, print a summary of at most 5 lines, and continue to the next stage. Stop at every STOP marker.
```

## Prompt for System 2 (decision side, Laptop B)

```
You are building System 2 of the ShiftGate project.
Read contracts/00_SHARED_CONTRACT.md and contracts/02_SYSTEM2_GATE_APP_SUBMISSION.md completely.
Follow the working rules in the contract exactly. Edit only the folders System 2 owns.
Start at Part A, stage A1. You do not need the GPU or real data yet: use the FAKE data as the brief says.
After each stage, run its CHECK, print a summary of at most 5 lines, and continue. Stop at every STOP marker (B and C).
```

## If the agent drifts (paste as a follow-up)

```
Stop. Re-read the contract section "How to work" and the stage you are on. List which rule you broke, undo that change, and continue from the current stage's CHECK.
```

## When you reach a STOP
- STOP A (System 1): run the smoke test on the AMD instance, then tell the agent: "AMD is ready. Here is the smoke test output: <paste>. Continue with Stage 5."
- STOP B (System 2): merge or copy System 1's `results/` into your branch, then tell the agent: "Real results are in results/. Continue at STOP B."
- STOP C (System 2): after asking the organizers, tell the agent which hosting option you chose.
