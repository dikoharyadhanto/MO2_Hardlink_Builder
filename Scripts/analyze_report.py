"""Analyze execution_report.json for success/failure stats."""
import json
from collections import Counter

print("[*] Loading execution report...")
with open('execution_report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)

print(f"[+] Total entries: {len(report)}")

# Count by status
status_counts = Counter(v["status"] for v in report.values())
print(f"\n=== STATUS SUMMARY ===")
for status, count in status_counts.items():
    print(f"  {status}: {count}")

# Count by method (for successful ones)
method_counts = Counter(v.get("method", "N/A") for v in report.values() if v["status"] == "SUCCESS")
print(f"\n=== METHOD BREAKDOWN (SUCCESS only) ===")
for method, count in method_counts.items():
    print(f"  {method}: {count}")

# Find failures and their reasons
failures = {k: v for k, v in report.items() if v["status"] == "FAILED"}
print(f"\n=== FAILURES ({len(failures)} total) ===")

if failures:
    # Group by error type
    error_counts = Counter(v["error"] for v in failures.values())
    print("Error breakdown:")
    for error, count in error_counts.most_common(10):
        # Truncate long error messages
        error_short = error[:100] + "..." if len(error) > 100 else error
        print(f"  [{count}x] {error_short}")
    
    # Show first 10 failed files
    print("\nFirst 10 failed files:")
    for i, (path, info) in enumerate(list(failures.items())[:10]):
        print(f"  {i+1}. {path}")
        print(f"     Error: {info['error'][:80]}...")
        print(f"     Mod: {info['mod']}")
else:
    print("  No failures! 🎉")

print("\n[SUCCESS] Analysis complete!")
