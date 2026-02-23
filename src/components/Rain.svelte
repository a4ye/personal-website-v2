<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    let enabled: boolean = true;

    let canvas: HTMLCanvasElement;
    let context: CanvasRenderingContext2D;
    let animationFrameId: number;

    type Raindrop = {
        x: number;
        y: number;
        length: number;
        speed: number;
        opacity: number;
    };

    type RainLayer = {
        baseCount: number;
        count: number;
        minLength: number;
        maxLength: number;
        minSpeed: number;
        maxSpeed: number;
        drops: Raindrop[];
        alpha: number;
    };

    const BASE_WIDTH = 1920;
    const BASE_HEIGHT = 1080;
    const BASE_AREA = BASE_WIDTH * BASE_HEIGHT;

    const layers: RainLayer[] = [
        {
            baseCount: 100,
            count: 100,
            minLength: 10,
            maxLength: 15,
            minSpeed: 400,
            maxSpeed: 500,
            drops: [],
            alpha: 0.15,
        },
        {
            baseCount: 80,
            count: 80,
            minLength: 15,
            maxLength: 22,
            minSpeed: 500,
            maxSpeed: 650,
            drops: [],
            alpha: 0.25,
        },
        {
            baseCount: 50,
            count: 50,
            minLength: 22,
            maxLength: 30,
            minSpeed: 650,
            maxSpeed: 800,
            drops: [],
            alpha: 0.35,
        },
    ];

    function getScaleFactor() {
        const area = window.innerWidth * window.innerHeight;
        const raw = area / BASE_AREA;
        return Math.max(0.25, Math.min(raw, 3));
    }

    function updateCounts() {
        const sf = getScaleFactor();
        layers.forEach((layer) => {
            layer.count = Math.max(10, Math.round(layer.baseCount * sf));
        });
    }

    function adjustLayerDropsForCount() {
        layers.forEach((layer, idx) => {
            if (!layer.drops) layer.drops = [];
            if (layer.drops.length > layer.count) {
                layer.drops.length = layer.count;
            }
            while (layer.drops.length < layer.count) {
                layer.drops.push(createRaindrop(idx, -50));
            }
        });
    }

    function resizeCanvas() {
        const dpr = window.devicePixelRatio || 1;
        const width = window.innerWidth;
        const height = window.innerHeight;

        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;

        context.setTransform(dpr, 0, 0, dpr, 0, 0);

        updateCounts();
        adjustLayerDropsForCount();

        context.clearRect(0, 0, canvas.width, canvas.height);
    }

    function createRaindrop(
        layerIndex: number,
        startY = Math.random() * window.innerHeight,
    ): Raindrop {
        const layer = layers[layerIndex];
        const length = layer.minLength + Math.random() * (layer.maxLength - layer.minLength);
        const speed = layer.minSpeed + Math.random() * (layer.maxSpeed - layer.minSpeed);
        return {
            x: Math.random() * window.innerWidth,
            y: startY,
            length,
            speed,
            opacity: 0.3 + Math.random() * 0.5,
        };
    }

    function initializeLayers() {
        updateCounts();
        for (let i = 0; i < layers.length; i++) {
            const layer = layers[i];
            layer.drops = Array.from({ length: layer.count }, () => createRaindrop(i));
        }
    }

    let lastTimestamp = performance.now();

    function drawFrame(ts?: number) {
        const now = ts ?? performance.now();
        const delta = Math.min((now - lastTimestamp) / 1000, 0.1);
        lastTimestamp = now;

        context.clearRect(0, 0, canvas.width, canvas.height);

        layers.forEach((layer) => {
            layer.drops = layer.drops.filter(
                (drop) => drop.y < window.innerHeight + drop.length,
            );
            while (layer.drops.length < layer.count) {
                layer.drops.push(createRaindrop(layer.drops[0] ? 0 : 0, -50));
            }

            context.save();
            context.strokeStyle = `rgba(174, 194, 224, ${layer.alpha})`;
            context.lineWidth = 1.5;
            context.lineCap = "round";

            layer.drops.forEach((drop) => {
                context.save();
                context.globalAlpha = drop.opacity;
                context.beginPath();
                context.moveTo(drop.x, drop.y);
                context.lineTo(drop.x + 2, drop.y + drop.length);
                context.stroke();
                context.restore();

                drop.y += drop.speed * delta;
                drop.x += 30 * delta; // slight wind drift

                if (drop.x > window.innerWidth + 50) drop.x = -10;
            });
            context.restore();
        });

        animationFrameId = window.requestAnimationFrame(drawFrame);
    }

    let initialized = false;

    function startRain() {
        if (initialized || !canvas) return;
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        context = canvas.getContext("2d")!;
        window.addEventListener("resize", resizeCanvas);

        resizeCanvas();
        initializeLayers();
        drawFrame();
        initialized = true;
    }

    function stopRain() {
        if (animationFrameId) {
            window.cancelAnimationFrame(animationFrameId);
            animationFrameId = 0;
        }
        window.removeEventListener("resize", resizeCanvas);
        initialized = false;
    }

    function handleRainToggle(e: CustomEvent<{ enabled: boolean }>) {
        enabled = e.detail.enabled;
        if (enabled) {
            setTimeout(() => startRain(), 0);
        } else {
            stopRain();
        }
    }

    onMount(() => {
        const stored = localStorage.getItem("rain-enabled");
        if (stored !== null) {
            enabled = stored === "true";
        }

        window.addEventListener("rain-toggle", handleRainToggle as EventListener);

        if (enabled) {
            startRain();
        }
    });

    onDestroy(() => {
        stopRain();
        window.removeEventListener("rain-toggle", handleRainToggle as EventListener);
    });
</script>

{#if enabled}
    <canvas bind:this={canvas} class="fixed inset-0 pointer-events-none z-[999999]"></canvas>
{/if}
