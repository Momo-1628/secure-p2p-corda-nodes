"""Generates report/Project_Report_24BTRBT013.docx from the real code, evidence files and images.
Gagan N (24BTRBT013).     python scripts/make_report.py
"""
import os
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor, Inches

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence")
OUT = os.path.join(ROOT, "report", "Project_Report_24BTRBT013.docx")
NAVY = RGBColor(0x0B, 0x1F, 0x3A)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
GREY = RGBColor(0x47, 0x55, 0x69)

TITLE = "Implementation of Secure Peer-to-Peer Communication between Enterprise Corda Nodes"


# ------------------------------------------------------------------ evidence parsing

def ev(name):
    with open(os.path.join(EV, name), encoding="utf-8") as f:
        return f.read()


def table_rows(text, header_start):
    """Parse the first ASCII table whose header line starts with `| header_start`."""
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("| " + header_start):
            rows = [[c.strip() for c in l.strip("|").split("|")]]
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip("|").split("|")])
                j += 1
            return rows
    return []


DEMO = ev("demo_run.txt")
TESTS = ev("test_results.txt")
TLS = ev("tls_handshake.txt")
PING_SAMPLES = [float(x) for x in re.findall(r"#\d\d +([\d.]+) ms", DEMO)]
PING = table_rows(DEMO, "Samples")[1]          # samples, avg, min, max, median, sd
SEND = table_rows(DEMO, "#")[1:]
BENCH = table_rows(DEMO, "Body size")
PRIV = table_rows(DEMO, "Node        | SecureMessageStates")
if not PRIV:
    PRIV = table_rows(DEMO, "Node")
NETMAP = table_rows(DEMO, "Node")
KEX = re.search(r"X25519 keygen x2 \+ ECDH \+ HKDF : ([\d.]+) us", DEMO).group(1)
DECRYPT_US = re.search(r"Decrypt time\s+: (\d+) us", DEMO).group(1)
UNTRUSTED_MSG = re.search(r"Message\s+: (Untrusted peer[^\n]+)", DEMO).group(1)
TOTAL_TESTS = re.search(r"TOTAL: (\d+) tests\s+PASSED: (\d+)\s+FAILED: (\d+)", TESTS).groups()
BUILD_TIME = re.search(r"BUILD SUCCESSFUL in ([^\n]+)", TESTS).group(1)
TLS_CIPHER = re.search(r"Negotiated cipher\s+\(with cert\): (\S+)", TLS).group(1)
TLS_PROTO = re.search(r"Negotiated protocol \(with cert\): (\S+)", TLS).group(1)
TLS_SUBJ = re.search(r"Server certificate subject\s+: ([^\n]+)", TLS).group(1).strip()
DIGEST = re.search(r"contentHash \(ledger\)\s+: (\w+)", DEMO).group(1)


# ------------------------------------------------------------------ code excerpts

def excerpt(rel, start, end, include_end=True, drop=()):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        lines = f.read().splitlines()
    s = next(i for i, l in enumerate(lines) if re.search(start, l))
    e = next(i for i, l in enumerate(lines[s + 1:], s + 1) if re.search(end, l))
    chunk = lines[s:e + (1 if include_end else 0)]
    chunk = [l for l in chunk if not any(re.search(d, l) for d in drop)]
    # de-indent
    ind = min(len(l) - len(l.lstrip()) for l in chunk if l.strip())
    return "\n".join(l[ind:] for l in chunk)


# ------------------------------------------------------------------ docx helpers

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.3)
sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.0)

st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for lvl, size, col in ((1, 16, NAVY), (2, 13, TEAL), (3, 11.5, NAVY)):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Calibri"
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = col
    h.element.rPr.rFonts.set(qn("w:asciiTheme"), "")
    h.element.rPr.rFonts.set(qn("w:hAnsiTheme"), "")
    h.element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    h.element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True


def shade(el, hex_fill):
    pPr = el.get_or_add_pPr() if hasattr(el, "get_or_add_pPr") else el
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    pPr.append(shd)


def cell_shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def P(text="", bold_lead=None, size=None, align=None, italic=False, after=None, color=None):
    p = doc.add_paragraph()
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
    # simple **bold** markup
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        r = p.add_run(part)
        r.bold = i % 2 == 1
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    if align:
        p.alignment = align
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", it)):
            r = p.add_run(part)
            r.bold = i % 2 == 1
        p.paragraph_format.space_after = Pt(3)


def numbered(items):
    for n, it in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.add_run(f"{n}.  ")
        for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", it)):
            r = p.add_run(part)
            r.bold = i % 2 == 1
        p.paragraph_format.space_after = Pt(3)


def H(text, lvl=1):
    return doc.add_heading(text, level=lvl)


def code(text, caption=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    lines = text.split("\n")
    for i, l in enumerate(lines):
        r = p.add_run(l)
        r.font.name = "Consolas"
        r.font.size = Pt(8)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        if i < len(lines) - 1:
            r.add_break()
    shade(p._p, "F1F5F9")
    pBdr = OxmlElement("w:pBdr")
    for side in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:space"), "4")
        b.set(qn("w:color"), "CBD5E1")
        pBdr.append(b)
    p._p.get_or_add_pPr().append(pBdr)
    if caption:
        cap(caption)


FIG = [0]
TAB = [0]


def cap(text, kind="Listing"):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = GREY
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)


def figure(path, caption, width=16.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(os.path.join(ROOT, path), width=Cm(width))
    FIG[0] += 1
    cap(f"Figure {FIG[0]}: {caption}")


def figure_pair(p1, c1, p2, c2, width=7.9):
    t = doc.add_table(rows=2, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trPr.append(cs)
    for j, (pth, c) in enumerate(((p1, c1), (p2, c2))):
        cell = t.cell(0, j)
        par = cell.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.add_run().add_picture(os.path.join(ROOT, pth), width=Cm(width))
        FIG[0] += 1
        cp = t.cell(1, j).paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(f"Figure {FIG[0]}: {c}")
        r.italic = True
        r.font.size = Pt(9)
        r.font.color.rgb = GREY
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def table(rows, widths=None, header=True, size=9.5, caption=None):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            par = c.paragraphs[0]
            par.paragraph_format.space_after = Pt(1)
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = par.add_run(str(val))
            r.font.size = Pt(size)
            if header and i == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                cell_shade(c, "0B1F3A")
            elif i % 2 == 0:
                cell_shade(c, "F1F5F9")
            if widths:
                c.width = Cm(widths[j])
    if caption:
        TAB[0] += 1
        cap(f"Table {TAB[0]}: {caption}")
    else:
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def field(paragraph, instr):
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = instr
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    r._r.append(b); r._r.append(i); r._r.append(s); r._r.append(t); r._r.append(e)
    return r


# ================================================================== COVER

sec.different_first_page_header_footer = True
for _ in range(2):
    doc.add_paragraph()
P("JAIN (DEEMED-TO-BE UNIVERSITY)", size=16, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY).runs[0].bold = True
P("Faculty of Engineering and Technology", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
P("Department of Computer Science and Engineering", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
doc.add_paragraph()
P("Corda Development", size=15, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL).runs[0].bold = True
P("Mini Project Report", size=13, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
t = P(TITLE, size=22, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY)
t.runs[0].bold = True
P("Topic No. 12  |  Module M2  |  Focus: Secure communication", size=11.5, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
for _ in range(3):
    doc.add_paragraph()
P("Submitted by:", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
P("Gagan N (24BTRBT013)", size=17, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY).runs[0].bold = True
P("B.Tech - Computer Science and Engineering (Blockchain Technology)", size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
P("Semester V", size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(4):
    doc.add_paragraph()
P("Jain (Deemed-to-be University), Bengaluru  |  November 2026", size=11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
page_break()

# footer with page numbers (not on cover)
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
rr = fp.add_run("Gagan N (24BTRBT013)  |  Secure P2P Communication between Enterprise Corda Nodes  |  Page ")
rr.font.size = Pt(8.5); rr.font.color.rgb = GREY
field(fp, "PAGE").font.size = Pt(8.5)

# ================================================================== TOC
P("Contents", size=16, align=WD_ALIGN_PARAGRAPH.LEFT, color=NAVY).runs[0].bold = True
tocp = doc.add_paragraph()
field(tocp, 'TOC \\o "1-1" \\h \\z \\u')
page_break()

# ================================================================== 1 TITLE
H("1. Title")
P(f"**{TITLE}**", align=WD_ALIGN_PARAGRAPH.LEFT)
table([
    ["Item", "Details"],
    ["Course", "Corda Development - B.Tech CSE (Blockchain Technology), Semester V"],
    ["Topic", "No. 12, Module M2 - Secure communication"],
    ["Student", "Gagan N, USN 24BTRBT013 (individual project)"],
    ["Platform", "Corda 4.12 (Community Edition), JDK 17, Gradle 7.6, Java CorDapp from the R3 cordapp-template-java"],
    ["Network", "4 nodes: Notary, EnterpriseA (Bengaluru), EnterpriseB (Mumbai), EnterpriseC (Delhi)"],
    ["Security", "TLS 1.2 mutual authentication, Ed25519 signatures, X25519 ECDH + AES-256-GCM, SHA-256, trusted-peer policy"],
    ["Package", "com.securep2p  (contracts, workflows, clients)"],
], widths=[3.2, 13.0])
P("In this project I built a CorDapp that lets enterprises exchange confidential business messages, such as purchase "
  "orders and contract terms, directly from one Corda node to another. I designed it so that only the sender and the "
  "receiver can ever read a message, that the link between the nodes is encrypted and mutually authenticated, and that "
  "every message is signed, acknowledged and tamper-evident. I verified all of this with automated tests and with a "
  "live four-node network running on my laptop.")

# ================================================================== 2 PROBLEM
H("2. Problem Statement")
P("Companies that trade with each other constantly exchange sensitive information: purchase orders with prices and "
  "volumes, draft contract terms, invoices and bank details. Today this mostly travels by e-mail or through shared "
  "portals. E-mail is often stored in plaintext on several servers, attachments can be forwarded to anyone, there is "
  "no reliable proof that a message was received unchanged, and the sender cannot prove later what exactly was agreed.")
P("Public blockchains do not solve this problem, because they broadcast every transaction to every node. A purchase "
  "price that a supplier offers to one buyer must not be visible to competing buyers or to the supplier's other "
  "partners. The problem I address is therefore:")
P("**How can two enterprise nodes exchange confidential messages so that (a) only the two parties ever see the content, "
  "(b) the communication channel is encrypted and both ends are authenticated, (c) every message is signed, "
  "acknowledged and tamper-evident, and (d) a node only talks to counterparties it explicitly trusts?**", italic=False)
P("The solution also has to survive realistic threats: a curious notary or node operator, a stolen vault backup, an "
  "attacker on the network, a member of the same network who is not part of the conversation, and a modified "
  "ciphertext.")

# ================================================================== 3 OBJECTIVES
H("3. Objectives")
numbered([
    "Set up a Corda 4.12 network with a notary and three enterprise nodes (EnterpriseA, EnterpriseB, EnterpriseC), each with its own P2P/RPC ports and RPC users.",
    "Design a **SecureMessageState** (LinearState) whose participants are only the sender and the receiver, and a **SecureMessageContract** with Send and Acknowledge commands and strict validation rules.",
    "Implement **application-layer encryption**: an in-flow X25519 ECDH key exchange over the flow session, HKDF-SHA256 key derivation and AES-256-GCM with a fresh random key per message, so that the notary and vault backups only see ciphertext.",
    "Implement the flows **SendSecureMessageFlow**, **AcknowledgeMessageFlow**, **ReadMessageFlow** (local decrypt + SHA-256 integrity check) and **PingPeerFlow** (P2P latency).",
    "Enforce a **trusted-peer policy** from the CorDapp configuration, with EnterpriseC configured as not trusted by EnterpriseA.",
    "Prove the properties with **contract tests** (ledger DSL) and **flow tests** (MockNetwork) for correctness, privacy, integrity, trust and ciphertext storage.",
    "Collect **real transport-security evidence** from the running nodes: certificate chains (keytool), the TLS handshake (openssl s_client) and the AMQP bridge logs.",
    "Measure and analyse **P2P latency** and the **overhead of encryption**.",
])

# ================================================================== 4 INTRO
H("4. Introduction")
P("Corda is an open-source distributed ledger platform from R3 that was designed specifically for regulated businesses. "
  "Unlike Bitcoin or Ethereum, Corda has no global broadcast of transactions. Each transaction is shared only with the "
  "parties that need to see it, and nodes talk to each other directly over an authenticated, encrypted messaging "
  "layer. Every node has a well-known legal identity (an X.500 name such as O=EnterpriseA, L=Bengaluru, C=IN) that is "
  "certified by the network operator, so a node always knows exactly who it is talking to.")
P("These properties make Corda a natural fit for confidential business-to-business messaging, but they are not "
  "enough on their own. Transport encryption (TLS) protects data only while it travels between nodes. Once a message "
  "arrives it is stored in the node's vault database, it is visible to database administrators, it ends up in backups, "
  "and with a validating notary it would also be visible to the notary. For truly confidential content I wanted the "
  "message to stay encrypted end-to-end, so that only the sender's and receiver's CorDapp code can ever turn it back "
  "into plaintext.")
P("In this project I combined the security that the Corda platform already provides (mutual TLS, certified identities, "
  "digital signatures, notarisation, need-to-know distribution) with two layers that I implemented myself in the "
  "CorDapp: end-to-end message encryption with a key agreed inside the flow, and an explicit trusted-peer allow-list. "
  "I then tested each security claim and collected evidence from a real running network instead of relying on "
  "assumptions.")
P("The rest of this report explains the Corda concepts I used (Section 5), the architecture (Section 6), my method "
  "(Section 7), the implementation with key code (Section 8), the results, screenshots and analysis (Sections 9-11), "
  "and finally the advantages, limitations and conclusions.")

# ================================================================== 5 CONCEPTS
H("5. Corda / Blockchain Concepts Used")
table([
    ["Concept", "How I used it in this project"],
    ["Nodes & legal identities", "Four JVM processes, each with an X.500 name and an Ed25519 identity key certified by the network's Doorman CA."],
    ["Network map", "Lets every node discover the others' addresses and identities; printed by the DemoClient."],
    ["Flows & sessions", "Point-to-point conversations. SendSecureMessageFlow uses its FlowSession for the X25519 key exchange, signature collection and finality."],
    ["Artemis / AMQP 1.0", "Corda's P2P messaging: each node runs an embedded ActiveMQ Artemis broker; outbound AMQP bridges connect to peers over mutual TLS 1.2."],
    ["States (LinearState)", "SecureMessageState keeps the same linearId while it evolves from SENT to ACKNOWLEDGED."],
    ["Contracts & commands", "SecureMessageContract validates Send and Acknowledge, including required signers and a time window."],
    ["Notary (non-validating)", "Prevents a SENT state from being acknowledged twice and time-stamps the Send. It only sees a filtered transaction."],
    ["Vault", "Each node stores only the states it participates in; EnterpriseC's vault stays empty."],
    ["Need-to-know privacy", "participants = sender + receiver; FinalityFlow distributes to the receiver only."],
    ["CorDapp configuration", "Per-node config file (cordapps/config/workflows-0.1.conf) that holds the trustedPeers list."],
    ["RPC", "The DemoClient uses CordaRPCClient to start flows and query vaults on A, B and C."],
], widths=[4.2, 12.0])
P("**Cryptographic building blocks.** TLS 1.2 with ECDHE-ECDSA (transport), Ed25519 (transaction signatures and key "
  "derivation), X25519 (ephemeral Diffie-Hellman key agreement, RFC 7748), HKDF-SHA256 (key derivation, RFC 5869), "
  "AES-256-GCM (authenticated encryption, NIST SP 800-38D) and SHA-256 (content hash, FIPS 180-4).")

# ================================================================== 6 ARCHITECTURE
H("6. System Architecture")
P("The network consists of a non-validating notary and three enterprise nodes. EnterpriseA and EnterpriseB exchange "
  "messages; EnterpriseC is a legitimate member of the same network (it holds a valid certificate) but is not part of "
  "their conversation and is deliberately not trusted by EnterpriseA.")
figure("diagrams/d1_topology.png", "Network topology - four nodes, point-to-point AMQP over mutual TLS")
table([
    ["Node", "X.500 name", "P2P", "RPC", "Admin", "RPC user", "trustedPeers"],
    ["Notary", "O=Notary,L=Bengaluru,C=IN", "10002", "10003", "10043", "none", "none"],
    ["EnterpriseA", "O=EnterpriseA,L=Bengaluru,C=IN", "10005", "10006", "10046", "userA", "B"],
    ["EnterpriseB", "O=EnterpriseB,L=Mumbai,C=IN", "10008", "10009", "10049", "userB", "A, C"],
    ["EnterpriseC", "O=EnterpriseC,L=Delhi,C=IN", "10011", "10012", "10052", "userC", "A, B"],
], widths=[2.4, 5.2, 1.3, 1.3, 1.3, 1.8, 2.4], size=9, caption="Node configuration generated by deployNodes")
P("**Security layers.** I designed the system as defence in depth. Each message is protected by four independent "
  "layers; breaking one layer does not expose the content (Figure 2).")
figure("diagrams/d2_security_layers.png", "Four security layers applied to every message")
P("**Certificate hierarchy.** Corda's PKI gives every node a certificate chain rooted at the network's root CA. The "
  "TLS certificate used on the P2P port and the legal-identity certificate used for signing are both issued by the "
  "node's own CA, which in turn is issued by the Doorman CA (Figure 3). A peer is accepted at the TLS layer only if "
  "its chain validates to the root CA in truststore.jks.")
figure("diagrams/d3_certificate_hierarchy.png", "Certificate hierarchy of EnterpriseA (from keytool output)", width=15)

# ================================================================== 7 METHODOLOGY
H("7. Methodology")
P("I followed an incremental, test-driven approach:")
numbered([
    "**Environment.** I verified JDK 17 (java -version), cloned the official cordapp-template-java (release/4.12) into a new folder, removed its git history and sample code, re-initialised git and renamed the package to com.securep2p.",
    "**Threat model.** I listed what I wanted to defend against: network eavesdroppers and outsiders (TLS), impersonation and repudiation (signatures), curious operators, notaries and stolen backups (end-to-end encryption), other network members (need-to-know + allow-list) and tampering (GCM tag + SHA-256).",
    "**Data model and contract first.** I designed SecureMessageState and the contract rules and wrote 15 ledger-DSL contract tests covering valid and invalid cases.",
    "**Crypto helper.** I wrote SecureCrypto (X25519, HKDF, AES-GCM, SHA-256) as plain static methods so that no Cipher or PrivateKey object is ever held on a flow's stack across a checkpoint.",
    "**Flows and policy.** I implemented the four flows and the TrustedPeerPolicy, then wrote 7 MockNetwork flow tests (send/ack, privacy, integrity, trust, ciphertext, ping, double acknowledgement).",
    "**Deployment.** I configured deployNodes with four nodes and per-node CorDapp config, started each node headless (java -jar corda.jar) and waited for the \"started up\" log line.",
    "**Evidence.** I collected keytool listings, openssl s_client handshakes, AMQP bridge log lines and the DemoClient output into the evidence folder, and rendered screenshots from those files.",
    "**Measurement.** I ran PingPeerFlow 20 times and a local cryptographic micro-benchmark to quantify latency and encryption overhead.",
])
P("**Message protocol.** Figure 4 shows the complete message sequence that I implemented, from the key exchange to the "
  "acknowledgement.")
figure("diagrams/d4_sequence.png", "Sequence: key exchange - encrypt - sign - notarise - finality - acknowledge", width=14.5)

# ================================================================== 8 IMPLEMENTATION
H("8. Implementation")
H("8.1 SecureMessageState", 2)
P("The state stores only ciphertext and metadata. The two key envelopes contain the per-message AES key wrapped "
  "separately for the sender and for the receiver. The participants list is exactly the sender and the receiver.")
code(excerpt("contracts/src/main/java/com/securep2p/states/SecureMessageState.java",
             r"^@BelongsToContract", r"Status\.SENT\)|receiverKeyEnvelope, sentAt, status, Arrays.asList",
             drop=(r"^\s*$", r"@ConstructorForDeserialization", r"this\.\w+ = ")),
     "Listing 1: SecureMessageState - fields and the participants rule (excerpt)")
H("8.2 SecureMessageContract", 2)
P("The contract enforces the business and security rules of the Send command. The Acknowledge command similarly "
  "checks SENT to ACKNOWLEDGED, unchanged content and parties, and the receiver's signature.")
code(excerpt("contracts/src/main/java/com/securep2p/contracts/SecureMessageContract.java",
             r"private void verifySend", r"^    }$"),
     "Listing 2: Send command verification")
H("8.3 SendSecureMessageFlow", 2)
P("The initiating flow checks the trust policy, performs the X25519 exchange over the session, encrypts the body, "
  "builds and signs the transaction, collects the receiver's signature and finalises it with the notary. The "
  "responder refuses untrusted peers before any key material is exchanged and, before signing, decrypts the "
  "ciphertext itself and checks that the SHA-256 matches the contentHash, so a dishonest sender cannot make the "
  "receiver sign a hash that does not belong to the content.")
code(excerpt("workflows/src/main/java/com/securep2p/flows/SendSecureMessageFlow.java",
             r"progressTracker.setCurrentStep\(TRUST\)", r"return subFlow\(new FinalityFlow",
             drop=(r"^\s*$", r"progressTracker\.setCurrentStep\((KEX|ENCRYPT|SIGN|COLLECT|FINALISE)\)")),
     "Listing 3: SendSecureMessageFlow.call() - key exchange, encryption, signing and finality")
H("8.4 Encryption helper", 2)
P("SecureCrypto implements the key agreement and authenticated encryption with the standard Java Cryptography "
  "Architecture. Every message gets a fresh 256-bit key (from fresh ephemeral X25519 keys) and a random 96-bit IV. "
  "The message metadata (id, subject, sender, receiver) is bound to the ciphertext as additional authenticated data, "
  "so moving a ciphertext into another message is also detected.")
code(excerpt("workflows/src/main/java/com/securep2p/crypto/SecureCrypto.java",
             r"public static byte\[\] deriveMessageKey", r"^    }$") + "\n\n" +
     excerpt("workflows/src/main/java/com/securep2p/crypto/SecureCrypto.java",
             r"public static String encrypt\(", r"^    }$"),
     "Listing 4: X25519 + HKDF key derivation and AES-256-GCM encryption")
P("**Key envelopes.** To allow ReadMessageFlow to decrypt later without ever storing a plaintext key, each node wraps "
  "the message key with a key-encryption key that it re-derives on demand from a deterministic Ed25519 signature of "
  "its own identity key: KEK = HKDF(sign(identityKey, \"securep2p-kek|\" + linearId)). Only the holder of the private "
  "identity key can produce that signature, so a stolen database or backup contains nothing that can be decrypted.")
H("8.5 Trust policy", 2)
P("Each node's allow-list is read from its CorDapp configuration. Both the initiator and every responder call "
  "requireTrusted, and the default is to deny when the key is missing.")
code(excerpt("workflows/src/main/java/com/securep2p/policy/TrustedPeerPolicy.java",
             r"public static Set<CordaX500Name> trustedPeers", r"^    }$") + "\n\n" +
     excerpt("workflows/src/main/java/com/securep2p/policy/TrustedPeerPolicy.java",
             r"public static void requireTrusted", r"^    }$") + "\n\n" +
     "// build.gradle (deployNodes) - EnterpriseA trusts only EnterpriseB\n" +
     "cordapp(project(':workflows')) {\n    config \"trustedPeers = [\\\"${B_NAME}\\\"]\"\n}",
     "Listing 5: TrustedPeerPolicy and the per-node configuration")
P("**Other flows.** AcknowledgeMessageFlow runs ReadMessageFlow first (so an acknowledgement means \"received intact\"), "
  "then consumes the SENT state and produces the ACKNOWLEDGED state, signed by the receiver and notarised. "
  "PingPeerFlow sends a nonce with session.sendAndReceive and measures the round trip with System.nanoTime().")
figure("diagrams/d5_lifecycle.png", "SecureMessageState lifecycle and rejected paths")

# ================================================================== 9 RESULTS
H("9. Results")
H("9.1 Automated tests", 2)
P(f"All **{TOTAL_TESTS[0]} tests passed** ({TOTAL_TESTS[1]} passed, {TOTAL_TESTS[2]} failed; Gradle: BUILD SUCCESSFUL "
  f"in {BUILD_TIME}). The table maps the required test cases to my implementation.")
table([
    ["Requirement", "Test", "Result"],
    ["Contract: valid / invalid cases (15)", "SecureMessageContractTests: missing sender/receiver signature, 3 participants, bad hash, send to self, empty subject, inputs on Send, wrong status, no time window, changed content/hash on Acknowledge, sender-only ack, re-ack", "PASS"],
    ["(1) A to B send + acknowledge", "sendAndAcknowledgeWorks", "PASS"],
    ["(2) Privacy: C vault = 0", "thirdPartyVaultIsEmpty", "PASS"],
    ["(3) Integrity: tampered payload", "tamperedPayloadFailsIntegrityCheck", "PASS"],
    ["(4) Trust policy: C to A rejected", "untrustedPeerIsRejected", "PASS"],
    ["(5) Payload is not plaintext", "storedPayloadIsCiphertext", "PASS"],
    ["Extra", "pingReturnsLatency, cannotAcknowledgeTwice", "PASS"],
], widths=[4.6, 10.0, 1.6], size=9, caption="Test coverage of the project requirements")
H("9.2 Transport security", 2)
P(f"With the nodes running I connected to EnterpriseA's P2P port with openssl s_client. The server presented the "
  f"certificate **{TLS_SUBJ}** with its full chain (node CA, Corda Doorman CA, Corda Node Root CA), negotiated "
  f"**{TLS_PROTO}** with the cipher suite **{TLS_CIPHER}** (ECDHE key exchange on X25519, so forward secrecy) and sent "
  "a CertificateRequest naming the Corda root CA. Without a client certificate the handshake was **rejected with "
  "alert 40 (handshake_failure)** and the node logged \"Empty client certificate chain\". When I presented "
  "EnterpriseB's Doorman-issued TLS certificate and chain, the handshake **completed**. A TLS 1.3 attempt was refused "
  "with a protocol_version alert, because Corda 4.12 pins TLS 1.2. The node logs show AMQP bridges A-B, A-Notary, "
  "B-Notary and C-A, each with \"Handshake completed with subject: ...\".")
H("9.3 Live demonstration", 2)
P("The DemoClient connected over RPC to all three enterprise nodes and performed the complete scenario. The four "
  "messages were sent, encrypted and finalised:")
rows = [["#", "From", "To", "Subject", "Ciphertext (stored)", "Flow time"]]
for r in SEND:
    rows.append([r[0], r[1], r[2], r[3], r[5][:26] + "...", r[6] + " ms"])
table(rows, widths=[0.7, 2.4, 2.4, 4.6, 4.4, 1.8], size=9, caption="Messages sent in the live run (evidence/demo_run.txt)")
P(f"All four messages were then acknowledged by their receivers. On EnterpriseB, ReadMessageFlow decrypted the purchase "
  f"order, recomputed the SHA-256 (**{DIGEST[:16]}...**) and found it identical to the contentHash on the ledger "
  f"(integrity check PASSED, {DECRYPT_US} us for envelope unwrap and decryption). When EnterpriseC tried to send a "
  f"message to EnterpriseA, the flow failed with: **\"{UNTRUSTED_MSG}\"**.")

# ================================================================== 10 SCREENSHOTS
H("10. Screenshots")
P("All screenshots below were rendered from the real output files in the evidence folder of the project.")
figure_pair("images/ev_tests.png", "gradlew test - 22 tests passed",
            "images/ev_certificates.png", "keytool summary of EnterpriseA's keystores")
figure("images/ev_node_startup.png", "Four nodes started headless; EnterpriseA console", width=12)
figure("images/ev_tls_handshake.png", "openssl s_client -tls1_2 without a client certificate - rejected (mutual TLS)", width=14.5)
figure("images/ev_p2p_links.png", "AMQP/TLS bridge events from the node logs", width=13.5)
figure("images/ev_demo_part1.png", "DemoClient: network map, encrypted sends, acknowledgements, decryption on B", width=14.5)
figure("images/ev_demo_part2.png", "DemoClient: privacy, trust policy rejection, latency and encryption overhead", width=12.5)

# ================================================================== 11 ANALYSIS
H("11. Analysis")
H("11.1 P2P latency", 2)
P("PingPeerFlow measures the time for one session.sendAndReceive round trip between EnterpriseA and EnterpriseB, "
  "inside the flow (so RPC time is excluded). Each sample opens a new flow session, so it includes session "
  "initiation, AMQP transfer over the TLS bridge, the Artemis queues on both nodes and the responder's checkpoint.")
table([["Samples", "Average (ms)", "Min (ms)", "Max (ms)", "Median (ms)", "Std dev (ms)"], PING],
      widths=[2.4, 2.8, 2.6, 2.6, 2.8, 2.8], caption="PingPeerFlow EnterpriseA to EnterpriseB, 20 round trips")
samples = [["Ping"] + [f"#{i+1}" for i in range(10)], ["ms"] + [f"{x:.1f}" for x in PING_SAMPLES[:10]],
           ["Ping"] + [f"#{i+11}" for i in range(10)], ["ms"] + [f"{x:.1f}" for x in PING_SAMPLES[10:20]]]
table(samples, widths=[1.3] + [1.49] * 10, size=8.5, header=False, caption="Individual latency samples (ms)")
P(f"The average of {PING[1]} ms is high compared to a raw TCP ping on localhost, but this is expected: all four Corda "
  "nodes, their embedded brokers and H2 databases ran on one laptop, and each round trip includes flow start, "
  "checkpointing of the responder and two hops through Artemis queues. The spread is small (standard deviation "
  f"{PING[5]} ms), which shows a stable link. A full SendSecureMessageFlow took about 1.0-1.7 s once warm "
  f"(the first message took {SEND[0][6]} ms because it included JIT compilation, first-time session and bridge "
  "set-up). Most of that time is spent in signature collection and notarisation, not in encryption.")
H("11.2 Overhead of encryption", 2)
rows = [BENCH[0]] + BENCH[1:]
table(rows, widths=[2.4, 3.6, 2.6, 2.4, 2.4, 2.6], size=9, caption="AES-256-GCM cost per message size (3000 iterations each)")
P(f"The X25519 key agreement (two key pairs, ECDH and HKDF) costs about **{float(KEX)/1000:.2f} ms per message**, and "
  "AES-GCM encryption or decryption of a typical 0.25-4 KB business message costs only **10-30 microseconds**. "
  "Compared with a send flow of about 1,000-1,700 ms, application-level encryption adds roughly **0.1 %** to the "
  "end-to-end time. The size overhead is fixed at 28 bytes (12-byte IV + 16-byte tag), and base64 encoding of the "
  "String field adds 33 %. For small messages this appears as +48 %; for 16 KB and above it approaches the "
  "base64 limit of +33 %. Storing the ciphertext as bytes instead of base64 would remove most of the size overhead.")
H("11.3 Privacy results", 2)
rows = [PRIV[0][:5]] + [r[:5] for r in PRIV[1:]]
table(rows, widths=[3.4, 4.6, 2.6, 2.2, 3.4], size=9.5, caption="SecureMessageStates per vault after the live run")
P("EnterpriseA and EnterpriseB each hold 8 states (4 consumed SENT states and 4 unconsumed ACKNOWLEDGED states). "
  "**EnterpriseC holds 0**, both in the MockNetwork test and on the real network, because it was never a participant "
  "and FinalityFlow never sent it a transaction. Even if a copy of a state reached C, ReadMessageFlow refuses it "
  "(\"Access denied\") and C cannot unwrap either key envelope. The vaults of A and B store only ciphertext, which I "
  "verified in test (5), and the non-validating notary only received filtered transactions (inputs, time window and "
  "notary), never the encrypted payload. The trust policy worked at the application layer even though C is a valid "
  "TLS peer: C's AMQP bridge to A was established, but A's responder rejected the flow before any key material was "
  "exchanged, and A's vault contains 0 messages from C.")
table([
    ["Threat", "Mitigation", "Evidence"],
    ["Network eavesdropping / MITM", "TLS 1.2 ECDHE-ECDSA-AES128-GCM, mutual auth", "tls_handshake.txt"],
    ["Outsider connecting to P2P port", "Client certificate required (alert 40)", "tls_handshake.txt, node log"],
    ["Other network member reading", "need-to-know participants, finality to receiver only", "Vault C = 0, test (2)"],
    ["Unsolicited / untrusted peer", "trustedPeers allow-list in both flow roles", "Untrusted peer, test (4)"],
    ["Stolen vault backup / curious DBA", "AES-256-GCM, keys wrapped with identity-derived KEK", "test (5)"],
    ["Modified ciphertext or hash", "GCM tag + SHA-256 contentHash", "test (3)"],
    ["Repudiation / double acknowledgement", "two signatures, notary uniqueness", "contract tests, cannotAcknowledgeTwice"],
], widths=[4.6, 6.6, 5.0], size=9, caption="Threat - mitigation - evidence summary")

# ================================================================== 12 ADV / LIM
H("12. Advantages and Limitations")
H("Advantages", 3)
bullets([
    "**Defence in depth:** content stays protected even if the TLS layer, the database or a backup is compromised.",
    "**True need-to-know privacy:** no broadcast; uninvolved members (EnterpriseC) store nothing.",
    "**Non-repudiation and proof of receipt:** both parties sign the message, and the receiver signs an acknowledgement only after verifying integrity.",
    "**Tamper evidence:** GCM authentication plus SHA-256 detects any change to payload, metadata or hash.",
    "**Forward secrecy per message:** fresh ephemeral X25519 keys for every message; no long-term encryption key to steal.",
    "**Configurable trust:** the allow-list is plain configuration and is checked by both the initiator and the responder.",
    "**Low overhead:** encryption costs about a millisecond per message, negligible next to signing and notarisation.",
])
H("Limitations", 3)
bullets([
    "The network uses Corda **dev-mode certificates** and a single notary; production needs a real Doorman/network map and a notary cluster.",
    "Identity keys live in **JKS files**, not an HSM; the KEK derivation would be stronger with HSM-backed keys.",
    "There is **no key rotation** or re-encryption of old messages, and no revocation of a trusted peer's past messages.",
    "Message metadata (subject, parties, time) is not encrypted, so the subject should not contain secrets.",
    "The trust list is static configuration and requires a node restart to change.",
    "Latency was measured on one laptop with all nodes co-located; real WAN latency will differ.",
])

# ================================================================== 13 CONCLUSION
H("13. Conclusion")
P("In this project I implemented and verified secure peer-to-peer communication between enterprise Corda nodes. I "
  "built a CorDapp in which confidential messages travel over Corda's mutually authenticated TLS 1.2 channel, are "
  "encrypted end-to-end with AES-256-GCM using a key that the two nodes agree inside the flow via X25519, are signed "
  "by both parties and notarised, and can only be decrypted and integrity-checked by the sender and the receiver.")
P(f"All {TOTAL_TESTS[0]} automated tests pass, and the live four-node network confirmed every claim: the TLS handshake "
  "is rejected without a valid client certificate, EnterpriseC's vault stayed empty, EnterpriseC was rejected as an "
  f"untrusted peer, tampering was detected, and the P2P round trip averaged {PING[1]} ms with encryption adding only "
  "about a millisecond per message. Through this work I learned how Corda's identity, messaging and privacy model "
  "differ from broadcast blockchains, and how application-level cryptography can be layered on top of a platform "
  "safely, for example by keeping only byte arrays across flow checkpoints.")
P("**Future scope.** I would move the identity and key-encryption keys into an HSM, add key rotation and re-keying of "
  "stored messages, make the trust list dynamic, encrypt attachments for large documents, and port the design to "
  "Corda 5, where the Membership Group Manager (MGM) can manage which members are allowed to communicate.")

# ================================================================== 14 REFERENCES
H("14. References")
refs = [
    "R3, \"Corda 4.12 Documentation - Key concepts, Flows, Vault, Notaries,\" docs.r3.com, 2024.",
    "R3, \"Corda Network: Certificate hierarchy and TLS / P2P messaging,\" Corda 4 documentation (Network and Messaging).",
    "M. Hearn and R. G. Brown, \"Corda: A Distributed Ledger,\" Corda Technical White Paper, version 1.0, R3, 2019.",
    "R3, \"cordapp-template-java,\" GitHub repository, branch release/4.12.",
    "A. Langley, M. Hamburg and S. Turner, \"Elliptic Curves for Security,\" RFC 7748 (X25519), IETF, 2016.",
    "H. Krawczyk and P. Eronen, \"HMAC-based Extract-and-Expand Key Derivation Function (HKDF),\" RFC 5869, IETF, 2010.",
    "M. Dworkin, \"Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC,\" NIST SP 800-38D, 2007.",
    "NIST, \"Secure Hash Standard (SHS),\" FIPS PUB 180-4, 2015.",
    "S. Josefsson and I. Liusvaara, \"Edwards-Curve Digital Signature Algorithm (EdDSA),\" RFC 8032, IETF, 2017.",
    "T. Dierks and E. Rescorla, \"The Transport Layer Security (TLS) Protocol Version 1.2,\" RFC 5246, IETF, 2008.",
    "OASIS, \"Advanced Message Queuing Protocol (AMQP) Version 1.0,\" OASIS Standard, 2012.",
    "Apache Software Foundation, \"ActiveMQ Artemis Documentation,\" activemq.apache.org.",
    "Oracle, \"Java Cryptography Architecture (JCA) Reference Guide,\" Java SE 17 documentation.",
    "OpenSSL Project, \"s_client - SSL/TLS client program,\" OpenSSL 3.2 manual.",
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    p.paragraph_format.space_after = Pt(3)
    p.add_run(f"[{i}]  " + r).font.size = Pt(10)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.core_properties.author = "Gagan N (24BTRBT013)"
doc.core_properties.title = TITLE
doc.save(OUT)
print("saved", OUT)
