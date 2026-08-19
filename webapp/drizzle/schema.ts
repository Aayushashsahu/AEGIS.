import { int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/** User-configured AEGIS protection contracts. Lifecycle evidence remains in the canonical Python projection. */
export const reliabilityCases = mysqlTable("reliabilityCases", {
  caseId: varchar("caseId", { length: 80 }).primaryKey(),
  name: varchar("name", { length: 255 }).notNull(),
  targetUrl: text("targetUrl").notNull(),
  collectorId: varchar("collectorId", { length: 128 }),
  description: text("description"),
  fieldsJson: text("fieldsJson").notNull(),
  invariantsJson: text("invariantsJson").notNull(),
  correlationId: varchar("correlationId", { length: 100 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type ReliabilityCase = typeof reliabilityCases.$inferSelect;
export type InsertReliabilityCase = typeof reliabilityCases.$inferInsert;
