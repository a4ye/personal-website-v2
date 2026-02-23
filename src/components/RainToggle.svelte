<script lang="ts">
    import { onMount } from "svelte";

    let enabled = true;

    onMount(() => {
        const stored = localStorage.getItem("rain-enabled");
        if (stored !== null) {
            enabled = stored === "true";
        }
        updateRainVisibility();
    });

    function toggle() {
        enabled = !enabled;
        localStorage.setItem("rain-enabled", String(enabled));
        updateRainVisibility();
    }

    function updateRainVisibility() {
        window.dispatchEvent(new CustomEvent("rain-toggle", { detail: { enabled } }));
    }
</script>

<button
    on:click={toggle}
    class="cursor-pointer flex items-center justify-center text-ctp-subtext0 hover:text-ctp-text transition-all duration-200"
    title={enabled ? "Disable rain" : "Enable rain"}
    aria-label={enabled ? "Disable rain" : "Enable rain"}
>
    <span class="mt-0.5 duration-200" class:opacity-50={!enabled}>
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
            <path d="M16 14v6"/>
            <path d="M8 14v6"/>
            <path d="M12 16v6"/>
        </svg>
    </span>
</button>
