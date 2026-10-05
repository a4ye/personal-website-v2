<script lang="ts">
    import { onDestroy } from "svelte";

    /**
     * The small label that appears over an icon on hover or focus.
     *
     * This replaces @radix-ui/react-tooltip, which brought React with it: 254 KB of library for
     * seven labels. The behaviour it had is kept - opens at once on hover and on keyboard focus,
     * closes on leave, blur, Escape and on press, sits above the trigger unless there is no room,
     * stays inside the window, and is announced through aria-describedby.
     */
    /** The text in the bubble. */
    export let label = "";
    /**
     * An ISO date, for the footer's commit. Given one, the bubble reads "Last updated on <date>"
     * in the reader's own locale, which is why it is written out here and not when the page builds.
     */
    export let date = "";

    const id = `tooltip-${Math.random().toString(36).slice(2, 9)}`;
    const GAP = 4; // the offset between the trigger and the bubble
    // How near the window edge the bubble may come before it is moved. Zero, measured against the
    // tooltip this replaces: the icons in the header leave exactly 6 px above them, and anything
    // larger here sends every one of those labels to the wrong side of its icon.
    const EDGE = 0;

    let trigger: HTMLSpanElement;
    let bubble: HTMLDivElement | null = null;
    let open = false;
    let above = true;
    let left = 0;
    let top = 0;
    // Where the bubble grows from: the trigger, even when the window edge has pushed it sideways
    let originX = 0;

    $: text = date ? `Last updated on ${new Date(date).toLocaleDateString()}` : label;

    function place() {
        if (!trigger || !bubble) return;
        const t = trigger.getBoundingClientRect();
        const b = bubble.getBoundingClientRect();
        above = t.top - b.height - GAP >= EDGE;
        top = above ? t.top - b.height - GAP : t.bottom + GAP;
        left = Math.min(
            Math.max(t.left + t.width / 2 - b.width / 2, EDGE),
            Math.max(EDGE, window.innerWidth - b.width - EDGE),
        );
        originX = Math.round(t.left + t.width / 2 - left);
    }

    /**
     * Hang the bubble off the body, where nothing can clip it, and place it before the browser
     * has drawn it. An action runs as the node is inserted, so there is no frame in the wrong spot.
     */
    function float(node: HTMLDivElement) {
        document.body.appendChild(node);
        bubble = node;
        place();
        return {
            destroy() {
                bubble = null;
                node.remove();
            },
        };
    }

    function show(e: PointerEvent | FocusEvent) {
        // A tooltip has nowhere to go on a touch screen: the finger is already on the thing
        if (e.type === "pointerenter" && (e as PointerEvent).pointerType === "touch") return;
        // Focus alone is not enough. Tapping or clicking the trigger focuses it too, and a bubble
        // that opens on that reads as a bug; :focus-visible is the browser's own answer to whether
        // the reader is on the keyboard.
        if (e.type === "focusin" && !(e.target as Element)?.matches?.(":focus-visible")) return;
        keep();
        open = true;
    }

    /**
     * The bubble can be hovered, the way the one this replaces could, so leaving the trigger is
     * not on its own a reason to close: the pointer may be on its way across the 4 px gap. The
     * close is left until the next frame, by which time the bubble has had its own pointerenter
     * and cancelled it. The bridge in the stylesheet below covers the gap itself, so a slow hand
     * never passes over bare page.
     */
    let closing = 0;

    function keep() {
        if (closing) cancelAnimationFrame(closing);
        closing = 0;
    }

    function hide() {
        keep();
        closing = requestAnimationFrame(() => {
            closing = 0;
            open = false;
        });
    }

    function hideNow() {
        keep();
        open = false;
    }

    function onKeydown(e: KeyboardEvent) {
        if (open && e.key === "Escape") hideNow();
    }

    function reposition() {
        if (open) place();
    }

    onDestroy(keep);

    const curve = (p1: number, p2: number, u: number) =>
        3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u ** 2 * p2 + u ** 3;

    /**
     * CSS's own `ease`, cubic-bezier(.25, .1, .25, 1), which is what a CSS animation uses when it
     * is not told otherwise - and so what the animation this replaces ran on. Svelte bakes the
     * easing into the keyframes it writes, so the curve has to be solved here rather than named.
     */
    function ease(t: number) {
        let lo = 0;
        let hi = 1;
        for (let i = 0; i < 20; i++) {
            const mid = (lo + hi) / 2;
            if (curve(0.25, 0.25, mid) < t) lo = mid;
            else hi = mid;
        }
        return curve(0.1, 1, (lo + hi) / 2);
    }

    /** 150 ms: fades up from nothing, grows from 95%, and rises 8 px off the side it points at. */
    function grow() {
        const shift = above ? 8 : -8;
        return {
            duration: 150,
            easing: ease,
            css: (t: number, u: number) =>
                `opacity: ${t}; transform: translateY(${u * shift}px) scale(${0.95 + 0.05 * t})`,
        };
    }

    /** Going away is the same, without the slide - it shrinks in place, as it did before. */
    function shrink() {
        return {
            duration: 150,
            easing: ease,
            css: (t: number) => `opacity: ${t}; transform: scale(${0.95 + 0.05 * t})`,
        };
    }
</script>

<svelte:window on:keydown={onKeydown} on:scroll={reposition} on:resize={reposition} />

<span
    bind:this={trigger}
    aria-describedby={open ? id : undefined}
    on:pointerenter={show}
    on:pointerleave={hide}
    on:pointerdown={hideNow}
    on:focusin={show}
    on:focusout={hideNow}
>
    <slot />
</span>

{#if open}
    <div
        use:float
        {id}
        role="tooltip"
        in:grow
        out:shrink
        class="bubble fixed z-50 rounded-md bg-accent px-3 py-1.5 text-xs text-white"
        class:below={!above}
        style="left: {left}px; top: {top}px; transform-origin: {originX}px {above ? '100%' : '0'}"
        on:pointerenter={keep}
        on:pointerleave={hide}
    >
        {text}
    </div>
{/if}

<style>
    /* The gap between the trigger and the bubble, made part of the bubble, so that crossing it
       slowly is not the same as leaving. Transparent, and only as deep as the offset. */
    .bubble::after {
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        height: 6px;
        bottom: -6px;
    }
    .bubble.below::after {
        bottom: auto;
        top: -6px;
    }
</style>
