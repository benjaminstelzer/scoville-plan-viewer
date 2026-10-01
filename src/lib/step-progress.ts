import type { StepStatus, WorkItem } from "./types";

export function stepStatus(item: WorkItem, number: number): StepStatus | null {
  return item.step_statuses?.find((entry) => entry.number === number)?.status ?? null;
}

export function stepText(item: WorkItem, number: number): string {
  const text = item.steps[number - 1];
  return stepStatus(item, number) ? text.replace(/^\[status: (todo|in_progress|done|cancelled)\] /, "") : text;
}

export function stepPosition(item: WorkItem) {
  const statuses = item.steps.map((_, index) => stepStatus(item, index + 1));
  const untracked = statuses.flatMap((status, index) => status === null ? [index + 1] : []);
  if (item.status === "done" || item.status === "cancelled") return { numbers: [], untracked, reason: "work_terminal" };
  const active = statuses.flatMap((status, index) => status === "in_progress" ? [index + 1] : []);
  if (active.length) return { numbers: active, untracked, reason: untracked.length ? "written_in_progress_with_untracked" : "written_in_progress" };
  if (!statuses.length) return { numbers: [], untracked, reason: "whole_work_item" };
  const first = statuses.findIndex((status) => status !== "done" && status !== "cancelled");
  if (first === -1) return { numbers: [], untracked, reason: "steps_terminal_work_item_acceptance_pending" };
  if (statuses[first] === null) return { numbers: [], untracked, reason: "untracked_progress_requires_inspection" };
  return { numbers: [first + 1], untracked, reason: "next_written_todo" };
}
