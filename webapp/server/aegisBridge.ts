/** Canonical-root transport boundary for read-only AEGIS lifecycle projections. */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

export type AegisAction = "historical" | "controlled" | "configured" | "benchmark" | "downstream";
export type AegisRequest = { action: AegisAction; case?: Record<string, unknown> };

export class AegisAdapterError extends Error {
  constructor(public readonly code: string, message: string, public readonly detail?: string) {
    super(message);
    this.name = "AegisAdapterError";
  }
}

const SERVER_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
const MAX_DETAIL_LENGTH = 500;
let resolvedPython: string | undefined;

function safeDetail(value: unknown): string | undefined {
  const detail = String(value ?? "").replace(/[\r\n]+/g, " ").trim();
  return detail ? detail.slice(0, MAX_DETAIL_LENGTH) : undefined;
}

function isCanonicalRoot(candidate: string): boolean {
  return existsSync(path.join(candidate, "src", "aegis"))
    && existsSync(path.join(candidate, "benchmarks"))
    && existsSync(path.join(candidate, "experiments"))
    && existsSync(path.join(candidate, "scripts", "mission032_lifecycle_api.py"));
}

/** Resolve a clone portably by explicit environment override or upward marker walk. */
export function resolveRepositoryRoot(startDirectory = SERVER_DIRECTORY): string {
  const explicitRoot = process.env.AEGIS_ROOT;
  if (explicitRoot) {
    const resolved = path.resolve(explicitRoot);
    if (isCanonicalRoot(resolved)) return resolved;
    throw new AegisAdapterError("AEGIS_ROOT_INVALID", "Canonical AEGIS repository root is unavailable", "AEGIS_ROOT does not contain src/aegis, benchmarks, experiments, and scripts/mission032_lifecycle_api.py.");
  }
  let cursor = path.resolve(startDirectory);
  while (true) {
    if (isCanonicalRoot(cursor)) return cursor;
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
    cursor = parent;
  }
  throw new AegisAdapterError("AEGIS_ROOT_NOT_FOUND", "Canonical AEGIS repository root is unavailable", "Set AEGIS_ROOT or run the webapp from a clone containing src/aegis, benchmarks, experiments, and scripts/mission032_lifecycle_api.py.");
}

function canExecutePython(executable: string): boolean {
  const probe = spawnSync(executable, ["--version"], { encoding: "utf8", timeout: 3_000, windowsHide: true });
  return !probe.error && probe.status === 0;
}

/** Prefer explicit configuration, then discover cross-platform Python candidates once. */
export function resolvePythonExecutable(): string {
  if (resolvedPython) return resolvedPython;
  const requested = process.env.AEGIS_PYTHON;
  if (requested) {
    if (canExecutePython(requested)) return (resolvedPython = requested);
    throw new AegisAdapterError("AEGIS_PYTHON_INVALID", "Canonical AEGIS Python adapter unavailable", "AEGIS_PYTHON was provided but cannot execute Python.");
  }
  const candidates = process.platform === "win32" ? ["python", "python3"] : ["python3", "python"];
  const executable = candidates.find(canExecutePython);
  if (!executable) throw new AegisAdapterError("AEGIS_PYTHON_MISSING", "Canonical AEGIS Python adapter unavailable", "Install Python 3 or set AEGIS_PYTHON to a working interpreter.");
  resolvedPython = executable;
  return executable;
}

export function invokeAegis(request: AegisRequest): Record<string, any> {
  const repositoryRoot = resolveRepositoryRoot();
  const script = path.join(repositoryRoot, "scripts", "mission032_lifecycle_api.py");
  if (!existsSync(script)) throw new AegisAdapterError("AEGIS_ADAPTER_SCRIPT_MISSING", "Canonical AEGIS Python adapter unavailable", "scripts/mission032_lifecycle_api.py is missing from the canonical repository root.");
  const python = resolvePythonExecutable();
  const pythonPath = [path.join(repositoryRoot, "src"), repositoryRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const result = spawnSync(python, [script, "--root", repositoryRoot], {
    cwd: repositoryRoot,
    env: { ...process.env, PYTHONPATH: pythonPath },
    input: JSON.stringify(request),
    encoding: "utf8",
    timeout: 15_000,
    maxBuffer: 2_000_000,
    windowsHide: true,
  });
  if (result.error) {
    const code = result.error.name === "TimeoutError" ? "AEGIS_ADAPTER_TIMEOUT" : "AEGIS_ADAPTER_UNAVAILABLE";
    throw new AegisAdapterError(code, "Canonical AEGIS Python adapter unavailable", safeDetail(result.error.message));
  }
  if (result.status !== 0) throw new AegisAdapterError("AEGIS_ADAPTER_FAILED", "Canonical AEGIS Python adapter failed", safeDetail(result.stderr));
  try {
    return JSON.parse(result.stdout) as Record<string, any>;
  } catch {
    throw new AegisAdapterError("AEGIS_ADAPTER_MALFORMED_JSON", "Canonical AEGIS Python adapter returned malformed JSON");
  }
}
