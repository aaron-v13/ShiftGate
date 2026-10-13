"""Audit pipeline source code for hard-coded device literals and NVIDIA-specific calls."""
import re
from pathlib import Path

def main():
    pipeline_files = sorted(Path("pipeline").glob("*.py"))
    allowed = {"device.py", "amd_smoke_test.py", "check_device_rules.py"}

    violations = 0
    for f in pipeline_files:
        if f.name in allowed:
            print(f"[OK - allowed exception] {f.name}")
            continue
        content = f.read_text(encoding="utf-8")
        cuda_calls = re.findall(r"\.cuda\(", content)
        nvidia_words = re.findall(r"nvidia", content, re.IGNORECASE)
        cuda_literals = re.findall(r"['\"]cuda['\"]", content, re.IGNORECASE)
        cpu_literals = re.findall(r"['\"]cpu['\"]", content, re.IGNORECASE)

        if cuda_calls or nvidia_words or cuda_literals or cpu_literals:
            print(f"[VIOLATION] in {f.name}:")
            if cuda_calls:
                print(f"  .cuda() calls: {cuda_calls}")
            if nvidia_words:
                print(f"  nvidia occurrences: {nvidia_words}")
            if cuda_literals:
                print(f"  cuda literals: {cuda_literals}")
            if cpu_literals:
                print(f"  cpu literals: {cpu_literals}")
            violations += 1
        else:
            print(f"[OK - clean] {f.name}")

    if violations == 0:
        print("ALL pipeline files strictly comply with Rule 9!")
    else:
        print(f"Found violations in {violations} files.")

if __name__ == "__main__":
    main()
