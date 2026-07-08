import type * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Inline link sized to the surrounding text. Renders an <a> when href is
 * given, otherwise a <button>. Use inside sentences/captions where
 * Button variant="link" would break text flow.
 */
interface TextLinkProps {
  href?: string;
  onClick?: React.MouseEventHandler<HTMLElement>;
  children: React.ReactNode;
  className?: string;
}

export function TextLink({ href, onClick, children, className }: TextLinkProps) {
  const classes = cn(
    "fr rounded-sm font-medium text-sage-600 underline-offset-2 hover:text-sage-700 hover:underline dark:text-sage-300 dark:hover:text-sage-200",
    className,
  );
  if (href) {
    return (
      <a href={href} onClick={onClick} className={classes}>
        {children}
      </a>
    );
  }
  return (
    <button type="button" onClick={onClick} className={classes}>
      {children}
    </button>
  );
}
