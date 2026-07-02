import React, { useEffect, useMemo, useRef, useState } from "react";
import * as PIXI from "pixi.js";

const CUBISM2_RUNTIME_URL = "https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js";
const AVATAR_MODELS = [
  { name: "Shizuku", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@latest/assets/shizuku.model.json" },
  { name: "Hibiki", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-hibiki@latest/assets/hibiki.model.json" },
  { name: "Izumi", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-izumi@latest/assets/izumi.model.json" },
  { name: "Koharu", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-koharu@latest/assets/koharu.model.json" },
  { name: "Tororo", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-tororo@latest/assets/tororo.model.json" },
  { name: "Z16", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-z16@latest/assets/z16.model.json" },
  { name: "Tsumiki", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-tsumiki@latest/assets/tsumiki.model.json" },
  { name: "Unitychan", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-unitychan@latest/assets/unitychan.model.json" },
];
const MOUTH_PARAMETER_IDS = [
  "ParamMouthOpenY",
  "PARAM_MOUTH_OPEN_Y",
  "PARAM_MOUTH_OPENY",
  "ParamMouthOpen",
  "PARAM_MOUTH_OPEN",
  "PARAM_A",
  "ParamA",
];
const LOOK_X_ANGLE_PARAMETER_IDS = ["ParamAngleX", "PARAM_ANGLE_X"];
const LOOK_Y_ANGLE_PARAMETER_IDS = ["ParamAngleY", "PARAM_ANGLE_Y"];
const LOOK_X_EYE_PARAMETER_IDS = ["ParamEyeBallX", "PARAM_EYE_BALL_X"];
const LOOK_Y_EYE_PARAMETER_IDS = ["ParamEyeBallY", "PARAM_EYE_BALL_Y"];
const EDGE_GAP = 10;
const MIN_SIZE = 140;
const MAX_SIZE = 640;
const RANDOM_MOUTH_MIN = 0.55;
const RANDOM_MOUTH_RANGE = 0.4;
const MOBILE_BREAKPOINT = 900;
const getResponsiveTutorSize = () => {
  if (typeof window === "undefined") return 220;
  const target = window.innerWidth * 0.25;
  const byHeight = window.innerHeight * 0.6;
  return Math.round(Math.max(MIN_SIZE, Math.min(MAX_SIZE, Math.min(target, byHeight))));
};
const isMobileViewport = () => {
  if (typeof window === "undefined") return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};
const getMobileTutorRect = () => {
  if (typeof window === "undefined") return { x: EDGE_GAP, y: EDGE_GAP, width: 320, height: 180 };
  const width = Math.max(220, window.innerWidth - (EDGE_GAP * 2));
  const height = Math.round(Math.max(140, Math.min(260, window.innerHeight * 0.26)));
  return {
    x: EDGE_GAP,
    y: Math.max(EDGE_GAP, window.innerHeight - height - EDGE_GAP),
    width,
    height,
  };
};

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

const applyLookValue = (model, lookX, lookY) => {
  const core = model?.internalModel?.coreModel || model?.internalModel?.live2DModel;
  if (!core) return;
  for (const parameterId of LOOK_X_ANGLE_PARAMETER_IDS) {
    try {
      if (typeof core.setParameterValueById === "function") {
        core.setParameterValueById(parameterId, lookX);
      } else if (typeof core.setParameterValue === "function") {
        core.setParameterValue(parameterId, lookX);
      } else if (typeof core.setParamFloat === "function") {
        core.setParamFloat(parameterId, lookX);
      }
    } catch (_error) {
      // no-op
    }
  }
  for (const parameterId of LOOK_Y_ANGLE_PARAMETER_IDS) {
    try {
      if (typeof core.setParameterValueById === "function") {
        core.setParameterValueById(parameterId, lookY);
      } else if (typeof core.setParameterValue === "function") {
        core.setParameterValue(parameterId, lookY);
      } else if (typeof core.setParamFloat === "function") {
        core.setParamFloat(parameterId, lookY);
      }
    } catch (_error) {
      // no-op
    }
  }
  const eyeX = Math.max(-1, Math.min(1, lookX / 30));
  const eyeY = Math.max(-1, Math.min(1, lookY / 30));
  for (const parameterId of LOOK_X_EYE_PARAMETER_IDS) {
    try {
      if (typeof core.setParameterValueById === "function") {
        core.setParameterValueById(parameterId, eyeX);
      } else if (typeof core.setParameterValue === "function") {
        core.setParameterValue(parameterId, eyeX);
      } else if (typeof core.setParamFloat === "function") {
        core.setParamFloat(parameterId, eyeX);
      }
    } catch (_error) {
      // no-op
    }
  }
  for (const parameterId of LOOK_Y_EYE_PARAMETER_IDS) {
    try {
      if (typeof core.setParameterValueById === "function") {
        core.setParameterValueById(parameterId, eyeY);
      } else if (typeof core.setParameterValue === "function") {
        core.setParameterValue(parameterId, eyeY);
      } else if (typeof core.setParamFloat === "function") {
        core.setParamFloat(parameterId, eyeY);
      }
    } catch (_error) {
      // no-op
    }
  }
};

const Live2DTutor = ({ audioElement, isVisible = true, assistantMode = false, assistantSpeaking = false }) => {
  const mountRef = useRef(null);
  const panelRef = useRef(null);
  const dragStateRef = useRef(null);
  const resizeStateRef = useRef(null);
  const baseModelSizeRef = useRef({ width: 1, height: 1 });
  const mouthValueRef = useRef(0);
  const lookValueRef = useRef({ x: 0, y: 0 });
  const pointerRef = useRef({ x: 0, y: 0 });
  const lastTapAtRef = useRef(0);
  const assistantModeRef = useRef(assistantMode);
  const assistantSpeakingRef = useRef(assistantSpeaking);
  const [avatarIndex, setAvatarIndex] = useState(() => {
    if (typeof window === "undefined") return 0;
    const raw = window.localStorage.getItem("live2d.avatarIndex");
    const parsed = Number.parseInt(raw || "0", 10);
    if (!Number.isFinite(parsed)) return 0;
    return Math.max(0, parsed % AVATAR_MODELS.length);
  });
  const [ready, setReady] = useState(false);
  const [isMobile, setIsMobile] = useState(() => isMobileViewport());
  const [panelRect, setPanelRect] = useState({
    x: EDGE_GAP,
    y: Math.max(EDGE_GAP, window.innerHeight - getResponsiveTutorSize() - EDGE_GAP),
    width: getResponsiveTutorSize(),
    height: getResponsiveTutorSize(),
  });

  const activeAvatar = useMemo(() => {
    const idx = Math.max(0, avatarIndex % AVATAR_MODELS.length);
    return AVATAR_MODELS[idx];
  }, [avatarIndex]);

  useEffect(() => {
    assistantModeRef.current = assistantMode;
  }, [assistantMode]);

  useEffect(() => {
    assistantSpeakingRef.current = assistantSpeaking;
  }, [assistantSpeaking]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("live2d.avatarIndex", String(Math.max(0, avatarIndex % AVATAR_MODELS.length)));
  }, [avatarIndex]);

  useEffect(() => {
    if (!mountRef.current) return undefined;

    let app = null;
    let model = null;
    let animationFrame = 0;
    let smoothed = 0;
    let lookXSmooth = 0;
    let lookYSmooth = 0;
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

    const applyFrameValues = () => {
      if (!model) return;
      applyMouthValue(model, mouthValueRef.current);
      applyLookValue(model, lookValueRef.current.x, lookValueRef.current.y);
    };

    const updateLoop = () => {
      if (cancelled) return;
      let target = 0;
      const useAssistantMode = Boolean(assistantModeRef.current);
      const isMp3Playing = Boolean(audioElement && !audioElement.paused && !audioElement.ended);
      if (useAssistantMode && assistantSpeakingRef.current) {
        const t = performance.now() / 1000;
        const waveA = (Math.sin(t * 11.7) + 1) * 0.5;
        const waveB = (Math.sin(t * 19.1 + 0.8) + 1) * 0.5;
        const motion = (waveA * 0.58) + (waveB * 0.42);
        target = RANDOM_MOUTH_MIN + (motion * RANDOM_MOUTH_RANGE);
      } else if (!useAssistantMode && isMp3Playing) {
        const t = Number.isFinite(audioElement?.currentTime) ? audioElement.currentTime : performance.now() / 1000;
        const waveA = (Math.sin(t * 10.7) + 1) * 0.5;
        const waveB = (Math.sin(t * 17.9 + 0.8) + 1) * 0.5;
        const waveC = (Math.sin(t * 27.4 + 1.7) + 1) * 0.5;
        const motion = (waveA * 0.42) + (waveB * 0.36) + (waveC * 0.22);
        target = RANDOM_MOUTH_MIN + (motion * RANDOM_MOUTH_RANGE);
      }
      smoothed += (target - smoothed) * 0.75;
      mouthValueRef.current = smoothed;

      const desiredLookX = useAssistantMode && assistantSpeakingRef.current ? pointerRef.current.x : 0;
      const desiredLookY = useAssistantMode && assistantSpeakingRef.current ? pointerRef.current.y : 0;
      lookXSmooth += (desiredLookX - lookXSmooth) * 0.35;
      lookYSmooth += (desiredLookY - lookYSmooth) * 0.35;
      lookValueRef.current = {
        x: Math.max(-30, Math.min(30, lookXSmooth * 30)),
        y: Math.max(-30, Math.min(30, lookYSmooth * 30)),
      };

      applyFrameValues();
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
        model = await Live2DModel.from(activeAvatar.url);
        if (cancelled) return;
        model.scale.set(1);
        const baseBounds = typeof model.getLocalBounds === "function" ? model.getLocalBounds() : null;
        baseModelSizeRef.current = {
          width: Math.max(baseBounds?.width || 1, 1),
          height: Math.max(baseBounds?.height || 1, 1),
        };
        app.stage.addChild(model);
        onAfterMotionUpdate = () => {
          applyFrameValues();
        };
        onBeforeModelUpdate = () => {
          applyFrameValues();
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

    const onPointerMove = (event) => {
      const x = (event.clientX / Math.max(window.innerWidth, 1)) * 2 - 1;
      const y = (event.clientY / Math.max(window.innerHeight, 1)) * 2 - 1;
      pointerRef.current = {
        x: Math.max(-1, Math.min(1, x)),
        y: Math.max(-1, Math.min(1, y)),
      };
    };
    window.addEventListener("pointermove", onPointerMove, { passive: true });

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
      window.removeEventListener("pointermove", onPointerMove);
    };
  }, [audioElement, activeAvatar.url]);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    setPanelRect((current) => {
      if (isMobileViewport()) {
        return getMobileTutorRect();
      }
      const responsiveSize = getResponsiveTutorSize();
      const safeBottom = Math.max(EDGE_GAP, window.innerHeight - EDGE_GAP);
      const next = {
        ...current,
        width: responsiveSize,
        height: responsiveSize,
        x: EDGE_GAP,
        y: Math.max(EDGE_GAP, safeBottom - responsiveSize),
      };
      return next;
    });
    const onResize = () => {
      const mobile = isMobileViewport();
      setIsMobile(mobile);
      setPanelRect((current) => {
        if (mobile) {
          return getMobileTutorRect();
        }
        const responsiveSize = getResponsiveTutorSize();
        const parentWidth = window.innerWidth || 0;
        const parentHeight = window.innerHeight || 0;
        const maxX = Math.max(EDGE_GAP, parentWidth - responsiveSize - EDGE_GAP);
        const safeBottom = Math.max(EDGE_GAP, parentHeight - EDGE_GAP);
        const maxY = Math.max(EDGE_GAP, safeBottom - responsiveSize);
        return {
          ...current,
          width: responsiveSize,
          height: responsiveSize,
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
    if (isMobile) return;
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
    if (isMobile) return;
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

  const cycleAvatar = () => {
    setAvatarIndex((prev) => (prev + 1) % AVATAR_MODELS.length);
  };

  const handleMobilePointerUp = (event) => {
    if (!isMobile) return;
    if (event.pointerType !== "touch" && event.pointerType !== "pen") return;
    const now = Date.now();
    if (now - lastTapAtRef.current < 360) {
      lastTapAtRef.current = 0;
      cycleAvatar();
      return;
    }
    lastTapAtRef.current = now;
  };

  return (
    <div
      ref={panelRef}
      className={`live2d-tutor ${ready ? "ready" : ""} ${isVisible ? "" : "hidden"}`.trim()}
      onDoubleClick={cycleAvatar}
      onPointerUp={handleMobilePointerUp}
      title={`Double click to switch avatar (${activeAvatar.name})`}
      style={{
        position: isMobile ? "relative" : "fixed",
        width: `${panelRect.width}px`,
        height: `${panelRect.height}px`,
        left: isMobile ? "auto" : `${panelRect.x}px`,
        top: isMobile ? "auto" : `${panelRect.y}px`,
        bottom: "auto",
        margin: isMobile ? `${EDGE_GAP}px` : 0,
        alignSelf: isMobile ? "stretch" : "auto",
      }}
    >
      {!isMobile && (
        <button type="button" className="live2d-tutor-handle" onPointerDown={handleDragStart}>
          Tutor · {activeAvatar.name}
        </button>
      )}
      <div ref={mountRef} className="live2d-tutor-canvas" />
      {!isMobile && (
        <button type="button" className="live2d-tutor-resizer" onPointerDown={handleResizeStart} aria-label="Resize tutor" />
      )}
    </div>
  );
};

export default Live2DTutor;
