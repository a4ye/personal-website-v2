<script lang="ts">
    import { onMount } from "svelte";

    let theme: string | null = null;

    onMount(() => {
        const stored = localStorage.getItem("theme");
        // Convert old theme names to new system
        if (stored === "latte") {
            theme = "light";
            localStorage.setItem("theme", "light");
        } else if (stored === "mocha") {
            theme = "dark";
            localStorage.setItem("theme", "dark");
        } else if (stored === "light" || stored === "dark") {
            theme = stored;
        } else {
            // Check current class
            if (document.documentElement.classList.contains("light") || document.documentElement.classList.contains("latte")) {
                theme = "light";
            } else {
                theme = "dark";
            }
        }
    });

    function toggle() {
        theme = theme === "dark" ? "light" : "dark";
        document.documentElement.classList.add("theme-transition");
        document.documentElement.classList.remove("light", "dark", "latte", "mocha");
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
        class="cursor-pointer flex items-center justify-center transition-all duration-200 hover:opacity-70"
        style="color: var(--text-tertiary);"
        aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
        {#if theme === "dark"}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
        {:else}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
        {/if}
    </button>
{:else}
    <div class="w-4 h-4"></div>
{/if}
