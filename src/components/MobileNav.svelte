<script lang="ts">
    import { fade } from "svelte/transition";
    import { fly } from "svelte/transition";
    import { cubicOut, cubicIn } from "svelte/easing";

    let open = false;

    function smoothScroll(id: string) {
        open = false;
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: "smooth" });
        else window.location.href = `/#${id}`;
    }
</script>

<button
    class="md:hidden text-accent hover:text-base transition-colors duration-200"
    on:click={() => (open = true)}
    aria-label="Open navigation menu"
>
    <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
</button>

{#if open}
<div
    class="fixed inset-0 bg-surface z-[200] flex flex-col"
    transition:fade={{ duration: 200 }}
>
    <div
        class="max-w-6xl mx-auto w-full flex items-center justify-end px-6 md:px-10 pt-9 pb-8"
        in:fly={{ y: -8, duration: 250, delay: 50, easing: cubicOut }}
        out:fly={{ y: -8, duration: 150, easing: cubicIn }}
    >
        <button
            on:click={() => (open = false)}
            aria-label="Close navigation menu"
            class="text-accent hover:text-base transition-colors duration-200"
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    </div>
    <nav
        class="flex flex-col items-center justify-center flex-1 gap-10"
        in:fly={{ y: 16, duration: 300, delay: 80, easing: cubicOut }}
        out:fly={{ y: 16, duration: 150, easing: cubicIn }}
    >
        <a
            class="font-serif text-4xl text-accent hover:text-base transition-colors duration-200"
            href="/#about"
            on:click|preventDefault={() => smoothScroll("about")}>About</a
        >
        <a
            class="font-serif text-4xl text-accent hover:text-base transition-colors duration-200"
            href="/#projects"
            on:click|preventDefault={() => smoothScroll("projects")}>Projects</a
        >
        <a
            class="font-serif text-4xl text-accent hover:text-base transition-colors duration-200"
            href="/writing"
            on:click={() => (open = false)}>Writing</a
        >
        <a
            class="font-serif text-4xl text-accent hover:text-base transition-colors duration-200"
            href="/guestbook"
            on:click={() => (open = false)}>Guestbook</a
        >
    </nav>
</div>
{/if}
