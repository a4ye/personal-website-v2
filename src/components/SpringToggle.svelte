<script lang="ts">
    import { onMount } from "svelte";

    let enabled = true;

    onMount(() => {
        const stored = localStorage.getItem("spring-enabled");
        if (stored !== null) {
            enabled = stored === "true";
        }
        updateSpringVisibility();
    });

    function toggle() {
        enabled = !enabled;
        localStorage.setItem("spring-enabled", String(enabled));
        updateSpringVisibility();
    }

    function updateSpringVisibility() {
        window.dispatchEvent(new CustomEvent("spring-toggle", { detail: { enabled } }));
    }
</script>

<button
    on:click={toggle}
    class="cursor-pointer flex items-center justify-center text-ctp-subtext0 hover:text-ctp-text transition-all duration-200"
    aria-label={enabled ? "Disable petals" : "Enable petals"}
>
    <span class="duration-200" class:opacity-50={!enabled}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7.5a4.5 4.5 0 1 1 4.5 4.5M12 7.5a4.5 4.5 0 1 0-4.5 4.5M12 7.5V9m-4.5 3a4.5 4.5 0 1 0 4.5 4.5M7.5 12H9m7.5 0a4.5 4.5 0 1 1-4.5 4.5m4.5-4.5H15m-3 4.5V15"/><circle cx="12" cy="12" r="3"/><path d="m8 16 1.5-1.5"/><path d="M14.5 9.5 16 8"/><path d="m8 8 1.5 1.5"/><path d="M14.5 14.5 16 16"/></svg>
    </span>
</button>
