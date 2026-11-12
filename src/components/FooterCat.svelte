<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    // Files, not data URLs: the small ones would otherwise be written into the script
    import catImage from "../assets/cat/cat.avif?url&no-inline";
    import nearEyeImage from "../assets/cat/eye-near.webp?url&no-inline";
    import farEyeImage from "../assets/cat/eye-far.webp?url&no-inline";
    import butterflyImage from "../assets/cat/butterfly.webp?url&no-inline";

    /**
     * The cat behind the footer line.
     *
     * It stands against the right edge of the screen, and only the tips of its ears show above the
     * line. Pressing them brings the cat up, where it blinks now and then and watches the cursor,
     * or a butterfly that comes by every few seconds while the cursor is still. Pressing it while
     * it is up gets a blink back, held shut a little longer. Scrolling the footer away sends it
     * back down. Both come from one pin, cut out and recoloured by scripts/cat-art/cat.py.
     */

    // The picture, as printed by cat.py: its width over its height, and the box each eye lies in,
    // as fractions of it. The eyes are dots laid over the cat, which has none under them: they
    // move to look, and squash to blink. look is how far each moves: the far eye is turned away,
    // so less of the move shows. tilt is the angle, in degrees up from level, of the way its lids
    // go, as the face is turned: the long way across the dot. Shut, it is a line across that.
    const ASPECT = 400 / 604;
    const NEAR_EYE = {
        left: 0.4004,
        top: 0.3215,
        width: 0.1141,
        height: 0.083,
        look: 0.5,
        tilt: 80,
    };
    const FAR_EYE = {
        left: 0.0984,
        top: 0.3156,
        width: 0.0872,
        height: 0.0607,
        look: 0.35,
        tilt: 70,
    };
    const SQUASH = 0.88; // how much of a dot's length goes, shut: what is left is the line of a shut eye
    const place = (eye: typeof NEAR_EYE) =>
        `left: ${eye.left * 100}%; top: ${eye.top * 100}%; ` +
        `width: ${eye.width * 100}%; height: ${eye.height * 100}%;`;
    // Turned so that the way its lids go is level, squashed that way, and turned back
    const lids = (eye: typeof NEAR_EYE, shut: number) =>
        shut
            ? `transform: rotate(${-eye.tilt}deg) scaleX(${1 - SQUASH * shut}) rotate(${eye.tilt}deg);`
            : "";
    // How much of it shows. Hiding, the top 13%: its ears. Up, the top 75%: its head and neck;
    // the bottom of the picture is cut straight, and stays behind the line.
    const PEEK = 0.2;
    const SHOW = 0.75;
    // What takes a press: the cat's outline, MARGIN of its width out round it, as printed by
    // cat.py, in a box that much bigger than the picture all round. Only what shows of it takes
    // one, so while the cat hides, that is its ears and the margin round them.
    const MARGIN = 0.05;
    const OUTLINE =
        "polygon(52.7% 1.3%, 48.2% 2.8%, 43.3% 6.3%, 35.7% 15.9%, 30.6% 19.2%, 20.0% 24.1%, 15.5% 27.4%, 7.6% 34.8%, 2.4% 42.2%, 1.0% 46.1%, 0.6% 54.7%, 5.5% 65.5%, 11.2% 73.0%, 14.1% 81.3%, 12.2% 97.5%, 14.1% 99.4%, 16.7% 100.0%, 96.9% 99.9%, 99.2% 98.7%, 100.0% 97.5%, 100.0% 5.8%, 99.2% 4.6%, 96.9% 3.5%, 89.0% 3.9%, 71.4% 14.9%, 67.6% 12.7%, 65.9% 9.2%, 59.0% 2.6%, 56.1% 1.3%)";

    const FIRST = 1200; // ms after it comes up before the first butterfly
    const BETWEEN = [4000, 8000]; // ms from one butterfly leaving to the next coming
    const FLIGHT = 7000;
    // The butterfly's way past, through these points, as fractions of the cat's width from its
    // top left. It stays on the side the cat faces: in from the left, a while where the cat looks
    // in the pin (beside its head, as high as its ears), a loop over its head, and away up to the
    // left.
    const PATH = [
        [-1.7, 0.15],
        [-0.9, -0.05],
        [-0.32, 0.0],
        [0.25, -0.3],
        [-0.15, -0.55],
        [-0.9, -0.9],
    ];

    // It watches the cursor, or the butterfly once the cursor has been still a while: its eyes go
    // there quickly, and its head follows more slowly, leaning a little that way, and standing a
    // little taller for something above. All of it eases there, and nothing goes past.
    const REST = PATH[2]; // where it looks as painted; looking there, it is as painted
    const LEAN = 2.5; // degrees, at most
    const CRANE = 0.015; // of its height, at most
    const REACH = 1.5; // cat widths to the side, or above, at which it leans or stands all the way
    const LOOK = 0.014; // cat widths the near eye moves, at most
    const EYE_TIME = 60; // ms for the eyes to go most of the way there
    const HEAD_TIME = 400;
    const BORED = 3000; // ms after the cursor stops before the cat stops watching it

    let spot: HTMLDivElement;
    let cat: HTMLDivElement; // wider than spot: the rest of it is past the edge of the screen
    let up = false;
    let curious = false;
    let shut = 0; // how shut the eyes are, from 0 to 1
    let ready = false; // the eyes are only asked for once the footer has come into view
    let fly: { x: number; y: number; opacity: number } | null = null;
    let found = false;
    let calm = false; // the reader has asked for less motion: it comes up and blinks, and that is all
    let observer: IntersectionObserver | null = null;
    let blinkTimer: ReturnType<typeof setTimeout>;
    let butterflyTimer: ReturnType<typeof setTimeout>;
    let frame = 0;
    let lidFrame = 0;
    let watchFrame = 0;
    let lean = 0; // degrees, to the right
    let crane = 0;
    let nearLook = [0, 0]; // px each eye has moved
    let farLook = [0, 0];
    let pointer = { x: 0, y: 0, at: -Infinity }; // the cursor, and when it last moved

    /** Shut, held shut for hold ms, and open again. */
    function blink(hold: number) {
        clearTimeout(blinkTimer);
        cancelAnimationFrame(lidFrame);
        const closing = 90; // ms
        const opening = 160; // a little slower, as eyes do
        const start = performance.now();
        const step = (now: number) => {
            const t = now - start;
            // How shut, from 0 open to 1 shut, easing in and out of each move: the lids settle
            // shut and open, they are not pressed
            const o = (t - closing - hold) / opening;
            const s = t < closing ? t / closing : t < closing + hold ? 1 : o < 1 ? 1 - o : 0;
            shut = s * s * (3 - 2 * s);
            if (o < 1) {
                lidFrame = requestAnimationFrame(step);
                return;
            }
            lidFrame = 0;
            if (up && !calm) blinkLater();
        };
        lidFrame = requestAnimationFrame(step);
    }

    function blinkLater() {
        clearTimeout(blinkTimer);
        blinkTimer = setTimeout(() => blink(60), 3000 + Math.random() * 4000);
    }

    function butterflyLater(ms: number) {
        clearTimeout(butterflyTimer);
        butterflyTimer = setTimeout(flyPast, ms);
    }

    /** A point on a smooth curve through PATH (Catmull-Rom), at u from 0 to 1. */
    function along(u: number) {
        const last = PATH.length - 1;
        const at = Math.min(u * last, last - 1e-6);
        const i = Math.floor(at);
        const t = at - i;
        const [p0, p1, p2, p3] = [i - 1, i, i + 1, i + 2].map(
            (k) => PATH[Math.max(0, Math.min(last, k))],
        );
        return [0, 1].map(
            (d) =>
                0.5 *
                (2 * p1[d] +
                    (p2[d] - p0[d]) * t +
                    (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t * t +
                    (3 * p1[d] - p0[d] - 3 * p2[d] + p3[d]) * t * t * t),
        );
    }

    function flyPast() {
        const w = cat.offsetWidth;
        const start = performance.now();
        const step = (now: number) => {
            const u = Math.min((now - start) / FLIGHT, 1);
            const [fx, fy] = along(u);
            fly = {
                x: fx * w,
                y: fy * w + 6 * Math.sin(14 * Math.PI * u), // and up and down as it flaps
                opacity: Math.min(u / 0.1, 1, (1 - u) / 0.1),
            };
            if (u < 1) {
                frame = requestAnimationFrame(step);
            } else {
                frame = 0;
                fly = null;
                butterflyLater(BETWEEN[0] + Math.random() * (BETWEEN[1] - BETWEEN[0]));
            }
        };
        frame = requestAnimationFrame(step);
    }

    /** Where to look, in px from the cat's top left. */
    function target(w: number) {
        if (up && performance.now() - pointer.at < BORED) {
            const box = spot.getBoundingClientRect();
            return [pointer.x - box.left, pointer.y - box.top];
        }
        if (fly && fly.opacity > 0.2) return [fly.x + 17, fly.y + 15]; // the butterfly's middle
        return [REST[0] * w, REST[1] * w];
    }

    /** How far, in px, an eye moves to look at a point, from where it looks as painted. */
    function looking(eye: typeof NEAR_EYE, point: number[], w: number) {
        const x = (eye.left + eye.width / 2) * w;
        const y = ((eye.top + eye.height / 2) * w) / ASPECT;
        const way = ([px, py]: number[]) => {
            const d = Math.hypot(px - x, py - y) || 1;
            return [(px - x) / d, (py - y) / d];
        };
        const [tx, ty] = way(point);
        const [rx, ry] = way([REST[0] * w, REST[1] * w]);
        // As far as it can go for anything more than about 35 degrees from where it looks; and for
        // something right up against the eye, there is no telling which way, so hardly at all
        const gain = Math.min(1.7, 1 / (Math.hypot(tx - rx, ty - ry) || 1));
        const sure = Math.min(Math.hypot(point[0] - x, point[1] - y) / (0.2 * w), 1);
        const most = LOOK * w * eye.look * sure * gain;
        return [(tx - rx) * most, (ty - ry) * most];
    }

    /** Eyes and head after what it watches, until it has gone down and they have come back. */
    function watch() {
        cancelAnimationFrame(watchFrame);
        let last = performance.now();
        const step = (now: number) => {
            const eyes = 1 - Math.exp(-(now - last) / EYE_TIME);
            const head = 1 - Math.exp(-(now - last) / HEAD_TIME);
            last = now;
            const w = cat.offsetWidth;
            const point = target(w);
            const toward = (from: number[], to: number[]) =>
                from.map((v, i) => v + (to[i] - v) * eyes);
            nearLook = toward(nearLook, looking(NEAR_EYE, point, w));
            farLook = toward(farLook, looking(FAR_EYE, point, w));
            const side = Math.max(-1, Math.min((point[0] - REST[0] * w) / (REACH * w), 1));
            const above = Math.max(0, Math.min((REST[1] * w - point[1]) / (REACH * w), 1));
            lean += (side * LEAN - lean) * head;
            crane += (above * CRANE - crane) * head;
            const settled =
                Math.abs(lean) < 0.01 && crane < 1e-4 && Math.hypot(...nearLook, ...farLook) < 0.05;
            if (!up && settled) {
                [lean, crane, nearLook, farLook, watchFrame] = [0, 0, [0, 0], [0, 0], 0];
                return;
            }
            watchFrame = requestAnimationFrame(step);
        };
        watchFrame = requestAnimationFrame(step);
    }

    function press() {
        if (up) {
            blink(110); // held a little longer: a cat blinks hello
            return;
        }
        up = true;
        curious = false;
        if (!found) {
            found = true;
            (window as any).umami?.track("cat-found");
        }
        if (calm) return;
        blinkLater();
        butterflyLater(FIRST);
        watch();
    }

    function hide() {
        up = false;
        shut = 0;
        fly = null;
        clearTimeout(blinkTimer);
        clearTimeout(butterflyTimer);
        cancelAnimationFrame(frame);
        cancelAnimationFrame(lidFrame);
        frame = 0;
        lidFrame = 0;
    }

    // A finger on a touch screen is not something to watch: it is only there while it touches
    function moved(event: PointerEvent) {
        if (event.pointerType !== "touch")
            pointer = { x: event.clientX, y: event.clientY, at: event.timeStamp };
    }

    onMount(() => {
        calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        window.addEventListener("pointermove", moved, { passive: true });
        ready = true;
        observer = new IntersectionObserver(([entry]) => {
            if (!entry.isIntersecting) hide();
        });
        observer.observe(spot);
    });

    onDestroy(() => {
        observer?.disconnect();
        if (!spot) return; // rendered on the server, where none of this was started
        window.removeEventListener("pointermove", moved);
        cancelAnimationFrame(watchFrame);
        hide();
    });
</script>

<div
    class="spot"
    class:up
    class:curious
    bind:this={spot}
    style="--aspect: {ASPECT}; --peek: {PEEK}; --show: {SHOW}; --margin: {MARGIN};"
>
    <div class="window">
        <div class="cat" bind:this={cat} style="transform: skewX({-lean}deg) scaleY({1 + crane});">
            <img
                class="body"
                src={catImage}
                alt=""
                draggable="false"
                loading="lazy"
                decoding="async"
            />
            <!-- Written out, not in an #each: that would bring Svelte's list code for two eyes -->
            <span
                class="eye"
                style="{place(NEAR_EYE)} translate: {nearLook[0]}px {nearLook[1]}px; {lids(
                    NEAR_EYE,
                    shut,
                )} {ready ? `background-image: url(${nearEyeImage});` : ''}"
            ></span>
            <span
                class="eye"
                style="{place(FAR_EYE)} translate: {farLook[0]}px {farLook[1]}px; {lids(
                    FAR_EYE,
                    shut,
                )} {ready ? `background-image: url(${farEyeImage});` : ''}"
            ></span>
            <!-- In the cat, so that it goes up and leans with it -->
            <button
                class="hit"
                type="button"
                style="clip-path: {OUTLINE};"
                aria-label={up ? "Pet the cat" : "Something is hiding behind the line"}
                on:click={press}
                on:pointerenter={(e) => (curious = !up && e.pointerType === "mouse")}
                on:pointerleave={() => (curious = false)}
            ></button>
        </div>
    </div>
    {#if fly}
        <img
            class="butterfly"
            src={butterflyImage}
            alt=""
            aria-hidden="true"
            style="translate: {fly.x}px {fly.y}px; opacity: {fly.opacity};"
        />
    {/if}
</div>

<style>
    .spot {
        --w: 170px;
        --h: calc(var(--w) / var(--aspect));
        /* How much of the cat is past the right edge of the screen. Where the pin cuts it off is
           there, out of sight, even when it leans away from the edge. */
        --past: calc(var(--w) * 0.06);
        position: absolute;
        /* The footer starts with its line; this puts the cat just above it */
        bottom: 100%;
        right: 0;
        width: calc(var(--w) - var(--past));
        height: calc(var(--h) * var(--show));
        pointer-events: none;
        /* Neither the cat nor the butterfly is picked up when the page's text is selected */
        -webkit-user-select: none;
        user-select: none;
    }

    /* Up, it stands over whatever is above the footer, and a phone has less room to spare */
    @media (max-width: 39.999rem) {
        .spot {
            --w: 130px;
        }
    }

    /* Everything of the cat below the line is cut off here, which is what hides it, and
       everything past the edge of the screen. Above and to the left there is room for it to lean
       and stand taller. */
    .window {
        --room: 12px;
        position: absolute;
        inset: calc(-1 * var(--room)) 0 0 calc(-1 * var(--room));
        overflow: clip; /* not hidden: that can still be scrolled, as focusing the button does */
    }

    .cat {
        position: absolute;
        left: var(--room);
        top: var(--room);
        width: var(--w);
        height: var(--h);
        /* It leans from where it meets the line */
        transform-origin: 50% calc(var(--show) * 100%);
        translate: 0 calc(var(--h) * (var(--show) - var(--peek)));
        transition: translate 0.35s ease-in;
    }

    .curious .cat {
        translate: 0 calc(var(--h) * (var(--show) - var(--peek)) - 6px);
        transition: translate 0.3s ease-out;
    }

    .up .cat {
        translate: 0 0;
        transition: translate 0.6s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .body {
        width: 100%;
        height: 100%;
    }

    /* A shut eye is a line a little below the middle of the dot, where its lids meet */
    .eye {
        position: absolute;
        background-size: 100% 100%;
        transform-origin: 50% 60%;
    }

    .butterfly {
        position: absolute;
        left: 0;
        top: 0;
        width: 34px;
        animation: flap 0.16s ease-in-out infinite alternate;
    }

    @keyframes flap {
        to {
            scale: 0.35 1;
        }
    }

    /* The box OUTLINE is drawn in */
    .hit {
        position: absolute;
        left: calc(var(--w) * var(--margin) * -1);
        top: calc(var(--w) * var(--margin) * -1);
        width: calc(var(--w) * (1 + 2 * var(--margin)));
        height: calc(var(--h) + var(--w) * 2 * var(--margin));
        pointer-events: auto;
        cursor: pointer;
    }

    /* The outline cuts the browser's focus ring round the button down to a sliver, so the ring
       goes round what shows of the cat instead */
    .hit:focus-visible {
        outline: none;
    }

    .spot:has(.hit:focus-visible)::after {
        content: "";
        position: absolute;
        inset: auto 0 0;
        height: calc(var(--h) * var(--peek));
        outline: 2px solid var(--color-accent);
        outline-offset: 2px;
        border-radius: 0.5rem;
    }

    .up:has(.hit:focus-visible)::after {
        height: 100%;
    }

    @media (prefers-reduced-motion: reduce) {
        .cat {
            transition: none;
        }
    }
</style>
