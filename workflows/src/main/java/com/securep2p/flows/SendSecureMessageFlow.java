package com.securep2p.flows;

import co.paralleluniverse.fibers.Suspendable;
import com.securep2p.contracts.SecureMessageContract;
import com.securep2p.crypto.KeyEnvelopes;
import com.securep2p.crypto.SecureCrypto;
import com.securep2p.policy.TrustedPeerPolicy;
import com.securep2p.states.SecureMessageState;
import net.corda.core.contracts.ContractState;
import net.corda.core.contracts.TimeWindow;
import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.crypto.SecureHash;
import net.corda.core.flows.*;
import net.corda.core.identity.Party;
import net.corda.core.transactions.SignedTransaction;
import net.corda.core.transactions.TransactionBuilder;
import net.corda.core.utilities.ProgressTracker;
import org.jetbrains.annotations.NotNull;

import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.Collections;

/**
 * Sends a confidential message to one counterparty.
 *
 *   1. trust check (our own allow-list)          4. build tx (Send, time window) and sign
 *   2. X25519 key exchange over the session      5. CollectSignaturesFlow (receiver verifies + signs)
 *   3. AES-256-GCM encrypt + SHA-256 hash        6. FinalityFlow -> notary -> receiver only
 *
 * Author: Gagan N (24BTRBT013)
 */
@InitiatingFlow
@StartableByRPC
public class SendSecureMessageFlow extends FlowLogic<SignedTransaction> {
    private final Party receiver;
    private final String subject;
    private final String body;

    private final ProgressTracker.Step TRUST = new ProgressTracker.Step("Checking trusted-peer policy");
    private final ProgressTracker.Step KEX = new ProgressTracker.Step("X25519 key exchange over the P2P session");
    private final ProgressTracker.Step ENCRYPT = new ProgressTracker.Step("Encrypting body with AES-256-GCM");
    private final ProgressTracker.Step SIGN = new ProgressTracker.Step("Building and signing the transaction");
    private final ProgressTracker.Step COLLECT = new ProgressTracker.Step("Collecting the receiver's signature") {
        @Override public ProgressTracker childProgressTracker() { return CollectSignaturesFlow.tracker(); }
    };
    private final ProgressTracker.Step FINALISE = new ProgressTracker.Step("Notarising and distributing to the receiver") {
        @Override public ProgressTracker childProgressTracker() { return FinalityFlow.tracker(); }
    };
    private final ProgressTracker progressTracker = new ProgressTracker(TRUST, KEX, ENCRYPT, SIGN, COLLECT, FINALISE);

    public SendSecureMessageFlow(Party receiver, String subject, String body) {
        this.receiver = receiver;
        this.subject = subject;
        this.body = body;
    }

    @Override public ProgressTracker getProgressTracker() { return progressTracker; }

    @Suspendable
    @Override
    public SignedTransaction call() throws FlowException {
        Party me = getOurIdentity();
        if (receiver.equals(me)) throw new FlowException("Cannot send a secure message to yourself.");
        if (subject == null || subject.trim().isEmpty()) throw new FlowException("Subject must not be empty.");

        progressTracker.setCurrentStep(TRUST);
        TrustedPeerPolicy.requireTrusted(getServiceHub(), receiver);

        progressTracker.setCurrentStep(KEX);
        UniqueIdentifier linearId = new UniqueIdentifier();
        byte[][] eph = SecureCrypto.generateEphemeralX25519();
        byte[] ourPublic = eph[0];
        byte[] ourPrivate = eph[1];
        FlowSession session = initiateFlow(receiver);
        KeyExchangeMessages.Reply reply = session.sendAndReceive(KeyExchangeMessages.Reply.class,
                new KeyExchangeMessages.Init(linearId, ourPublic)).unwrap(r -> {
            if (r.getEphemeralPublicKey() == null || r.getEphemeralPublicKey().length < 32)
                throw new IllegalArgumentException("Invalid ephemeral public key from responder");
            if (r.getReceiverKeyEnvelope() == null || r.getReceiverKeyEnvelope().isEmpty())
                throw new IllegalArgumentException("Missing receiver key envelope");
            return r;
        });
        byte[] messageKey = SecureCrypto.deriveMessageKey(ourPrivate, reply.getEphemeralPublicKey(), linearId.getId().toString());
        Arrays.fill(ourPrivate, (byte) 0);

        progressTracker.setCurrentStep(ENCRYPT);
        byte[] plaintext = SecureCrypto.utf8(body);
        String contentHash = SecureCrypto.sha256Hex(plaintext);
        String payload = SecureCrypto.encrypt(messageKey, plaintext,
                KeyEnvelopes.payloadAad(linearId, subject, me.getName().toString(), receiver.getName().toString()));
        String senderEnvelope = KeyEnvelopes.wrap(getServiceHub(), me.getOwningKey(), linearId, messageKey);
        Arrays.fill(messageKey, (byte) 0);

        progressTracker.setCurrentStep(SIGN);
        Instant sentAt = getServiceHub().getClock().instant();
        SecureMessageState state = new SecureMessageState(linearId, me, receiver, subject, contentHash, payload,
                senderEnvelope, reply.getReceiverKeyEnvelope(), sentAt, SecureMessageState.Status.SENT);
        Party notary = getServiceHub().getNetworkMapCache().getNotaryIdentities().get(0);
        TransactionBuilder builder = new TransactionBuilder(notary)
                .addOutputState(state, SecureMessageContract.ID)
                .addCommand(new SecureMessageContract.Commands.Send(),
                        Arrays.asList(me.getOwningKey(), receiver.getOwningKey()))
                .setTimeWindow(TimeWindow.withTolerance(sentAt, Duration.ofSeconds(60)));
        builder.verify(getServiceHub());
        SignedTransaction partSigned = getServiceHub().signInitialTransaction(builder);

        progressTracker.setCurrentStep(COLLECT);
        SignedTransaction fullySigned = subFlow(new CollectSignaturesFlow(partSigned,
                Collections.singletonList(session), COLLECT.childProgressTracker()));

        progressTracker.setCurrentStep(FINALISE);
        return subFlow(new FinalityFlow(fullySigned, Collections.singletonList(session), FINALISE.childProgressTracker()));
    }

    // ===================================================================================== responder

    @InitiatedBy(SendSecureMessageFlow.class)
    public static class Responder extends FlowLogic<SignedTransaction> {
        private final FlowSession session;

        public Responder(FlowSession session) { this.session = session; }

        @Suspendable
        @Override
        public SignedTransaction call() throws FlowException {
            Party me = getOurIdentity();
            Party sender = session.getCounterparty();
            // 1. Trusted-peer policy: reject before any key material is exchanged.
            TrustedPeerPolicy.requireTrusted(getServiceHub(), sender);

            // 2. Key exchange.
            KeyExchangeMessages.Init init = session.receive(KeyExchangeMessages.Init.class).unwrap(i -> {
                if (i.getEphemeralPublicKey() == null || i.getEphemeralPublicKey().length < 32)
                    throw new IllegalArgumentException("Invalid ephemeral public key from initiator");
                return i;
            });
            final UniqueIdentifier expectedId = init.getLinearId();
            byte[][] eph = SecureCrypto.generateEphemeralX25519();
            byte[] messageKey = SecureCrypto.deriveMessageKey(eph[1], init.getEphemeralPublicKey(), expectedId.getId().toString());
            Arrays.fill(eph[1], (byte) 0);
            final String ourEnvelope = KeyEnvelopes.wrap(getServiceHub(), me.getOwningKey(), expectedId, messageKey);
            Arrays.fill(messageKey, (byte) 0);
            session.send(new KeyExchangeMessages.Reply(eph[0], ourEnvelope));

            // 3. Verify what we are asked to sign: decrypt it ourselves and check the SHA-256.
            SignTransactionFlow signFlow = new SignTransactionFlow(session) {
                @Override
                protected void checkTransaction(@NotNull SignedTransaction stx) throws FlowException {
                    ContractState output = stx.getTx().getOutputs().get(0).getData();
                    if (!(output instanceof SecureMessageState)) throw new FlowException("Not a SecureMessageState");
                    SecureMessageState s = (SecureMessageState) output;
                    if (!s.getReceiver().equals(me)) throw new FlowException("We are not the receiver");
                    if (!s.getSender().equals(sender)) throw new FlowException("Sender does not match session counterparty");
                    if (!s.getLinearId().equals(expectedId)) throw new FlowException("linearId does not match key exchange");
                    if (!s.getReceiverKeyEnvelope().equals(ourEnvelope)) throw new FlowException("Receiver key envelope was altered");
                    try {
                        byte[] key = KeyEnvelopes.unwrap(getServiceHub(), me.getOwningKey(), s.getLinearId(), s.getReceiverKeyEnvelope());
                        byte[] plain = SecureCrypto.decrypt(key, s.getEncryptedPayload(), KeyEnvelopes.payloadAad(
                                s.getLinearId(), s.getSubject(), s.getSender().getName().toString(), s.getReceiver().getName().toString()));
                        Arrays.fill(key, (byte) 0);
                        if (!SecureCrypto.sha256Hex(plain).equals(s.getContentHash()))
                            throw new FlowException("Integrity check failed: contentHash does not match the decrypted body");
                    } catch (SecureCrypto.IntegrityException e) {
                        throw new FlowException("Integrity check failed: " + e.getMessage());
                    }
                }
            };
            SecureHash txId = subFlow(signFlow).getId();
            // 4. Receive the notarised transaction.
            return subFlow(new ReceiveFinalityFlow(session, txId));
        }
    }
}
