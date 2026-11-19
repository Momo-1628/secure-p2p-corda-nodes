package com.securep2p.crypto;

import javax.crypto.AEADBadTagException;
import javax.crypto.Cipher;
import javax.crypto.KeyAgreement;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

/**
 * Application-layer cryptography for secure P2P messages.
 *
 *  - X25519 ephemeral ECDH to agree a per-message secret between the two nodes (over the flow session)
 *  - HKDF-SHA256 to turn that secret into a 256-bit AES key
 *  - AES-256-GCM (12-byte random IV, 128-bit tag) for the message body and for key envelopes
 *  - SHA-256 for the content hash (tamper evidence)
 *
 * All methods are plain (non-suspendable) static helpers, so that no Cipher / PrivateKey object is ever held
 * on a flow's stack across a checkpoint: flows only keep byte[] / String values.
 *
 * Author: Gagan N (24BTRBT013)
 */
public final class SecureCrypto {
    public static final int AES_KEY_BYTES = 32;     // AES-256
    public static final int GCM_IV_BYTES = 12;
    public static final int GCM_TAG_BITS = 128;
    private static final SecureRandom RNG = new SecureRandom();

    private SecureCrypto() { }

    /** Thrown when decryption or the SHA-256 integrity check fails. */
    public static class IntegrityException extends Exception {
        public IntegrityException(String msg) { super(msg); }
    }

    // ------------------------------------------------------------------ X25519 key exchange

    /** Returns { X.509-encoded public key, PKCS#8-encoded private key } of a fresh ephemeral X25519 key pair. */
    public static byte[][] generateEphemeralX25519() {
        try {
            KeyPairGenerator kpg = KeyPairGenerator.getInstance("X25519");
            KeyPair kp = kpg.generateKeyPair();
            return new byte[][]{kp.getPublic().getEncoded(), kp.getPrivate().getEncoded()};
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("X25519 not available", e);
        }
    }

    /** ECDH(ourPrivate, theirPublic) -> HKDF-SHA256 -> 32-byte AES key bound to the given context string. */
    public static byte[] deriveMessageKey(byte[] ourPrivatePkcs8, byte[] theirPublicX509, String context) {
        try {
            KeyFactory kf = KeyFactory.getInstance("X25519");
            PrivateKey priv = kf.generatePrivate(new PKCS8EncodedKeySpec(ourPrivatePkcs8));
            PublicKey pub = kf.generatePublic(new X509EncodedKeySpec(theirPublicX509));
            KeyAgreement ka = KeyAgreement.getInstance("X25519");
            ka.init(priv);
            ka.doPhase(pub, true);
            byte[] shared = ka.generateSecret();
            return hkdfSha256(shared, "securep2p-ecdh-v1".getBytes(StandardCharsets.UTF_8),
                    context.getBytes(StandardCharsets.UTF_8), AES_KEY_BYTES);
        } catch (GeneralSecurityException e) {
            throw new IllegalArgumentException("ECDH key agreement failed: " + e.getMessage(), e);
        }
    }

    /** Derives a node-local key-encryption key from (deterministic Ed25519) signature bytes. */
    public static byte[] deriveKek(byte[] identitySignature, String context) {
        return hkdfSha256(identitySignature, "securep2p-kek-v1".getBytes(StandardCharsets.UTF_8),
                context.getBytes(StandardCharsets.UTF_8), AES_KEY_BYTES);
    }

    // ------------------------------------------------------------------ AES-256-GCM

    /** Encrypts and returns base64( IV || ciphertext || tag ). */
    public static String encrypt(byte[] key, byte[] plaintext, byte[] aad) {
        try {
            byte[] iv = new byte[GCM_IV_BYTES];
            RNG.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            if (aad != null) cipher.updateAAD(aad);
            byte[] ct = cipher.doFinal(plaintext);
            return Base64.getEncoder().encodeToString(ByteBuffer.allocate(iv.length + ct.length).put(iv).put(ct).array());
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("AES-GCM encryption failed", e);
        }
    }

    /** Decrypts base64( IV || ciphertext || tag ); throws IntegrityException if the GCM tag does not verify. */
    public static byte[] decrypt(byte[] key, String payloadB64, byte[] aad) throws IntegrityException {
        byte[] all;
        try {
            all = Base64.getDecoder().decode(payloadB64);
        } catch (IllegalArgumentException e) {
            throw new IntegrityException("payload is not valid base64");
        }
        if (all.length < GCM_IV_BYTES + GCM_TAG_BITS / 8) throw new IntegrityException("payload too short");
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"),
                    new GCMParameterSpec(GCM_TAG_BITS, all, 0, GCM_IV_BYTES));
            if (aad != null) cipher.updateAAD(aad);
            return cipher.doFinal(all, GCM_IV_BYTES, all.length - GCM_IV_BYTES);
        } catch (AEADBadTagException e) {
            throw new IntegrityException("AES-GCM authentication tag mismatch (ciphertext was modified)");
        } catch (GeneralSecurityException e) {
            throw new IntegrityException("decryption failed: " + e.getMessage());
        }
    }

    // ------------------------------------------------------------------ hashing / HKDF

    public static String sha256Hex(byte[] data) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(data);
            StringBuilder sb = new StringBuilder(64);
            for (byte x : d) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** RFC 5869 HKDF with HMAC-SHA256. */
    public static byte[] hkdfSha256(byte[] ikm, byte[] salt, byte[] info, int length) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(salt, "HmacSHA256"));
            byte[] prk = mac.doFinal(ikm);
            mac.init(new SecretKeySpec(prk, "HmacSHA256"));
            ByteArrayOutputStream okm = new ByteArrayOutputStream();
            byte[] t = new byte[0];
            for (int i = 1; okm.size() < length; i++) {
                mac.update(t);
                mac.update(info);
                mac.update((byte) i);
                t = mac.doFinal();
                okm.write(t, 0, t.length);
            }
            byte[] out = new byte[length];
            System.arraycopy(okm.toByteArray(), 0, out, 0, length);
            return out;
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }

    public static byte[] utf8(String s) { return s.getBytes(StandardCharsets.UTF_8); }

    /** Short preview of a base64 value for display. */
    public static String preview(String b64, int n) {
        return b64.length() <= n ? b64 : b64.substring(0, n) + "...";
    }
}
