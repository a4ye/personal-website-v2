<script lang="ts">
    import { onMount } from "svelte";
    import blossomIcon from "../assets/blossom.svg?raw";

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
    title={enabled ? "Disable petals" : "Enable petals"}
    aria-label={enabled ? "Disable petals" : "Enable petals"}
>
    <span class="mt-0.5 duration-200" class:opacity-50={!enabled}>
        {@html blossomIcon}
    </span>
</button>
