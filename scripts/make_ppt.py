"""Builds ppt/Topic12_Secure_P2P_Corda_24BTRBT013.pptx (16:9, dark navy + teal) with speaker notes.
Gagan N (24BTRBT013).    python scripts/make_ppt.py
"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ppt", "Topic12_Secure_P2P_Corda_24BTRBT013.pptx")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
NAVY2 = RGBColor(0x13, 0x2C, 0x52)
CARD = RGBColor(0x16, 0x33, 0x5C)
TEAL = RGBColor(0x14, 0xB8, 0xA6)
TEAL_L = RGBColor(0x99, 0xF6, 0xE4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0xE2, 0xE8, 0xF0)
MUTED = RGBColor(0x94, 0xA3, 0xB8)
RED = RGBColor(0xF8, 0x71, 0x71)
GREEN = RGBColor(0x4A, 0xDE, 0x80)
FONT = "Segoe UI"
ARROW = "→"
BULLET = "▸"

DEMO = open(os.path.join(ROOT, "evidence", "demo_run.txt"), encoding="utf-8").read()
PING = [float(x) for x in re.findall(r"#\d\d +([\d.]+) ms", DEMO)]
STATS = re.search(r"\| 20 +\| ([\d.]+) +\| ([\d.]+) +\| ([\d.]+) +\| ([\d.]+) +\| ([\d.]+)", DEMO).groups()
KEX_MS = float(re.search(r"ECDH \+ HKDF : ([\d.]+) us", DEMO).group(1)) / 1000


# ------------------------------------------------------------------ latency chart (single series, no legend)
def latency_chart():
    p = os.path.join(ROOT, "diagrams", "latency_chart.png")
    fig, ax = plt.subplots(figsize=(6.4, 2.9), dpi=200)
    bg = "#132C52"
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    xs = list(range(1, len(PING) + 1))
    ax.bar(xs, PING, width=0.62, color="#14B8A6", edgecolor=bg, linewidth=1)
    avg = float(STATS[0])
    ax.axhline(avg, color="#E2E8F0", lw=1.2, ls=(0, (4, 3)))
    ax.text(len(PING) + 0.7, avg + 2, f"avg {avg:.1f}", color="#E2E8F0", fontsize=9, va="bottom", ha="left")
    ax.text(0.01, 0.97, f"min {min(PING):.1f} ms   max {max(PING):.1f} ms   median {float(STATS[3]):.1f} ms",
            transform=ax.transAxes, color="#E2E8F0", fontsize=9, va="top")
    ax.set_xlim(0.3, len(PING) + 3.2)
    ax.set_ylim(0, max(PING) * 1.28)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_xlabel("PingPeerFlow round trip #  (EnterpriseA -> EnterpriseB)", color="#94A3B8", fontsize=9)
    ax.set_ylabel("latency (ms)", color="#94A3B8", fontsize=9)
    ax.tick_params(colors="#94A3B8", labelsize=8.5, length=0)
    ax.grid(axis="y", color="#2A4470", lw=0.6)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(p, facecolor=bg)
    plt.close(fig)
    return "diagrams/latency_chart.png"


# ------------------------------------------------------------------ helpers
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SLIDE_NO = [0]


def add_runs(p, line, size, color, bold=False, font=FONT, emph=TEAL_L):
    for j, part in enumerate(re.split(r"\*\*(.+?)\*\*", line)):
        if not part:
            continue
        r = p.add_run()
        r.text = part
        r.font.size = Pt(size)
        r.font.name = font
        r.font.bold = bold or j % 2 == 1
        r.font.color.rgb = emph if (j % 2 == 1 and not bold) else color


def text(slide, x, y, w, h, content, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         font=FONT, gap=0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    lines = content if isinstance(content, list) else [content]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if gap:
            p.space_after = Pt(gap)
        add_runs(p, line, size, color, bold, font)
    return tb


def set_bullet(p):
    """Real PowerPoint bullet with a hanging indent, so wrapped lines align with the text."""
    pPr = p._p.get_or_add_pPr()
    hang = int(Inches(0.36))
    pPr.set("marL", str(hang))
    pPr.set("indent", str(-hang))
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", "14B8A6")
    etree.SubElement(pPr, qn("a:buSzPct")).set("val", "90000")
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Segoe UI Symbol")
    etree.SubElement(pPr, qn("a:buChar")).set("char", BULLET)


def bullets(slide, items, x=0.6, y=1.75, w=5.9, h=4.9, size=19, gap=10):
    assert len(items) <= 5, "max 5 bullets"
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        set_bullet(p)
        add_runs(p, it, size, INK, emph=WHITE)
    return tb


def rect(slide, x, y, w, h, fill=CARD, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb = line
        s.line.width = Pt(1.25)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def bar(slide, x, y, w, h=0.06):
    b = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid()
    b.fill.fore_color.rgb = TEAL
    b.line.fill.background()


def image_fit(slide, path, x, y, w, h, card=False, pad=0.12):
    """Place an image inside the box (x,y,w,h) keeping aspect ratio, centred; optional light card behind."""
    full = os.path.join(ROOT, path)
    iw, ih = Image.open(full).size
    bw, bh = w - (2 * pad if card else 0), h - (2 * pad if card else 0)
    scale = min(bw / iw, bh / ih)
    pw, ph = iw * scale, ih * scale
    px, py = x + (w - pw) / 2, y + (h - ph) / 2
    if card:
        rect(slide, px - pad, py - pad, pw + 2 * pad, ph + 2 * pad, fill=RGBColor(0xF8, 0xFA, 0xFC), radius=0.03)
    else:
        rect(slide, px - 0.03, py - 0.03, pw + 0.06, ph + 0.06, fill=RGBColor(0x33, 0x41, 0x55), radius=0.01)
    slide.shapes.add_picture(full, Inches(px), Inches(py), Inches(pw), Inches(ph))


def new_slide(title, notes, kicker=None):
    s = prs.slides.add_slide(BLANK)
    SLIDE_NO[0] += 1
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    if title:
        if kicker:
            text(s, 0.6, 0.32, 9, 0.35, kicker.upper(), size=12, color=TEAL, bold=True)
        text(s, 0.6, 0.58, 12.1, 0.8, title, size=30, color=WHITE, bold=True)
        bar(s, 0.62, 1.38, 1.1)
        text(s, 0.6, 7.02, 9, 0.3, "Gagan N – 24BTRBT013  |  Secure P2P Communication between Enterprise Corda Nodes",
             size=10, color=MUTED)
        text(s, 12.0, 7.02, 0.8, 0.3, str(SLIDE_NO[0]), size=10, color=MUTED, align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = notes
    return s


def tile(slide, x, y, w, h, head, body, head_color=TEAL_L, size_h=15, size_b=12.5, fill=CARD):
    rect(slide, x, y, w, h, fill=fill)
    text(slide, x + 0.18, y + 0.14, w - 0.36, 0.45, head, size=size_h, color=head_color, bold=True)
    text(slide, x + 0.18, y + 0.62, w - 0.36, h - 0.72, body, size=size_b, color=INK, gap=6)


def grid8(slide, items):
    for i, (h, b) in enumerate(items):
        col, row = i % 4, i // 4
        tile(slide, 0.6 + col * 3.07, 1.85 + row * 2.45, 2.85, 2.15, h, b, size_h=19, size_b=16)


# ================================================================== slides

# 1 Title
s = new_slide(None, "Hello, I am Gagan N, USN 24BTRBT013, from CSE Blockchain Technology, semester five. My mini project "
    "for the Corda Development course is topic number twelve: Implementation of Secure Peer-to-Peer Communication "
    "between Enterprise Corda Nodes. In this presentation I will explain the problem I chose, the Corda concepts I "
    "used, and how I designed the network, the state, the contract and the flows. Then I will show how I added "
    "end-to-end encryption and a trusted peer policy, and the real results I measured on a running four-node network.")
side = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.9), 0, Inches(4.433), Inches(7.5))
side.fill.solid(); side.fill.fore_color.rgb = NAVY2; side.line.fill.background()
text(s, 0.7, 0.9, 7.8, 0.4, "CORDA DEVELOPMENT  |  MINI PROJECT  |  TOPIC 12 (M2)", size=13, color=TEAL, bold=True)
text(s, 0.7, 1.5, 7.9, 2.6, "Implementation of Secure Peer-to-Peer Communication between Enterprise Corda Nodes",
     size=36, color=WHITE, bold=True)
bar(s, 0.72, 4.25, 1.4, 0.07)
text(s, 0.7, 4.55, 7.8, 0.6, "Gagan N – 24BTRBT013", size=26, color=WHITE, bold=True)
text(s, 0.7, 5.2, 7.8, 1.0, ["CSE (Blockchain Technology), Semester V",
                             "Jain (Deemed-to-be University), Bengaluru"], size=16, color=INK)
facts = [("Platform", "Corda 4.12, JDK 17"), ("Network", "Notary + 3 enterprise nodes"),
         ("Transport", "TLS 1.2 mutual auth"), ("Payload", "X25519 + AES-256-GCM"),
         ("Policy", "Trusted-peer allow-list")]
text(s, 9.35, 0.9, 3.6, 0.4, "AT A GLANCE", size=13, color=TEAL, bold=True)
for i, (k, v) in enumerate(facts):
    y = 1.45 + i * 1.0
    rect(s, 9.35, y, 3.55, 0.85, fill=CARD)
    text(s, 9.5, y + 0.07, 3.3, 0.3, k, size=11.5, color=MUTED)
    text(s, 9.5, y + 0.36, 3.3, 0.4, v, size=15, color=WHITE, bold=True)

# 2 Problem
s = new_slide("Problem Statement", "Let me start with the problem. Companies share very sensitive information with each "
    "other, like purchase orders, prices, contract terms and invoices. Most of this still goes through e-mail, where "
    "messages sit in plain text on many servers, can be forwarded to anyone, and give no strong proof of what was "
    "received. Public blockchains are not the answer either, because they broadcast every transaction to every node. "
    "So I needed a way for two enterprises to talk privately, securely and verifiably, and only with partners they trust.",
    kicker="Why this project")
bullets(s, ["Enterprises exchange **confidential data**: purchase orders, prices, contract terms, invoices",
            "E-mail / portals: **plaintext on many servers**, easy to forward, no proof of receipt",
            "Public blockchains **broadcast everything** to every node",
            "Need: only **sender + receiver** can read, channel **encrypted & authenticated**",
            "Every message **signed, acknowledged, tamper-evident**, only with **trusted** partners"], w=6.4)
tile(s, 7.4, 1.8, 5.3, 2.3, "Today: e-mail / shared portal", ["Readable by servers, admins, backups",
     "No cryptographic proof of what was agreed", "Any recipient can forward it"], head_color=RED, size_h=18, size_b=16)
tile(s, 7.4, 4.35, 5.3, 2.3, "Needed: secure P2P channel", ["Point-to-point, need-to-know only",
     "End-to-end encrypted, signed by both sides", "Only explicitly trusted counterparties"], head_color=GREEN,
     size_h=18, size_b=16)

# 3 Objectives
s = new_slide("Objectives", "These were my objectives. First, I set up a Corda 4.12 network with a notary and three "
    "enterprise nodes. Second, I designed a secure message state and a contract with strict rules. Third, I added "
    "application-level encryption using an X25519 key exchange and AES-256-GCM. Fourth, I enforced a trusted-peer "
    "policy from configuration. And finally, I proved everything with automated tests and with real evidence from the "
    "running nodes, such as the certificates, the TLS handshake and latency measurements.", kicker="What I set out to do")
objs = [("01", "Network", "Notary + EnterpriseA, B, C with own P2P/RPC ports (deployNodes)"),
        ("02", "State & contract", "SecureMessageState + Send / Acknowledge rules"),
        ("03", "End-to-end encryption", "In-flow X25519 ECDH, HKDF, AES-256-GCM per message"),
        ("04", "Trust policy", "trustedPeers config; C is not trusted by A"),
        ("05", "Proof", "22 tests + certificates, TLS handshake, privacy & latency evidence")]
for i, (n, h, b) in enumerate(objs):
    y = 1.75 + i * 1.02
    rect(s, 0.6, y, 12.1, 0.88, fill=CARD)
    text(s, 0.8, y + 0.14, 0.9, 0.6, n, size=26, color=TEAL, bold=True)
    text(s, 1.8, y + 0.2, 3.6, 0.5, h, size=19, color=WHITE, bold=True)
    text(s, 5.4, y + 0.22, 7.1, 0.5, b, size=16, color=INK)

# 4 Why Corda
s = new_slide("Why Corda for Enterprise P2P", "I chose Corda because it was built for exactly this kind of business "
    "privacy. In a public blockchain everyone sees everything and participants are anonymous. In Corda every node has "
    "a known, certified legal identity, and data is shared only on a need-to-know basis. Transactions go directly from "
    "one node to another and are never broadcast. The notary only confirms uniqueness and time, and does not need to "
    "see the content. This model gave me a strong base, and I built extra layers on top of it.", kicker="Platform choice")
bullets(s, ["**No broadcast**: transactions go only to the parties involved",
            "**Need-to-know**: a vault stores only states its node participates in",
            "**Known identities**: X.500 names certified by the network CA",
            "**Notary** confirms uniqueness and time, not content",
            "Direct **node-to-node** messaging over mutual TLS"], w=5.9, size=18)
rows = [("", "Public blockchain", "Corda"), ("Visibility", "everyone sees all", "need-to-know"),
        ("Identity", "pseudonymous", "certified X.500"), ("Delivery", "gossip broadcast", "point-to-point"),
        ("Consensus", "global ordering", "notary + signers"), ("Fit for B2B secrets", "poor", "strong")]
tb = s.shapes.add_table(len(rows), 3, Inches(6.9), Inches(1.85), Inches(5.8), Inches(4.4)).table
tb.columns[0].width = Inches(2.0); tb.columns[1].width = Inches(1.9); tb.columns[2].width = Inches(1.9)
for i, row in enumerate(rows):
    for j, val in enumerate(row):
        c = tb.cell(i, j)
        c.fill.solid()
        c.fill.fore_color.rgb = TEAL if i == 0 else (CARD if i % 2 else NAVY2)
        c.text = val or " "
        r = c.text_frame.paragraphs[0].runs[0]
        r.font.size = Pt(15)
        r.font.name = FONT
        r.font.bold = i == 0 or j == 0
        r.font.color.rgb = NAVY if i == 0 else (GREEN if j == 2 else INK)

# 5 Concepts
s = new_slide("Corda Concepts Used", "These are the Corda concepts I used. Nodes are the participants, each with its own "
    "vault database. The network map tells every node where its peers are. Flows describe the conversation between "
    "nodes, and sessions are the actual point-to-point channels inside a flow. Underneath, Corda uses the Artemis "
    "message broker and the AMQP protocol over TLS. The notary prevents double spending and time-stamps transactions, "
    "and the vault stores only the states a node participates in.", kicker="Building blocks")
grid8(s, [("Nodes", "JVM processes with a legal identity + keys"),
          ("Network map", "Discovery of peers' addresses and identities"),
          ("Flows", "Scripted multi-party protocols (@InitiatingFlow)"),
          ("Sessions", "Point-to-point channels: send / receive"),
          ("Artemis / AMQP", "Embedded broker, AMQP 1.0 bridges over TLS"),
          ("Notary", "Uniqueness + time window, non-validating"),
          ("Vault", "Stores only the node's own states"),
          ("Contracts", "Deterministic rules checked by every signer")])

# 6 Architecture
s = new_slide("Network Architecture", "Here is my network. I have four nodes, created with deployNodes: a non-validating "
    "notary, EnterpriseA in Bengaluru, EnterpriseB in Mumbai and EnterpriseC in Delhi. Each node has its own P2P port, "
    "RPC port and RPC user. EnterpriseA and EnterpriseB exchange the secure messages. EnterpriseC is a valid member of "
    "the network, but EnterpriseA does not trust it, so I can show what happens when an untrusted peer tries to send "
    "a message.", kicker="deployNodes: 4 nodes")
text(s, 0.6, 1.75, 4.0, 0.4, "P2P / RPC PORTS", size=12, color=TEAL, bold=True)
bullets(s, ["**Notary** 10002 / 10003",
            "**EnterpriseA** 10005 / 10006",
            "**EnterpriseB** 10008 / 10009",
            "**EnterpriseC** 10011 / 10012",
            "Trust: A=[B]  B=[A,C]  C=[A,B]"], y=2.2, w=4.1, size=17, gap=14)
image_fit(s, "diagrams/d1_topology.png", 4.8, 1.65, 8.0, 5.2, card=True)

# 7 Security layers
s = new_slide("Security Layers", "I designed the security as four layers. The first layer is transport: TLS 1.2 with "
    "mutual authentication between the Artemis brokers. The second is identity: both sender and receiver sign every "
    "message with their Ed25519 keys, and the notary signs too. The third layer is my own end-to-end encryption, "
    "AES-256-GCM with a fresh key for every message. The fourth is privacy: only the two parties are participants, and "
    "a trusted-peer list controls who may talk at all.", kicker="Defence in depth")
image_fit(s, "diagrams/d2_security_layers.png", 0.6, 1.65, 12.1, 5.25, card=True)

# 8 Certificates & mTLS
s = new_slide("Certificate Hierarchy & Mutual TLS", "This slide shows the certificate hierarchy that I extracted with "
    "keytool. The Corda root CA signs the Doorman CA, which signs each node's CA. The node CA then issues two "
    "certificates: the TLS certificate used on the P2P port, and the legal identity certificate used for signing. When "
    "I connected with openssl without a client certificate, the handshake was rejected with alert forty. With a valid "
    "network certificate it completed, using TLS 1.2 and an ECDHE ECDSA AES GCM cipher suite.", kicker="PKI & transport")
image_fit(s, "diagrams/d3_certificate_hierarchy.png", 0.6, 1.65, 7.6, 5.2, card=True)
bullets(s, [f"Root CA {ARROW} Doorman CA {ARROW} **Node CA** {ARROW} TLS + identity",
            "TLS key **ECDSA P-256**, identity key **Ed25519**",
            f"No client cert {ARROW} **rejected** (alert 40)",
            f"Valid network cert {ARROW} **TLS 1.2** handshake completes",
            "TLS 1.3 / legacy versions refused"], x=8.5, w=4.3, size=16, gap=12)

# 9 State & contract
s = new_slide("State & Contract Design", "My SecureMessageState is a linear state. It stores the sender, the receiver, "
    "a subject, a SHA-256 content hash, the encrypted payload, two wrapped key envelopes, the time and a status. The "
    "participants are only the sender and the receiver. The contract has two commands. Send needs no inputs, one SENT "
    "output, different parties, a valid hash, exactly two participants and both signatures. Acknowledge changes SENT "
    "to ACKNOWLEDGED, keeps the content unchanged, and must be signed by the receiver.",
    kicker="SecureMessageState + SecureMessageContract")
tile(s, 0.6, 1.75, 4.6, 5.0, "SecureMessageState", ["linearId, sender, receiver",
     "subject, contentHash (SHA-256)", "encryptedPayload (AES-GCM)", "sender / receiver key envelopes",
     "sentAt, status {SENT, ACKNOWLEDGED}", "participants = sender + receiver"], size_h=20, size_b=17)
image_fit(s, "diagrams/d5_lifecycle.png", 5.5, 1.75, 7.2, 3.5, card=True)
text(s, 5.5, 5.5, 7.2, 1.3, [f"**Send:** 0 in {ARROW} 1 SENT, sender ≠ receiver, 64-hex hash, 2 participants, both sign",
                             f"**Acknowledge:** SENT {ARROW} ACKNOWLEDGED, content unchanged, receiver signs"], size=15, gap=6)

# 10 Flow design
s = new_slide("Flow Design", "This sequence diagram shows my send flow. First, EnterpriseA checks its trust list and "
    "sends an ephemeral X25519 public key over the session. EnterpriseB checks its own trust list, replies with its "
    "public key, and both sides derive the same AES key. A encrypts the body and builds the transaction. B decrypts it "
    "and verifies the hash before signing. Then the notary signs, and finality delivers the transaction only to B. "
    "Later, B reads the message and acknowledges it.", kicker="Sequence diagram")
image_fit(s, "diagrams/d4_sequence.png", 0.6, 1.6, 8.6, 5.3, card=True)
bullets(s, ["**SendSecureMessageFlow** + responder", "**AcknowledgeMessageFlow** (receiver)",
            "**ReadMessageFlow**: local decrypt + hash check", "**PingPeerFlow**: raw P2P latency"],
        x=9.5, w=3.3, size=15, gap=14)

# 11 Encryption & trust policy
s = new_slide("Encryption & Trust Policy", "Let me explain the encryption in more detail. For every message, both nodes "
    "create fresh X25519 key pairs, and the shared secret goes through HKDF to give a 256-bit AES key. The body is "
    "encrypted with AES-GCM, which also detects any modification. To decrypt later, each node wraps the key with a key "
    "derived from its own identity key, so the vault never holds a plain key. The trust policy is a simple list in "
    "each node's CorDapp configuration file.", kicker="Application layer")
steps = [("X25519", ["ephemeral ECDH", "over the session"]), ("HKDF-SHA256", ["256-bit key", "per message"]),
         ("AES-256-GCM", ["IV + tag,", "metadata as AAD"]), ("Key envelope", ["wrapped with", "identity-derived KEK"])]
for i, (h, b) in enumerate(steps):
    x = 0.6 + i * 3.1
    rect(s, x, 1.8, 2.75, 1.7, fill=CARD, line=TEAL)
    text(s, x + 0.1, 1.92, 2.55, 0.45, h, size=18, color=TEAL_L, bold=True, align=PP_ALIGN.CENTER)
    text(s, x + 0.1, 2.45, 2.55, 0.9, b, size=14, color=INK, align=PP_ALIGN.CENTER)
    if i < 3:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.8), Inches(2.45), Inches(0.26), Inches(0.4))
        a.fill.solid(); a.fill.fore_color.rgb = TEAL; a.line.fill.background()
bullets(s, ["Notary, vault & backups see **only ciphertext**",
            "**SHA-256 contentHash** checked by receiver before signing",
            "trustedPeers checked by **initiator and responder**",
            "Default-deny if the config key is missing"], x=0.6, y=3.85, w=6.3, h=3.0, size=17)
rect(s, 7.2, 3.85, 5.5, 2.95, fill=RGBColor(0x0D, 0x11, 0x17), line=RGBColor(0x33, 0x41, 0x55), radius=0.03)
text(s, 7.4, 3.95, 5.2, 2.8, ["# cordapps/config/workflows-0.1.conf",
                              "# EnterpriseA:",
                              'trustedPeers = ["O=EnterpriseB,L=Mumbai,C=IN"]',
                              "",
                              "# responder on A when C calls:",
                              "FlowException: Untrusted peer:",
                              "  O=EnterpriseC, L=Delhi, C=IN"], size=12.5, color=GREEN, font="Consolas")

# 12 Tech stack
s = new_slide("Tech Stack", "This is the technology I used. The CorDapp is written in Java on Corda 4.12 Community "
    "Edition, running on JDK 17 and built with Gradle. For testing I used the MockServices ledger DSL and MockNetwork "
    "with JUnit. For the security evidence I used keytool and OpenSSL. I wrote the helper scripts in Python, with Pillow "
    "and matplotlib for the images, python-docx and python-pptx for the documents, and ffmpeg with edge-tts for the "
    "videos.", kicker="Tools")
grid8(s, [("Corda 4.12", "Community Edition, CorDapp template"), ("Java + JDK 17", "contracts, flows, RPC client"),
          ("Gradle 7.6", "build, deployNodes, cordformation"), ("JUnit", "MockServices ledger DSL, MockNetwork"),
          ("Java crypto (JCA)", "X25519, HKDF-SHA256, AES-GCM, SHA-256"), ("keytool + OpenSSL", "certificates, TLS handshake"),
          ("Python", "Pillow, matplotlib, python-docx / pptx"), ("ffmpeg + edge-tts", "videos and narration")])

# 13 Results - tests
s = new_slide("Results – Tests", "Now the results. I wrote fifteen contract tests and seven flow tests, and all "
    "twenty-two pass. The contract tests check cases like a missing signature, three participants, a bad hash and "
    "changed content on acknowledge. The flow tests prove the five key properties: a send and acknowledge works, "
    "EnterpriseC's vault stays empty, a tampered payload fails the integrity check, an untrusted peer is rejected, and "
    "the stored payload really is ciphertext.", kicker="gradlew test")
text(s, 0.6, 1.75, 5.5, 1.0, "22 / 22 passed", size=40, color=GREEN, bold=True)
bullets(s, ["**15 contract tests**: signatures, participants, hash, content",
            "**Privacy**: EnterpriseC vault = 0",
            "**Integrity**: tampered payload rejected",
            f"**Trust**: C {ARROW} A fails with \"Untrusted peer\"",
            "**Ciphertext** stored, never plaintext"], y=2.75, w=5.7, h=4.1, size=17)
image_fit(s, "images/ev_tests.png", 6.6, 1.6, 6.2, 5.3)

# 14 Results - TLS & certs
s = new_slide("Results – TLS & Certificate Evidence", "Here is the real transport evidence from my running nodes. "
    "The server certificate subject was EnterpriseA in Bengaluru, and the full chain went up to the Corda root CA. The "
    "negotiated protocol was TLS 1.2 with the cipher ECDHE ECDSA AES128 GCM SHA256. Without a client certificate, the "
    "node refused the handshake and logged an empty client certificate chain. TLS 1.3 was refused as well. The node "
    "logs also show the AMQP bridges between A, B and the notary.", kicker="openssl s_client + keytool")
image_fit(s, "images/ev_tls_handshake.png", 0.6, 1.6, 7.9, 5.3)
facts = [("Server cert", "O=EnterpriseA, L=Bengaluru"), ("Protocol", "TLSv1.2"),
         ("Cipher", "ECDHE-ECDSA-AES128-GCM-SHA256"), ("No client cert", "REJECTED (alert 40)"),
         ("Valid peer cert", "Handshake completed")]
for i, (k, v) in enumerate(facts):
    y = 1.65 + i * 1.04
    rect(s, 8.8, y, 3.95, 0.9, fill=CARD)
    text(s, 8.95, y + 0.07, 3.7, 0.3, k, size=12, color=MUTED)
    text(s, 8.95, y + 0.36, 3.7, 0.45, v, size=13.5 if len(v) > 24 else 15,
         color=RED if "REJECTED" in v else WHITE, bold=True)

# 15 Results - demo, privacy, latency
s = new_slide("Results – Live Demo, Privacy & Latency", "In the live run, EnterpriseA sent three encrypted messages "
    "to EnterpriseB, and B sent one invoice back. All four were acknowledged, and B decrypted the purchase order with a "
    "matching hash. The vault counts show the privacy result: A and B have eight states each, and EnterpriseC has zero. "
    f"EnterpriseC's attempt to message A was rejected as an untrusted peer. Twenty pings averaged about "
    f"{round(float(STATS[0]))} milliseconds, and the key exchange and encryption added only about one millisecond per message.",
    kicker="DemoClient over RPC")
stats = [("Vault C", "0 states", GREEN), (f"C {ARROW} A", "Untrusted peer", RED),
         ("Avg ping (20 runs)", f"{float(STATS[0]):.1f} ms", WHITE), ("Crypto cost", f"≈{KEX_MS:.1f} ms / msg", WHITE)]
for i, (k, v, c) in enumerate(stats):
    x = 0.6 + i * 3.07
    rect(s, x, 1.7, 2.85, 1.15, fill=CARD)
    text(s, x + 0.15, 1.77, 2.6, 0.3, k, size=12.5, color=MUTED)
    text(s, x + 0.15, 2.1, 2.6, 0.6, v, size=21, color=c, bold=True)
image_fit(s, "images/ev_demo_privacy.png", 0.6, 3.1, 5.9, 3.75)
image_fit(s, latency_chart(), 6.75, 3.1, 6.0, 3.75)

# 16 Advantages & limitations
s = new_slide("Advantages & Limitations", "To sum up the advantages: the content stays protected even if the database "
    "or a backup leaks, uninvolved nodes store nothing, both parties sign so nobody can deny a message, tampering is "
    "detected, and the cost is very low. There are also limitations. I used development certificates and a single "
    "notary, the keys are in keystore files and not in a hardware security module, there is no key rotation yet, and "
    "the subject line is not encrypted.", kicker="Evaluation")
rect(s, 0.6, 1.75, 5.95, 5.05, fill=CARD)
text(s, 0.85, 1.9, 5.5, 0.5, "Advantages", size=21, color=GREEN, bold=True)
bullets(s, ["Content safe even if DB / backup leaks", "Uninvolved nodes store **nothing**",
            "Both parties sign: **non-repudiation**", "Tampering detected (GCM + SHA-256)",
            "Low cost: ~1 ms crypto per message"], x=0.85, y=2.55, w=5.5, h=4.2, size=18, gap=16)
rect(s, 6.75, 1.75, 5.95, 5.05, fill=CARD)
text(s, 7.0, 1.9, 5.5, 0.5, "Limitations", size=21, color=RED, bold=True)
bullets(s, ["Dev-mode certificates, **single notary**", "Keys in JKS files, **no HSM** yet",
            "**No key rotation** / re-keying", "Subject + parties are not encrypted",
            "Static trust list (restart to change)"], x=7.0, y=2.55, w=5.5, h=4.2, size=18, gap=16)

# 17 Conclusion & future scope
s = new_slide("Conclusion & Future Scope", "In conclusion, I built a working CorDapp in which confidential messages "
    "travel over mutual TLS, are encrypted end-to-end, are signed by both parties and notarised, and are readable only "
    "by the sender and the receiver. All tests pass, and the live network confirmed privacy, integrity and the trust "
    "policy. In future I would like to move the keys into an HSM, add key rotation, and port the design to Corda 5, "
    "where the MGM manages group membership.", kicker="Wrap-up")
bullets(s, ["Working CorDapp: **mutual TLS + E2E AES-GCM + 2 signatures + notary**",
            "Only sender and receiver can read; **C vault = 0**",
            "**22/22 tests** pass; live evidence confirms every claim",
            "Encryption overhead is **negligible** next to signing/notarisation"], w=6.3, size=18, gap=14)
text(s, 7.3, 1.75, 5.4, 0.45, "FUTURE SCOPE", size=13, color=TEAL, bold=True)
for i, (h, b) in enumerate([("HSM-backed keys", "identity + KEK in a hardware security module"),
                            ("Key rotation", "periodic re-keying and re-encryption of stored messages"),
                            ("Corda 5 MGM", "membership groups instead of a static trustedPeers list")]):
    tile(s, 7.3, 2.25 + i * 1.5, 5.4, 1.32, h, b, size_h=17, size_b=14)

# 18 Thank you / references
s = new_slide("Thank You", "Thank you for listening to my presentation. The main references I used were the Corda 4.12 "
    "documentation, the Corda technical white paper, and the standards for X25519, HKDF, AES-GCM, SHA-256 and TLS 1.2. "
    "The full code, the test results and all the evidence files are in my project folder. I am happy to take any "
    "questions about the design or the implementation.", kicker="Questions welcome")
text(s, 0.6, 1.75, 5.6, 0.8, "Gagan N – 24BTRBT013", size=26, color=WHITE, bold=True)
text(s, 0.6, 2.5, 5.6, 1.2, ["CSE (Blockchain Technology), Semester V", "Corda Development – Topic 12 (M2)"],
     size=16, color=INK)
text(s, 0.6, 3.9, 5.6, 0.8, "Thank you!", size=40, color=TEAL, bold=True)
text(s, 6.8, 1.75, 5.9, 0.45, "REFERENCES", size=13, color=TEAL, bold=True)
text(s, 6.8, 2.25, 5.9, 4.5, ["R3, Corda 4.12 Documentation, docs.r3.com",
                              "Hearn & Brown, Corda: A Distributed Ledger (white paper), 2019",
                              "RFC 7748 X25519  |  RFC 5869 HKDF  |  RFC 8032 EdDSA",
                              "NIST SP 800-38D (AES-GCM)  |  FIPS 180-4 (SHA-256)",
                              "RFC 5246 TLS 1.2  |  OASIS AMQP 1.0",
                              "Apache ActiveMQ Artemis docs; R3 cordapp-template-java"], size=14.5, color=INK, gap=8)

prs.save(OUT)
for i, sl in enumerate(prs.slides, 1):
    n = len(sl.notes_slide.notes_text_frame.text.split())
    print(f"slide {i:2d}: notes {n} words")
print("saved", OUT)
