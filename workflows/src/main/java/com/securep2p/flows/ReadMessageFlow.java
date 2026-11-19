package com.securep2p.flows;

import co.paralleluniverse.fibers.Suspendable;
import com.securep2p.crypto.KeyEnvelopes;
import com.securep2p.crypto.SecureCrypto;
import com.securep2p.states.SecureMessageState;
import net.corda.core.contracts.StateAndRef;
import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.flows.FlowException;
import net.corda.core.flows.FlowLogic;
import net.corda.core.flows.StartableByRPC;
import net.corda.core.identity.Party;
import net.corda.core.node.services.Vault;
import net.corda.core.node.services.vault.QueryCriteria;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Decrypts a SecureMessageState locally (no network traffic) and verifies SHA-256(body) == contentHash.
 * Only the sender or the receiver can run it successfully: each unwraps its own key envelope with a KEK derived
 * from its private identity key.
 *
 * The second constructor verifies a given copy of a state (e.g. one restored from a backup or an export);
 * the tests use it to prove that a tampered payload is detected.
 *
 * Author: Gagan N (24BTRBT013)
 */
@StartableByRPC
public class ReadMessageFlow extends FlowLogic<DecryptedMessage> {
    private final UniqueIdentifier linearId;
    private final SecureMessageState providedState;

    public ReadMessageFlow(UniqueIdentifier linearId) {
        this.linearId = linearId;
        this.providedState = null;
    }

    public ReadMessageFlow(SecureMessageState state) {
        this.linearId = state.getLinearId();
        this.providedState = state;
    }

    @Suspendable
    @Override
    public DecryptedMessage call() throws FlowException {
        SecureMessageState s = providedState != null ? providedState : loadLatest(linearId);
        Party me = getOurIdentity();
        String envelope;
        if (me.equals(s.getReceiver())) envelope = s.getReceiverKeyEnvelope();
        else if (me.equals(s.getSender())) envelope = s.getSenderKeyEnvelope();
        else throw new FlowException("Access denied: " + me.getName() + " is not a participant of this message");

        long t0 = System.nanoTime();
        byte[] plain;
        try {
            byte[] key = KeyEnvelopes.unwrap(getServiceHub(), me.getOwningKey(), s.getLinearId(), envelope);
            plain = SecureCrypto.decrypt(key, s.getEncryptedPayload(), KeyEnvelopes.payloadAad(
                    s.getLinearId(), s.getSubject(), s.getSender().getName().toString(), s.getReceiver().getName().toString()));
            Arrays.fill(key, (byte) 0);
        } catch (SecureCrypto.IntegrityException e) {
            throw new FlowException("Integrity check failed: " + e.getMessage());
        }
        long micros = (System.nanoTime() - t0) / 1000;

        String computed = SecureCrypto.sha256Hex(plain);
        if (!computed.equals(s.getContentHash())) {
            throw new FlowException("Integrity check failed: SHA-256 of decrypted body (" + computed
                    + ") does not match contentHash (" + s.getContentHash() + ")");
        }
        return new DecryptedMessage(s.getLinearId().getId().toString(), s.getSender().getName().toString(),
                s.getReceiver().getName().toString(), s.getSubject(), new String(plain, java.nio.charset.StandardCharsets.UTF_8),
                s.getContentHash(), computed, s.getStatus().name(), true, micros);
    }

    private SecureMessageState loadLatest(UniqueIdentifier id) throws FlowException {
        QueryCriteria criteria = new QueryCriteria.LinearStateQueryCriteria(null, Collections.singletonList(id.getId()), null,
                Vault.StateStatus.UNCONSUMED);
        List<StateAndRef<SecureMessageState>> found =
                getServiceHub().getVaultService().queryBy(SecureMessageState.class, criteria).getStates();
        if (found.isEmpty()) throw new FlowException("No SecureMessageState with id " + id + " in this vault");
        return found.get(0).getState().getData();
    }
}
