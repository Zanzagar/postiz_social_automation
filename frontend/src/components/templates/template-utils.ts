import type { Template } from "@/lib/api";

/** Splits template text so `{{variable}}` tokens land in their own parts. */
export const VARIABLE_SPLIT_RE = /(\{\{.+?\}\})/;
/** Matches a whole `{{variable}}` token, capturing the name. */
export const VARIABLE_MATCH_RE = /^\{\{(.+?)\}\}$/;

/** Unique `{{variable}}` names, in order of first appearance. */
export function parseVariables(body: string): string[] {
  const names: string[] = [];
  for (const match of body.matchAll(/\{\{(.+?)\}\}/g)) {
    const name = match[1].trim();
    if (name && !names.includes(name)) names.push(name);
  }
  return names;
}

/** Variable names for a template — saved list first, else parsed from body. */
export function templateVariableNames(template: Template): string[] {
  if (template.variables && template.variables.length > 0) {
    return template.variables.map((v) => v.name);
  }
  return parseVariables(template.raw_text_template ?? "");
}

/** Trigger options mapping to the backend `schedule_pattern` format. */
export const TRIGGER_OPTIONS: { value: string; label: string }[] = [
  { value: "manual", label: "Manual — I'll run it" },
  { value: "weekly:sunday", label: "Every Sunday" },
  { value: "weekly:monday", label: "Every Monday" },
  { value: "weekly:tuesday", label: "Every Tuesday" },
  { value: "weekly:wednesday", label: "Every Wednesday" },
  { value: "weekly:thursday", label: "Every Thursday" },
  { value: "weekly:friday", label: "Every Friday" },
  { value: "weekly:saturday", label: "Every Saturday" },
  { value: "biweekly", label: "Every 2 weeks" },
  { value: "monthly:1", label: "Monthly — 1st" },
  { value: "monthly:15", label: "Monthly — 15th" },
];

export function isWeeklyPattern(pattern: string | null | undefined): boolean {
  return !!pattern && pattern.startsWith("weekly");
}

function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function ordinal(n: number): string {
  const rem10 = n % 10;
  const rem100 = n % 100;
  if (rem10 === 1 && rem100 !== 11) return `${n}st`;
  if (rem10 === 2 && rem100 !== 12) return `${n}nd`;
  if (rem10 === 3 && rem100 !== 13) return `${n}rd`;
  return `${n}th`;
}

/** Human label for a schedule_pattern ("weekly:thursday" → "Every Thursday"). */
export function formatSchedule(pattern: string | null | undefined): string {
  if (!pattern || pattern === "manual") return "Manual";
  if (pattern.startsWith("weekly:")) {
    return `Every ${capitalize(pattern.slice("weekly:".length))}`;
  }
  if (pattern === "weekly") return "Weekly";
  if (pattern === "biweekly") return "Every 2 weeks";
  if (pattern.startsWith("monthly:")) {
    const day = Number(pattern.slice("monthly:".length));
    return Number.isFinite(day) ? `Monthly — ${ordinal(day)}` : "Monthly";
  }
  return pattern;
}

/** Sample values for "Preview filled" — real herd names where relevant. */
const SAMPLE_VALUES: Record<string, string> = {
  cow_name: "Lakshmi",
  trait: "our gentlest mother, with one half-black ear",
  arrival_season: "the winter of 2022",
  recent_activity: "grazing the east pasture with Tabby and Sparkle",
  festival: "Janmashtami",
  date: "Thursday, July 9",
  month: "July",
  location: "the east pasture",
  name: "Tabby",
  event: "the Sunday feast",
  quote: "The soul is never born, nor does it ever die.",
  verse: "Bhagavad-gita 2.20",
  topic: "morning milking",
  pasture: "the east pasture",
  theme: "gratitude",
  goal: "72",
};

/** Sample fill-in for a variable name (fallback: humanized name). */
export function sampleValue(name: string): string {
  return SAMPLE_VALUES[name] ?? name.replace(/_/g, " ");
}

/** Replaces every `{{variable}}` in the body via the resolver. */
export function fillTemplate(
  body: string,
  resolve: (name: string) => string,
): string {
  return body.replace(/\{\{(.+?)\}\}/g, (_, raw: string) => resolve(raw.trim()));
}
