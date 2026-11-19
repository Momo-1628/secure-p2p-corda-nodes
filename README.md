# Secure Peer-to-Peer Communication between Enterprise Corda Nodes

**Author:** Gagan N &nbsp;|&nbsp; **USN:** 24BTRBT013 &nbsp;|&nbsp; B.Tech CSE (Blockchain Technology), Semester V
**Course:** Corda Development, Jain (Deemed-to-be University) &nbsp;|&nbsp; Topic No. 12, Module M2, focus: secure communication

This is a CorDapp for **Corda 4.12 / JDK 17**. Enterprises use it to exchange confidential business messages (purchase details, contract terms) directly node-to-node:

* **Only the sender and the receiver ever see a message.** It is distributed point-to-point, never broadcast.
* **Transport:** TLS 1.2 with mutual authentication (AMQP 1.0 over Artemis bridges).
* **Application-layer end-to-end encryption:** an in-flow **X25519 ECDH** key exchange, then **HKDF-SHA256**, then **AES-256-GCM** with a fresh key for every message. The notary, the vault and any vault backup only ever see ciphertext.
* **Signed, acknowledged and tamper-evident:** the sender and the receiver both sign. A SHA-256 `contentHash` is checked on read. An `Acknowledge` transaction is notarised.
* **Trusted-peer policy:** a per-node allow-list (`trustedPeers` CorDapp config). An unlisted counterparty is rejected with `Untrusted peer`.

---

## 1. Architecture

```
                 EnterpriseC (Delhi)  P2P 10011 / RPC 10012     trustedPeers = [A, B]
                       |  C -> A  REJECTED "Untrusted peer"
                       v
 EnterpriseA (Bengaluru) <==== AMQP 1.0 / TLS 1.2 mutual auth ====> EnterpriseB (Mumbai)
 P2P 10005 / RPC 10006                                              P2P 10008 / RPC 10009
 trustedPeers = [B]                                                 trustedPeers = [A, C]
            \                                                      /
             \------ notarisation (filtered tx only) ----- Notary (non-validating)
                                                          P2P 10002 / RPC 10003
```

| Node | X.500 name | P2P | RPC | RPC admin | RPC user / password | trustedPeers |
|---|---|---|---|---|---|---|
| Notary | `O=Notary,L=Bengaluru,C=IN` | 10002 | 10003 | 10043 | none | none |
| EnterpriseA | `O=EnterpriseA,L=Bengaluru,C=IN` | 10005 | 10006 | 10046 | `userA` / `passA` | B |
| EnterpriseB | `O=EnterpriseB,L=Mumbai,C=IN` | 10008 | 10009 | 10049 | `userB` / `passB` | A, C |
| EnterpriseC | `O=EnterpriseC,L=Delhi,C=IN` | 10011 | 10012 | 10052 | `userC` / `passC` | A, B |

EnterpriseC is a valid network member. It holds a Doorman-issued certificate, so its TLS link to A succeeds. A's flow-level policy then refuses it.

## 2. Security design (four layers)

| Layer | Mechanism | Stops |
|---|---|---|
| 1 Transport | TLS 1.2 mutual auth, `ECDHE-ECDSA-AES128-GCM-SHA256`, certificate chain Root CA → Doorman CA → Node CA → TLS cert | eavesdropping, MITM, outsiders |
| 2 Identity | Ed25519 legal-identity signatures (sender + receiver on Send, receiver on Acknowledge), notary signature + time window | impersonation, repudiation, double acknowledgement |
| 3 Application | X25519 ECDH over the flow session → HKDF-SHA256 → AES-256-GCM (12-byte IV, 128-bit tag, metadata as AAD); SHA-256 `contentHash` | content leaks via vault, backups, notary, operators; tampering |
| 4 Privacy | participants = sender + receiver only; `FinalityFlow` to the receiver only; `trustedPeers` allow-list checked by initiator **and** responder | leaking to other members, unsolicited peers |

**Key handling.** The per-message AES key is never stored in plaintext. Each party keeps a *key envelope* inside the state: the AES key wrapped with a key-encryption key (KEK). Each node re-derives its KEK on demand:
`KEK = HKDF( Ed25519-sign(nodeIdentityKey, "securep2p-kek|" + linearId) )`.
Ed25519 signatures are deterministic, so only the node that holds the private identity key (in `nodekeystore.jks`, or an HSM in production) can unwrap its own envelope. Ephemeral X25519 private keys and AES keys are zeroed after use. Only `byte[]`/`String` values cross flow checkpoints.

## 3. CorDapp components (package `com.securep2p`)

| Component | File |
|---|---|
| `SecureMessageState` (LinearState: linearId, sender, receiver, subject, contentHash, encryptedPayload, senderKeyEnvelope, receiverKeyEnvelope, sentAt, status SENT/ACKNOWLEDGED; participants = sender + receiver) | `contracts/.../states/SecureMessageState.java` |
| `SecureMessageContract` with the `Send` and `Acknowledge` commands | `contracts/.../contracts/SecureMessageContract.java` |
| `SendSecureMessageFlow` + responder: key exchange, encrypt, CollectSignatures, Finality | `workflows/.../flows/SendSecureMessageFlow.java` |
| `AcknowledgeMessageFlow` + responder: the receiver confirms after an integrity check | `workflows/.../flows/AcknowledgeMessageFlow.java` |
| `ReadMessageFlow`: local decrypt + SHA-256 verification | `workflows/.../flows/ReadMessageFlow.java` |
| `PingPeerFlow` + responder: raw `sendAndReceive` latency in ms | `workflows/.../flows/PingPeerFlow.java` |
| `SecureCrypto`, `KeyEnvelopes`: X25519, HKDF, AES-GCM, SHA-256, KEK | `workflows/.../crypto/` |
| `TrustedPeerPolicy`: reads the `trustedPeers` CorDapp config, default-deny | `workflows/.../policy/TrustedPeerPolicy.java` |
| `DemoClient` (RPC): network map, sends, acks, decrypt, privacy, trust, latency, crypto benchmark | `clients/.../clients/DemoClient.java` |

**Contract rules.** *Send:* 0 inputs and 1 output with status SENT; sender ≠ receiver; the subject is not empty; `contentHash` is 64 hex characters; exactly 2 participants (the sender and the receiver); signed by both; it carries a time window that contains `sentAt`.
*Acknowledge:* SENT → ACKNOWLEDGED; linearId, parties and all content fields are unchanged; signed by the receiver.

## 4. Build, test, run

Requirements: JDK 17 and Python 3 (for the helper scripts). Windows commands are shown; on Linux/macOS use `./gradlew`.

```bash
gradlew test                        # 15 contract tests + 7 MockNetwork flow tests
python scripts/run_tests.py         # same, writes evidence/test_results.txt
gradlew deployNodes                 # builds build/nodes/{Notary,EnterpriseA,EnterpriseB,EnterpriseC}
python scripts/nodes.py start       # starts the 4 nodes headless (java -jar corda.jar), waits for "started up"
gradlew :clients:writeClasspath     # once, for the fast launcher below
scripts/demo_client.sh all          # or: gradlew :clients:runDemo -Pmode=all
python scripts/collect_certs.py     # evidence/certificates.txt   (keytool -list -v on the 3 keystores per node)
python scripts/tls_check.py         # evidence/tls_handshake.txt  (openssl s_client -tls1_2 against port 10005)
python scripts/collect_p2p_links.py # evidence/p2p_links.txt      (AMQP/TLS bridge lines from the node logs)
python scripts/nodes.py stop
```

DemoClient modes: `all | networkmap | send | ack | privacy | untrusted | ping | bench`.

The trusted-peer list for each node is in `build/nodes/<Node>/cordapps/config/workflows-0.1.conf`. It is generated from `build.gradle`, for example `trustedPeers = ["O=EnterpriseB,L=Mumbai,C=IN"]` for EnterpriseA.

> **Low disk space:** Artemis blocks message producers when the disk is more than 90% full. `scripts/nodes.py` starts the nodes with `-Dbrokerconfig.maxDiskUsage=100` so that the demo still runs on a nearly full laptop drive.

## 5. Results (from `evidence/`)

* **Tests:** 22/22 pass (15 contract, 7 flow), covering the A→B send + acknowledge, privacy (C vault = 0), integrity (tampering detected), the trust policy (C→A rejected) and ciphertext ≠ plaintext.
* **TLS:** server certificate `C=IN, L=Bengaluru, O=EnterpriseA`, TLSv1.2, `ECDHE-ECDSA-AES128-GCM-SHA256`. Without a client certificate the handshake is rejected (alert 40, "Empty client certificate chain"). With a Doorman-issued certificate it completes. TLS 1.3 is refused.
* **Live demo:** 3 messages A→B and 1 B→A, all acknowledged. B decrypts with the integrity check PASSED. Vault counts are A = 8, B = 8, **C = 0**. C→A gives `Untrusted peer`. 20 pings A→B average **≈121 ms** on a single laptop running all 4 nodes.
* **Crypto cost:** ~1 ms per message for the key agreement. AES-GCM takes ~9–25 µs for 0.25–4 KB bodies. Size overhead is +28 bytes, then ×4/3 for base64.

## 6. Repository layout

```
contracts/   state + contract + contract tests
workflows/   flows, crypto, trust policy + MockNetwork flow tests
clients/     RPC DemoClient
scripts/     node control, evidence collectors, image/report/PPT/video builders
evidence/    real outputs (tests, certificates, TLS handshake, P2P links, demo run, node start-up)
images/      terminal screenshots rendered from evidence/;  diagrams/  architecture diagrams
demo/        demo_script.py used for the live demonstration video
deliverables/ report (docx/pdf), PPT, videos, subtitles, links.txt
```

## 7. Limitations and future scope

The network uses dev-mode certificates and a single notary. Keys sit in JKS files rather than an HSM. There is no key rotation or re-keying of old messages. Corda 5 would replace `trustedPeers` with MGM-managed membership groups.

Based on the R3 `cordapp-template-java` (Apache 2.0, see `LICENCE`).
