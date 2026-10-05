/**
 * The hero shader, and everything that draws it.
 *
 * This lives apart from the component so it can run in either of two places. Compiling and linking
 * the program blocks whichever thread asks whether it is finished - 375 ms on a machine that has
 * never seen the page, because the driver has nothing cached - and that is the last thing on this
 * site that blocks anything. So the component hands the canvas to a worker and this runs there,
 * where a stall costs nobody anything. Browsers that cannot transfer a canvas run it on the main
 * thread exactly as before.
 */

const vertexShaderSource = `
    attribute vec2 a_position;
    varying vec2 v_uv;
    void main() {
        v_uv = a_position * 0.5 + 0.5;
        gl_Position = vec4(a_position, 0.0, 1.0);
    }
`;

// Liquify effect + chromatic aberration + mouse tracking (nucleo's exact algorithm)
const fragmentShaderSource = `
    precision highp float;
    varying vec2 v_uv;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec2 u_mouse;
    uniform sampler2D u_texture;
    uniform float u_hueShift;

    const float PI = 3.14159265;

    mat2 rot(float a) {
        return mat2(cos(a), -sin(a), sin(a), cos(a));
    }

    // Nucleo's exact liquify algorithm with mouse-driven center
    vec2 liquify(vec2 st, float rotAngle, float freq, float amplitude, float speed, vec2 center) {
        float aspectRatio = u_resolution.x / u_resolution.y;

        st -= center;
        st.x *= aspectRatio;
        st = st * rot(rotAngle * 2.0 * PI);

        float t = u_time * speed;

        for (float i = 1.0; i <= 5.0; i++) {
            st = st * rot(i / 5.0 * PI * 2.0);
            float ff = i * freq;
            st.x += amplitude * cos(ff * st.y + t);
            st.y += amplitude * sin(ff * st.x + t);
        }

        st = st * rot(rotAngle * -2.0 * PI);
        st.x /= aspectRatio;
        st += center;

        return st;
    }

    void main() {
        vec2 uv = v_uv;

        float screenAspect = u_resolution.x / u_resolution.y;

        // On landscape screens rotate 90° clockwise; on portrait use image as-is
        vec2 texUV;
        float imageAspect;
        if (screenAspect >= 1.0) {
            texUV = vec2(1.0 - uv.y, uv.x);
            imageAspect = 1530.0 / 1122.0;
            // After rotation UV axes are swapped, so crop logic is inverted
            if (screenAspect > imageAspect) {
                float scale = screenAspect / imageAspect;
                texUV.x = (texUV.x - 0.5) / scale + 0.5;
            } else {
                float scale = imageAspect / screenAspect;
                texUV.y = (texUV.y - 0.5) / scale + 0.5;
            }
        } else {
            texUV = vec2(1.0 - uv.x, 1.0 - uv.y);
            imageAspect = 1122.0 / 1530.0;
            if (screenAspect > imageAspect) {
                float scale = screenAspect / imageAspect;
                texUV.y = (texUV.y - 0.5) / scale + 0.5;
            } else {
                float scale = imageAspect / screenAspect;
                texUV.x = (texUV.x - 0.5) / scale + 0.5;
            }
        }

        // Mirror horizontally
        texUV.y = 1.0 - texUV.y;

        // Liquify pass 1
        vec2 center1 = vec2(0.5, 0.5) + (u_mouse - 0.5) * 0.3;
        float freq1 = 5.0 * (0.14 + 0.1);
        float amp1 = 0.34 * mix(0.2, 0.2 / (0.14 + 0.05), 0.25) * 0.4;
        vec2 uv1 = mix(texUV, liquify(texUV, 0.8807, freq1, amp1, 0.0, center1), 0.15);

        // Liquify pass 2
        vec2 center2 = vec2(0.5, 0.5) + (u_mouse - 0.5) * 0.2;
        float freq2 = 5.0 * (1.27 + 0.1);
        float amp2 = 0.23 * mix(0.2, 0.2 / (1.27 + 0.05), 0.25) * 0.2;
        vec2 finalUV = clamp(mix(uv1, liquify(uv1, 0.121, freq2, amp2, 0.0, center2), 0.08), 0.0, 1.0);

        vec3 color = texture2D(u_texture, finalUV).rgb;

        // Hue shift
        if (u_hueShift > 0.001) {
            float mx = max(color.r, max(color.g, color.b));
            float mn = min(color.r, min(color.g, color.b));
            float d = mx - mn;
            float l = (mx + mn) * 0.5;
            float s = d < 0.001 ? 0.0 : d / (1.0 - abs(2.0 * l - 1.0));
            float h = 0.0;
            if (d > 0.001) {
                if (mx == color.r) h = mod((color.g - color.b) / d, 6.0) / 6.0;
                else if (mx == color.g) h = ((color.b - color.r) / d + 2.0) / 6.0;
                else h = ((color.r - color.g) / d + 4.0) / 6.0;
            }
            h = fract(h + u_hueShift);
            if (s > 0.001) {
                float q = l < 0.5 ? l * (1.0 + s) : l + s - l * s;
                float p = 2.0 * l - q;
                vec3 t3 = fract(vec3(h + 1.0/3.0, h, h - 1.0/3.0));
                color.r = t3.x < 1.0/6.0 ? p+(q-p)*6.0*t3.x : t3.x < 0.5 ? q : t3.x < 2.0/3.0 ? p+(q-p)*(2.0/3.0-t3.x)*6.0 : p;
                color.g = t3.y < 1.0/6.0 ? p+(q-p)*6.0*t3.y : t3.y < 0.5 ? q : t3.y < 2.0/3.0 ? p+(q-p)*(2.0/3.0-t3.y)*6.0 : p;
                color.b = t3.z < 1.0/6.0 ? p+(q-p)*6.0*t3.z : t3.z < 0.5 ? q : t3.z < 2.0/3.0 ? p+(q-p)*(2.0/3.0-t3.z)*6.0 : p;
            }
        }

        color = clamp(color, 0.0, 1.0);

        gl_FragColor = vec4(color, 1.0);
    }
`;

export interface Renderer {
    /** CSS pixels; the device pixel ratio is applied here. */
    setSize(width: number, height: number, dpr: number): void;
    /** The pointer, already as a fraction of the canvas, y counted from the bottom. */
    setMouse(x: number, y: number): void;
    setHue(hueShift: number): void;
    setTexture(blob: Blob): Promise<void>;
    start(): void;
    stop(): void;
    destroy(): void;
}

type AnyCanvas = HTMLCanvasElement | OffscreenCanvas;

function createShader(gl: WebGLRenderingContext, type: number, source: string) {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    // Deliberately not asking for COMPILE_STATUS here: the question cannot be answered until the
    // driver has finished, so asking is what makes the compile block. If anything did go wrong,
    // the link below fails and the logs are read then.
    return shader;
}

/**
 * Build the program, asking the driver whether it is finished rather than waiting for it.
 *
 * KHR_parallel_shader_compile adds a status flag that is meant to be readable without stalling.
 * ANGLE on desktop OpenGL blocks on it anyway, which is the reason the whole renderer is kept off
 * the main thread; on the drivers that do honour it this also keeps the worker responsive. The
 * deadline is for drivers that never report completion.
 */
async function createProgram(gl: WebGLRenderingContext) {
    const vs = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);
    if (!vs || !fs) return null;
    const program = gl.createProgram();
    if (!program) return null;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);

    const parallel = gl.getExtension("KHR_parallel_shader_compile");
    if (parallel) {
        const deadline = performance.now() + 2000;
        while (
            !gl.getProgramParameter(program, parallel.COMPLETION_STATUS_KHR) &&
            performance.now() < deadline
        ) {
            await new Promise((resolve) => setTimeout(resolve, 8));
        }
    }

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        console.error(
            "hero program link error:",
            gl.getProgramInfoLog(program),
            gl.getShaderInfoLog(vs),
            gl.getShaderInfoLog(fs),
        );
        gl.deleteProgram(program);
        return null;
    }
    return program;
}

export function createRenderer(canvas: AnyCanvas, hueShift: number): Renderer | null {
    const gl = canvas.getContext("webgl", {
        antialias: false,
        alpha: false,
    }) as WebGLRenderingContext | null;
    if (!gl) {
        console.error("WebGL not supported");
        return null;
    }

    let program: WebGLProgram | null = null;
    let uniforms: Record<string, WebGLUniformLocation | null> = {};
    let hasTexture = false;
    let wanted = false;
    let frame = 0;
    let startTime = 0;
    let pausedAt = 0;
    let mouseX = 0.5;
    let mouseY = 0.5;
    let targetMouseX = 0.5;
    let targetMouseY = 0.5;

    // rAF exists on a dedicated worker, and ties the loop to the page's own frames; the timer is
    // only there for anything that does not have it.
    const nextFrame: (cb: (now: number) => void) => number =
        typeof requestAnimationFrame === "function"
            ? requestAnimationFrame
            : (cb) => setTimeout(() => cb(performance.now()), 16) as unknown as number;
    const cancelFrame: (id: number) => void =
        typeof cancelAnimationFrame === "function" ? cancelAnimationFrame : clearTimeout;

    const compiling = createProgram(gl).then((prog) => {
        if (!prog) return;
        program = prog;

        // Full-screen quad
        const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
        gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
        gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

        gl.useProgram(prog);
        const position = gl.getAttribLocation(prog, "a_position");
        gl.enableVertexAttribArray(position);
        gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

        // Reading a uniform's location costs a lookup by name; the draw used to do five of them
        // every frame
        for (const name of ["u_time", "u_resolution", "u_mouse", "u_texture", "u_hueShift"]) {
            uniforms[name] = gl.getUniformLocation(prog, name);
        }
        gl.uniform1i(uniforms.u_texture, 0);
        gl.uniform1f(uniforms.u_hueShift, hueShift);
        run();
    });

    function render(now: number) {
        if (!program) return;
        const elapsed = (now - startTime) / 1000;

        // Smooth the pointer with heavy lag, for a subtle, fluid response
        const smoothing = 0.02;
        mouseX += (targetMouseX - mouseX) * smoothing;
        mouseY += (targetMouseY - mouseY) * smoothing;

        gl.uniform1f(uniforms.u_time, elapsed);
        gl.uniform2f(uniforms.u_resolution, canvas.width, canvas.height);
        gl.uniform2f(uniforms.u_mouse, mouseX, mouseY);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        frame = nextFrame(render);
    }

    /**
     * The shader costs a full-screen draw every frame, which is wasted once the hero is scrolled
     * past or the tab is in the background. Time is carried across the gap so the animation picks
     * up where it left off rather than jumping.
     */
    function run() {
        if (frame || !wanted || !program || !hasTexture) return;
        if (!startTime) startTime = performance.now();
        if (pausedAt) {
            startTime += performance.now() - pausedAt;
            pausedAt = 0;
        }
        frame = nextFrame(render);
    }

    return {
        setSize(width, height, dpr) {
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            gl.viewport(0, 0, canvas.width, canvas.height);
        },
        setMouse(x, y) {
            targetMouseX = x;
            targetMouseY = y;
        },
        setHue(value) {
            hueShift = value;
            if (program) gl.uniform1f(uniforms.u_hueShift, hueShift);
        },
        async setTexture(blob) {
            // createImageBitmap decodes off whichever thread asks, which is why the photo is
            // handed over as bytes rather than as a URL to fetch and an <img> to wait on
            const bitmap = await createImageBitmap(blob, { premultiplyAlpha: "none" });
            const texture = gl.createTexture();
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, bitmap);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            bitmap.close(); // the GPU has it now
            hasTexture = true;
            run();
        },
        start() {
            wanted = true;
            run();
        },
        stop() {
            wanted = false;
            if (!frame) return;
            cancelFrame(frame);
            frame = 0;
            pausedAt = performance.now();
        },
        destroy() {
            this.stop();
            void compiling;
            gl.getExtension("WEBGL_lose_context")?.loseContext();
        },
    };
}
