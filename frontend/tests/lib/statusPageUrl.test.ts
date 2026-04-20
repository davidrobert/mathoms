import { describe, it, expect, vi, afterEach } from "vitest";
import { getStatusPageUrl } from "@/lib/statusPageUrl";

describe("getStatusPageUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns undefined when unset or empty", () => {
    vi.stubEnv("NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL", "");
    expect(getStatusPageUrl()).toBeUndefined();
  });

  it("returns valid https URL", () => {
    vi.stubEnv("NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL", "https://status.example.com");
    expect(getStatusPageUrl()).toBe("https://status.example.com");
  });

  it("returns undefined for javascript: and other non-http(s) schemes", () => {
    vi.stubEnv("NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL", "javascript:alert(1)");
    expect(getStatusPageUrl()).toBeUndefined();
  });
});
