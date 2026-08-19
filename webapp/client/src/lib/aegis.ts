/**
 * Tensioned Signal Web: local browser state never impersonates a provider or AEGIS evidence record.
 * This module only holds user-authored configuration until a documented API adapter is connected.
 */
export type FieldType = "text" | "number" | "url" | "boolean" | "date";

export type FieldDefinition = {
  id: string;
  name: string;
  type: FieldType;
  description: string;
};

export type InvariantDefinition = {
  id: string;
  expression: string;
};

export type ReliabilityCase = {
  id: string;
  name: string;
  targetUrl: string;
  fields: FieldDefinition[];
  invariants: InvariantDefinition[];
  createdAt: string;
};

export const fieldTypes: FieldType[] = ["text", "number", "url", "boolean", "date"];

export const createId = (prefix: string) =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? `${prefix}_${crypto.randomUUID()}`
    : `${prefix}_${Math.random().toString(36).slice(2, 10)}`;

export function hostFromTarget(target: string) {
  try {
    return new URL(target).hostname.replace(/^www\./, "");
  } catch {
    return target;
  }
}

export const localCaseStorageKey = "aegis.reliability.case.v1";
