<script lang="ts">
    export let currentPath: string = "/";
    // Normalize path to remove trailing slash except for root
    $: normalizedPath =
        currentPath.length > 1 && currentPath.endsWith("/")
            ? currentPath.slice(0, -1)
            : currentPath;
</script>

<div class="flex gap-8 text-sm sm:text-base">
    <a
        class="font-medium transition-colors duration-300 hover:text-accent-blue"
        class:active={normalizedPath === "/"}
        href="/"
    >
        Home
    </a>
    <a
        class="font-medium transition-colors duration-300 hover:text-accent-blue"
        class:active={normalizedPath === "/projects"}
        href="/projects"
    >
        Projects
    </a>
    <a
        class="font-medium transition-colors duration-300 hover:text-accent-blue"
        class:active={normalizedPath === "/writing"}
        href="/writing"
    >
        Writing
    </a>
    <a
        class="font-medium transition-colors duration-300 hover:text-accent-blue"
        class:active={normalizedPath === "/guestbook"}
        href="/guestbook"
    >
        Guestbook
    </a>
</div>

<style>
    a {
        color: var(--text-primary);
    }
    a.active {
        color: var(--accent-blue);
    }
</style>
