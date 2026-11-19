"""Start / stop / check the 4 Corda nodes headless (Gagan N, 24BTRBT013).

    python scripts/nodes.py start      # starts Notary, EnterpriseA, EnterpriseB, EnterpriseC in the background
    python scripts/nodes.py stop
    python scripts/nodes.py status
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES_DIR = os.path.join(ROOT, "build", "nodes")
NODES = ["Notary", "EnterpriseA", "EnterpriseB", "EnterpriseC"]
STDOUT = "node-stdout.log"


def node_dir(n):
    return os.path.join(NODES_DIR, n)


def started(n):
    p = os.path.join(node_dir(n), "logs", STDOUT)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "started up and registered" in line:
                return line.strip()
    return None


def start(quiet=False):
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    for n in NODES:
        d = node_dir(n)
        os.makedirs(os.path.join(d, "logs"), exist_ok=True)
        out = open(os.path.join(d, "logs", STDOUT), "w", encoding="utf-8")
        proc = subprocess.Popen(["java", "-Dbrokerconfig.maxDiskUsage=100", "-jar", "corda.jar", "--no-local-shell"], cwd=d, stdout=out,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags)
        with open(os.path.join(d, "demo.pid"), "w") as f:
            f.write(str(proc.pid))
        print(f"  launched {n:<12} (java -jar corda.jar, logs -> build/nodes/{n}/logs/{STDOUT})", flush=True)
    t0 = time.time()
    pending = list(NODES)
    while pending and time.time() - t0 < 600:
        for n in list(pending):
            line = started(n)
            if line:
                pending.remove(n)
                print(f"  [{time.time() - t0:5.1f}s] {n:<12} {line[line.find('Node for'):]}", flush=True)
        time.sleep(1)
    if pending:
        print("  TIMEOUT waiting for: " + ", ".join(pending))
        return False
    return True


def node_pids(n):
    """PIDs of the java/javaw processes running net.corda.node.Corda inside build/nodes/<n> (Corda re-launches itself)."""
    if os.name != "nt":
        r = subprocess.run(["pgrep", "-f", f"build/nodes/{n}/"], capture_output=True, text=True)
        return r.stdout.split()
    needle = os.path.join("build", "nodes", n) + os.sep
    ps = ("Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') "
          "-and $_.CommandLine -like '*" + needle.replace("'", "''") + "*' } | ForEach-Object { $_.ProcessId }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return [x.strip() for x in r.stdout.split() if x.strip().isdigit()]


def stop():
    for n in NODES:
        pids = node_pids(n)
        for pid in pids:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True, text=True)
            else:
                subprocess.run(["kill", pid])
        pf = os.path.join(node_dir(n), "demo.pid")
        if os.path.exists(pf):
            os.remove(pf)
        print(f"  stopped {n:<12} " + (f"(pids {', '.join(pids)})" if pids else "(was not running)"), flush=True)


def status():
    for n in NODES:
        print(f"  {n:<12} {'UP' if started(n) else 'not started'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"start": start, "stop": stop, "status": status}[cmd]()
