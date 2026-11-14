"use client";

import { useEffect, useRef, useState } from 'react';

/** A mobile drawer must not leave off-screen links in the keyboard order. */
export function useNavigationDrawer(open: boolean, close: () => void, breakpoint: number) {
  const panel = useRef<HTMLElement>(null);
  const closeRef = useRef(close);
  const [mobile, setMobile] = useState(false);
  useEffect(() => { closeRef.current = close; }, [close]);
  useEffect(() => {
    const query = matchMedia(`(max-width: ${breakpoint}px)`);
    const update = () => { setMobile(query.matches); if (!query.matches) closeRef.current(); };
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, [breakpoint]);
  useEffect(() => {
    if (!mobile || !open) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    const focusable = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('a[href], button:not(:disabled), input:not(:disabled), [tabindex="0"]') || []).filter(item => item.getClientRects().length > 0);
    document.body.style.overflow = 'hidden';
    (panel.current?.querySelector<HTMLElement>('[data-drawer-close]') || focusable()[0])?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); closeRef.current(); }
      if (event.key !== 'Tab') return;
      const items = focusable();
      const first = items[0]; const last = items.at(-1);
      if (event.shiftKey && (document.activeElement === first || !panel.current?.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !panel.current?.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', onKey); if (previous?.isConnected) previous.focus(); };
  }, [mobile, open]);
  return { panel, mobile };
}
