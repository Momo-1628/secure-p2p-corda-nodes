package com.securep2p.contracts;

import com.securep2p.states.SecureMessageState;
import net.corda.core.contracts.TimeWindow;
import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.identity.AbstractParty;
import net.corda.core.identity.CordaX500Name;
import net.corda.testing.core.TestIdentity;
import net.corda.testing.node.MockServices;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;

import static net.corda.testing.node.NodeTestUtils.ledger;

/** Contract tests for SecureMessageContract (ledger DSL). Author: Gagan N (24BTRBT013) */
public class SecureMessageContractTests {
    private final TestIdentity a = new TestIdentity(new CordaX500Name("EnterpriseA", "Bengaluru", "IN"));
    private final TestIdentity b = new TestIdentity(new CordaX500Name("EnterpriseB", "Mumbai", "IN"));
    private final TestIdentity c = new TestIdentity(new CordaX500Name("EnterpriseC", "Delhi", "IN"));
    private final MockServices ledgerServices = new MockServices(Arrays.asList("com.securep2p.contracts"));

    private final Instant now = Instant.now();
    private final TimeWindow window = TimeWindow.withTolerance(now, Duration.ofSeconds(30));

    private static String sha256(String s) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte x : d) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (Exception e) { throw new RuntimeException(e); }
    }

    private SecureMessageState sent() {
        return new SecureMessageState(new UniqueIdentifier(), a.getParty(), b.getParty(), "PO-2026-0412",
                sha256("Purchase 500 units"), "q83vEjRWeJA=Y2lwaGVydGV4dA==", "ZW52LUE=", "ZW52LUI=",
                now, SecureMessageState.Status.SENT);
    }

    // ---------------------------------------------------------------- Send

    @Test
    public void validSendVerifies() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, sent());
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.verifies();
            });
            return null;
        });
    }

    @Test
    public void sendMissingReceiverSignatureFails() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, sent());
                tx.command(a.getPublicKey(), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("The receiver must sign.");
            });
            return null;
        });
    }

    @Test
    public void sendMissingSenderSignatureFails() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, sent());
                tx.command(b.getPublicKey(), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("The sender must sign.");
            });
            return null;
        });
    }

    @Test
    public void sendWithThreeParticipantsFails() {
        SecureMessageState s = sent();
        SecureMessageState three = new SecureMessageState(s.getLinearId(), s.getSender(), s.getReceiver(), s.getSubject(),
                s.getContentHash(), s.getEncryptedPayload(), s.getSenderKeyEnvelope(), s.getReceiverKeyEnvelope(),
                s.getSentAt(), s.getStatus(), Arrays.<AbstractParty>asList(a.getParty(), b.getParty(), c.getParty()));
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, three);
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("There must be exactly 2 participants.");
            });
            return null;
        });
    }

    @Test
    public void sendWithBadHashFails() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, sent().withContentHash("not-a-sha256"));
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("contentHash must be a 64-character lowercase SHA-256 hex string.");
            });
            return null;
        });
    }

    @Test
    public void sendToSelfFails() {
        SecureMessageState s = new SecureMessageState(new UniqueIdentifier(), a.getParty(), a.getParty(), "Self",
                sha256("x"), "cGF5bG9hZA==", "ZQ==", "ZQ==", now, SecureMessageState.Status.SENT,
                Arrays.<AbstractParty>asList(a.getParty(), b.getParty()));
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, s);
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("Sender and receiver must be different parties.");
            });
            return null;
        });
    }

    @Test
    public void sendWithEmptySubjectFails() {
        SecureMessageState s = sent();
        SecureMessageState empty = new SecureMessageState(s.getLinearId(), s.getSender(), s.getReceiver(), "  ",
                s.getContentHash(), s.getEncryptedPayload(), s.getSenderKeyEnvelope(), s.getReceiverKeyEnvelope(),
                s.getSentAt(), s.getStatus());
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, empty);
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("Subject must not be empty.");
            });
            return null;
        });
    }

    @Test
    public void sendWithInputFails() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.input(SecureMessageContract.ID, sent());
                tx.output(SecureMessageContract.ID, sent());
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("Send must have no inputs.");
            });
            return null;
        });
    }

    @Test
    public void sendWithAcknowledgedStatusFails() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, sent().acknowledge());
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                tx.timeWindow(window);
                return tx.failsWith("A new message must have status SENT.");
            });
            return null;
        });
    }

    @Test
    public void sendWithoutTimeWindowFails() {
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.output(SecureMessageContract.ID, sent());
                tx.command(Arrays.asList(a.getPublicKey(), b.getPublicKey()), new SecureMessageContract.Commands.Send());
                return tx.failsWith("Send must carry a notarised time window.");
            });
            return null;
        });
    }

    // --------------------------------------------------------- Acknowledge

    @Test
    public void validAcknowledgeVerifies() {
        SecureMessageState s = sent();
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.input(SecureMessageContract.ID, s);
                tx.output(SecureMessageContract.ID, s.acknowledge());
                tx.command(b.getPublicKey(), new SecureMessageContract.Commands.Acknowledge());
                return tx.verifies();
            });
            return null;
        });
    }

    @Test
    public void acknowledgeWithChangedContentFails() {
        SecureMessageState s = sent();
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.input(SecureMessageContract.ID, s);
                tx.output(SecureMessageContract.ID, s.acknowledge().withEncryptedPayload("dGFtcGVyZWQ="));
                tx.command(b.getPublicKey(), new SecureMessageContract.Commands.Acknowledge());
                return tx.failsWith("Message content must not change.");
            });
            return null;
        });
    }

    @Test
    public void acknowledgeWithChangedHashFails() {
        SecureMessageState s = sent();
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.input(SecureMessageContract.ID, s);
                tx.output(SecureMessageContract.ID, s.acknowledge().withContentHash(sha256("other")));
                tx.command(b.getPublicKey(), new SecureMessageContract.Commands.Acknowledge());
                return tx.failsWith("Message content must not change.");
            });
            return null;
        });
    }

    @Test
    public void acknowledgeSignedOnlyBySenderFails() {
        SecureMessageState s = sent();
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.input(SecureMessageContract.ID, s);
                tx.output(SecureMessageContract.ID, s.acknowledge());
                tx.command(a.getPublicKey(), new SecureMessageContract.Commands.Acknowledge());
                return tx.failsWith("The receiver must sign the acknowledgement.");
            });
            return null;
        });
    }

    @Test
    public void acknowledgeAlreadyAcknowledgedFails() {
        SecureMessageState s = sent().acknowledge();
        ledger(ledgerServices, l -> {
            l.transaction(tx -> {
                tx.input(SecureMessageContract.ID, s);
                tx.output(SecureMessageContract.ID, s);
                tx.command(b.getPublicKey(), new SecureMessageContract.Commands.Acknowledge());
                return tx.failsWith("Input status must be SENT.");
            });
            return null;
        });
    }
}
