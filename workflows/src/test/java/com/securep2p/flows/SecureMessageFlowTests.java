package com.securep2p.flows;

import com.securep2p.states.SecureMessageState;
import net.corda.core.concurrent.CordaFuture;
import net.corda.core.flows.FlowException;
import net.corda.core.identity.CordaX500Name;
import net.corda.core.identity.Party;
import net.corda.core.node.services.Vault;
import net.corda.core.node.services.vault.QueryCriteria;
import net.corda.core.transactions.SignedTransaction;
import net.corda.testing.node.*;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.*;
import java.util.concurrent.ExecutionException;

import static org.junit.Assert.*;

/** MockNetwork flow tests. Author: Gagan N (24BTRBT013) */
public class SecureMessageFlowTests {
    private static final CordaX500Name A_NAME = CordaX500Name.parse("O=EnterpriseA,L=Bengaluru,C=IN");
    private static final CordaX500Name B_NAME = CordaX500Name.parse("O=EnterpriseB,L=Mumbai,C=IN");
    private static final CordaX500Name C_NAME = CordaX500Name.parse("O=EnterpriseC,L=Delhi,C=IN");

    private static final String BODY = "Purchase order PO-2026-0412: 500 units of industrial sensors @ INR 1,250/unit, delivery by 15-Dec.";

    private MockNetwork network;
    private StartedMockNode a, b, c;
    private Party partyA, partyB, partyC;

    private static TestCordapp flowsWithTrust(CordaX500Name... trusted) {
        List<String> names = new ArrayList<>();
        for (CordaX500Name n : trusted) names.add(n.toString());
        Map<String, Object> cfg = new HashMap<>();
        cfg.put("trustedPeers", String.join(";", names));
        return TestCordapp.findCordapp("com.securep2p.flows").withConfig(cfg);
    }

    @Before
    public void setup() {
        network = new MockNetwork(new MockNetworkParameters()
                .withCordappsForAllNodes(Collections.singletonList(TestCordapp.findCordapp("com.securep2p.contracts")))
                .withNotarySpecs(Collections.singletonList(new MockNetworkNotarySpec(CordaX500Name.parse("O=Notary,L=Bengaluru,C=IN")))));
        // Same trust policy as deployNodes: A trusts only B; B and C trust the other two.
        a = network.createNode(new MockNodeParameters().withLegalName(A_NAME)
                .withAdditionalCordapps(Collections.singletonList(flowsWithTrust(B_NAME))));
        b = network.createNode(new MockNodeParameters().withLegalName(B_NAME)
                .withAdditionalCordapps(Collections.singletonList(flowsWithTrust(A_NAME, C_NAME))));
        c = network.createNode(new MockNodeParameters().withLegalName(C_NAME)
                .withAdditionalCordapps(Collections.singletonList(flowsWithTrust(A_NAME, B_NAME))));
        partyA = a.getInfo().getLegalIdentities().get(0);
        partyB = b.getInfo().getLegalIdentities().get(0);
        partyC = c.getInfo().getLegalIdentities().get(0);
        network.runNetwork();
    }

    @After
    public void tearDown() { network.stopNodes(); }

    private <T> T run(StartedMockNode node, net.corda.core.flows.FlowLogic<T> flow) throws Exception {
        CordaFuture<T> f = node.startFlow(flow);
        network.runNetwork();
        return f.get();
    }

    private List<SecureMessageState> vault(StartedMockNode node, Vault.StateStatus status) {
        return node.transaction(() -> {
            List<SecureMessageState> out = new ArrayList<>();
            node.getServices().getVaultService().queryBy(SecureMessageState.class,
                    new QueryCriteria.VaultQueryCriteria(status)).getStates()
                    .forEach(s -> out.add(s.getState().getData()));
            return out;
        });
    }

    private SecureMessageState sendAtoB() throws Exception {
        SignedTransaction stx = run(a, new SendSecureMessageFlow(partyB, "PO-2026-0412", BODY));
        return (SecureMessageState) stx.getTx().getOutputs().get(0).getData();
    }

    // (1) A -> B send + acknowledge works
    @Test
    public void sendAndAcknowledgeWorks() throws Exception {
        SecureMessageState sent = sendAtoB();
        assertEquals(SecureMessageState.Status.SENT, sent.getStatus());
        assertEquals(1, vault(a, Vault.StateStatus.UNCONSUMED).size());
        assertEquals(1, vault(b, Vault.StateStatus.UNCONSUMED).size());

        DecryptedMessage read = run(b, new ReadMessageFlow(sent.getLinearId()));
        assertEquals(BODY, read.getBody());
        assertTrue(read.isIntegrityVerified());

        run(b, new AcknowledgeMessageFlow(sent.getLinearId()));
        for (StartedMockNode n : Arrays.asList(a, b)) {
            List<SecureMessageState> states = vault(n, Vault.StateStatus.UNCONSUMED);
            assertEquals(1, states.size());
            assertEquals(SecureMessageState.Status.ACKNOWLEDGED, states.get(0).getStatus());
        }
        // The sender can also decrypt its own copy.
        assertEquals(BODY, run(a, new ReadMessageFlow(sent.getLinearId())).getBody());
    }

    // (2) PRIVACY: EnterpriseC's vault has 0 SecureMessageStates after A -> B
    @Test
    public void thirdPartyVaultIsEmpty() throws Exception {
        SecureMessageState sent = sendAtoB();
        run(b, new AcknowledgeMessageFlow(sent.getLinearId()));
        assertEquals(0, vault(c, Vault.StateStatus.ALL).size());
        // and C cannot read a copy even if it obtained one
        try {
            run(c, new ReadMessageFlow(sent));
            fail("C should not be able to read the message");
        } catch (ExecutionException e) {
            assertTrue(e.getCause().getMessage().contains("Access denied"));
        }
    }

    // (3) INTEGRITY: a tampered payload fails ReadMessageFlow's integrity check
    @Test
    public void tamperedPayloadFailsIntegrityCheck() throws Exception {
        SecureMessageState sent = sendAtoB();
        // (a) flip one byte of the ciphertext
        byte[] raw = Base64.getDecoder().decode(sent.getEncryptedPayload());
        raw[20] ^= 0x01;
        SecureMessageState tamperedCipher = sent.withEncryptedPayload(Base64.getEncoder().encodeToString(raw));
        try {
            run(b, new ReadMessageFlow(tamperedCipher));
            fail("Tampered ciphertext must be rejected");
        } catch (ExecutionException e) {
            assertTrue(e.getCause() instanceof FlowException);
            assertTrue(e.getCause().getMessage().startsWith("Integrity check failed"));
        }
        // (b) change the recorded hash: decryption works but the SHA-256 comparison fails
        SecureMessageState tamperedHash = sent.withContentHash(
                "0000000000000000000000000000000000000000000000000000000000000000");
        try {
            run(b, new ReadMessageFlow(tamperedHash));
            fail("Hash mismatch must be rejected");
        } catch (ExecutionException e) {
            assertTrue(e.getCause().getMessage().contains("does not match contentHash"));
        }
    }

    // (4) TRUST POLICY: C -> A is rejected with "Untrusted peer"
    @Test
    public void untrustedPeerIsRejected() throws Exception {
        try {
            run(c, new SendSecureMessageFlow(partyA, "Unsolicited offer", "Hello from C"));
            fail("A must reject C");
        } catch (ExecutionException e) {
            assertTrue(e.getCause() instanceof FlowException);
            assertTrue(e.getCause().getMessage().contains("Untrusted peer"));
        }
        assertEquals(0, vault(a, Vault.StateStatus.ALL).size());
        assertEquals(0, vault(c, Vault.StateStatus.ALL).size());
        // A also refuses to initiate towards C
        try {
            run(a, new PingPeerFlow(partyC));
            fail("A must not ping C");
        } catch (ExecutionException e) {
            assertTrue(e.getCause().getMessage().contains("Untrusted peer"));
        }
    }

    // (5) the encrypted payload stored in the state is not equal to the plaintext
    @Test
    public void storedPayloadIsCiphertext() throws Exception {
        SecureMessageState sent = sendAtoB();
        SecureMessageState onB = vault(b, Vault.StateStatus.UNCONSUMED).get(0);
        assertNotEquals(BODY, onB.getEncryptedPayload());
        assertFalse(onB.getEncryptedPayload().contains("PO-2026-0412"));
        assertFalse(new String(Base64.getDecoder().decode(onB.getEncryptedPayload()),
                java.nio.charset.StandardCharsets.ISO_8859_1).contains("industrial sensors"));
        assertEquals(64, onB.getContentHash().length());
        assertEquals(sent.getEncryptedPayload(), onB.getEncryptedPayload());
    }

    // extra: P2P ping round trip and duplicate acknowledgement prevention
    @Test
    public void pingReturnsLatency() throws Exception {
        Double ms = run(a, new PingPeerFlow(partyB));
        assertTrue(ms >= 0);
    }

    @Test
    public void cannotAcknowledgeTwice() throws Exception {
        SecureMessageState sent = sendAtoB();
        run(b, new AcknowledgeMessageFlow(sent.getLinearId()));
        try {
            run(b, new AcknowledgeMessageFlow(sent.getLinearId()));
            fail("Second acknowledgement must fail");
        } catch (ExecutionException e) {
            assertTrue(e.getCause().getMessage().contains("already acknowledged"));
        }
    }
}
