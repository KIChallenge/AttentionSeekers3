"use client";

import { animate, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { fmt } from "@/lib/format";

/** Counts up to `value` (motion). The final text is always exactly the API value. */
export function AnimatedNumber({ value, digits, className }: { value: number; digits?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? value : 0);
  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setShown(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setShown(v),
      onComplete: () => setShown(value),
    });
    return () => controls.stop();
  }, [value, inView, reduce]);
  const isInt = Number.isInteger(value) && digits === undefined;
  return (
    <span ref={ref} className={className} aria-label={fmt(value, digits)}>
      {shown === value ? fmt(value, digits) : isInt ? fmt(Math.round(shown)) : fmt(shown, digits ?? 1)}
    </span>
  );
}
