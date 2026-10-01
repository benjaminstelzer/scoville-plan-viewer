<script lang="ts">
  import CircleIcon from "@lucide/svelte/icons/circle";
  import PlayIcon from "@lucide/svelte/icons/play";
  import XIcon from "@lucide/svelte/icons/x";
  import { stepStatus, stepText } from "$lib/step-progress";
  import type { StepStatus, WorkItem } from "$lib/types";

  export let item: WorkItem;
  export let numbers: number[] | undefined = undefined;
  $: visibleNumbers = numbers ?? item.steps.map((_, index) => index + 1);
  const labels: Record<StepStatus, string> = { todo: "Upcoming", in_progress: "In progress", done: "Completed", cancelled: "Cancelled" };
</script>

<ol class="work-steps">
  {#each visibleNumbers as number}
    {@const status = stepStatus(item, number)}
    <li value={number} class:step-done={status === "done"} class:step-cancelled={status === "cancelled"} class:step-active={status === "in_progress"}>
      <span class="step-state" aria-hidden="true">
        {#if status === "done"}✓{:else if status === "cancelled"}<XIcon />{:else if status === "in_progress"}<PlayIcon />{:else if status === "todo"}<CircleIcon />{/if}
      </span>
      <span class="step-label">{stepText(item, number)}{#if status}{" · "}<span class="step-status-label">{labels[status]}</span>{/if}</span>
    </li>
  {/each}
</ol>
