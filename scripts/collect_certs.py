"""Lists each node's keystores with keytool and summarises the certificate hierarchy -> evidence/certificates.txt
Gagan N (24BTRBT013)."""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES = ["EnterpriseA", "EnterpriseB", "EnterpriseC", "Notary"]
STORES = [("sslkeystore.jks", "cordacadevpass", "TLS key store (P2P transport)"),
          ("nodekeystore.jks", "cordacadevpass", "Node CA + legal identity key store"),
          ("truststore.jks", "trustpass", "Trust store (network root CA)")]


def keytool(path, pw):
    r = subprocess.run(["keytool", "-list", "-v", "-keystore", path, "-storepass", pw],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def parse(out):
    """Return a list of entries: (alias, [ (subject, issuer, sigalg, keyalg, valid_until) ... ])."""
    entries = []
    for block in re.split(r"\n(?=Alias name:)", out):
        m = re.search(r"Alias name: (.+)", block)
        if not m:
            continue
        alias = m.group(1).strip()
        certs = []
        for cb in re.split(r"Certificate\[\d+\]:", block)[1:] or [block]:
            owner = re.search(r"Owner: (.+)", cb)
            issuer = re.search(r"Issuer: (.+)", cb)
            alg = re.search(r"Signature algorithm name: (.+)", cb)
            key = re.search(r"Subject Public Key Algorithm: (.+)", cb)
            until = re.search(r"until: (.+)", cb)
            if owner:
                certs.append((owner.group(1).strip(), issuer.group(1).strip() if issuer else "",
                              alg.group(1).strip() if alg else "", key.group(1).strip() if key else "",
                              until.group(1).strip() if until else ""))
        entries.append((alias, certs))
    return entries


def main():
    out = []
    w = out.append
    w("=" * 100)
    w("  CERTIFICATE EVIDENCE - Secure P2P Corda network  |  Gagan N (24BTRBT013)")
    w("  Source: build/nodes/<Node>/certificates/*.jks  (keytool -list -v)")
    w("=" * 100)
    w("")
    w("HIERARCHY (Corda dev-mode PKI, same structure as a production Corda Network):")
    w("")
    w("  Corda Root CA  (self-signed, in truststore.jks of every node)")
    w("    +-- Corda Doorman / Intermediate CA  (issues node CA certificates)")
    w("    |     +-- Node CA  'O=EnterpriseX,...'  (cordaclientca in nodekeystore.jks)")
    w("    |           +-- Legal identity  (identity-private-key, Ed25519)  -> signs transactions")
    w("    |           +-- TLS certificate (cordaclienttls in sslkeystore.jks, ECDSA P-256) -> mutual TLS for P2P/AMQP")
    w("    +-- Network Map CA  (signs the network map / network parameters; not stored in the node keystores)")
    w("")
    full = []
    for node in NODES:
        d = os.path.join(ROOT, "build", "nodes", node, "certificates")
        w("-" * 100)
        w(f"NODE: {node}")
        w("-" * 100)
        for store, pw, desc in STORES:
            p = os.path.join(d, store)
            if not os.path.exists(p):
                w(f"  {store}: MISSING")
                continue
            o = keytool(p, pw)
            full.append(f"\n\n######## {node} / {store} ########\n{o}")
            n_entries = re.search(r"Your keystore contains (\d+) entr", o)
            w(f"  {store}  [{desc}]  - {n_entries.group(1) if n_entries else '?'} entries")
            for alias, certs in parse(o):
                w(f"    alias '{alias}': chain length {len(certs)}")
                for i, (subj, iss, sig, key, until) in enumerate(certs):
                    w(f"      [{i}] subject: {subj}")
                    w(f"          issuer : {iss}")
                    w(f"          key    : {key:<10} sig: {sig:<16} valid until: {until}")
            w("")
    w("")
    w("=" * 100)
    w("  FULL keytool -list -v OUTPUT")
    w("=" * 100)
    text = "\n".join(out) + "".join(full)
    dest = os.path.join(ROOT, "evidence", "certificates.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)
    print("\n".join(out[:12]))
    print(f"... written {len(text)} chars to evidence/certificates.txt")
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        print("\n".join(out))


if __name__ == "__main__":
    main()
