import { VARIABLE_MATCH_RE, VARIABLE_SPLIT_RE } from "./template-utils";

interface TemplatePreviewTextProps {
  text: string;
}

/** Raw template text with `{{variables}}` highlighted as cream inline chips. */
export function TemplatePreviewText({ text }: TemplatePreviewTextProps) {
  return (
    <>
      {text.split(VARIABLE_SPLIT_RE).map((part, i) => {
        const match = part.match(VARIABLE_MATCH_RE);
        return match ? (
          <span
            key={i}
            className="t-caption inline-block rounded bg-cream-300 px-1 py-px font-medium text-cream-ink dark:bg-cream-400/30"
          >
            {match[1]}
          </span>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </>
  );
}
