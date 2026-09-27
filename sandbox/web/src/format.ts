// Display helpers. Dates render as ISO (yyyy-mm-dd) on purpose: locale-independent scenario assertions.
import type { ClaimStatus, MemberStatus } from "./api";

export const MEMBER_STATUSES: MemberStatus[] = ["ACTIVE", "INACTIVE", "SUSPENDED", "PENDING"];
export const STATES = ["CA", "FL", "GA", "IL", "NY", "OH", "TX", "WA"];

export function titleCase(value: MemberStatus | ClaimStatus): string {
  return value
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

export function money(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export function maskSsn(ssn: string): string {
  return `***-**-${ssn.slice(-4)}`;
}

export function timestamp(value: string): string {
  return value.replace("T", " ").replace(/\.\d+/, "").replace("Z", " UTC");
}
