// Dreamtalk - Frontend Animata
// Based on animata (MIT License)
// Source: animata

import { cn } from "@/lib/utils";

import "./marquee.css";

interface MarqueeProps extends React.HTMLAttributes<HTMLDivElement> {
  vertical?: boolean;
  repeat?: number;
  reverse?: boolean;
  pauseOnHover?: boolean;
  applyMask?: boolean;
}

export default function Marquee({
  children,
  vertical = false,
  repeat = 5,
  pauseOnHover = false,
  reverse = false,
  className,
  applyMask = true,
  ...props
}: MarqueeProps) {
  return (
    <div
      {...props}
      className={cn(
        "group/marquee relative flex h-full w-full p-2 [--duration:10s] [--gap:12px] [gap:var(--gap)]",
        {
          "flex-col": vertical,
          "flex-row": !vertical,
        },
        className,
      )}
    >
      {Array.from({ length: repeat }).map((_, index) => (
        <div
          key={`item-${index}`}
          className={cn("flex shrink-0 [gap:var(--gap)]", {
            "marquee-pause-on-hover": pauseOnHover,
            "marquee-horizontal flex-row": !vertical,
            "marquee-vertical flex-col": vertical,
          })}
          style={reverse ? { animationDirection: "reverse" } : undefined}
        >
          {children}
        </div>
      ))}
      {applyMask && (
        <div
          className={cn(
            "pointer-events-none absolute inset-0 z-10 h-full w-full from-white/50 from-5% via-transparent via-50% to-white/50 to-95% dark:from-gray-800/50 dark:via-transparent dark:to-gray-800/50",
            {
              "bg-linear-to-b": vertical,
              "bg-linear-to-r": !vertical,
            },
          )}
        />
      )}
    </div>
  );
}
