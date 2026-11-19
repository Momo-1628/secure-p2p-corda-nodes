package com.securep2p.contracts;

import com.securep2p.states.SecureMessageState;
import net.corda.core.contracts.CommandData;
import net.corda.core.contracts.CommandWithParties;
import net.corda.core.contracts.Contract;
import net.corda.core.contracts.TimeWindow;
import net.corda.core.transactions.LedgerTransaction;
import org.jetbrains.annotations.NotNull;

import java.security.PublicKey;
import java.util.List;
import java.util.regex.Pattern;

import static net.corda.core.contracts.ContractsDSL.requireSingleCommand;
import static net.corda.core.contracts.ContractsDSL.requireThat;

/**
 * Rules for the SecureMessageState lifecycle: SENT -> ACKNOWLEDGED.
 * Author: Gagan N (24BTRBT013)
 */
public class SecureMessageContract implements Contract {
    public static final String ID = "com.securep2p.contracts.SecureMessageContract";

    private static final Pattern SHA256_HEX = Pattern.compile("^[0-9a-f]{64}$");

    public interface Commands extends CommandData {
        class Send implements Commands { }
        class Acknowledge implements Commands { }
    }

    @Override
    public void verify(@NotNull LedgerTransaction tx) {
        CommandWithParties<Commands> command = requireSingleCommand(tx.getCommands(), Commands.class);
        List<PublicKey> signers = command.getSigners();

        if (command.getValue() instanceof Commands.Send) {
            verifySend(tx, signers);
        } else if (command.getValue() instanceof Commands.Acknowledge) {
            verifyAcknowledge(tx, signers);
        } else {
            throw new IllegalArgumentException("Unrecognised command.");
        }
    }

    private void verifySend(LedgerTransaction tx, List<PublicKey> signers) {
        requireThat(req -> {
            req.using("Send must have no inputs.", tx.getInputStates().isEmpty());
            req.using("Send must have exactly one output.", tx.getOutputStates().size() == 1);
            req.using("The output must be a SecureMessageState.",
                    tx.getOutputStates().get(0) instanceof SecureMessageState);
            SecureMessageState out = (SecureMessageState) tx.getOutputStates().get(0);

            req.using("A new message must have status SENT.", out.getStatus() == SecureMessageState.Status.SENT);
            req.using("Sender and receiver must be different parties.", !out.getSender().equals(out.getReceiver()));
            req.using("Subject must not be empty.", out.getSubject() != null && !out.getSubject().trim().isEmpty());
            req.using("contentHash must be a 64-character lowercase SHA-256 hex string.",
                    out.getContentHash() != null && SHA256_HEX.matcher(out.getContentHash()).matches());
            req.using("encryptedPayload must not be empty.",
                    out.getEncryptedPayload() != null && !out.getEncryptedPayload().isEmpty());
            req.using("Both key envelopes must be present.",
                    notEmpty(out.getSenderKeyEnvelope()) && notEmpty(out.getReceiverKeyEnvelope()));
            req.using("There must be exactly 2 participants.", out.getParticipants().size() == 2);
            req.using("The participants must be exactly the sender and the receiver.",
                    out.getParticipants().contains(out.getSender()) && out.getParticipants().contains(out.getReceiver()));
            req.using("The sender must sign.", signers.contains(out.getSender().getOwningKey()));
            req.using("The receiver must sign.", signers.contains(out.getReceiver().getOwningKey()));

            TimeWindow tw = tx.getTimeWindow();
            req.using("Send must carry a notarised time window.", tw != null);
            req.using("sentAt must fall inside the transaction time window.", tw.contains(out.getSentAt()));
            return null;
        });
    }

    private void verifyAcknowledge(LedgerTransaction tx, List<PublicKey> signers) {
        requireThat(req -> {
            req.using("Acknowledge must consume exactly one input.", tx.getInputStates().size() == 1);
            req.using("Acknowledge must produce exactly one output.", tx.getOutputStates().size() == 1);
            req.using("Input must be a SecureMessageState.", tx.getInputStates().get(0) instanceof SecureMessageState);
            req.using("Output must be a SecureMessageState.", tx.getOutputStates().get(0) instanceof SecureMessageState);
            SecureMessageState in = (SecureMessageState) tx.getInputStates().get(0);
            SecureMessageState out = (SecureMessageState) tx.getOutputStates().get(0);

            req.using("Input status must be SENT.", in.getStatus() == SecureMessageState.Status.SENT);
            req.using("Output status must be ACKNOWLEDGED.", out.getStatus() == SecureMessageState.Status.ACKNOWLEDGED);
            req.using("linearId must not change.", in.getLinearId().equals(out.getLinearId()));
            req.using("Parties must not change.",
                    in.getSender().equals(out.getSender()) && in.getReceiver().equals(out.getReceiver())
                            && in.getParticipants().equals(out.getParticipants()));
            req.using("Message content must not change.",
                    in.getSubject().equals(out.getSubject()) && in.getContentHash().equals(out.getContentHash())
                            && in.getEncryptedPayload().equals(out.getEncryptedPayload())
                            && in.getSenderKeyEnvelope().equals(out.getSenderKeyEnvelope())
                            && in.getReceiverKeyEnvelope().equals(out.getReceiverKeyEnvelope())
                            && in.getSentAt().equals(out.getSentAt()));
            req.using("The receiver must sign the acknowledgement.", signers.contains(out.getReceiver().getOwningKey()));
            return null;
        });
    }

    private static boolean notEmpty(String s) { return s != null && !s.isEmpty(); }
}
