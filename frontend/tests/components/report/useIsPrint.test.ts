/**
 * v2.E.3 — unit specs do `useIsPrint`.
 *
 * Cobre: estado inicial false em jsdom (matchMedia mockado retorna
 * `matches: false`), e mudança para true quando o listener de change
 * é disparado com `matches: true`.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useIsPrint } from "@/components/report/hooks/useIsPrint";

afterEach(() => vi.restoreAllMocks());

describe("useIsPrint", () => {
  it("retorna false por default em jsdom (matchMedia mock matches=false)", () => {
    const { result } = renderHook(() => useIsPrint());
    expect(result.current).toBe(false);
  });

  it("vira true quando o evento change dispara matches=true", () => {
    let fire: ((e: MediaQueryListEvent) => void) | null = null;
    const mql = {
      matches: false,
      media: "print",
      onchange: null,
      addEventListener: vi.fn((_evt: string, cb: (e: MediaQueryListEvent) => void) => {
        fire = cb;
      }),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    };
    vi.spyOn(window, "matchMedia").mockReturnValue(mql as unknown as MediaQueryList);

    const { result } = renderHook(() => useIsPrint());
    expect(result.current).toBe(false);

    act(() => {
      fire?.({ matches: true } as MediaQueryListEvent);
    });

    expect(result.current).toBe(true);
  });
});
