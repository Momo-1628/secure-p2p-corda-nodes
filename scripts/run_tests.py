"""Runs `gradlew test` and writes a clean summary + per-test table -> evidence/test_results.txt
Gagan N (24BTRBT013)."""
import glob
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADLEW = os.path.join(ROOT, "gradlew.bat" if os.name == "nt" else "gradlew")

DESCRIPTIONS = {
    "sendAndAcknowledgeWorks": "(1) A->B send + acknowledge works; both can decrypt",
    "thirdPartyVaultIsEmpty": "(2) PRIVACY: EnterpriseC vault = 0, C cannot read",
    "tamperedPayloadFailsIntegrityCheck": "(3) INTEGRITY: tampered payload / hash rejected",
    "untrustedPeerIsRejected": "(4) TRUST POLICY: C->A rejected 'Untrusted peer'",
    "storedPayloadIsCiphertext": "(5) stored encryptedPayload != plaintext",
    "pingReturnsLatency": "PingPeerFlow returns a P2P latency",
    "cannotAcknowledgeTwice": "double acknowledgement is prevented",
}


def main(quiet=False):
    t0 = time.time()
    cmd = [GRADLEW, "test", "--rerun-tasks", "--console=plain"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    dur = time.time() - t0
    gradle_lines = [l for l in proc.stdout.splitlines() if re.match(r"^(> Task :\S+:(compile\w*Java|test)\b|BUILD|\d+ actionable)", l)]

    rows, total, failed = [], 0, 0
    for xml in sorted(glob.glob(os.path.join(ROOT, "*", "build", "test-results", "test", "*.xml"))):
        suite = ET.parse(xml).getroot()
        for tc in suite.findall("testcase"):
            total += 1
            ok = tc.find("failure") is None and tc.find("error") is None
            failed += 0 if ok else 1
            cls = tc.get("classname").split(".")[-1]
            rows.append((cls, tc.get("name"), "PASS" if ok else "FAIL", float(tc.get("time", 0))))

    out = []
    w = out.append
    w("=" * 104)
    w("  TEST RESULTS - Secure P2P Communication between Enterprise Corda Nodes  |  Gagan N (24BTRBT013)")
    w("  Command: gradlew test --rerun-tasks      (Corda 4.12, JDK 17, MockServices ledger DSL + MockNetwork)")
    w("=" * 104)
    w("")
    w("Gradle output:")
    for l in gradle_lines:
        w("  " + l)
    w("")
    w(f"{'Suite':<28} {'Test':<40} {'Result':<7} {'Time s':>7}")
    w("-" * 104)
    for cls, name, res, t in rows:
        w(f"{cls:<28} {name:<40} {res:<7} {t:>7.2f}")
        if name in DESCRIPTIONS:
            w(f"{'':<28}   -> {DESCRIPTIONS[name]}")
    w("-" * 104)
    contract = sum(1 for r in rows if r[0].endswith("ContractTests"))
    flow = sum(1 for r in rows if r[0].endswith("FlowTests"))
    w(f"TOTAL: {total} tests   PASSED: {total - failed}   FAILED: {failed}   "
      f"(contract tests: {contract}, flow tests: {flow})   wall time: {dur:.0f} s")
    w("RESULT: " + ("ALL TESTS PASSED" if failed == 0 and proc.returncode == 0 else "FAILURES PRESENT"))
    text = "\n".join(out) + "\n"
    with open(os.path.join(ROOT, "evidence", "test_results.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
