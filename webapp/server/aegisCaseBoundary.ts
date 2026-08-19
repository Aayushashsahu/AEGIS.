import type { ApiField, CreateCaseInput } from "./aegisCases";

const MAX_URL_LENGTH = 2_048;
const MAX_NAME_LENGTH = 120;
const MAX_DESCRIPTION_LENGTH = 1_000;
const MAX_COLLECTOR_ID_LENGTH = 128;
const MAX_FIELDS = 20;
const MAX_FIELD_NAME_LENGTH = 64;
const MAX_FIELD_DESCRIPTION_LENGTH = 280;
const MAX_INVARIANTS = 20;
const MAX_INVARIANT_LENGTH = 240;
const MAX_PAYLOAD_BYTES = 12_000;
const MAX_CREATES_PER_WINDOW = 5;
const WINDOW_MS = 60_000;

export class CaseBoundaryError extends Error {
  constructor(public readonly code: string, message: string) { super(message); this.name = "CaseBoundaryError"; }
}

function boundedText(value: string | undefined, maxLength: number, label: string): string | undefined {
  if (value === undefined) return undefined;
  const normalized = value.trim();
  if (normalized.length > maxLength) throw new CaseBoundaryError("AEGIS_CASE_INPUT_TOO_LARGE", `${label} exceeds its maximum length.`);
  return normalized || undefined;
}

function normalizeUrl(value: string): string {
  if (value.length > MAX_URL_LENGTH) throw new CaseBoundaryError("AEGIS_CASE_INPUT_TOO_LARGE", "Target URL exceeds its maximum length.");
  let url: URL;
  try { url = new URL(value.trim()); } catch { throw new CaseBoundaryError("AEGIS_CASE_URL_INVALID", "Target URL must be an absolute HTTP or HTTPS URL."); }
  if (!/^https?:$/.test(url.protocol) || url.username || url.password) throw new CaseBoundaryError("AEGIS_CASE_URL_INVALID", "Target URL must be an absolute HTTP or HTTPS URL without credentials.");
  url.hash = "";
  url.hostname = url.hostname.toLowerCase();
  const parameters = Array.from(url.searchParams.entries()).sort(([a, av], [b, bv]) => a.localeCompare(b) || av.localeCompare(bv));
  url.search = "";
  for (const [key, parameter] of parameters) url.searchParams.append(key, parameter);
  if (url.pathname !== "/" && url.pathname.endsWith("/")) url.pathname = url.pathname.slice(0, -1);
  return url.toString();
}

export function normalizeCreateCaseInput(input: CreateCaseInput): CreateCaseInput {
  const targetUrl = normalizeUrl(input.targetUrl);
  if (!Array.isArray(input.fields) || input.fields.length < 1 || input.fields.length > MAX_FIELDS) throw new CaseBoundaryError("AEGIS_CASE_FIELD_LIMIT", `Provide between 1 and ${MAX_FIELDS} fields.`);
  if (!Array.isArray(input.invariants) || input.invariants.length > MAX_INVARIANTS) throw new CaseBoundaryError("AEGIS_CASE_INVARIANT_LIMIT", `Provide at most ${MAX_INVARIANTS} invariants.`);
  const seenFields = new Set<string>();
  const fields = input.fields.map((field): ApiField => {
    const name = boundedText(field.name, MAX_FIELD_NAME_LENGTH, "Field name");
    const description = boundedText(field.description, MAX_FIELD_DESCRIPTION_LENGTH, "Field description") ?? "";
    if (!name) throw new CaseBoundaryError("AEGIS_CASE_FIELD_INVALID", "Field name is required.");
    const key = name.toLowerCase();
    if (seenFields.has(key)) throw new CaseBoundaryError("AEGIS_CASE_FIELD_DUPLICATE", "Field names must be unique.");
    seenFields.add(key);
    return { name, type: field.type, description };
  });
  const invariants = input.invariants.map((invariant) => {
    const normalized = boundedText(invariant, MAX_INVARIANT_LENGTH, "Invariant");
    if (!normalized) throw new CaseBoundaryError("AEGIS_CASE_INVARIANT_INVALID", "Invariant cannot be empty.");
    return normalized;
  });
  const normalized: CreateCaseInput = { targetUrl, fields, invariants, name: boundedText(input.name, MAX_NAME_LENGTH, "Case name"), collectorId: boundedText(input.collectorId, MAX_COLLECTOR_ID_LENGTH, "Collector ID"), description: boundedText(input.description, MAX_DESCRIPTION_LENGTH, "Description") };
  if (Buffer.byteLength(JSON.stringify(normalized), "utf8") > MAX_PAYLOAD_BYTES) throw new CaseBoundaryError("AEGIS_CASE_PAYLOAD_TOO_LARGE", "Case payload exceeds the maximum size.");
  return normalized;
}

const rateWindows = new Map<string, number[]>();

export function enforcePublicCaseCreationRateLimit(clientKey: string, now = Date.now()): void {
  const windowStart = now - WINDOW_MS;
  const retained = (rateWindows.get(clientKey) ?? []).filter((timestamp) => timestamp > windowStart);
  if (retained.length >= MAX_CREATES_PER_WINDOW) throw new CaseBoundaryError("AEGIS_CASE_RATE_LIMITED", "Public demo case creation is temporarily rate-limited. Try again in one minute.");
  retained.push(now);
  rateWindows.set(clientKey, retained);
}

export function resetCaseBoundaryRateLimitsForTest(): void { rateWindows.clear(); }
