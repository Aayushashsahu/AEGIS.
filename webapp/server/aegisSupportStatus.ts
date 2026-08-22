/**
 * Read-only support ledger state. This module has no Bright Data client,
 * provider credential, mutation path, mailbox access, or polling behavior.
 */
export type AegisSupportStatus = {
  source: "BRIGHT_DATA_SUPPORT";
  status: "DIAGNOSIS_PENDING" | "DIAGNOSIS_RECEIVED";
  diagnosis: string | null;
  providerError: string | null;
  recommendedAction: string;
  evidenceReference: string;
  providerCalls: 0;
  providerMutations: 0;
  retries: 0;
};

export function getAegisSupportStatus(): AegisSupportStatus {
  return {
    source: "BRIGHT_DATA_SUPPORT",
    status: "DIAGNOSIS_PENDING",
    diagnosis: null,
    providerError: null,
    recommendedAction: "Provider lane frozen pending a real Bright Data support response.",
    evidenceReference: "support_request_sent_record.md",
    providerCalls: 0,
    providerMutations: 0,
    retries: 0,
  };
}
