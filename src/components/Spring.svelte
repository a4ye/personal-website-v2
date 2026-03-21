<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import petalSvg from "/src/assets/leaf.svg";
    let enabled: boolean = true;

    let canvas: HTMLCanvasElement;
    let context: CanvasRenderingContext2D;
    let animationFrameId: number;
    let petalImg: HTMLImageElement;

    type Petal = {
        x: number;
        y: number;
        size: number;
        fallSpeed: number;
        drift: number;
        layer: number;
        rotation: number;
        rotationSpeed: number;
        swayPhase: number;
        swaySpeed: number;
    };

    type PetalLayer = {
        baseCount: number;
        count: number;
        minSize: number;
        maxSize: number;
        minSpeed: number;
        maxSpeed: number;
        minAngleDeg: number;
        maxAngleDeg: number;
        petals: Petal[];
        alpha: number;
    };

    const BASE_WIDTH = 1920;
    const BASE_HEIGHT = 1080;
    const BASE_AREA = BASE_WIDTH * BASE_HEIGHT;

    const layers: PetalLayer[] = [
        {
            baseCount: 20,
            count: 40,
            minSize: 14,
            maxSize: 22,
            minSpeed: 50,
            maxSpeed: 60,
            minAngleDeg: 50,
            maxAngleDeg: 65,
            petals: [],
            alpha: 0.4,
        },
        {
            baseCount: 15,
            count: 30,
            minSize: 18,
            maxSize: 26,
            minSpeed: 60,
            maxSpeed: 70,
            minAngleDeg: 50,
            maxAngleDeg: 65,
            petals: [],
            alpha: 0.6,
        },
        {
            baseCount: 8,
            count: 20,
            minSize: 26,
            maxSize: 32,
            minSpeed: 70,
            maxSpeed: 80,
            minAngleDeg: 50,
            maxAngleDeg: 65,
            petals: [],
            alpha: 0.8,
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
            layer.count = Math.max(5, Math.round(layer.baseCount * sf));
        });
    }

    function adjustLayerPetalsForCount() {
        layers.forEach((layer, idx) => {
            if (!layer.petals) layer.petals = [];
            if (layer.petals.length > layer.count) {
                layer.petals.length = layer.count;
            }
            while (layer.petals.length < layer.count) {
                layer.petals.push(createPetal(idx, -50));
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
        adjustLayerPetalsForCount();

        context.clearRect(0, 0, canvas.width, canvas.height);
    }

    function createPetal(
        layerIndex: number,
        startY = Math.random() * window.innerHeight,
    ): Petal {
        const layer = layers[layerIndex];
        const size = layer.minSize + Math.random() * (layer.maxSize - layer.minSize);
        const fallSpeed = layer.minSpeed + Math.random() * (layer.maxSpeed - layer.minSpeed);
        const angleDeg =
            layer.minAngleDeg + Math.random() * (layer.maxAngleDeg - layer.minAngleDeg);
        const angleRad = (angleDeg * Math.PI) / 180;
        const drift = Math.cos(angleRad) * fallSpeed;
        const verticalSpeed = Math.sin(angleRad) * fallSpeed;
        return {
            x: Math.random() * window.innerWidth,
            y: startY,
            size,
            fallSpeed: verticalSpeed,
            drift,
            layer: layerIndex,
            rotation: Math.random() * Math.PI * 2,
            rotationSpeed: (Math.random() - 0.5) * 2,
            swayPhase: Math.random() * Math.PI * 2,
            swaySpeed: 1 + Math.random() * 2,
        };
    }

    function initializeLayers() {
        updateCounts();
        for (let i = 0; i < layers.length; i++) {
            const layer = layers[i];
            layer.petals = Array.from({ length: layer.count }, () => createPetal(i));
        }
    }

    let lastTimestamp = performance.now();

    function drawFrame(ts?: number) {
        const now = ts ?? performance.now();
        const delta = Math.min((now - lastTimestamp) / 1000, 0.1);
        lastTimestamp = now;

        context.clearRect(0, 0, canvas.width, canvas.height);

        layers.forEach((layer) => {
            layer.petals = layer.petals.filter(
                (petal) => petal.y < window.innerHeight + petal.size * 2,
            );
            while (layer.petals.length < layer.count) {
                layer.petals.push(createPetal(layer.petals[0]?.layer ?? 0, -50));
            }

            context.save();
            context.globalAlpha = layer.alpha;
            layer.petals.forEach((petal) => {
                if (petalImg) {
                    context.save();

                    const sway = Math.sin(petal.swayPhase) * 30;
                    context.translate(petal.x + sway, petal.y);
                    context.rotate(petal.rotation);
                    context.drawImage(
                        petalImg,
                        -petal.size / 2,
                        -petal.size / 2,
                        petal.size,
                        petal.size,
                    );
                    context.restore();
                }

                petal.y += petal.fallSpeed * delta;
                petal.x += petal.drift * delta;
                petal.rotation += petal.rotationSpeed * delta;
                petal.swayPhase += petal.swaySpeed * delta;

                if (petal.x > window.innerWidth + 50) petal.x = -50;
                if (petal.x < -50) petal.x = window.innerWidth + 50;
            });
            context.restore();
        });

        animationFrameId = window.requestAnimationFrame(drawFrame);
    }

    let initialized = false;

    function startSpring() {
        if (initialized || !canvas) return;
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        context = canvas.getContext("2d")!;
        window.addEventListener("resize", resizeCanvas);

        petalImg = new Image();
        petalImg.src = petalSvg.src;
        petalImg.onload = () => {
            resizeCanvas();
            initializeLayers();
            drawFrame();
        };
        initialized = true;
    }

    function stopSpring() {
        if (animationFrameId) {
            window.cancelAnimationFrame(animationFrameId);
            animationFrameId = 0;
        }
        window.removeEventListener("resize", resizeCanvas);
        initialized = false;
    }

    function handleSpringToggle(e: CustomEvent<{ enabled: boolean }>) {
        enabled = e.detail.enabled;
        if (enabled) {
            setTimeout(() => startSpring(), 0);
        } else {
            stopSpring();
        }
    }

    onMount(() => {
        const stored = localStorage.getItem("spring-enabled");
        if (stored !== null) {
            enabled = stored === "true";
        }

        window.addEventListener("spring-toggle", handleSpringToggle as EventListener);

        if (enabled) {
            startSpring();
        }
    });

    onDestroy(() => {
        stopSpring();
        window.removeEventListener("spring-toggle", handleSpringToggle as EventListener);
    });
</script>

{#if enabled}
    <canvas bind:this={canvas} class="fixed inset-0 pointer-events-none z-[999999]"></canvas>
{/if}
