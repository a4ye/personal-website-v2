/**
 * Draws the hero on a worker thread.
 *
 * All this does is carry messages to the renderer. The reason it exists is that compiling the
 * shader blocks the thread that asks whether the driver has finished, and on a first visit that is
 * most of a second. Here, nobody is waiting.
 */
import { createRenderer, type Renderer } from "./renderer";

type Message =
    | { type: "init"; canvas: OffscreenCanvas; hueShift: number; width: number; height: number; dpr: number }
    | { type: "texture"; blob: Blob }
    | { type: "size"; width: number; height: number; dpr: number }
    | { type: "mouse"; x: number; y: number }
    | { type: "run"; on: boolean }
    | { type: "hue"; hueShift: number };

let renderer: Renderer | null = null;

self.onmessage = ({ data }: MessageEvent<Message>) => {
    switch (data.type) {
        case "init":
            renderer = createRenderer(data.canvas, data.hueShift);
            renderer?.setSize(data.width, data.height, data.dpr);
            break;
        case "texture":
            renderer?.setTexture(data.blob);
            break;
        case "size":
            renderer?.setSize(data.width, data.height, data.dpr);
            break;
        case "mouse":
            renderer?.setMouse(data.x, data.y);
            break;
        case "run":
            if (data.on) renderer?.start();
            else renderer?.stop();
            break;
        case "hue":
            renderer?.setHue(data.hueShift);
            break;
    }
};
