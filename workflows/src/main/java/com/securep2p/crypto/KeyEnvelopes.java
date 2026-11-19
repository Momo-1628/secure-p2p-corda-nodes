package com.securep2p.crypto;

import net.corda.core.contracts.UniqueIdentifier;
import net.corda.core.crypto.DigitalSignature;
import net.corda.core.node.ServiceHub;

import java.security.PublicKey;

/**
 * Wraps / unwraps a per-message AES key so that only *this* node can recover it later.
 *
 * The key-encryption key (KEK) is never stored. It is re-derived on demand:
 *     KEK = HKDF( Ed25519-sign(nodeIdentityKey, "securep2p-kek|" + linearId) )
 * Ed25519 signatures are deterministic, so the same node always derives the same KEK, while nobody without the
 * node's private identity key (kept in nodekeystore.jks, or an HSM in production) can. The vault and any vault
 * backup therefore only contain ciphertext and wrapped keys.
 *
 * Author: Gagan N (24BTRBT013)
 */
public final class KeyEnvelopes {
    private KeyEnvelopes() { }

    private static byte[] kek(ServiceHub serviceHub, PublicKey ourKey, UniqueIdentifier linearId) {
        byte[] label = SecureCrypto.utf8("securep2p-kek|" + linearId.getId());
        DigitalSignature.WithKey sig = serviceHub.getKeyManagementService().sign(label, ourKey);
        return SecureCrypto.deriveKek(sig.getBytes(), linearId.getId().toString());
    }

    public static String wrap(ServiceHub serviceHub, PublicKey ourKey, UniqueIdentifier linearId, byte[] messageKey) {
        byte[] kek = kek(serviceHub, ourKey, linearId);
        try {
            return SecureCrypto.encrypt(kek, messageKey, SecureCrypto.utf8("envelope|" + linearId.getId()));
        } finally {
            java.util.Arrays.fill(kek, (byte) 0);
        }
    }

    public static byte[] unwrap(ServiceHub serviceHub, PublicKey ourKey, UniqueIdentifier linearId, String envelope)
            throws SecureCrypto.IntegrityException {
        byte[] kek = kek(serviceHub, ourKey, linearId);
        try {
            return SecureCrypto.decrypt(kek, envelope, SecureCrypto.utf8("envelope|" + linearId.getId()));
        } finally {
            java.util.Arrays.fill(kek, (byte) 0);
        }
    }

    /** Associated data that binds a ciphertext to its message metadata. */
    public static byte[] payloadAad(UniqueIdentifier linearId, String subject, String sender, String receiver) {
        return SecureCrypto.utf8(linearId.getId() + "|" + subject + "|" + sender + "|" + receiver);
    }
}
