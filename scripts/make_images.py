"""Builds evidence screenshots (dark terminal PNGs from the REAL evidence files) and architecture diagrams.
Gagan N (24BTRBT013).   python scripts/make_images.py
"""
import os
import re

from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence")
IMG = os.path.join(ROOT, "images")
DIA = os.path.join(ROOT, "diagrams")
os.makedirs(IMG, exist_ok=True)
os.makedirs(DIA, exist_ok=True)

FONT_DIR = r"C:\Windows\Fonts"
MONO = os.path.join(FONT_DIR, "consola.ttf")
MONO_B = os.path.join(FONT_DIR, "consolab.ttf")

NAVY = "#0B1F3A"
NAVY2 = "#13294B"
TEAL = "#14B8A6"
TEAL_D = "#0F766E"
RED = "#DC2626"
AMBER = "#D97706"
GREY = "#64748B"
LIGHT = "#F8FAFC"

PRIVATE_PREFIXES = [r"C:\Users\LENOVO\Downloads\Corda_Lab_Codes_15_Experiments" + "\\",
                    "C:/Users/LENOVO/Downloads/Corda_Lab_Codes_15_Experiments/"]


def sanitize(s):
    for p in PRIVATE_PREFIXES:
        s = s.replace(p, "")
    return s


def read(name):
    with open(os.path.join(EV, name), encoding="utf-8") as f:
        return [sanitize(l.rstrip("\n")) for l in f]


# ============================================================================ terminal renderer

def colour_for(line):
    l = line.strip()
    if re.search(r"\b(FAIL(ED|URES)?|REJECTED|Untrusted peer|alert|error:|refused)\b", line) and "FAILED: 0" not in line:
        return "#F87171"
    if re.search(r"\b(PASS(ED)?|ALL TESTS PASSED|BUILD SUCCESSFUL|started up|COMPLETED|ACKNOWLEDGED|Handshake completed|Bridge Connected)\b", line):
        return "#4ADE80"
    if l.startswith(">>") or l.startswith("TEST ") or l.startswith("NODE:") or l.startswith("SUMMARY") or l.startswith("STEP"):
        return "#22D3EE"
    if l.startswith("=") or l.startswith("-") or l.startswith("+"):
        return "#475569"
    if l.startswith("$"):
        return "#FACC15"
    return "#E2E8F0"


def terminal_png(lines, out, title="PowerShell - gagan-secure-p2p-corda", size=18, max_cols=None, min_cols=80):
    if max_cols:
        lines = [l[:max_cols] for l in lines]
    font = ImageFont.truetype(MONO, size)
    bold = ImageFont.truetype(MONO_B, size)
    cw = font.getbbox("M")[2]
    lh = int(size * 1.35)
    cols = max(min_cols, max(len(l) for l in lines))
    pad = 24
    bar = 40
    W = cols * cw + pad * 2
    H = bar + pad + len(lines) * lh + pad
    img = Image.new("RGB", (W, H), "#0D1117")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, bar], fill="#1F2937")
    for i, c in enumerate(["#EF4444", "#F59E0B", "#22C55E"]):
        d.ellipse([16 + i * 24, 13, 30 + i * 24, 27], fill=c)
    d.text((100, 10), title, font=ImageFont.truetype(MONO, 16), fill="#9CA3AF")
    y = bar + pad
    for l in lines:
        c = colour_for(l)
        d.text((pad, y), l, font=bold if c == "#22D3EE" else font, fill=c)
        y += lh
    img.save(out)
    return out


def section(lines, start, end=None):
    """Lines from the first line starting with `start` up to (not incl.) the first line starting with `end`."""
    out, on = [], False
    for l in lines:
        if l.startswith(start):
            on = True
        elif end and on and l.startswith(end):
            break
        if on:
            out.append(l)
    while out and not out[-1].strip():
        out.pop()
    return out


def evidence_images():
    made = []
    # tests
    t = read("test_results.txt")
    made.append(terminal_png(["$ gradlew test --rerun-tasks"] + t, os.path.join(IMG, "ev_tests.png"), size=17))

    # node start-up: banner from EnterpriseA console + the 4 started-up lines
    banner = []
    p = os.path.join(ROOT, "build", "nodes", "EnterpriseA", "logs", "node-stdout.log")
    if os.path.exists(p):
        with open(p, encoding="utf-8", errors="replace") as f:
            raw = [sanitize(x.rstrip()) for x in f]
        for x in raw:
            if x.startswith("[WARN") or x.startswith("[ERROR") or x.startswith("[INFO"):
                continue
            if not x.startswith("---") and ":" not in x and "!" not in x and "Node for" not in x and "Running" not in x:
                x = x[:38].rstrip()   # ASCII-art logo only; drop Corda's random tagline
            banner.append(x[:118])
            if "Running P2PMessaging loop" in x:
                break
    start = read("node_startup.txt")
    made.append(terminal_png(["$ python scripts/nodes.py start"] + start + ["", "--- EnterpriseA console (build/nodes/EnterpriseA/logs/node-stdout.log) ---"] + banner,
                             os.path.join(IMG, "ev_node_startup.png"), size=17))

    # certificates (EnterpriseA section + hierarchy)
    c = read("certificates.txt")
    cert = section(c, "HIERARCHY", "NODE: EnterpriseB")
    cert = [l for l in cert if not l.startswith("-" * 50)]
    made.append(terminal_png(["$ keytool -list -v -keystore build/nodes/EnterpriseA/certificates/<store>.jks   (summary)"] + cert,
                             os.path.join(IMG, "ev_certificates.png"), size=16))

    # TLS handshake
    tl = read("tls_handshake.txt")
    t1 = section(tl, "TEST 1", "TEST 2")
    t1 = [l for l in t1 if "Signature Algorithms" not in l]
    summ = section(tl, "SERVER SIDE")
    summ = [re.sub(r"\[P2PServer-netty-\d+\] core.server. - | for client from /\[[^\]]+\]:\d+|javax.net.ssl.", "", l) for l in summ]
    made.append(terminal_png(t1 + [""] + [l[:150] for l in summ], os.path.join(IMG, "ev_tls_handshake.png"), size=16))

    # p2p links summary
    pl = read("p2p_links.txt")
    a_lines = section(pl, "NODE: EnterpriseA", "------")
    a_block = [l for l in section(pl, "NODE: EnterpriseA", "NODE: EnterpriseB") if "AMQP" in l or "Connect" in l or "Handshake" in l or "Bridge" in l][:9]
    made.append(terminal_png(["$ grep AMQP/TLS bridge events in build/nodes/*/logs/node-*.log"] + a_lines[:1] + [l[:150] for l in a_block] + [""] + section(pl, "  SUMMARY"),
                             os.path.join(IMG, "ev_p2p_links.png"), size=16))

    # demo run - full + per section
    dr = read("demo_run.txt")
    header = dr[:4]
    made.append(terminal_png(["$ scripts/demo_client.sh all"] + section(dr, "===", ">> 5"), os.path.join(IMG, "ev_demo_part1.png"), size=15))
    made.append(terminal_png(section(dr, ">> 5"), os.path.join(IMG, "ev_demo_part2.png"), size=15))
    for key, start, end in [("networkmap", ">> 1", ">> 2"), ("send", ">> 2", ">> 3"), ("ack", ">> 3", ">> 4"),
                            ("read", ">> 4", ">> 5"), ("privacy", ">> 5", ">> 6"), ("untrusted", ">> 6", ">> 7"),
                            ("ping", ">> 7", ">> 8"), ("bench", ">> 8", "Done.")]:
        made.append(terminal_png(section(dr, start, end), os.path.join(IMG, f"ev_demo_{key}.png"), size=17, min_cols=60))
    return made


# ============================================================================ diagrams

def box(ax, x, y, w, h, text, fc=NAVY, ec=None, tc="white", fs=11, bold=True, r=0.02, sub=None, subc=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.005,rounding_size={r}", fc=fc, ec=ec or fc, lw=1.6))
    if sub:
        ax.text(x + w / 2, y + h * 0.62, text, ha="center", va="center", color=tc, fontsize=fs, weight="bold" if bold else "normal")
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", color=subc or tc, fontsize=fs - 2.5)
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs, weight="bold" if bold else "normal")


def arrow(ax, p1, p2, color=TEAL, lw=2.2, style="-|>", ls="-", rad=0.0, ms=16):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, color=color, lw=lw, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", mutation_scale=ms))


def new_fig(w=16, h=9):
    fig, ax = plt.subplots(figsize=(w, h), dpi=120)
    fig.patch.set_facecolor(LIGHT)
    ax.set_facecolor(LIGHT)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    plt.rcParams["font.family"] = "Segoe UI"
    return fig, ax


def save(fig, name):
    p = os.path.join(DIA, name)
    fig.savefig(p, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return p


def d_topology():
    fig, ax = new_fig()
    ax.text(0.5, 0.965, "Network Topology - 4 Corda 4.12 nodes, point-to-point AMQP over mutual TLS", ha="center",
            fontsize=18, weight="bold", color=NAVY)
    # nodes
    A = (0.06, 0.48, 0.24, 0.16)
    B = (0.70, 0.48, 0.24, 0.16)
    C = (0.38, 0.76, 0.24, 0.14)
    N = (0.38, 0.12, 0.24, 0.15)
    box(ax, *A, "EnterpriseA", sub="O=EnterpriseA, L=Bengaluru, C=IN\nP2P 10005 | RPC 10006", fs=15)
    box(ax, *B, "EnterpriseB", sub="O=EnterpriseB, L=Mumbai, C=IN\nP2P 10008 | RPC 10009", fs=15)
    box(ax, *C, "EnterpriseC", fc="#334155", sub="O=EnterpriseC, L=Delhi, C=IN\nP2P 10011 | RPC 10012", fs=15)
    box(ax, *N, "Notary (non-validating)", fc=TEAL_D, sub="O=Notary, L=Bengaluru, C=IN\nP2P 10002 | RPC 10003", fs=14)
    # A <-> B
    arrow(ax, (0.30, 0.58), (0.70, 0.58), color=TEAL, lw=4, style="<|-|>")
    ax.text(0.5, 0.615, "SecureMessage flows: key exchange, signatures, finality", ha="center", fontsize=12, color=TEAL_D, weight="bold")
    ax.text(0.5, 0.545, "AMQP 1.0 / TLS 1.2 mutual auth\nECDHE-ECDSA-AES128-GCM-SHA256", ha="center", va="top", fontsize=10.5, color=NAVY)
    # notary links
    arrow(ax, (0.20, 0.48), (0.40, 0.27), color=GREY, lw=2, style="<|-|>", ls="--")
    arrow(ax, (0.80, 0.48), (0.60, 0.27), color=GREY, lw=2, style="<|-|>", ls="--")
    ax.text(0.22, 0.34, "notarise\n(filtered tx only)", fontsize=10.5, color=GREY, ha="center")
    ax.text(0.78, 0.34, "notarise\n(filtered tx only)", fontsize=10.5, color=GREY, ha="center")
    # C links
    arrow(ax, (0.40, 0.76), (0.24, 0.64), color=RED, lw=2.4, style="-|>", ls="--")
    ax.text(0.205, 0.735, "C -> A rejected:\n\"Untrusted peer\"", fontsize=11, color=RED, ha="center", weight="bold")
    arrow(ax, (0.60, 0.76), (0.76, 0.64), color="#94A3B8", lw=1.6, style="<|-|>", ls=":")
    ax.text(0.80, 0.735, "trusted by B\n(no traffic in demo)", fontsize=10.5, color=GREY, ha="center")
    # legend / trust
    ax.text(0.03, 0.06, "trustedPeers:  A = [B]   |   B = [A, C]   |   C = [A, B]        Network map & PKI: dev-mode Corda Root CA -> Doorman CA -> node CAs",
            fontsize=11, color=NAVY)
    return save(fig, "d1_topology.png")


def d_layers():
    fig, ax = new_fig(16, 9)
    ax.text(0.5, 0.965, "Defence in Depth - four security layers on every message", ha="center", fontsize=18, weight="bold", color=NAVY)
    layers = [
        ("1  TRANSPORT", "TLS 1.2 mutual authentication (AMQP 1.0 over Artemis bridges)",
         "Both nodes present Doorman-issued certs (ECDSA P-256); ECDHE forward secrecy;\nno client cert = handshake_failure (alert 40); TLS 1.3/legacy refused",
         "Eavesdropping, MITM,\noutsiders connecting", "#1E3A5F"),
        ("2  IDENTITY", "Corda identity signatures + notary",
         "Ed25519 legal-identity keys: sender AND receiver sign Send; receiver signs Acknowledge;\nnon-validating notary signs + time-stamps, prevents double acknowledgement",
         "Impersonation, repudiation,\ndouble-spend of state", "#155E75"),
        ("3  APPLICATION", "End-to-end AES-256-GCM per message",
         "In-flow X25519 ECDH + HKDF-SHA256 -> random per-message key; GCM tag + SHA-256 contentHash;\nkey envelopes wrapped with a KEK derived from each node's own identity key",
         "Vault/backup leaks, notary or\noperator reading content, tampering", TEAL_D),
        ("4  PRIVACY", "Need-to-know distribution + trusted-peer policy",
         "participants = sender + receiver only; FinalityFlow sends to the receiver only;\ncordapp config trustedPeers allow-list checked by initiator and responder",
         "Data leaking to other members,\nunsolicited counterparties", "#0D9488"),
    ]
    y = 0.90
    for i, (name, head, body, threat, col) in enumerate(layers):
        x0 = 0.02 + i * 0.025
        w = 0.70 - i * 0.05
        box(ax, x0, y - 0.155, w, 0.155, "", fc=col)
        ax.text(x0 + 0.015, y - 0.035, name, color="#99F6E4", fontsize=12.5, weight="bold", va="center")
        ax.text(x0 + 0.015, y - 0.072, head, color="white", fontsize=14, weight="bold", va="center")
        ax.text(x0 + 0.015, y - 0.122, body, color="#E2E8F0", fontsize=10.2, va="center")
        box(ax, 0.76, y - 0.14, 0.22, 0.125, "Stops:", fc="white", ec=col, tc=col, fs=11, sub=threat, subc=NAVY)
        arrow(ax, (x0 + w + 0.005, y - 0.078), (0.758, y - 0.078), color=col, lw=1.8)
        y -= 0.20
    ax.text(0.02, 0.06, "Outer layers are provided by the Corda platform; layers 3 and 4 are implemented in this CorDapp (com.securep2p).",
            fontsize=11.5, color=NAVY, style="italic")
    return save(fig, "d2_security_layers.png")


def d_certs():
    fig, ax = new_fig(16, 9)
    ax.text(0.5, 0.965, "Certificate Hierarchy (from keytool on build/nodes/EnterpriseA/certificates)", ha="center", fontsize=18, weight="bold", color=NAVY)
    box(ax, 0.36, 0.78, 0.28, 0.12, "Corda Node Root CA", sub="self-signed, ECDSA P-256 | truststore.jks (all nodes)", fs=14)
    box(ax, 0.06, 0.55, 0.26, 0.12, "Network Map CA", fc="#475569", sub="signs network map + parameters", fs=13)
    box(ax, 0.40, 0.55, 0.30, 0.12, "Corda Doorman CA", fc=NAVY2, sub="intermediate; issues node CA certs", fs=14)
    box(ax, 0.40, 0.32, 0.30, 0.12, "Node CA: O=EnterpriseA", fc=TEAL_D, sub="cordaclientca | nodekeystore.jks", fs=14)
    box(ax, 0.18, 0.07, 0.32, 0.14, "TLS certificate", fc="#0E7490", sub="cordaclienttls | sslkeystore.jks\nECDSA P-256 -> mutual TLS on P2P port 10005", fs=14)
    box(ax, 0.58, 0.07, 0.34, 0.14, "Legal identity certificate", fc="#0E7490", sub="identity-private-key | nodekeystore.jks\nEd25519 -> signs transactions (+ derives KEK)", fs=14)
    arrow(ax, (0.44, 0.78), (0.22, 0.67), color=GREY)
    arrow(ax, (0.52, 0.78), (0.55, 0.67), color=NAVY, lw=2.6)
    arrow(ax, (0.55, 0.55), (0.55, 0.44), color=NAVY, lw=2.6)
    arrow(ax, (0.50, 0.32), (0.36, 0.21), color=TEAL_D, lw=2.6)
    arrow(ax, (0.60, 0.32), (0.73, 0.21), color=TEAL_D, lw=2.6)
    ax.text(0.76, 0.40, "Chain presented in the TLS handshake\n(4 certs): TLS -> Node CA -> Doorman -> Root",
            fontsize=11.5, color=NAVY, va="center")
    ax.text(0.03, 0.40, "A peer is accepted only if its chain\nvalidates up to the Root CA in\ntruststore.jks (pass: trustpass)",
            fontsize=11.5, color=NAVY, va="center")
    return save(fig, "d3_certificate_hierarchy.png")


def d_sequence():
    fig, ax = new_fig(16, 10)
    ax.text(0.5, 0.975, "SendSecureMessageFlow + AcknowledgeMessageFlow - sequence", ha="center", fontsize=18, weight="bold", color=NAVY)
    xs = {"A": 0.16, "B": 0.56, "N": 0.88}
    names = {"A": "EnterpriseA (sender)", "B": "EnterpriseB (receiver)", "N": "Notary"}
    for k, x in xs.items():
        box(ax, x - 0.1, 0.89, 0.2, 0.055, names[k], fc=TEAL_D if k == "N" else NAVY, fs=12.5)
        ax.plot([x, x], [0.04, 0.89], color="#94A3B8", lw=1.5, ls="--", zorder=0)
    steps = [
        ("A", "A", "1  trust check: B in trustedPeers", None),
        ("A", "B", "2  Init(linearId, ephemeral X25519 pubA)", TEAL),
        ("B", "B", "3  trust check A; gen ephB; ECDH+HKDF -> K; wrap K (B's KEK)", None),
        ("B", "A", "4  Reply(pubB, receiverKeyEnvelope)", TEAL),
        ("A", "A", "5  ECDH+HKDF -> K; AES-256-GCM(body); SHA-256; wrap K", None),
        ("A", "A", "6  build tx: Send + time window; sign (Ed25519)", None),
        ("A", "B", "7  CollectSignaturesFlow: tx (ciphertext only)", NAVY),
        ("B", "B", "8  unwrap K, decrypt, verify SHA-256 -> sign", None),
        ("B", "A", "9  receiver signature", NAVY),
        ("A", "N", "10  FinalityFlow: notarise (filtered tx)", GREY),
        ("N", "A", "11  notary signature (time-stamped)", GREY),
        ("A", "B", "12  finalised tx -> B's vault (C never receives it)", NAVY),
        ("B", "B", "13  ReadMessageFlow: decrypt + integrity check", None),
        ("B", "N", "14  Acknowledge: SENT -> ACK (B signs)", AMBER),
        ("B", "A", "15  finality: A records ACKNOWLEDGED", AMBER),
    ]
    y = 0.85
    dy = 0.053
    for s, t, label, col in steps:
        if s == t:
            x = xs[s]
            ax.add_patch(FancyBboxPatch((x + 0.01, y - 0.018), 0.0064 * len(label) + 0.018, 0.034,
                                        boxstyle="round,pad=0.003,rounding_size=0.008", fc="#E0F2F1", ec=TEAL_D, lw=1))
            ax.text(x + 0.018, y, label, fontsize=10.8, va="center", color=NAVY)
        else:
            x1, x2 = xs[s], xs[t]
            arrow(ax, (x1, y), (x2, y), color=col, lw=2.2)
            ax.text((x1 + x2) / 2, y + 0.012, label, ha="center", fontsize=10.8, color=NAVY,
                    bbox=dict(fc=LIGHT, ec="none", pad=0.6))
        y -= dy
    return save(fig, "d4_sequence.png")


def d_lifecycle():
    fig, ax = new_fig(16, 7.5)
    ax.text(0.5, 0.95, "SecureMessageState lifecycle (SecureMessageContract)", ha="center", fontsize=18, weight="bold", color=NAVY)
    ax.plot([0.09], [0.55], marker="o", markersize=26, color=NAVY)
    box(ax, 0.33, 0.45, 0.18, 0.2, "SENT", fc=NAVY2, fs=17, sub="in A and B vaults", subc="#99F6E4")
    box(ax, 0.75, 0.45, 0.2, 0.2, "ACKNOWLEDGED", fc=TEAL_D, fs=17, sub="final state", subc="white")
    arrow(ax, (0.115, 0.55), (0.33, 0.55), color=NAVY, lw=2.6)
    ax.text(0.22, 0.60, "Send", ha="center", fontsize=14, weight="bold", color=NAVY)
    ax.text(0.22, 0.42, "0 inputs -> 1 output\nsender != receiver\nsubject not empty\nhash = 64 hex\n2 participants\nsigned by sender + receiver\nnotarised time window",
            ha="center", va="top", fontsize=10.5, color=NAVY)
    arrow(ax, (0.51, 0.55), (0.75, 0.55), color=TEAL_D, lw=2.6)
    ax.text(0.63, 0.60, "Acknowledge", ha="center", fontsize=14, weight="bold", color=TEAL_D)
    ax.text(0.63, 0.42, "1 input SENT -> 1 output ACK\ncontent, parties, hash unchanged\nsigned by receiver\n(after decrypt + SHA-256 check)\nnotary consumes SENT",
            ha="center", va="top", fontsize=10.5, color=NAVY)
    # rejections
    box(ax, 0.30, 0.78, 0.24, 0.09, "Tampered payload/hash", fc="#FEE2E2", ec=RED, tc=RED, fs=12, sub="ReadMessageFlow: Integrity check failed", subc=RED)
    arrow(ax, (0.42, 0.65), (0.42, 0.78), color=RED, lw=1.8, ls="--")
    box(ax, 0.73, 0.78, 0.24, 0.09, "Second acknowledgement", fc="#FEE2E2", ec=RED, tc=RED, fs=12, sub="rejected: already acknowledged", subc=RED)
    arrow(ax, (0.85, 0.65), (0.85, 0.78), color=RED, lw=1.8, ls="--")
    box(ax, 0.02, 0.78, 0.22, 0.09, "Untrusted sender (C)", fc="#FEE2E2", ec=RED, tc=RED, fs=12, sub="no state created", subc=RED)
    arrow(ax, (0.13, 0.78), (0.10, 0.59), color=RED, lw=1.8, ls="--")
    ax.text(0.5, 0.08, "linearId stays the same across both states; only the status changes", ha="center", fontsize=12, color=GREY, style="italic")
    return save(fig, "d5_lifecycle.png")


if __name__ == "__main__":
    out = evidence_images()
    out += [d_topology(), d_layers(), d_certs(), d_sequence(), d_lifecycle()]
    for p in out:
        im = Image.open(p)
        print(f"{os.path.relpath(p, ROOT):<40} {im.size[0]}x{im.size[1]}")
