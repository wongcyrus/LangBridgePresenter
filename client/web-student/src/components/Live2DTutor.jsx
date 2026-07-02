import React, { useEffect, useRef, useState } from "react";
import * as PIXI from "pixi.js";

const MODEL_URL = "https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@latest/assets/shizuku.model.json";
const CUBISM2_RUNTIME_URL = "https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js";
const MOUTH_PARAMETER_IDS = [
  "ParamMouthOpenY",
  "PARAM_MOUTH_OPEN_Y",
  "PARAM_MOUTH_OPENY",
  "ParamMouthOpen",
  "PARAM_MOUTH_OPEN",
  "PARAM_A",
  "ParamA",
];
const EDGE_GAP = 10;
const MIN_SIZE = 140;
const MAX_SIZE = 300;
const RANDOM_MOUTH_MIN = 0.55;
const RANDOM_MOUTH_RANGE = 0.4;

const ensureCubism2Runtime = async () => {
  if (window.Live2D) return;
  await new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-live2d-runtime="cubism2"]');
    if (existing) {
      if (window.Live2D) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Failed to load Cubism2 runtime")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = CUBISM2_RUNTIME_URL;
    script.async = true;
    script.dataset.live2dRuntime = "cubism2";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Cubism2 runtime"));
    document.head.appendChild(script);
  });
};

const applyMouthValue = (model, value) => {
  const core = model?.internalModel?.coreModel || model?.internalModel?.live2DModel;
  if (!core) return;
  for (const parameterId of MOUTH_PARAMETER_IDS) {
    try {
      if (typeof core.setParameterValueById === "function") {
        core.setParameterValueById(parameterId, value);
      } else if (typeof core.setParameterValue === "function") {
        core.setParameterValue(parameterId, value);
      } else if (typeof core.setParamFloat === "function") {
        core.setParamFloat(parameterId, value);
      }
    } catch (_error) {
      // no-op
    }
  }
};

const Live2DTutor = ({ audioElement, isVisible = true }) => {
  const mountRef = useRef(null);
  const panelRef = useRef(null);
  const dragStateRef = useRef(null);
  const resizeStateRef = useRef(null);
  const baseModelSizeRef = useRef({ width: 1, height: 1 });
  const mouthValueRef = useRef(0);
  const [ready, setReady] = useState(false);
  const [panelRect, setPanelRect] = useState({
    x: EDGE_GAP,
    y: Math.max(EDGE_GAP, window.innerHeight - 180 - EDGE_GAP),
    width: 180,
    height: 180,
  });

  useEffect(() => {
    if (!mountRef.current) return undefined;

    let app = null;
    let model = null;
    let animationFrame = 0;
    let smoothed = 0;
    let cancelled = false;
    let Live2DModel = null;
    let resizeObserver = null;
    let onAfterMotionUpdate = null;
    let onBeforeModelUpdate = null;
    const layoutModel = () => {
      if (!app || !model) return;
      const modelWidth = Math.max(baseModelSizeRef.current.width || 1, 1);
      const modelHeight = Math.max(baseModelSizeRef.current.height || 1, 1);
      const targetScale = Math.min((app.screen.width * 0.82) / modelWidth, (app.screen.height * 0.95) / modelHeight);
      model.anchor.set(0.5, 1);
      model.scale.set(targetScale);
      model.x = app.screen.width * 0.5;
      model.y = app.screen.height * 0.98;
    };

    const updateLoop = () => {
      if (cancelled) return;
      let target = 0;
      const isPlaying = Boolean(audioElement && !audioElement.paused && !audioElement.ended);
      if (isPlaying) {
        const t = Number.isFinite(audioElement?.currentTime) ? audioElement.currentTime : performance.now() / 1000;
        const waveA = (Math.sin(t * 10.7) + 1) * 0.5;
        const waveB = (Math.sin(t * 17.9 + 0.8) + 1) * 0.5;
        const waveC = (Math.sin(t * 27.4 + 1.7) + 1) * 0.5;
        const motion = (waveA * 0.42) + (waveB * 0.36) + (waveC * 0.22);
        target = RANDOM_MOUTH_MIN + (motion * RANDOM_MOUTH_RANGE);
      }
      smoothed += (target - smoothed) * 0.75;
      mouthValueRef.current = smoothed;
      if (model) applyMouthValue(model, smoothed);
      animationFrame = window.requestAnimationFrame(updateLoop);
    };

    const init = async () => {
      try {
        window.PIXI = PIXI;
        app = new PIXI.Application({
          resizeTo: mountRef.current,
          backgroundAlpha: 0,
          antialias: true,
        });
        mountRef.current.appendChild(app.view);
        await ensureCubism2Runtime();
        const live2dModule = await import("pixi-live2d-display/cubism2");
        Live2DModel = live2dModule.Live2DModel;
        model = await Live2DModel.from(MODEL_URL);
        if (cancelled) return;
        model.scale.set(1);
        const baseBounds = typeof model.getLocalBounds === "function" ? model.getLocalBounds() : null;
        baseModelSizeRef.current = {
          width: Math.max(baseBounds?.width || 1, 1),
          height: Math.max(baseBounds?.height || 1, 1),
        };
        app.stage.addChild(model);
        onAfterMotionUpdate = () => {
          applyMouthValue(model, mouthValueRef.current);
        };
        onBeforeModelUpdate = () => {
          applyMouthValue(model, mouthValueRef.current);
        };
        if (model.internalModel?.on) {
          model.internalModel.on("afterMotionUpdate", onAfterMotionUpdate);
          model.internalModel.on("beforeModelUpdate", onBeforeModelUpdate);
        }
        layoutModel();
        resizeObserver = new ResizeObserver(() => {
          if (mountRef.current && app?.renderer) {
            app.renderer.resize(mountRef.current.clientWidth, mountRef.current.clientHeight);
          }
          layoutModel();
        });
        resizeObserver.observe(mountRef.current);
        setReady(true);
        updateLoop();
      } catch (error) {
        console.error("Live2D tutor initialization failed:", error);
      }
    };

    init();

    return () => {
      cancelled = true;
      setReady(false);
      if (animationFrame) {
        window.cancelAnimationFrame(animationFrame);
      }
      if (model?.internalModel?.off) {
        if (onAfterMotionUpdate) model.internalModel.off("afterMotionUpdate", onAfterMotionUpdate);
        if (onBeforeModelUpdate) model.internalModel.off("beforeModelUpdate", onBeforeModelUpdate);
      }
      if (app) {
        app.destroy(true, true);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
    };
  }, [audioElement]);

  useEffect(() => {
    setPanelRect((current) => {
      const safeBottom = Math.max(EDGE_GAP, window.innerHeight - EDGE_GAP);
      const next = {
        ...current,
        x: EDGE_GAP,
        y: Math.max(EDGE_GAP, safeBottom - current.height),
      };
      return next;
    });
    const onResize = () => {
      setPanelRect((current) => {
        const parentWidth = window.innerWidth || 0;
        const parentHeight = window.innerHeight || 0;
        const maxX = Math.max(EDGE_GAP, parentWidth - current.width - EDGE_GAP);
        const safeBottom = Math.max(EDGE_GAP, parentHeight - EDGE_GAP);
        const maxY = Math.max(EDGE_GAP, safeBottom - current.height);
        return {
          ...current,
          x: Math.max(EDGE_GAP, Math.min(maxX, current.x)),
          y: Math.max(EDGE_GAP, Math.min(maxY, current.y)),
        };
      });
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, []);

  const handleDragStart = (event) => {
    event.preventDefault();
    dragStateRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      originX: panelRect.x,
      originY: panelRect.y,
      width: panelRect.width,
      height: panelRect.height,
    };
    const onMove = (moveEvent) => {
      if (!dragStateRef.current) return;
      const deltaX = moveEvent.clientX - dragStateRef.current.startX;
      const deltaY = moveEvent.clientY - dragStateRef.current.startY;
      const parentWidth = window.innerWidth || 0;
      const parentHeight = window.innerHeight || 0;
      const maxX = Math.max(EDGE_GAP, parentWidth - dragStateRef.current.width - EDGE_GAP);
      const safeBottom = Math.max(EDGE_GAP, parentHeight - EDGE_GAP);
      const maxY = Math.max(EDGE_GAP, safeBottom - dragStateRef.current.height);
      setPanelRect((current) => ({
        ...current,
        x: Math.max(EDGE_GAP, Math.min(maxX, dragStateRef.current.originX + deltaX)),
        y: Math.max(EDGE_GAP, Math.min(maxY, dragStateRef.current.originY + deltaY)),
      }));
    };
    const onUp = () => {
      dragStateRef.current = null;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const handleResizeStart = (event) => {
    event.preventDefault();
    event.stopPropagation();
    resizeStateRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      width: panelRect.width,
      height: panelRect.height,
      originY: panelRect.y,
    };
    const onMove = (moveEvent) => {
      if (!resizeStateRef.current) return;
      const deltaX = moveEvent.clientX - resizeStateRef.current.startX;
      const deltaY = moveEvent.clientY - resizeStateRef.current.startY;
      const parentHeight = window.innerHeight || 0;
      const maxHeightByFooter = Math.max(MIN_SIZE, parentHeight - EDGE_GAP - resizeStateRef.current.originY);
      const maxSquareByViewport = Math.max(MIN_SIZE, maxHeightByFooter);
      const growth = Math.max(deltaX, deltaY);
      const nextSize = Math.max(MIN_SIZE, Math.min(Math.min(MAX_SIZE, maxSquareByViewport), resizeStateRef.current.width + growth));
      setPanelRect((current) => ({
        ...current,
        width: nextSize,
        height: nextSize,
      }));
    };
    const onUp = () => {
      resizeStateRef.current = null;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    <div
      ref={panelRef}
      className={`live2d-tutor ${ready ? "ready" : ""} ${isVisible ? "" : "hidden"}`.trim()}
      style={{
        width: `${panelRect.width}px`,
        height: `${panelRect.height}px`,
        left: `${panelRect.x}px`,
        top: `${panelRect.y}px`,
      }}
    >
      <button type="button" className="live2d-tutor-handle" onPointerDown={handleDragStart}>
        Tutor
      </button>
      <div ref={mountRef} className="live2d-tutor-canvas" />
      <button type="button" className="live2d-tutor-resizer" onPointerDown={handleResizeStart} aria-label="Resize tutor" />
    </div>
  );
};

export default Live2DTutor;
