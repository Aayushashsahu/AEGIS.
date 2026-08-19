/** Persistence for user-configured case contracts; lifecycle decisions remain canonical AEGIS projections. */
import { desc, eq } from "drizzle-orm";
import { nanoid } from "nanoid";
import { reliabilityCases, type ReliabilityCase } from "../drizzle/schema";
import { getDb } from "./db";

export type ApiField = { name: string; type: "text" | "number" | "url" | "boolean" | "date"; description: string };
export type CreateCaseInput = { targetUrl: string; fields: ApiField[]; invariants: string[]; name?: string; collectorId?: string; description?: string };

function serialize(record: ReliabilityCase) {
  return {
    case_id: record.caseId,
    name: record.name,
    target_url: record.targetUrl,
    collector_id: record.collectorId,
    description: record.description,
    fields: JSON.parse(record.fieldsJson) as ApiField[],
    invariants: JSON.parse(record.invariantsJson) as string[],
    correlation_id: record.correlationId,
    created_at: record.createdAt.toISOString(),
    updated_at: record.updatedAt.toISOString(),
  };
}

export async function createAegisCase(input: CreateCaseInput) {
  const db = await getDb();
  if (!db) throw new Error("AEGIS case database is unavailable");
  const caseId = `case_${nanoid(16)}`;
  const now = new Date();
  await db.insert(reliabilityCases).values({
    caseId,
    name: input.name?.trim() || new URL(input.targetUrl).host,
    targetUrl: input.targetUrl,
    collectorId: input.collectorId?.trim() || null,
    description: input.description?.trim() || null,
    fieldsJson: JSON.stringify(input.fields),
    invariantsJson: JSON.stringify(input.invariants),
    correlationId: `corr_${nanoid(20)}`,
    createdAt: now,
    updatedAt: now,
  });
  const record = await db.select().from(reliabilityCases).where(eq(reliabilityCases.caseId, caseId)).limit(1);
  if (!record[0]) throw new Error("AEGIS case persistence failed");
  return serialize(record[0]);
}

export async function getAegisCase(caseId: string) {
  const db = await getDb();
  if (!db) throw new Error("AEGIS case database is unavailable");
  const record = await db.select().from(reliabilityCases).where(eq(reliabilityCases.caseId, caseId)).limit(1);
  return record[0] ? serialize(record[0]) : null;
}

export async function listAegisCases() {
  const db = await getDb();
  if (!db) return [];
  const records = await db.select().from(reliabilityCases).orderBy(desc(reliabilityCases.updatedAt));
  return records.map(serialize);
}
