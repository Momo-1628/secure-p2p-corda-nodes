package com.securep2p.flows;

import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.serialization.CordaSerializable;

/** Messages exchanged over the flow session during the in-flow X25519 key agreement. */
public final class KeyExchangeMessages {
    private KeyExchangeMessages() { }

    /** Initiator -> responder: the message id and the initiator's ephemeral X25519 public key. */
    @CordaSerializable
    public static class Init {
        private final UniqueIdentifier linearId;
        private final byte[] ephemeralPublicKey;

        public Init(UniqueIdentifier linearId, byte[] ephemeralPublicKey) {
            this.linearId = linearId;
            this.ephemeralPublicKey = ephemeralPublicKey;
        }
        public UniqueIdentifier getLinearId() { return linearId; }
        public byte[] getEphemeralPublicKey() { return ephemeralPublicKey; }
    }

    /** Responder -> initiator: the responder's ephemeral public key and its own wrapped copy of the derived key. */
    @CordaSerializable
    public static class Reply {
        private final byte[] ephemeralPublicKey;
        private final String receiverKeyEnvelope;

        public Reply(byte[] ephemeralPublicKey, String receiverKeyEnvelope) {
            this.ephemeralPublicKey = ephemeralPublicKey;
            this.receiverKeyEnvelope = receiverKeyEnvelope;
        }
        public byte[] getEphemeralPublicKey() { return ephemeralPublicKey; }
        public String getReceiverKeyEnvelope() { return receiverKeyEnvelope; }
    }
}
