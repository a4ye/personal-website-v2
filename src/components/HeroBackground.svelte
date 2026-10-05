<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import heroImage from "../assets/hero.avif";
    import { createRenderer, type Renderer } from "./hero/renderer";

    /** 0 to 1, where 1 is a full turn around the colour wheel. */
    export let hueShift = 0.4;

    let canvas: HTMLCanvasElement;
    // The canvas is drawn on a worker thread where it can be handed over, because compiling the
    // shader blocks whichever thread does it. Everything the renderer cannot see from there -
    // the pointer, the size, whether the hero is still on screen - is watched here and posted.
    let worker: Worker | null = null;
    let renderer: Renderer | null = null; // only used when the canvas cannot be handed over
    let observer: IntersectionObserver | null = null;
    let onScreen = true;
    // getBoundingClientRect on every mouse move forces a layout; the canvas only moves on resize
    // or scroll, so read it then instead.
    let canvasRect: DOMRect | null = null;
    let resizeTimeout: ReturnType<typeof setTimeout>;

    // Past 1.5 the shader costs more than the sharpness is worth
    const ratio = () => Math.min(window.devicePixelRatio || 1, 1.5);

    function setSize() {
        if (!canvas) return;
        canvasRect = canvas.getBoundingClientRect();
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        if (worker) worker.postMessage({ type: "size", width, height, dpr: ratio() });
        else renderer?.setSize(width, height, ratio());
    }

    function onMouseMove(e: MouseEvent) {
        if (!canvasRect) return;
        // As a fraction of the canvas, with y counted from the bottom, the way GL reads it
        const x = (e.clientX - canvasRect.left) / canvasRect.width;
        const y = 1 - (e.clientY - canvasRect.top) / canvasRect.height;
        if (worker) worker.postMessage({ type: "mouse", x, y });
        else renderer?.setMouse(x, y);
    }

    function onScroll() {
        if (canvas) canvasRect = canvas.getBoundingClientRect();
    }

    function debouncedResize() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(setSize, 50);
    }

    /** A full-screen draw every frame is wasted once the hero is scrolled past or the tab is hidden. */
    function syncRunning() {
        const on = onScreen && !document.hidden;
        if (worker) worker.postMessage({ type: "run", on });
        else if (on) renderer?.start();
        else renderer?.stop();
    }

    /** The photo, as bytes. index.astro chose which copy of it suits this screen and began fetching. */
    async function heroBlob(): Promise<Blob | null> {
        const handoff = (window as any).__hero as
            | { url: string; blob: Promise<Blob | null> }
            | undefined;
        const url = handoff?.url ?? (typeof heroImage === "string" ? heroImage : heroImage.src);
        try {
            const blob =
                (handoff && (await handoff.blob)) ||
                (await fetch(url).then((r) => (r.ok ? r.blob() : null)));
            if (!blob) throw new Error("the hero image did not load");
            return blob;
        } catch (e) {
            console.error("Failed to load hero background image", e);
            return null;
        }
    }

    onMount(async () => {
        if (typeof canvas.transferControlToOffscreen === "function" && typeof Worker !== "undefined") {
            try {
                worker = new Worker(new URL("./hero/worker.ts", import.meta.url), {
                    type: "module",
                });
                const surface = canvas.transferControlToOffscreen();
                worker.postMessage(
                    {
                        type: "init",
                        canvas: surface,
                        hueShift,
                        width: canvas.clientWidth,
                        height: canvas.clientHeight,
                        dpr: ratio(),
                    },
                    [surface],
                );
            } catch (e) {
                // Nothing is lost by drawing here instead, beyond the stall this was avoiding
                console.warn("hero: drawing on the main thread -", e);
                worker?.terminate();
                worker = null;
            }
        }
        if (!worker) {
            renderer = createRenderer(canvas, hueShift);
            if (!renderer) return;
            renderer.setSize(canvas.clientWidth, canvas.clientHeight, ratio());
        }

        canvasRect = canvas.getBoundingClientRect();
        window.addEventListener("resize", debouncedResize);
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("scroll", onScroll, { passive: true });
        document.addEventListener("visibilitychange", syncRunning);
        observer = new IntersectionObserver((entries) => {
            onScreen = entries[0].isIntersecting;
            syncRunning();
        });
        observer.observe(canvas);
        syncRunning();

        const blob = await heroBlob();
        if (!blob) return;
        if (worker) worker.postMessage({ type: "texture", blob });
        else renderer?.setTexture(blob);
    });

    // Nothing drives this today, but a hue that could not be changed after the first frame would
    // be a trap for whatever does next
    $: if (worker) worker.postMessage({ type: "hue", hueShift });

    onDestroy(() => {
        observer?.disconnect();
        worker?.terminate();
        renderer?.destroy();
        window.removeEventListener("resize", debouncedResize);
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("scroll", onScroll);
        document.removeEventListener("visibilitychange", syncRunning);
        clearTimeout(resizeTimeout);
    });
</script>

<canvas bind:this={canvas} class="absolute inset-0 w-full h-full"></canvas>
