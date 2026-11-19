package com.securep2p.states;

import com.securep2p.contracts.SecureMessageContract;
import net.corda.core.contracts.BelongsToContract;
import net.corda.core.contracts.LinearState;
import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.identity.AbstractParty;
import net.corda.core.identity.Party;
import net.corda.core.serialization.ConstructorForDeserialization;
import net.corda.core.serialization.CordaSerializable;
import org.jetbrains.annotations.NotNull;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;

/**
 * A confidential business message exchanged directly between two enterprise nodes.
 *
 * Only ciphertext is ever stored on the ledger:
 *  - encryptedPayload    : base64( IV(12) || AES-256-GCM(body) || tag(16) )
 *  - contentHash         : SHA-256 hex of the plaintext body (tamper evidence)
 *  - senderKeyEnvelope   : the per-message AES key, wrapped with a key that only the sender can re-derive
 *  - receiverKeyEnvelope : the same AES key, wrapped with a key that only the receiver can re-derive
 *
 * The participants are the sender and the receiver only (need-to-know privacy).
 *
 * Author: Gagan N (24BTRBT013)
 */
@BelongsToContract(SecureMessageContract.class)
public class SecureMessageState implements LinearState {

    @CordaSerializable
    public enum Status { SENT, ACKNOWLEDGED }

    private final UniqueIdentifier linearId;
    private final Party sender;
    private final Party receiver;
    private final String subject;
    private final String contentHash;
    private final String encryptedPayload;
    private final String senderKeyEnvelope;
    private final String receiverKeyEnvelope;
    private final Instant sentAt;
    private final Status status;
    private final List<AbstractParty> participants;

    @ConstructorForDeserialization
    public SecureMessageState(UniqueIdentifier linearId, Party sender, Party receiver, String subject,
                              String contentHash, String encryptedPayload, String senderKeyEnvelope,
                              String receiverKeyEnvelope, Instant sentAt, Status status,
                              List<AbstractParty> participants) {
        this.linearId = linearId;
        this.sender = sender;
        this.receiver = receiver;
        this.subject = subject;
        this.contentHash = contentHash;
        this.encryptedPayload = encryptedPayload;
        this.senderKeyEnvelope = senderKeyEnvelope;
        this.receiverKeyEnvelope = receiverKeyEnvelope;
        this.sentAt = sentAt;
        this.status = status;
        this.participants = new ArrayList<>(participants);
    }

    /** Normal constructor: participants are exactly the sender and the receiver. */
    public SecureMessageState(UniqueIdentifier linearId, Party sender, Party receiver, String subject,
                              String contentHash, String encryptedPayload, String senderKeyEnvelope,
                              String receiverKeyEnvelope, Instant sentAt, Status status) {
        this(linearId, sender, receiver, subject, contentHash, encryptedPayload, senderKeyEnvelope,
                receiverKeyEnvelope, sentAt, status, Arrays.asList(sender, receiver));
    }

    public SecureMessageState acknowledge() {
        return new SecureMessageState(linearId, sender, receiver, subject, contentHash, encryptedPayload,
                senderKeyEnvelope, receiverKeyEnvelope, sentAt, Status.ACKNOWLEDGED, participants);
    }

    /** Returns a copy with a different payload (used to simulate tampering at rest in tests). */
    public SecureMessageState withEncryptedPayload(String newPayload) {
        return new SecureMessageState(linearId, sender, receiver, subject, contentHash, newPayload,
                senderKeyEnvelope, receiverKeyEnvelope, sentAt, status, participants);
    }

    public SecureMessageState withContentHash(String newHash) {
        return new SecureMessageState(linearId, sender, receiver, subject, newHash, encryptedPayload,
                senderKeyEnvelope, receiverKeyEnvelope, sentAt, status, participants);
    }

    @NotNull @Override public UniqueIdentifier getLinearId() { return linearId; }
    @NotNull @Override public List<AbstractParty> getParticipants() { return participants; }
    public Party getSender() { return sender; }
    public Party getReceiver() { return receiver; }
    public String getSubject() { return subject; }
    public String getContentHash() { return contentHash; }
    public String getEncryptedPayload() { return encryptedPayload; }
    public String getSenderKeyEnvelope() { return senderKeyEnvelope; }
    public String getReceiverKeyEnvelope() { return receiverKeyEnvelope; }
    public Instant getSentAt() { return sentAt; }
    public Status getStatus() { return status; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof SecureMessageState)) return false;
        SecureMessageState that = (SecureMessageState) o;
        return linearId.equals(that.linearId) && sender.equals(that.sender) && receiver.equals(that.receiver)
                && subject.equals(that.subject) && contentHash.equals(that.contentHash)
                && encryptedPayload.equals(that.encryptedPayload) && senderKeyEnvelope.equals(that.senderKeyEnvelope)
                && receiverKeyEnvelope.equals(that.receiverKeyEnvelope) && sentAt.equals(that.sentAt)
                && status == that.status && participants.equals(that.participants);
    }

    @Override
    public int hashCode() {
        return Objects.hash(linearId, sender, receiver, subject, contentHash, encryptedPayload, sentAt, status);
    }

    @Override
    public String toString() {
        return "SecureMessageState{" + linearId + ", " + sender.getName().getOrganisation() + " -> "
                + receiver.getName().getOrganisation() + ", subject='" + subject + "', status=" + status + "}";
    }
}
