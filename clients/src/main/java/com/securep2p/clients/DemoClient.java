package com.securep2p.clients;

import com.securep2p.crypto.SecureCrypto;
import com.securep2p.flows.*;
import com.securep2p.states.SecureMessageState;
import net.corda.client.rpc.CordaRPCClient;
import net.corda.client.rpc.CordaRPCConnection;
import net.corda.core.contracts.StateAndRef;
import net.corda.core.identity.CordaX500Name;
import net.corda.core.identity.Party;
import net.corda.core.messaging.CordaRPCOps;
import net.corda.core.node.NodeInfo;
import net.corda.core.node.services.Vault;
import net.corda.core.node.services.vault.QueryCriteria;
import net.corda.core.transactions.SignedTransaction;
import net.corda.core.utilities.NetworkHostAndPort;

import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.stream.Collectors;

/**
 * RPC demo client for "Secure Peer-to-Peer Communication between Enterprise Corda Nodes".
 * Author: Gagan N (24BTRBT013), CSE (Blockchain Technology), Semester V.
 *
 * Usage: DemoClient [all | networkmap | send | ack | privacy | untrusted | ping | bench]
 */
public class DemoClient {
    private static final String A = "O=EnterpriseA,L=Bengaluru,C=IN";
    private static final String B = "O=EnterpriseB,L=Mumbai,C=IN";
    private static final String C = "O=EnterpriseC,L=Delhi,C=IN";

    private final Map<String, CordaRPCConnection> connections = new LinkedHashMap<>();
    private final Map<String, CordaRPCOps> ops = new LinkedHashMap<>();

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0].toLowerCase() : "all";
        DemoClient demo = new DemoClient();
        try {
            demo.run(mode);
        } finally {
            demo.close();
        }
        System.exit(0);
    }

    private void run(String mode) throws Exception {
        banner("Secure P2P Communication between Enterprise Corda Nodes  |  Gagan N (24BTRBT013)");
        if (!mode.equals("bench")) connectAll();
        switch (mode) {
            case "networkmap": networkMap(); break;
            case "send": send(); break;
            case "ack": acknowledgeAndRead(); break;
            case "privacy": privacy(); break;
            case "untrusted": untrusted(); break;
            case "ping": ping(20); break;
            case "bench": bench(); break;
            default:
                networkMap();
                send();
                acknowledgeAndRead();
                privacy();
                untrusted();
                ping(20);
                bench();
        }
        System.out.println();
        System.out.println("Done.");
    }

    // ------------------------------------------------------------------------------------------ connection

    private void connectAll() {
        connect("EnterpriseA", "localhost:10006", "userA", "passA");
        connect("EnterpriseB", "localhost:10009", "userB", "passB");
        connect("EnterpriseC", "localhost:10012", "userC", "passC");
        System.out.println("Connected over RPC to: " + String.join(", ", ops.keySet()));
    }

    private void connect(String name, String address, String user, String pass) {
        CordaRPCConnection conn = new CordaRPCClient(NetworkHostAndPort.parse(address)).start(user, pass);
        connections.put(name, conn);
        ops.put(name, conn.getProxy());
    }

    private void close() {
        for (CordaRPCConnection c : connections.values()) {
            try { c.notifyServerAndClose(); } catch (Exception ignored) { }
        }
    }

    private Party party(String x500) {
        return ops.get("EnterpriseA").wellKnownPartyFromX500Name(CordaX500Name.parse(x500));
    }

    private static String org(Party p) { return p.getName().getOrganisation(); }

    // ------------------------------------------------------------------------------------------ steps

    private void networkMap() {
        section("1. NETWORK MAP (as seen by EnterpriseA)");
        List<NodeInfo> nodes = new ArrayList<>(ops.get("EnterpriseA").networkMapSnapshot());
        nodes.sort(Comparator.comparing(n -> n.getLegalIdentities().get(0).getName().toString()));
        Set<Party> notaries = new HashSet<>(ops.get("EnterpriseA").notaryIdentities());
        Table t = new Table("Node", "X.500 name", "P2P address", "Platform", "Role");
        for (NodeInfo n : nodes) {
            Party p = n.getLegalIdentities().get(0);
            t.row(p.getName().getOrganisation(), p.getName().toString(), n.getAddresses().get(0).toString(),
                    String.valueOf(n.getPlatformVersion()), notaries.contains(p) ? "Notary (non-validating)" : "Enterprise node");
        }
        t.print();
    }

    private static final String[][] MESSAGES = {
            {A, B, "PO-2026-0412 Purchase details",
                    "Purchase order PO-2026-0412: 500 units of industrial IoT sensors (model TS-40) at INR 1,250 per unit. Total INR 6,25,000. Delivery to the Mumbai warehouse by 15-Dec-2026."},
            {A, B, "MSA-2026 Contract terms",
                    "Master Service Agreement draft v3: payment within 45 days of invoice, 2% late fee per month, liability capped at 1x annual contract value, governing law Karnataka, India."},
            {A, B, "Q1-2027 Pricing revision",
                    "Confidential: volume discount of 7.5% for orders above 2,000 units in Q1 2027. Not to be shared with other suppliers."},
            {B, A, "INV-B-7781 Invoice",
                    "Invoice INV-B-7781 for PO-2026-0412: INR 6,25,000 + 18% GST = INR 7,37,500. Payment to HDFC current account ending 4421."},
    };

    private void send() throws Exception {
        section("2. SENDING ENCRYPTED MESSAGES (X25519 key exchange + AES-256-GCM + 2 signatures + notary)");
        Table t = new Table("#", "From", "To", "Subject", "Tx id", "Ciphertext (base64, stored on ledger)", "Flow ms");
        int i = 1;
        for (String[] m : MESSAGES) {
            CordaRPCOps from = ops.get(CordaX500Name.parse(m[0]).getOrganisation());
            long t0 = System.nanoTime();
            SignedTransaction stx = from.startFlowDynamic(SendSecureMessageFlow.class, party(m[1]), m[2], m[3])
                    .getReturnValue().get();
            long ms = (System.nanoTime() - t0) / 1_000_000;
            SecureMessageState s = (SecureMessageState) stx.getTx().getOutputs().get(0).getData();
            t.row(String.valueOf(i++), org(s.getSender()), org(s.getReceiver()), s.getSubject(),
                    stx.getId().toString().substring(0, 12) + "...", SecureCrypto.preview(s.getEncryptedPayload(), 36),
                    String.valueOf(ms));
        }
        t.print();
        System.out.println("Each transaction is signed by sender + receiver and notarised (time window). FinalityFlow sent it to the receiver only.");
    }

    private void acknowledgeAndRead() throws Exception {
        section("3. ACKNOWLEDGE (receiver decrypts, verifies SHA-256, then signs SENT -> ACKNOWLEDGED)");
        Table t = new Table("Receiver", "Subject", "From", "Ack tx id", "New status");
        for (String node : Arrays.asList("EnterpriseB", "EnterpriseA")) {
            CordaRPCOps rpc = ops.get(node);
            Party me = rpc.nodeInfo().getLegalIdentities().get(0);
            for (SecureMessageState s : states(rpc, Vault.StateStatus.UNCONSUMED)) {
                if (s.getReceiver().equals(me) && s.getStatus() == SecureMessageState.Status.SENT) {
                    SignedTransaction stx = rpc.startFlowDynamic(AcknowledgeMessageFlow.class, s.getLinearId())
                            .getReturnValue().get();
                    SecureMessageState out = (SecureMessageState) stx.getTx().getOutputs().get(0).getData();
                    t.row(node, s.getSubject(), org(s.getSender()), stx.getId().toString().substring(0, 12) + "...",
                            out.getStatus().name());
                }
            }
        }
        t.print();

        section("4. READ + DECRYPT ON EnterpriseB (ReadMessageFlow, local only)");
        CordaRPCOps rpcB = ops.get("EnterpriseB");
        SecureMessageState target = states(rpcB, Vault.StateStatus.UNCONSUMED).stream()
                .filter(s -> s.getSubject().startsWith("PO-2026-0412")).findFirst()
                .orElse(states(rpcB, Vault.StateStatus.UNCONSUMED).get(0));
        DecryptedMessage d = rpcB.startFlowDynamic(ReadMessageFlow.class, target.getLinearId()).getReturnValue().get();
        kv("Message id", d.getLinearId());
        kv("From -> To", CordaX500Name.parse(d.getSender()).getOrganisation() + " -> " + CordaX500Name.parse(d.getReceiver()).getOrganisation());
        kv("Subject", d.getSubject());
        kv("Status", d.getStatus());
        kv("Ciphertext (vault)", SecureCrypto.preview(target.getEncryptedPayload(), 60));
        kv("Decrypted body", d.getBody());
        kv("contentHash (ledger)", d.getContentHash());
        kv("SHA-256(decrypted)", d.getComputedHash());
        kv("Integrity check", d.isIntegrityVerified() ? "PASSED (hashes match, GCM tag valid)" : "FAILED");
        kv("Decrypt time", d.getDecryptMicros() + " us (envelope unwrap + AES-GCM)");
    }

    private void privacy() {
        section("5. PRIVACY - VAULT CONTENTS PER NODE (need-to-know)");
        Table t = new Table("Node", "SecureMessageStates (all)", "Unconsumed", "SENT", "ACKNOWLEDGED", "Sees plaintext?");
        for (Map.Entry<String, CordaRPCOps> e : ops.entrySet()) {
            List<SecureMessageState> all = states(e.getValue(), Vault.StateStatus.ALL);
            List<SecureMessageState> un = states(e.getValue(), Vault.StateStatus.UNCONSUMED);
            long sent = un.stream().filter(s -> s.getStatus() == SecureMessageState.Status.SENT).count();
            long ack = un.stream().filter(s -> s.getStatus() == SecureMessageState.Status.ACKNOWLEDGED).count();
            t.row(e.getKey(), String.valueOf(all.size()), String.valueOf(un.size()), String.valueOf(sent),
                    String.valueOf(ack), all.isEmpty() ? "No (nothing stored)" : "Only via ReadMessageFlow");
        }
        t.print();
        System.out.println("EnterpriseC = 0: it was never a participant, so FinalityFlow never sent it any transaction.");
        System.out.println("The vault only stores ciphertext; the notary (non-validating) only saw a filtered transaction.");
    }

    private void untrusted() {
        section("6. TRUST POLICY - EnterpriseC tries to send to EnterpriseA (C is not in A's trustedPeers)");
        try {
            ops.get("EnterpriseC").startFlowDynamic(SendSecureMessageFlow.class, party(A),
                    "Unsolicited offer", "Hello from EnterpriseC").getReturnValue().get();
            System.out.println("UNEXPECTED: message was accepted");
        } catch (ExecutionException | InterruptedException ex) {
            Throwable cause = ex.getCause() != null ? ex.getCause() : ex;
            kv("Result", "REJECTED by EnterpriseA's responder flow");
            kv("Exception", cause.getClass().getSimpleName());
            kv("Message", cause.getMessage());
        }
        kv("A's vault after attempt", states(ops.get("EnterpriseA"), Vault.StateStatus.ALL).stream()
                .filter(s -> s.getSender().getName().getOrganisation().equals("EnterpriseC")).count() + " messages from EnterpriseC");
    }

    private void ping(int n) throws Exception {
        section("7. P2P LATENCY - PingPeerFlow EnterpriseA -> EnterpriseB (" + n + " round trips over TLS/AMQP)");
        CordaRPCOps rpcA = ops.get("EnterpriseA");
        Party b = party(B);
        List<Double> samples = new ArrayList<>();
        StringBuilder line = new StringBuilder();
        for (int i = 1; i <= n; i++) {
            double ms = rpcA.startFlowDynamic(PingPeerFlow.class, b).getReturnValue().get();
            samples.add(ms);
            line.append(String.format("#%02d %7.2f ms   ", i, ms));
            if (i % 5 == 0) { System.out.println(line); line.setLength(0); }
        }
        if (line.length() > 0) System.out.println(line);
        List<Double> sorted = samples.stream().sorted().collect(Collectors.toList());
        double avg = samples.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double median = sorted.size() % 2 == 0 ? (sorted.get(n / 2 - 1) + sorted.get(n / 2)) / 2 : sorted.get(n / 2);
        double sd = Math.sqrt(samples.stream().mapToDouble(x -> (x - avg) * (x - avg)).sum() / samples.size());
        Table t = new Table("Samples", "Average ms", "Min ms", "Max ms", "Median ms", "Std dev ms");
        t.row(String.valueOf(n), f(avg), f(sorted.get(0)), f(sorted.get(n - 1)), f(median), f(sd));
        t.print();
        System.out.println("(The first ping includes session set-up; later pings reuse the established AMQP/TLS bridge.)");
    }

    private void bench() {
        section("8. ENCRYPTION OVERHEAD (local micro-benchmark, 3000 iterations per size after JIT warm-up)");
        int iters = 3000;
        // Key agreement cost
        for (int w = 0; w < 3000; w++) {
            byte[][] x = SecureCrypto.generateEphemeralX25519();
            byte[][] y = SecureCrypto.generateEphemeralX25519();
            SecureCrypto.deriveMessageKey(x[1], y[0], "warmup");
        }
        long t0 = System.nanoTime();
        for (int w = 0; w < iters; w++) {
            byte[][] x = SecureCrypto.generateEphemeralX25519();
            byte[][] y = SecureCrypto.generateEphemeralX25519();
            SecureCrypto.deriveMessageKey(x[1], y[0], "bench");
        }
        double kexUs = (System.nanoTime() - t0) / 1000.0 / iters;
        kv("X25519 keygen x2 + ECDH + HKDF", f(kexUs) + " us per message");

        Table t = new Table("Body size", "Ciphertext (base64) size", "Size overhead", "Encrypt us", "Decrypt us", "SHA-256 us");
        byte[] key = new byte[32];
        new Random(7).nextBytes(key);
        // global warm-up across all sizes so the JIT has compiled AES-GCM / SHA-256 intrinsics before timing
        for (int round = 0; round < 3; round++) {
            for (int size : new int[]{256, 1024, 4096, 16384, 65536}) {
                byte[] body = new byte[size];
                for (int w = 0; w < 1500; w++) {
                    try { SecureCrypto.decrypt(key, SecureCrypto.encrypt(key, body, null), null); } catch (Exception ignored) { }
                    SecureCrypto.sha256Hex(body);
                }
            }
        }
        for (int size : new int[]{256, 1024, 4096, 16384, 65536}) {
            byte[] body = new byte[size];
            new Random(size).nextBytes(body);
            String ct = SecureCrypto.encrypt(key, body, null);
            long e0 = System.nanoTime();
            for (int k = 0; k < iters; k++) ct = SecureCrypto.encrypt(key, body, null);
            double enc = (System.nanoTime() - e0) / 1000.0 / iters;
            long d0 = System.nanoTime();
            for (int k = 0; k < iters; k++) {
                try { SecureCrypto.decrypt(key, ct, null); } catch (Exception ex) { throw new RuntimeException(ex); }
            }
            double dec = (System.nanoTime() - d0) / 1000.0 / iters;
            long h0 = System.nanoTime();
            for (int k = 0; k < iters; k++) SecureCrypto.sha256Hex(body);
            double h = (System.nanoTime() - h0) / 1000.0 / iters;
            t.row(size + " B", ct.length() + " B", String.format("+%.1f%%", 100.0 * (ct.length() - size) / size),
                    f(enc), f(dec), f(h));
        }
        t.print();
        System.out.println("Overhead per message = 12-byte IV + 16-byte GCM tag, then base64 (x4/3) for the String field.");
    }

    // ------------------------------------------------------------------------------------------ helpers

    private static List<SecureMessageState> states(CordaRPCOps rpc, Vault.StateStatus status) {
        return rpc.vaultQueryByCriteria(new QueryCriteria.VaultQueryCriteria(status), SecureMessageState.class)
                .getStates().stream().map(StateAndRef::getState).map(s -> s.getData()).collect(Collectors.toList());
    }

    private static String f(double d) { return String.format("%.2f", d); }

    private static void banner(String s) {
        String line = repeat('=', s.length() + 4);
        System.out.println(line);
        System.out.println("  " + s);
        System.out.println(line);
    }

    private static void section(String s) {
        System.out.println();
        System.out.println(">> " + s);
        System.out.println(repeat('-', Math.min(110, s.length() + 3)));
    }

    private static void kv(String k, String v) { System.out.printf("  %-26s : %s%n", k, v); }

    private static String repeat(char c, int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.append(c);
        return sb.toString();
    }

    /** Minimal ASCII table printer. */
    static class Table {
        private final String[] headers;
        private final List<String[]> rows = new ArrayList<>();

        Table(String... headers) { this.headers = headers; }

        void row(String... cells) { rows.add(cells); }

        void print() {
            int[] w = new int[headers.length];
            for (int i = 0; i < headers.length; i++) w[i] = headers[i].length();
            for (String[] r : rows) for (int i = 0; i < r.length; i++) w[i] = Math.max(w[i], r[i].length());
            StringBuilder sep = new StringBuilder("+");
            for (int x : w) sep.append(repeat('-', x + 2)).append('+');
            System.out.println(sep);
            System.out.println(line(headers, w));
            System.out.println(sep);
            for (String[] r : rows) System.out.println(line(r, w));
            System.out.println(sep);
        }

        private static String line(String[] cells, int[] w) {
            StringBuilder sb = new StringBuilder("|");
            for (int i = 0; i < w.length; i++) {
                String c = i < cells.length ? cells[i] : "";
                sb.append(' ').append(c).append(repeat(' ', w[i] - c.length() + 1)).append('|');
            }
            return sb.toString();
        }
    }
}
