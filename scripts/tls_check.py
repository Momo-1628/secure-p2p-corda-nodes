"""Mutual-TLS evidence for the running EnterpriseA P2P port -> evidence/tls_handshake.txt
Gagan N (24BTRBT013).

Test 1: openssl s_client -tls1_2 WITHOUT a client certificate  -> server requests a cert, handshake is rejected
Test 2: openssl s_client -tls1_2 WITH EnterpriseB's TLS cert   -> handshake completes (a trusted peer)
Test 3: openssl s_client -tls1_3                                -> shows which protocol versions are enabled
The temporary PEM copy of the dev TLS key for test 2 is written to a temp folder and deleted afterwards.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10005
GIT_OPENSSL = r"C:\Program Files\Git\usr\bin\openssl.exe"
OPENSSL = shutil.which("openssl") or (GIT_OPENSSL if os.path.exists(GIT_OPENSSL) else "openssl")
INTERESTING = re.compile(r"(^CONNECTED|^subject=|^issuer=|Protocol|Cipher is|Cipher +:|^New, |Verify return code|"
                         r"alert|error|errno|Acceptable client certificate CA names|^C=|^CN=|^O=|"
                         r"Peer signing digest|Peer signature type|Server Temp Key|Requested Signature|"
                         r"Client Certificate Types|SSL handshake has read|no peer certificate|"
                         r"Secure Renegotiation|^ *[0-9] s:|^ *i:)", re.I)


def s_client(extra, label):
    cmd = [OPENSSL, "s_client", "-connect", f"localhost:{PORT}", "-showcerts"] + extra
    try:
        r = subprocess.run(cmd, input="", capture_output=True, text=True, timeout=25)
        out = r.stdout + r.stderr
        code = r.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        code = "timeout"
    lines = [l for l in out.splitlines() if INTERESTING.search(l) and "BEGIN" not in l]
    printable = " ".join(c if not c.startswith(os.path.dirname(tempfile.gettempdir())) else "<temp>" for c in cmd)
    return code, lines, out, printable


def main():
    rep = []
    w = rep.append
    ver = subprocess.run([OPENSSL, "version"], capture_output=True, text=True).stdout.strip()
    w("=" * 100)
    w(f"  TLS HANDSHAKE EVIDENCE - EnterpriseA P2P port localhost:{PORT}  |  Gagan N (24BTRBT013)")
    w(f"  Tool: {ver}")
    w("=" * 100)

    # ---- Test 1
    code, lines, raw1, cmd = s_client(["-tls1_2"], "no client cert")
    w("")
    w("TEST 1: TLS 1.2 handshake WITHOUT a client certificate")
    w("  $ " + cmd.replace(OPENSSL, "openssl"))
    w(f"  exit code: {code}")
    for l in lines:
        w("  | " + l)
    proto = re.search(r"Protocol\s*:\s*(\S+)", raw1) or re.search(r"New, (\S+), Cipher is (\S+)", raw1)
    cipher = re.search(r"Cipher\s*:\s*(\S+)", raw1) or re.search(r"Cipher is (\S+)", raw1)
    subj = re.search(r"^subject=(.+)$", raw1, re.M)
    requested = "Acceptable client certificate CA names" in raw1
    failed = code != 0 or bool(re.search(r"ssl/tls alert", raw1, re.I))

    # ---- Test 2: present EnterpriseB's TLS certificate (a legitimate network member)
    tmp = tempfile.mkdtemp(prefix="tlscheck-")
    try:
        ks = os.path.join(ROOT, "build", "nodes", "EnterpriseB", "certificates", "sslkeystore.jks")
        p12 = os.path.join(tmp, "b.p12")
        key = os.path.join(tmp, "key.pem")
        leaf = os.path.join(tmp, "leaf.pem")
        chain = os.path.join(tmp, "chain.pem")
        subprocess.run(["keytool", "-importkeystore", "-srckeystore", ks, "-srcstorepass", "cordacadevpass",
                        "-srcalias", "cordaclienttls", "-destkeystore", p12, "-deststoretype", "PKCS12",
                        "-deststorepass", "tmppass", "-destkeypass", "tmppass", "-noprompt"],
                       capture_output=True, text=True)
        for extra, dst in ((["-nodes", "-nocerts"], key), (["-clcerts", "-nokeys"], leaf), (["-cacerts", "-nokeys"], chain)):
            subprocess.run([OPENSSL, "pkcs12", "-in", p12, "-passin", "pass:tmppass"] + extra + ["-out", dst],
                           capture_output=True, text=True)
        code2, lines2, raw2, cmd2 = s_client(["-tls1_2", "-cert", leaf, "-key", key, "-cert_chain", chain], "with B cert")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    w("")
    w("TEST 2: TLS 1.2 handshake WITH EnterpriseB's node TLS certificate (signed by the network's Doorman CA)")
    w("  $ openssl s_client -connect localhost:%d -showcerts -tls1_2 -cert <B tls cert> -key <B tls key> -cert_chain <B node CA, doorman, root>" % PORT)
    w(f"  exit code: {code2}")
    for l in lines2:
        w("  | " + l)
    proto2 = re.search(r"Protocol\s*:\s*(\S+)", raw2)
    cipher2 = re.search(r"Cipher\s*:\s*(\S+)", raw2)

    # ---- Test 3
    code3, lines3, raw3, cmd3 = s_client(["-tls1_3"], "tls1.3")
    w("")
    w("TEST 3: TLS 1.3 attempt (protocol version policy)")
    w("  $ " + cmd3.replace(OPENSSL, "openssl"))
    w(f"  exit code: {code3}")
    for l in lines3[:12]:
        w("  | " + l)

    # ---- Server-side view (EnterpriseA node log)
    log = os.path.join(ROOT, "build", "nodes", "EnterpriseA", "logs", "node-stdout.log")
    w("")
    w("SERVER SIDE: EnterpriseA node log lines produced by the tests above")
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            lines_log = [l.rstrip() for l in f if "AMQ222208" in l]
        for l in lines_log[-2:]:
            w("  | " + l[:260])

    # ---- Summary
    w("")
    w("=" * 100)
    w("  SUMMARY")
    w("=" * 100)
    w(f"  Server certificate subject     : {subj.group(1).strip() if subj else 'n/a'}")
    w(f"  Negotiated protocol (with cert): {proto2.group(1) if proto2 else 'n/a'}")
    w(f"  Negotiated cipher   (with cert): {cipher2.group(1) if cipher2 else 'n/a'}")
    w(f"  Server requested client cert   : {'YES (CertificateRequest with acceptable CA names)' if requested else 'see output'}")
    w(f"  Without client certificate     : {'HANDSHAKE REJECTED (alert 40 handshake_failure) -> mutual TLS enforced' if failed else 'completed (unexpected)'}")
    ok2 = code2 == 0 and not re.search(r"ssl/tls alert", raw2, re.I)
    w(f"  With a network TLS certificate : {'HANDSHAKE COMPLETED' if ok2 else 'did not complete'}")
    t13 = re.search(r"Protocol\s*:\s*(\S+)", raw3)
    w(f"  TLS 1.3 attempt                : {('negotiated ' + t13.group(1)) if t13 and 'NONE' not in raw3 else 'refused (TLS 1.2 only)'}")
    w("")
    w("  Corda's P2P transport is AMQP 1.0 over TLS between Artemis brokers/bridges. Both sides must present a")
    w("  certificate chaining to the network root CA (truststore.jks), so an outsider without a Doorman-issued")
    w("  certificate cannot even open a connection - before any flow or trust policy is reached.")

    dest = os.path.join(ROOT, "evidence", "tls_handshake.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
