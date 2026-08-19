import { COOKIE_NAME } from "@shared/const";
import { z } from "zod";
import { createAegisCase, getAegisCase, listAegisCases } from "./aegisCases";
import { enforcePublicCaseCreationRateLimit, normalizeCreateCaseInput } from "./aegisCaseBoundary";
import { invokeAegis } from "./aegisBridge";
import { SEEDED_CASE_METADATA } from "./aegisSeedMetadata";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),
  aegis: router({
    listCases: publicProcedure.query(async () => {
      const persisted = await listAegisCases();
      const cases = [...SEEDED_CASE_METADATA as unknown as Record<string, any>[], ...persisted as Record<string, any>[]].map((item) => ({
        case_id: item.case_id,
        name: item.name,
        target_url: item.target_url,
        created_at: item.created_at,
        evidence_status: item.evidence_status ?? item.lifecycle?.current_status ?? "CONFIGURED",
        event_count: item.event_count ?? item.lifecycle?.event_count ?? 0,
      }));
      return { cases };
    }),
    createCase: publicProcedure.input(z.object({
      targetUrl: z.string(), fields: z.array(z.object({ name: z.string(), type: z.enum(["text", "number", "url", "boolean", "date"]), description: z.string() })), invariants: z.array(z.string()), name: z.string().optional(), collectorId: z.string().optional(), description: z.string().optional(),
    })).mutation(async ({ input, ctx }) => {
      const forwarded = ctx.req.headers["x-forwarded-for"];
      const clientKey = Array.isArray(forwarded) ? forwarded[0] : (forwarded?.split(",")[0]?.trim() || "public-demo");
      enforcePublicCaseCreationRateLimit(clientKey);
      const configured = await createAegisCase(normalizeCreateCaseInput(input));
      return invokeAegis({ action: "configured", case: configured }).case;
    }),
    caseLifecycle: publicProcedure.input(z.object({ caseId: z.string().min(1) })).query(async ({ input }) => {
      if (input.caseId === "mission_029_real_provider") return invokeAegis({ action: "historical" });
      if (input.caseId === "controlled_silent_corruption") return invokeAegis({ action: "controlled" });
      const configured = await getAegisCase(input.caseId);
      if (!configured) throw new Error("AEGIS case not found");
      return invokeAegis({ action: "configured", case: configured });
    }),
    benchmark: publicProcedure.query(() => invokeAegis({ action: "benchmark" })),
    downstream: publicProcedure.query(() => invokeAegis({ action: "downstream" })),
  }),
});

export type AppRouter = typeof appRouter;
