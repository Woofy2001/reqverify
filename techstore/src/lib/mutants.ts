import { NextRequest } from "next/server";

/**
 * Retrieves the currently active mutant ID from cookie, header, or environment variable.
 */
export function getActiveMutant(): string {
  if (typeof window !== "undefined") {
    const match = document.cookie.match(/(?:^|;\s*)reqverify_mutant=([^;]+)/);
    if (match && match[1]) {
      return decodeURIComponent(match[1]).trim().toUpperCase();
    }
    return (process.env.NEXT_PUBLIC_MUTANT || "").trim().toUpperCase();
  }

  return (process.env.MUTANT || process.env.NEXT_PUBLIC_MUTANT || "").trim().toUpperCase();
}

/**
 * Helper for Next.js API routes to extract the active mutant from the incoming request.
 */
export function getMutantFromRequest(req: NextRequest): string {
  const cookieVal = req.cookies.get("reqverify_mutant")?.value;
  if (cookieVal) return cookieVal.trim().toUpperCase();

  const headerVal = req.headers.get("x-reqverify-mutant");
  if (headerVal) return headerVal.trim().toUpperCase();

  return (process.env.MUTANT || process.env.NEXT_PUBLIC_MUTANT || "").trim().toUpperCase();
}

/**
 * Checks if a specific mutant ID is currently active.
 */
export function isMutantActive(id: string, req?: NextRequest | null): boolean {
  const target = id.trim().toUpperCase();
  if (req) {
    return getMutantFromRequest(req) === target;
  }
  return getActiveMutant() === target;
}
