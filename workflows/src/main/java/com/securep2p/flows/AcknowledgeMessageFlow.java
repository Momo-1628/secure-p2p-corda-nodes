package com.securep2p.flows;

import co.paralleluniverse.fibers.Suspendable;
import com.securep2p.contracts.SecureMessageContract;
import com.securep2p.policy.TrustedPeerPolicy;
import com.securep2p.states.SecureMessageState;
import net.corda.core.contracts.StateAndRef;
import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.flows.*;
import net.corda.core.identity.Party;
import net.corda.core.node.services.Vault;
import net.corda.core.node.services.vault.QueryCriteria;
import net.corda.core.transactions.SignedTransaction;
import net.corda.core.transactions.TransactionBuilder;

import java.util.Collections;
import java.util.List;

/**
 * The receiver confirms a message: SENT -> ACKNOWLEDGED. Before acknowledging, the receiver decrypts the message and
 * verifies its SHA-256 (so an acknowledgement means "received intact"). The notary prevents a double acknowledgement.
 *
 * Author: Gagan N (24BTRBT013)
 */
@InitiatingFlow
@StartableByRPC
public class AcknowledgeMessageFlow extends FlowLogic<SignedTransaction> {
    private final UniqueIdentifier linearId;

    public AcknowledgeMessageFlow(UniqueIdentifier linearId) { this.linearId = linearId; }

    @Suspendable
    @Override
    public SignedTransaction call() throws FlowException {
        QueryCriteria criteria = new QueryCriteria.LinearStateQueryCriteria(null, Collections.singletonList(linearId.getId()), null,
                Vault.StateStatus.UNCONSUMED);
        List<StateAndRef<SecureMessageState>> found =
                getServiceHub().getVaultService().queryBy(SecureMessageState.class, criteria).getStates();
        if (found.isEmpty()) throw new FlowException("Message " + linearId + " not found");
        StateAndRef<SecureMessageState> inRef = found.get(0);
        SecureMessageState in = inRef.getState().getData();

        Party me = getOurIdentity();
        if (!in.getReceiver().equals(me)) throw new FlowException("Only the receiver can acknowledge a message");
        if (in.getStatus() != SecureMessageState.Status.SENT) throw new FlowException("Message already acknowledged");
        TrustedPeerPolicy.requireTrusted(getServiceHub(), in.getSender());

        // Integrity check before confirming receipt.
        subFlow(new ReadMessageFlow(in));

        TransactionBuilder builder = new TransactionBuilder(inRef.getState().getNotary())
                .addInputState(inRef)
                .addOutputState(in.acknowledge(), SecureMessageContract.ID)
                .addCommand(new SecureMessageContract.Commands.Acknowledge(), me.getOwningKey());
        builder.verify(getServiceHub());
        SignedTransaction stx = getServiceHub().signInitialTransaction(builder);

        FlowSession senderSession = initiateFlow(in.getSender());
        return subFlow(new FinalityFlow(stx, Collections.singletonList(senderSession)));
    }

    @InitiatedBy(AcknowledgeMessageFlow.class)
    public static class Responder extends FlowLogic<SignedTransaction> {
        private final FlowSession session;

        public Responder(FlowSession session) { this.session = session; }

        @Suspendable
        @Override
        public SignedTransaction call() throws FlowException {
            TrustedPeerPolicy.requireTrusted(getServiceHub(), session.getCounterparty());
            return subFlow(new ReceiveFinalityFlow(session));
        }
    }
}
