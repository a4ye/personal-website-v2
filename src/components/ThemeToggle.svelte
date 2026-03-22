<script lang="ts">
    import { onMount } from "svelte";

    let theme: string | null = null;

    onMount(() => {
        const stored = localStorage.getItem("theme");
        if (stored === "latte" || stored === "mocha") {
            theme = stored;
        } else {
            theme = document.documentElement.classList.contains("latte") ? "latte" : "mocha";
        }
    });

    function toggle() {
        theme = theme === "mocha" ? "latte" : "mocha";
        document.documentElement.classList.add("theme-transition");
        document.documentElement.classList.remove("latte", "mocha");
        document.documentElement.classList.add(theme);
        localStorage.setItem("theme", theme);
        setTimeout(() => {
            document.documentElement.classList.remove("theme-transition");
        }, 300);
    }
</script>

{#if theme}
    <button
        on:click={toggle}
        class="cursor-pointer flex items-center justify-center text-ctp-subtext0 hover:text-ctp-text transition-all duration-200"
        aria-label={theme === "mocha" ? "Switch to light mode" : "Switch to dark mode"}
    >
        {#if theme === "mocha"}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
        {:else}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
        {/if}
    </button>
{:else}
    <div class="w-4 h-4"></div>
{/if}
