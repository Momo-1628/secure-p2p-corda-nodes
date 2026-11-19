"""Extracts the AMQP/TLS bridge lines (current run only) from every node log -> evidence/p2p_links.txt
Gagan N (24BTRBT013)."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES = ["EnterpriseA", "EnterpriseB", "EnterpriseC", "Notary"]
PORTS = {"10002": "Notary", "10005": "EnterpriseA", "10008": "EnterpriseB", "10011": "EnterpriseC"}
PAT = re.compile(r"P2P messaging server listening|AMQPBridgeManager. - Create new AMQP bridge|AMQPClient. - Connect(ed)? to|"
                 r"Handshake completed with subject|New (client|server) connection|Bridge Connected|"
                 r"SSL handshake failed|Bridge Disconnected")
LOCAL = re.compile(r"\b(?:127\.0\.0\.1|0:0:0:0:0:0:0:1|localhost)\b")


def main():
    out = []
    w = out.append
    w("=" * 110)
    w("  P2P LINK EVIDENCE - AMQP 1.0 over mutual TLS between Artemis bridges  |  Gagan N (24BTRBT013)")
    w("  Source: build/nodes/<Node>/logs/node-*.log (lines from the current node run only)")
    w("=" * 110)
    pairs = {}
    for node in NODES:
        logs = [p for p in glob.glob(os.path.join(ROOT, "build", "nodes", node, "logs", "node-*.log"))
                if not any(x in p for x in ("node-info-gen", "run-migration", "schema-cordform", "node-stdout"))]
        lines = []
        for p in logs:
            with open(p, encoding="utf-8", errors="replace") as f:
                lines += f.readlines()
        # keep only the latest run
        starts = [i for i, l in enumerate(lines) if "Starting as node on" in l]
        if starts:
            lines = lines[starts[-1]:]
        hits = [l.rstrip() for l in lines if PAT.search(l)]
        w("")
        w("-" * 110)
        w(f"NODE: {node}   ({len(hits)} link events)")
        w("-" * 110)
        for l in hits:
            l = re.sub(r"^\[(\w+) *\] (\S+) \[[^\]]+\] ", r"\2 ", l)
            w("  " + l[:230])
            m = re.search(r"Connected to localhost:(\d+)", l)
            if m:
                pairs.setdefault((node, PORTS.get(m.group(1), m.group(1))), 0)
                pairs[(node, PORTS.get(m.group(1), m.group(1)))] += 1
            m = re.search(r"Handshake completed with subject: (O=[^,]+)", l)
            if m:
                key = (node, "TLS peer " + m.group(1)[2:])
                pairs[key] = pairs.get(key, 0) + 1
    w("")
    w("=" * 110)
    w("  SUMMARY: outbound AMQP bridges opened (from -> to) and mutually-authenticated TLS peers")
    w("=" * 110)
    for (a, b), n in sorted(pairs.items()):
        w(f"  {a:<12} -> {b:<28} x{n}")
    w("")
    w("  Note: EnterpriseC's bridge to EnterpriseA completes at the TLS layer (C holds a valid Doorman-issued")
    w("  certificate, it is a network member), but EnterpriseA's flow-level trusted-peer policy rejects C's flow.")
    w("  The single A -> C bridge was opened only to deliver that 'Untrusted peer' error back to C.")
    w("  A <-> B and A/B <-> Notary carry the business traffic; C never receives any A <-> B message (point-to-point).")
    text = "\n".join(out) + "\n"
    with open(os.path.join(ROOT, "evidence", "p2p_links.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
