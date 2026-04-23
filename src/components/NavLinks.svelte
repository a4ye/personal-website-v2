<script lang="ts">
    export let currentPath: string = "/";
    // Normalize path to remove trailing slash except for root
    $: normalizedPath =
        currentPath.length > 1 && currentPath.endsWith("/")
            ? currentPath.slice(0, -1)
            : currentPath;
</script>

<div class="flex gap-6">
    <a
        class="font-medium text-accent hover:text-base duration-200"
        href="/#about"
        on:click|preventDefault={() => {
            const el = document.getElementById('about');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
            else window.location.href = '/#about';
        }}>About</a
    >
    <a
        class="font-medium text-accent hover:text-base duration-200"
        href="/#projects"
        on:click|preventDefault={() => {
            const el = document.getElementById('projects');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
            else window.location.href = '/#projects';
        }}>Projects</a
    >
    <a
        class="font-medium text-accent hover:text-base duration-200"
        href="/writing">Writing</a
    >
    <a
        class="font-medium text-accent hover:text-base duration-200"
        href="/guestbook">Guestbook</a
    >
</div>
