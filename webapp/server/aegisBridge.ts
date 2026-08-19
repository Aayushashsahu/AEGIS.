/** Node transport boundary for the vendored canonical AEGIS Python projection. */
import { spawnSync } from "node:child_process";
import path from "node:path";

const projectRoot = process.cwd();
const coreRoot = path.join(projectRoot, "aegis_backend");
const script = path.join(coreRoot, "scripts", "mission032_lifecycle_api.py");

export type AegisRequest = { action: "seed_cases" | "historical" | "controlled" | "configured" | "benchmark"; case?: Record<string, unknown> };

export function invokeAegis(request: AegisRequest): Record<string, any> {
  const pythonPath = [path.join(coreRoot, "src"), coreRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const result = spawnSync("python3", [script, "--root", coreRoot], {
    cwd: projectRoot,
    env: { ...process.env, PYTHONPATH: pythonPath },
    input: JSON.stringify(request),
    encoding: "utf8",
    timeout: 15_000,
    maxBuffer: 2_000_000,
  });
  if (result.error) throw new Error(`AEGIS domain adapter unavailable: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`AEGIS domain adapter failed: ${result.stderr || "unknown adapter error"}`);
  try {
    return JSON.parse(result.stdout) as Record<string, any>;
  } catch {
    throw new Error("AEGIS domain adapter returned invalid JSON");
  }
}
