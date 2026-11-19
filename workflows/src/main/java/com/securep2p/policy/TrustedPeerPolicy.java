package com.securep2p.policy;

import net.corda.core.cordapp.CordappConfig;
import net.corda.core.flows.FlowException;
import net.corda.core.identity.CordaX500Name;
import net.corda.core.identity.Party;
import net.corda.core.node.ServiceHub;

import java.util.*;

/**
 * Trusted-peer allow-list, read from this node's CorDapp configuration:
 *
 *   build/nodes/EnterpriseA/cordapps/config/workflows-0.1.conf
 *     trustedPeers = ["O=EnterpriseB,L=Mumbai,C=IN"]
 *
 * Default-deny: if the key is missing, no peer is trusted. Both initiators and responders call
 * {@link #requireTrusted}, so a node neither opens nor accepts sessions with an unlisted counterparty.
 *
 * Author: Gagan N (24BTRBT013)
 */
public final class TrustedPeerPolicy {
    public static final String CONFIG_KEY = "trustedPeers";

    private TrustedPeerPolicy() { }

    public static Set<CordaX500Name> trustedPeers(ServiceHub serviceHub) {
        Set<CordaX500Name> result = new LinkedHashSet<>();
        CordappConfig cfg = serviceHub.getAppContext().getConfig();
        if (!cfg.exists(CONFIG_KEY)) return result;
        Object raw = cfg.get(CONFIG_KEY);
        List<String> names = new ArrayList<>();
        if (raw instanceof Collection) {
            for (Object o : (Collection<?>) raw) names.add(String.valueOf(o));
        } else if (raw != null) {
            names.addAll(Arrays.asList(raw.toString().split(";")));
        }
        for (String n : names) {
            if (!n.trim().isEmpty()) result.add(CordaX500Name.parse(n.trim()));
        }
        return result;
    }

    public static boolean isTrusted(ServiceHub serviceHub, Party peer) {
        return trustedPeers(serviceHub).contains(peer.getName());
    }

    public static void requireTrusted(ServiceHub serviceHub, Party peer) throws FlowException {
        if (!isTrusted(serviceHub, peer)) {
            throw new FlowException("Untrusted peer: " + peer.getName()
                    + " is not in the trustedPeers list of " + serviceHub.getMyInfo().getLegalIdentities().get(0).getName());
        }
    }
}
