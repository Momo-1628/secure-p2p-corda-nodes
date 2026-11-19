package com.securep2p.flows;

import co.paralleluniverse.fibers.Suspendable;
import com.securep2p.policy.TrustedPeerPolicy;
import net.corda.core.flows.*;
import net.corda.core.identity.Party;

/**
 * Raw P2P round trip: session.sendAndReceive of a nonce over the TLS/AMQP link. Returns the latency in milliseconds
 * (measured inside the initiating flow, so it excludes RPC overhead).
 *
 * Author: Gagan N (24BTRBT013)
 */
@InitiatingFlow
@StartableByRPC
public class PingPeerFlow extends FlowLogic<Double> {
    private final Party peer;

    public PingPeerFlow(Party peer) { this.peer = peer; }

    @Suspendable
    @Override
    public Double call() throws FlowException {
        TrustedPeerPolicy.requireTrusted(getServiceHub(), peer);
        FlowSession session = initiateFlow(peer);
        long nonce = System.nanoTime();
        long t0 = System.nanoTime();
        Long echo = session.sendAndReceive(Long.class, nonce).unwrap(v -> v);
        long t1 = System.nanoTime();
        if (echo != nonce + 1) throw new FlowException("Ping reply did not match the nonce");
        return (t1 - t0) / 1_000_000.0;
    }

    @InitiatedBy(PingPeerFlow.class)
    public static class Responder extends FlowLogic<Void> {
        private final FlowSession session;

        public Responder(FlowSession session) { this.session = session; }

        @Suspendable
        @Override
        public Void call() throws FlowException {
            TrustedPeerPolicy.requireTrusted(getServiceHub(), session.getCounterparty());
            long nonce = session.receive(Long.class).unwrap(v -> v);
            session.send(nonce + 1);
            return null;
        }
    }
}
