package com.securep2p.flows;

import net.corda.core.serialization.CordaSerializable;

/** Result of {@link ReadMessageFlow}: the decrypted body plus the integrity-check evidence. */
@CordaSerializable
public class DecryptedMessage {
    private final String linearId;
    private final String sender;
    private final String receiver;
    private final String subject;
    private final String body;
    private final String contentHash;
    private final String computedHash;
    private final String status;
    private final boolean integrityVerified;
    private final long decryptMicros;

    public DecryptedMessage(String linearId, String sender, String receiver, String subject, String body,
                            String contentHash, String computedHash, String status, boolean integrityVerified,
                            long decryptMicros) {
        this.linearId = linearId;
        this.sender = sender;
        this.receiver = receiver;
        this.subject = subject;
        this.body = body;
        this.contentHash = contentHash;
        this.computedHash = computedHash;
        this.status = status;
        this.integrityVerified = integrityVerified;
        this.decryptMicros = decryptMicros;
    }

    public String getLinearId() { return linearId; }
    public String getSender() { return sender; }
    public String getReceiver() { return receiver; }
    public String getSubject() { return subject; }
    public String getBody() { return body; }
    public String getContentHash() { return contentHash; }
    public String getComputedHash() { return computedHash; }
    public String getStatus() { return status; }
    public boolean isIntegrityVerified() { return integrityVerified; }
    public long getDecryptMicros() { return decryptMicros; }
}
