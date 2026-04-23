<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import heroImage from "../assets/hero.png";

    let canvas: HTMLCanvasElement;
    let gl: WebGLRenderingContext | null = null;
    let animationFrameId: number = 0;
    let startTime: number = 0;
    let program: WebGLProgram | null = null;

    // Mouse position (normalized 0-1, with smoothing)
    let mouseX = 0.5;
    let mouseY = 0.5;
    let targetMouseX = 0.5;
    let targetMouseY = 0.5;

    // Hue shift (0.0 to 1.0, where 1.0 = full 360° rotation)
    export let hueShift = 0.4;

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

            // Rotate 90 degrees clockwise (portrait to landscape)
            vec2 rotated = vec2(1.0 - uv.y, uv.x);

            // Match image aspect ratio to screen via cover-fit UV transform
            // Original image is 1080x2337, after 90° rotation it's 2337x1080
            float screenAspect = u_resolution.x / u_resolution.y;
            float imageAspect = 2337.0 / 1080.0;
            vec2 texUV = rotated;
            if (screenAspect > imageAspect) {
                float scale = screenAspect / imageAspect;
                texUV.y = (texUV.y - 0.5) / scale + 0.5;
            } else {
                float scale = imageAspect / screenAspect;
                texUV.x = (texUV.x - 0.5) / scale + 0.5;
            }

            // Mirror horizontally
            texUV.y = 1.0 - texUV.y;

            // Mouse-driven center for liquify pass 1
            vec2 center1 = vec2(0.5, 0.5) + (u_mouse - 0.5) * 0.3;

            // Liquify pass 1: mouse-tracking distortion only (no auto-animation)
            float freq1 = 5.0 * (0.14 + 0.1);
            float amp1 = 0.34 * mix(0.2, 0.2 / (0.14 + 0.05), 0.25) * 0.4;
            vec2 liq1 = liquify(texUV, 0.8807, freq1, amp1, 0.0, center1);

            // Chromatic aberration for pass 1 (subtle: 0.01)
            vec2 dir1 = liq1 - texUV;
            float len1 = length(dir1);
            vec2 ndir1 = len1 > 0.001 ? dir1 / len1 : vec2(0.0);
            float chromAbb1 = 0.0;

            vec2 offsetR1 = liq1 + chromAbb1 * ndir1 * len1;
            vec2 offsetG1 = liq1;
            vec2 offsetB1 = liq1 - chromAbb1 * ndir1 * len1;

            float mixAmt1 = 0.15;
            vec2 uvR = mix(texUV, offsetR1, mixAmt1);
            vec2 uvG = mix(texUV, offsetG1, mixAmt1);
            vec2 uvB = mix(texUV, offsetB1, mixAmt1);

            // Liquify pass 2: mouse-driven distortion
            vec2 center2 = vec2(0.5, 0.5) + (u_mouse - 0.5) * 0.2;
            float freq2 = 5.0 * (1.27 + 0.1);
            float amp2 = 0.23 * mix(0.2, 0.2 / (1.27 + 0.05), 0.25) * 0.2;

            vec2 liqR = liquify(uvR, 0.121, freq2, amp2, 0.0, center2);
            vec2 liqG = liquify(uvG, 0.121, freq2, amp2, 0.0, center2);
            vec2 liqB = liquify(uvB, 0.121, freq2, amp2, 0.0, center2);

            // Chromatic aberration for pass 2 (strong: 0.67)
            float chromAbb2 = 0.0;
            float mixAmt2 = 0.08;

            vec2 dirR = liqR - uvR;
            float distR = length(dirR);
            vec2 ndirR = distR > 0.001 ? dirR / distR : vec2(0.0);

            vec2 dirB = liqB - uvB;
            float distB = length(dirB);
            vec2 ndirB = distB > 0.001 ? dirB / distB : vec2(0.0);

            vec2 finalR = mix(uvR, liqR + chromAbb2 * ndirR * distR, mixAmt2);
            vec2 finalG = mix(uvG, liqG, mixAmt2);
            vec2 finalB = mix(uvB, liqB - chromAbb2 * ndirB * distB, mixAmt2);

            // Clamp UVs to prevent wrapping artifacts
            finalR = clamp(finalR, 0.0, 1.0);
            finalG = clamp(finalG, 0.0, 1.0);
            finalB = clamp(finalB, 0.0, 1.0);

            // Sample image texture with gaussian blur
            vec2 texelSize = 1.0 / u_resolution;
            float blurRadius = 1.5;

            vec3 color = vec3(0.0);
            color += texture2D(u_texture, finalG + texelSize * vec2(-1.0, -1.0) * blurRadius).rgb * 0.0625;
            color += texture2D(u_texture, finalG + texelSize * vec2( 0.0, -1.0) * blurRadius).rgb * 0.125;
            color += texture2D(u_texture, finalG + texelSize * vec2( 1.0, -1.0) * blurRadius).rgb * 0.0625;
            color += texture2D(u_texture, finalG + texelSize * vec2(-1.0,  0.0) * blurRadius).rgb * 0.125;
            color += texture2D(u_texture, finalG).rgb * 0.25;
            color += texture2D(u_texture, finalG + texelSize * vec2( 1.0,  0.0) * blurRadius).rgb * 0.125;
            color += texture2D(u_texture, finalG + texelSize * vec2(-1.0,  1.0) * blurRadius).rgb * 0.0625;
            color += texture2D(u_texture, finalG + texelSize * vec2( 0.0,  1.0) * blurRadius).rgb * 0.125;
            color += texture2D(u_texture, finalG + texelSize * vec2( 1.0,  1.0) * blurRadius).rgb * 0.0625;

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

            color = clamp((color - 0.5) + 0.5, 0.0, 1.0);

            gl_FragColor = vec4(color, 1.0);
        }
    `;

    function createShader(glCtx: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
        const shader = glCtx.createShader(type);
        if (!shader) return null;
        glCtx.shaderSource(shader, source);
        glCtx.compileShader(shader);
        if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
            console.error('Shader compile error:', glCtx.getShaderInfoLog(shader));
            glCtx.deleteShader(shader);
            return null;
        }
        return shader;
    }

    function createProgramFromSources(glCtx: WebGLRenderingContext, vsSrc: string, fsSrc: string): WebGLProgram | null {
        const vs = createShader(glCtx, glCtx.VERTEX_SHADER, vsSrc);
        const fs = createShader(glCtx, glCtx.FRAGMENT_SHADER, fsSrc);
        if (!vs || !fs) return null;
        const prog = glCtx.createProgram();
        if (!prog) return null;
        glCtx.attachShader(prog, vs);
        glCtx.attachShader(prog, fs);
        glCtx.linkProgram(prog);
        if (!glCtx.getProgramParameter(prog, glCtx.LINK_STATUS)) {
            console.error('Program link error:', glCtx.getProgramInfoLog(prog));
            glCtx.deleteProgram(prog);
            return null;
        }
        return prog;
    }

    function loadTexture(glCtx: WebGLRenderingContext, url: string): Promise<WebGLTexture | null> {
        return new Promise((resolve) => {
            const texture = glCtx.createTexture();
            const img = new Image();
            img.crossOrigin = "anonymous";
            img.onload = () => {
                glCtx.bindTexture(glCtx.TEXTURE_2D, texture);
                glCtx.texImage2D(glCtx.TEXTURE_2D, 0, glCtx.RGBA, glCtx.RGBA, glCtx.UNSIGNED_BYTE, img);
                glCtx.texParameteri(glCtx.TEXTURE_2D, glCtx.TEXTURE_MIN_FILTER, glCtx.LINEAR);
                glCtx.texParameteri(glCtx.TEXTURE_2D, glCtx.TEXTURE_MAG_FILTER, glCtx.LINEAR);
                glCtx.texParameteri(glCtx.TEXTURE_2D, glCtx.TEXTURE_WRAP_S, glCtx.CLAMP_TO_EDGE);
                glCtx.texParameteri(glCtx.TEXTURE_2D, glCtx.TEXTURE_WRAP_T, glCtx.CLAMP_TO_EDGE);
                resolve(texture);
            };
            img.onerror = () => {
                console.error('Failed to load hero background image');
                resolve(null);
            };
            img.src = url;
        });
    }

    function resizeCanvas() {
        if (!canvas || !gl) return;
        const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        gl.viewport(0, 0, canvas.width, canvas.height);
    }

    function onMouseMove(e: MouseEvent) {
        // Normalize to 0-1 range relative to the canvas
        const rect = canvas.getBoundingClientRect();
        targetMouseX = (e.clientX - rect.left) / rect.width;
        targetMouseY = 1.0 - (e.clientY - rect.top) / rect.height; // flip Y for GL coords
    }

    function render(now: number) {
        if (!gl || !program) return;

        const elapsed = (now - startTime) / 1000.0;

        // Smooth mouse position with heavy lag for subtle, fluid response
        const smoothing = 0.02;
        mouseX += (targetMouseX - mouseX) * smoothing;
        mouseY += (targetMouseY - mouseY) * smoothing;

        if ("useProgram" in gl) {
            gl.useProgram(program);
        }

        gl.uniform1f(gl.getUniformLocation(program, 'u_time'), elapsed);
        gl.uniform2f(gl.getUniformLocation(program, 'u_resolution'), canvas.width, canvas.height);
        if ("uniform2f" in gl) {
            gl.uniform2f(gl.getUniformLocation(program, "u_mouse"), mouseX, mouseY);
        }
        gl.uniform1i(gl.getUniformLocation(program, 'u_texture'), 0);
        gl.uniform1f(gl.getUniformLocation(program, 'u_hueShift'), hueShift);

        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        animationFrameId = requestAnimationFrame(render);
    }

    let resizeTimeout: ReturnType<typeof setTimeout>;
    function debouncedResize() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(resizeCanvas, 50);
    }

    onMount(async () => {
        gl = canvas.getContext('webgl', { antialias: false, alpha: false });
        if (!gl) {
            console.error('WebGL not supported');
            return;
        }

        program = createProgramFromSources(gl, vertexShaderSource, fragmentShaderSource);
        if (!program) return;

        // Full-screen quad
        const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

        gl.useProgram(program);
        const posLoc = gl.getAttribLocation(program, 'a_position');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

        // Load the holographic image texture
        const imageUrl = typeof heroImage === 'string' ? heroImage : heroImage.src;
        const texture = await loadTexture(gl, imageUrl);
        if (!texture) return;

        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);

        resizeCanvas();
        window.addEventListener('resize', debouncedResize);
        window.addEventListener('mousemove', onMouseMove);

        startTime = performance.now();
        animationFrameId = requestAnimationFrame(render);
    });

    onDestroy(() => {
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        window.removeEventListener('resize', debouncedResize);
        window.removeEventListener('mousemove', onMouseMove);
        clearTimeout(resizeTimeout);
    });
</script>

<canvas bind:this={canvas} class="absolute inset-0 w-full h-full"></canvas>
