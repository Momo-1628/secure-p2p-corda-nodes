"""Live demonstration script - Gagan N (24BTRBT013)
Secure Peer-to-Peer Communication between Enterprise Corda Nodes.

Runs the REAL project step by step in a maximised console with a large font. Before each step it prints a step
banner and logs a timestamp (demo/recording/steps.json); it pauses between steps so viewers can read, and long
enough for that step's narration (demo/recording/narration_durations.json, if present).

    python demo/demo_script.py            (normally started by demo/record_demo.py inside conhost)
Prerequisites: gradlew deployNodes; gradlew :clients:writeClasspath; the nodes must NOT be running.
"""
import ctypes
import glob
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "demo", "recording")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.makedirs(REC, exist_ok=True)

CYAN, YELLOW, GREEN, RED, GREY, BOLD, RESET = "\033[96m", "\033[93m", "\033[92m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"
BANNER_BG = "\033[48;5;30m\033[97m"
STEPS_LOG = []
NARR = {}
p = os.path.join(REC, "narration_durations.json")
if os.path.exists(p):
    NARR = {int(k): v for k, v in json.load(open(p)).items()}
TITLES = {d["step"]: d["title"] for d in json.load(open(os.path.join(ROOT, "demo", "narration.json"), encoding="utf-8"))}


# ----------------------------------------------------------------------------- console setup (Windows)
def setup_console(font_px=20):
    if os.name != "nt":
        return
    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    h = k32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    k32.GetConsoleMode(h, ctypes.byref(mode))
    k32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class FONT(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("nFont", ctypes.c_ulong), ("dwFontSize", COORD),
                    ("FontFamily", ctypes.c_uint), ("FontWeight", ctypes.c_uint), ("FaceName", ctypes.c_wchar * 32)]
    f = FONT()
    f.cbSize = ctypes.sizeof(FONT)
    f.dwFontSize.Y = font_px
    f.FontFamily = 54
    f.FontWeight = 400
    f.FaceName = "Consolas"
    k32.SetCurrentConsoleFontEx(h, False, ctypes.byref(f))
    k32.SetConsoleTitleW("Gagan N (24BTRBT013) - Secure P2P Corda - live demo")
    u32.ShowWindow(k32.GetConsoleWindow(), 3)  # SW_MAXIMIZE
    u32.SetForegroundWindow(k32.GetConsoleWindow())


def cols():
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 150


def clear():
    sys.stdout.write("\033[2J\033[3J\033[H")
    sys.stdout.flush()


def typed(cmd):
    sys.stdout.write(YELLOW + "$ ")
    for ch in cmd:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(0.025)
    sys.stdout.write(RESET + "\n")
    sys.stdout.flush()
    time.sleep(0.3)


def colour(line):
    if re.search(r"Untrusted peer|REJECTED|FAILED(?!: 0)|alert|refused", line):
        return RED + line + RESET
    if re.search(r"PASS|ALL TESTS PASSED|BUILD SUCCESSFUL|started up|COMPLETED|PASSED|ACKNOWLEDGED|UP-TO-DATE", line):
        return GREEN + line + RESET
    if line.startswith(">>") or line.startswith("NODE:") or line.startswith("TEST ") or "SUMMARY" in line:
        return CYAN + BOLD + line + RESET
    return line


def show(lines):
    for l in lines:
        print(colour(l))
        sys.stdout.flush()
        time.sleep(0.012)


def run(cmd, display, filt=None, env=None):
    """Run a real command, stream its output (optionally filtered)."""
    typed(display)
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", env=env)
    for line in proc.stdout:
        line = line.rstrip("\n")
        if filt is None or filt(line):
            print(colour(line))
            sys.stdout.flush()
    proc.wait()
    return proc.returncode


def demo_client(mode):
    cp = open(os.path.join(ROOT, "clients", "build", "classpath.txt")).read().strip()
    opens = []
    for m in ("java.time", "java.io", "java.util", "java.lang", "java.net", "java.nio"):
        opens += ["--add-opens", f"java.base/{m}=ALL-UNNAMED"]
    # skip the 3-line banner the client prints on every run (it is shown once in step 4)
    seen = {"n": 0}

    def filt(l):
        seen["n"] += 1
        return seen["n"] > 3 or mode == "networkmap"
    return run(["java"] + opens + ["-cp", cp, "com.securep2p.clients.DemoClient", mode],
               f"scripts/demo_client.sh {mode}", filt=filt)


# ----------------------------------------------------------------------------- step framework
def step(n, body):
    clear()
    w = min(cols(), 160) - 1
    title = f" STEP {n}/12 ▸ {TITLES[n]} "
    print(BANNER_BG + BOLD + title.ljust(w) + RESET)
    print(GREY + " Gagan N (24BTRBT013)  |  Secure P2P Communication between Enterprise Corda Nodes  |  Corda 4.12" + RESET)
    print()
    sys.stdout.flush()
    t = time.time()
    STEPS_LOG.append({"step": n, "title": TITLES[n], "wall": t})
    body()
    done = time.time()
    # pause: enough to read (>= 4 s after output) and to finish this step's narration
    target = max(done + 4.0, t + NARR.get(n, 0) + 1.5)
    while time.time() < target:
        time.sleep(0.1)


def s1():
    typed("tree /F (project structure, source files only)")
    keep = ("contracts/src", "workflows/src", "clients/src", "scripts", "demo", "evidence")
    lines = []
    for top in ("contracts", "workflows", "clients"):
        for f in sorted(glob.glob(os.path.join(ROOT, top, "src", "**", "*.java"), recursive=True)):
            rel = os.path.relpath(f, ROOT).replace("\\", "/")
            lines.append(rel)
    print(BOLD + "gagan-secure-p2p-corda/" + RESET)
    for name in ("build.gradle  (deployNodes: Notary, EnterpriseA, EnterpriseB, EnterpriseC + trustedPeers config)",
                 "README.md"):
        print("  " + name)
    last_dir = None
    for rel in lines:
        d, fn = rel.rsplit("/", 1)
        d = d.replace("/src/main/java/com/securep2p", " [main] com.securep2p").replace("/src/test/java/com/securep2p", " [test] com.securep2p")
        if d != last_dir:
            print(CYAN + "  " + d + "/" + RESET)
            last_dir = d
        print("      " + fn)
        time.sleep(0.02)
    print("  scripts/   nodes.py, collect_certs.py, tls_check.py, collect_p2p_links.py, run_tests.py ...")
    print("  evidence/  test_results, certificates, tls_handshake, p2p_links, demo_run")


def s2():
    gw = os.path.join(ROOT, "gradlew.bat" if os.name == "nt" else "gradlew")
    keep = lambda l: re.match(r"^(> Task :\w+:(test|compile\w*Java)\b|BUILD)", l) is not None
    run([gw, ":contracts:test", "--rerun-tasks", "--console=plain"], "gradlew :contracts:test --rerun-tasks", filt=keep)
    run([gw, "test", "--console=plain"], "gradlew test", filt=keep)
    print()
    rows = []
    for xml in sorted(glob.glob(os.path.join(ROOT, "*", "build", "test-results", "test", "*.xml"))):
        for tc in ET.parse(xml).getroot().findall("testcase"):
            ok = tc.find("failure") is None and tc.find("error") is None
            rows.append((tc.get("classname").split(".")[-1], tc.get("name"), "PASS" if ok else "FAIL"))
    half = (len(rows) + 1) // 2
    for i in range(half):
        a = rows[i]
        left = f"{a[2]}  {a[0][:18]:<18} {a[1]:<38}"
        b = rows[i + half] if i + half < len(rows) else None
        right = f"{b[2]}  {b[0][:18]:<18} {b[1]}" if b else ""
        print(colour(left) + "  " + colour(right))
    passed = sum(1 for r in rows if r[2] == "PASS")
    print()
    print(colour(f"TOTAL: {len(rows)} tests  PASSED: {passed}  FAILED: {len(rows) - passed}   -> "
                 + ("ALL TESTS PASSED" if passed == len(rows) else "FAILURES")))


def s3():
    import nodes
    typed("python scripts/nodes.py start")
    nodes.start()


def s4():
    demo_client("networkmap")


def s5():
    import collect_certs
    typed("keytool -list -v -keystore build/nodes/EnterpriseA/certificates/{sslkeystore,nodekeystore,truststore}.jks")
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        collect_certs.main()
    txt = open(os.path.join(ROOT, "evidence", "certificates.txt"), encoding="utf-8").read().splitlines()
    out, on = [], False
    for l in txt:
        if l.startswith("NODE: EnterpriseA"):
            on = True
        elif l.startswith("NODE: EnterpriseB"):
            break
        if on and not l.startswith("-" * 20):
            out.append(l)
    show([l for l in out if l.strip()][:34])


def s6():
    import tls_check
    import io, contextlib
    typed("openssl s_client -connect localhost:10005 -tls1_2   (no client certificate, then with a network cert, then -tls1_3)")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        tls_check.main()
    lines = buf.getvalue().splitlines()
    keep = []
    on = False
    for l in lines:
        if l.startswith("TEST 1"):
            on = True
        if l.startswith("TEST 2"):
            on = False
        if on and ("Signature Algorithms" in l or re.search(r"^\s+\|\s+(\d s:|i:)", l)):
            continue
        if on or l.strip().startswith(("Server certificate subject", "Negotiated", "Server requested",
                                        "Without client", "With a network", "TLS 1.3 attempt")):
            keep.append(l[:150])
    show(keep)


def s7():
    demo_client("send")


def s8():
    demo_client("ack")


def s9():
    demo_client("privacy")


def s10():
    demo_client("untrusted")


def s11():
    demo_client("ping")


def s12():
    import nodes
    typed("python scripts/nodes.py stop")
    nodes.stop()
    print()
    print(GREEN + BOLD + "Demo complete - all steps ran live.  Gagan N (24BTRBT013)" + RESET)


def main():
    setup_console()
    time.sleep(2.0)
    t_start = time.time()
    for n, fn in enumerate([s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12], 1):
        step(n, fn)
    time.sleep(1.0)
    json.dump({"start": t_start, "end": time.time(), "steps": STEPS_LOG},
              open(os.path.join(REC, "steps.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
