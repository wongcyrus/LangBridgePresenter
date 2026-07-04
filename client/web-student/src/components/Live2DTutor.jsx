import React, { useEffect, useMemo, useRef, useState } from "react";
import * as PIXI from "pixi.js";

const CUBISM2_RUNTIME_URL = "https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js";
const AVATAR_MODELS = [
  { name: "Ni-j", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-ni-j@latest/assets/ni-j.model.json" },
  { name: "Wild", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-wild@latest/assets/wild.model.json" },
  { name: "Epsilon2.1", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-epsilon2_1@latest/assets/Epsilon2.1.model.json" },
  { name: "Haru01", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-haru@latest/01/assets/haru01.model.json" },
  { name: "Haru02", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-haru@latest/02/assets/haru02.model.json" },
  { name: "Chitose", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-chitose@latest/assets/chitose.model.json" },
  { name: "Shizuku", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@latest/assets/shizuku.model.json" },
  { name: "Hibiki", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-hibiki@latest/assets/hibiki.model.json" },
  { name: "Izumi", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-izumi@latest/assets/izumi.model.json" },
  { name: "Koharu", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-koharu@latest/assets/koharu.model.json" },
  { name: "Tororo", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-tororo@latest/assets/tororo.model.json" },
  { name: "Z16", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-z16@latest/assets/z16.model.json" },
  { name: "Tsumiki", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-tsumiki@latest/assets/tsumiki.model.json" },
  { name: "Unitychan", url: "https://cdn.jsdelivr.net/npm/live2d-widget-model-unitychan@latest/assets/unitychan.model.json" },
];
const DEFAULT_AVATAR_LAYOUT = {
  fitWidthRatio: 0.82,
  fitHeightRatio: 0.95,
  scaleMultiplier: 1,
  xRatio: 0.5,
  yRatio: 0.98,
  drawableTopPaddingRatio: null,
};
const AVATAR_LAYOUT_PRESETS = {
  "Ni-j": { fitWidthRatio: 0.84, fitHeightRatio: 0.95, scaleMultiplier: 1.02, xRatio: 0.5, yRatio: 0.985 },
  Wanko: { fitWidthRatio: 0.86, fitHeightRatio: 0.96, scaleMultiplier: 1.14, xRatio: 0.5, yRatio: 0.99 },
  Wild: { fitWidthRatio: 0.86, fitHeightRatio: 0.96, scaleMultiplier: 1.12, xRatio: 0.5, yRatio: 0.99 },
  "Epsilon2.1": { fitWidthRatio: 0.8, fitHeightRatio: 0.93, scaleMultiplier: 0.9, xRatio: 0.51, yRatio: 0.985 },
  Haru01: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.97, xRatio: 0.5, yRatio: 0.985, drawableTopPaddingRatio: 0.05 },
  Haru02: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.97, xRatio: 0.5, yRatio: 0.985, drawableTopPaddingRatio: 0.05 },
  Chitose: { fitWidthRatio: 0.82, fitHeightRatio: 0.94, scaleMultiplier: 0.95, xRatio: 0.5, yRatio: 0.985 },
  Shizuku: { fitWidthRatio: 0.8, fitHeightRatio: 0.88, scaleMultiplier: 0.92, xRatio: 0.5, yRatio: 0.985 },
  Hibiki: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.98, xRatio: 0.5, yRatio: 0.985 },
  Izumi: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.98, xRatio: 0.5, yRatio: 0.985 },
  Koharu: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.97, xRatio: 0.5, yRatio: 0.985 },
  Tororo: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.98, xRatio: 0.5, yRatio: 0.985 },
  Z16: { fitWidthRatio: 0.8, fitHeightRatio: 0.93, scaleMultiplier: 0.92, xRatio: 0.5, yRatio: 0.985 },
  Tsumiki: { fitWidthRatio: 0.82, fitHeightRatio: 0.95, scaleMultiplier: 0.97, xRatio: 0.5, yRatio: 0.985 },
  Unitychan: { fitWidthRatio: 0.8, fitHeightRatio: 0.93, scaleMultiplier: 0.9, xRatio: 0.5, yRatio: 0.985 },
};
const getAvatarLayoutPreset = (avatarName) => {
  const name = String(avatarName || "").trim();
  const preset = AVATAR_LAYOUT_PRESETS[name];
  return preset ? { ...DEFAULT_AVATAR_LAYOUT, ...preset } : DEFAULT_AVATAR_LAYOUT;
};
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
const MIN_WIDTH = 160;
const MAX_WIDTH = 4096;
const MIN_HEIGHT = 180;
const MAX_HEIGHT = 4096;
const RANDOM_MOUTH_MIN = 0.55;
const RANDOM_MOUTH_RANGE = 0.4;
const MOBILE_BREAKPOINT = 900;
const PANEL_RECT_STORAGE_KEY = "live2d.panelRect";
const readStoredPanelRect = () => {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(PANEL_RECT_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    const x = Number(parsed?.x);
    const y = Number(parsed?.y);
    const width = Number(parsed?.width);
    const height = Number(parsed?.height);
    if (![x, y, width, height].every((value) => Number.isFinite(value))) return null;
    return { x, y, width, height };
  } catch (_error) {
    return null;
  }
};
const clampDesktopPanelRect = (rect) => {
  if (typeof window === "undefined") return rect;
  const parentWidth = window.innerWidth || 0;
  const parentHeight = window.innerHeight || 0;
  const width = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, Math.round(Number(rect?.width) || MIN_WIDTH)));
  const height = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, Math.round(Number(rect?.height) || MIN_HEIGHT)));
  const maxX = Math.max(EDGE_GAP, parentWidth - width - EDGE_GAP);
  const safeBottom = Math.max(EDGE_GAP, parentHeight - EDGE_GAP);
  const maxY = Math.max(EDGE_GAP, safeBottom - height);
  const x = Math.max(EDGE_GAP, Math.min(maxX, Math.round(Number(rect?.x) || EDGE_GAP)));
  const y = Math.max(EDGE_GAP, Math.min(maxY, Math.round(Number(rect?.y) || EDGE_GAP)));
  return { x, y, width, height };
};
const getResponsiveTutorRect = () => {
  if (typeof window === "undefined") return { width: 220, height: 320 };
  const widthByViewport = window.innerWidth * 0.24;
  const width = Math.round(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, widthByViewport)));
  const heightByViewport = window.innerHeight * 0.5;
  const heightByWidth = width * 1.35;
  const height = Math.round(Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, Math.min(heightByViewport, heightByWidth))));
  return { width, height };
};
const isMobileViewport = () => {
  if (typeof window === "undefined") return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};
const getMobileTutorRect = () => {
  if (typeof window === "undefined") return { x: EDGE_GAP, y: EDGE_GAP, width: 320, height: 180 };
  const width = Math.max(220, window.innerWidth - (EDGE_GAP * 2));
  const height = Math.round(Math.max(280, Math.min(520, window.innerHeight * 0.46)));
  return {
    x: EDGE_GAP,
    y: Math.max(EDGE_GAP, window.innerHeight - height - EDGE_GAP),
    width,
    height,
  };
};
const getExpandedTutorRect = () => {
  if (typeof window === "undefined") return { x: 0, y: 0, width: 320, height: 480 };
  const viewportWidth = Math.max(1, Math.round(window.visualViewport?.width || window.innerWidth || 1));
  const viewportHeight = Math.max(1, Math.round(window.visualViewport?.height || window.innerHeight || 1));
  return {
    x: 0,
    y: 0,
    width: viewportWidth,
    height: viewportHeight,
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

const Live2DTutor = ({
  audioElement,
  isVisible = true,
  assistantMode = false,
  assistantSpeaking = false,
  questionEnabled = false,
  questionBusy = false,
  questionStatus = "",
  chatHistory = [],
  canReplayTts = false,
  onReplayTts,
  onClearChat,
  onRegenerate,
  onStopSpeech,
  onExportChat,
  questionLanguage = "en-US",
  onSubmitQuestion,
}) => {
  const mountRef = useRef(null);
  const panelRef = useRef(null);
  const dragStateRef = useRef(null);
  const resizeStateRef = useRef(null);
  const expandedRectRef = useRef(null);
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
  const [questionText, setQuestionText] = useState("");
  const [isVoiceInputActive, setIsVoiceInputActive] = useState(false);
  const [voiceInputStatus, setVoiceInputStatus] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const speechRecognitionRef = useRef(null);
  const [panelRect, setPanelRect] = useState({
    ...(readStoredPanelRect() || {
      x: EDGE_GAP,
      y: Math.max(EDGE_GAP, window.innerHeight - getResponsiveTutorRect().height - EDGE_GAP),
      width: getResponsiveTutorRect().width,
      height: getResponsiveTutorRect().height,
    }),
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
    let lastFrameAt = 0;
    const applyDrawableTopCorrection = (layout) => {
      if (!model) return;
      const topPaddingRatio = layout.drawableTopPaddingRatio;
      if (!Number.isFinite(topPaddingRatio)) return;
      const internalModel = model.internalModel;
      if (!internalModel?.localTransform || typeof internalModel.getDrawableVertices !== "function") return;
      const drawCount = Number.isFinite(internalModel.drawDataCount) ? internalModel.drawDataCount : 0;
      if (drawCount <= 0) return;
      let minY = Number.POSITIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;
      for (let i = 0; i < drawCount; i += 1) {
        const vertices = internalModel.getDrawableVertices(i);
        if (!vertices || vertices.length < 2) continue;
        for (let j = 1; j < vertices.length; j += 2) {
          const y = vertices[j];
          if (!Number.isFinite(y)) continue;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
      if (!Number.isFinite(minY) || !Number.isFinite(maxY) || maxY <= minY) return;
      const drawableHeight = maxY - minY;
      const targetTop = drawableHeight * Math.max(0, topPaddingRatio);
      const currentTop = (minY * internalModel.localTransform.d) + internalModel.localTransform.ty;
      const deltaTy = targetTop - currentTop;
      internalModel.localTransform.ty += deltaTy;
    };
    const layoutModel = () => {
      if (!app || !model) return;
      const modelWidth = Math.max(model.internalModel?.width || 1, 1);
      const modelHeight = Math.max(model.internalModel?.height || 1, 1);
      const layout = getAvatarLayoutPreset(activeAvatar.name);
      const scaleToFit = Math.min(
        (app.screen.width * layout.fitWidthRatio) / modelWidth,
        (app.screen.height * layout.fitHeightRatio) / modelHeight,
      );
      const targetScale = scaleToFit * layout.scaleMultiplier;
      model.anchor.set(0.5, 1);
      model.scale.set(targetScale);
      model.position.set(app.screen.width * layout.xRatio, app.screen.height * layout.yRatio);
    };

    const applyFrameValues = () => {
      if (!model) return;
      applyMouthValue(model, mouthValueRef.current);
      applyLookValue(model, lookValueRef.current.x, lookValueRef.current.y);
    };

    const updateLoop = (frameNow) => {
      if (cancelled) return;
      if (model?.autoUpdate === false) {
        const now = Number.isFinite(frameNow) ? frameNow : performance.now();
        const dt = lastFrameAt > 0 ? Math.max(0, now - lastFrameAt) : 16.67;
        lastFrameAt = now;
        model.update(dt);
      }
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

      applyDrawableTopCorrection(getAvatarLayoutPreset(activeAvatar.name));
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
        model.autoUpdate = false;
        model.scale.set(1);
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
        updateLoop(performance.now());
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
      if (isExpanded) {
        return getExpandedTutorRect();
      }
      if (isMobileViewport()) {
        return getMobileTutorRect();
      }
      return clampDesktopPanelRect(current);
    });
    const onResize = () => {
      const mobile = isMobileViewport();
      setIsMobile(mobile);
      setPanelRect((current) => {
        if (isExpanded) {
          return getExpandedTutorRect();
        }
        if (mobile && !isExpanded) {
          return getMobileTutorRect();
        }
        return clampDesktopPanelRect(current);
      });
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, [isExpanded]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isMobile || isExpanded) return;
    window.localStorage.setItem(PANEL_RECT_STORAGE_KEY, JSON.stringify({
      x: panelRect.x,
      y: panelRect.y,
      width: panelRect.width,
      height: panelRect.height,
    }));
  }, [panelRect, isMobile, isExpanded]);

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
      const dragState = dragStateRef.current;
      if (!dragState) return;
      const deltaX = moveEvent.clientX - dragState.startX;
      const deltaY = moveEvent.clientY - dragState.startY;
      const parentWidth = window.innerWidth || 0;
      const parentHeight = window.innerHeight || 0;
      const maxX = Math.max(EDGE_GAP, parentWidth - dragState.width - EDGE_GAP);
      const safeBottom = Math.max(EDGE_GAP, parentHeight - EDGE_GAP);
      const maxY = Math.max(EDGE_GAP, safeBottom - dragState.height);
      setPanelRect((current) => ({
        ...current,
        x: Math.max(EDGE_GAP, Math.min(maxX, dragState.originX + deltaX)),
        y: Math.max(EDGE_GAP, Math.min(maxY, dragState.originY + deltaY)),
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
      originX: panelRect.x,
      originY: panelRect.y,
    };
    const onMove = (moveEvent) => {
      const resizeState = resizeStateRef.current;
      if (!resizeState) return;
      const deltaX = moveEvent.clientX - resizeState.startX;
      const deltaY = moveEvent.clientY - resizeState.startY;
      const parentWidth = window.innerWidth || 0;
      const parentHeight = window.innerHeight || 0;
      const maxWidthByViewport = Math.max(MIN_WIDTH, parentWidth - EDGE_GAP - resizeState.originX);
      const maxHeightByFooter = Math.max(MIN_HEIGHT, parentHeight - EDGE_GAP - resizeState.originY);
      const nextWidth = Math.max(MIN_WIDTH, Math.min(Math.min(MAX_WIDTH, maxWidthByViewport), resizeState.width + deltaX));
      const nextHeight = Math.max(MIN_HEIGHT, Math.min(Math.min(MAX_HEIGHT, maxHeightByFooter), resizeState.height + deltaY));
      setPanelRect((current) => ({
        ...current,
        width: nextWidth,
        height: nextHeight,
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

  const handleAsk = async () => {
    const text = String(questionText || "").trim();
    if (!text || questionBusy || !questionEnabled || typeof onSubmitQuestion !== "function") return;
    const ok = await onSubmitQuestion(text, { avatarName: activeAvatar.name });
    if (ok) setQuestionText("");
  };

  const handleQuestionKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAsk().catch(() => {});
    }
  };

  const stopVoiceInput = () => {
    const recognition = speechRecognitionRef.current;
    if (!recognition) return;
    try {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.stop();
    } catch (_error) {
      // no-op
    } finally {
      speechRecognitionRef.current = null;
      setIsVoiceInputActive(false);
    }
  };

  const startVoiceInput = () => {
    if (questionBusy || !questionEnabled || typeof window === "undefined") return;
    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceInputStatus("Voice input is not supported on this browser");
      return;
    }
    setVoiceInputStatus("");
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = questionLanguage || "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = async (event) => {
      const transcript = String(event?.results?.[0]?.[0]?.transcript || "").trim();
      if (!transcript) return;
      setQuestionText(transcript);
      if (typeof onSubmitQuestion === "function") {
        await onSubmitQuestion(transcript, { avatarName: activeAvatar.name });
      }
    };
    recognition.onerror = (event) => {
      const detail = String(event?.error || "voice input failed");
      setVoiceInputStatus(detail);
    };
    recognition.onend = () => {
      speechRecognitionRef.current = null;
      setIsVoiceInputActive(false);
    };
    speechRecognitionRef.current = recognition;
    setIsVoiceInputActive(true);
    try {
      recognition.start();
    } catch (_error) {
      speechRecognitionRef.current = null;
      setIsVoiceInputActive(false);
      setVoiceInputStatus("Failed to start voice input");
    }
  };

  const toggleVoiceInput = () => {
    if (isVoiceInputActive) {
      stopVoiceInput();
      return;
    }
    startVoiceInput();
  };

  const toggleExpand = () => {
    if (typeof window === "undefined") return;
    if (!isExpanded) {
      expandedRectRef.current = { ...panelRect };
      setPanelRect(getExpandedTutorRect());
      setIsExpanded(true);
      return;
    }
    const previous = expandedRectRef.current;
    if (previous) {
      setPanelRect(previous);
    }
    setIsExpanded(false);
  };

  useEffect(() => () => {
    stopVoiceInput();
  }, []);

  return (
    <div
      ref={panelRef}
      className={`live2d-tutor ${ready ? "ready" : ""} ${isVisible ? "" : "hidden"} ${isExpanded ? "expanded" : ""}`.trim()}
      onDoubleClick={cycleAvatar}
      onPointerUp={handleMobilePointerUp}
      title={`Double click to switch avatar (${activeAvatar.name})`}
      style={{
        position: (isMobile && !isExpanded) ? "relative" : "fixed",
        width: `${panelRect.width}px`,
        height: `${panelRect.height}px`,
        left: (isMobile && !isExpanded) ? "auto" : `${panelRect.x}px`,
        top: (isMobile && !isExpanded) ? "auto" : `${panelRect.y}px`,
        bottom: "auto",
        margin: (isMobile && !isExpanded) ? `${EDGE_GAP}px` : 0,
        alignSelf: (isMobile && !isExpanded) ? "stretch" : "auto",
      }}
    >
      {!isMobile && !isExpanded && (
        <button type="button" className="live2d-tutor-handle" onPointerDown={handleDragStart}>
          Tutor · {activeAvatar.name}
        </button>
      )}
      <button
        type="button"
        className="live2d-tutor-expand"
        onClick={toggleExpand}
        title={isExpanded ? "Close full screen tutor" : "Maximize tutor panel"}
        aria-label={isExpanded ? "Close full screen tutor" : "Maximize tutor panel"}
      >
        {isExpanded ? "✕" : "⛶"}
      </button>
      <div ref={mountRef} className="live2d-tutor-canvas" />
      <div className="live2d-tutor-chat" onPointerDown={(event) => event.stopPropagation()}>
        <div className="live2d-tutor-chat-head">
          <span>Chat</span>
          <div className="live2d-tutor-chat-tools">
            <select
              className="live2d-tutor-avatar-select"
              value={activeAvatar.name}
              onChange={(event) => {
                const nextIdx = AVATAR_MODELS.findIndex((item) => item.name === event.target.value);
                if (nextIdx >= 0) setAvatarIndex(nextIdx);
              }}
              title="Select tutor avatar"
              aria-label="Select tutor avatar"
            >
              {AVATAR_MODELS.map((item) => (
                <option key={item.name} value={item.name}>{item.name}</option>
              ))}
            </select>
            <button
              type="button"
              className="live2d-tutor-chat-btn"
              onClick={() => { if (typeof onRegenerate === "function") onRegenerate(activeAvatar.name); }}
              disabled={questionBusy}
              title="Regenerate last tutor answer"
            >
              Regen
            </button>
            <button
              type="button"
              className="live2d-tutor-chat-btn"
              onClick={() => { if (typeof onExportChat === "function") onExportChat(); }}
              disabled={!chatHistory.length}
              title="Export chat transcript"
            >
              Export
            </button>
            <button
              type="button"
              className="live2d-tutor-chat-btn"
              onClick={() => { if (typeof onClearChat === "function") onClearChat(); }}
              disabled={questionBusy || !chatHistory.length}
              title="Clear tutor chat history"
            >
              Clear
            </button>
          </div>
        </div>
        <div className="live2d-tutor-chat-log">
          {chatHistory.length ? chatHistory.slice(-8).map((item, idx) => (
            <div key={`${item.role}-${idx}`} className={`live2d-tutor-chat-msg ${item.role === "user" ? "user" : "assistant"}`.trim()}>
              <strong>{item.role === "user" ? "You" : "Tutor"}:</strong> {String(item.text || "")}
              {item.role === "assistant" && (item.usage || item.spend || (Array.isArray(item.citations) && item.citations.length)) ? (
                <div className="live2d-tutor-chat-meta">
                  {item.usage ? `tokens:${item.usage.total_tokens || 0}` : ""}
                  {item.spend ? ` cost:$${Number(item.spend.call_cost_usd || 0).toFixed(4)}` : ""}
                  {Array.isArray(item.citations) && item.citations.length ? (
                    <span>
                      {" "}
                      · <a href={item.citations[0]} target="_blank" rel="noreferrer">source</a>
                    </span>
                  ) : null}
                </div>
              ) : null}
            </div>
          )) : <div className="live2d-tutor-chat-empty">Start with a question about this slide.</div>}
        </div>
        <div className="live2d-tutor-chat-row">
          <input
            type="text"
            className="live2d-tutor-chat-input"
            placeholder={questionEnabled ? "Ask tutor about this slide..." : "Text chat requires grant"}
            value={questionText}
            onChange={(event) => setQuestionText(event.target.value)}
            onKeyDown={handleQuestionKeyDown}
            disabled={!questionEnabled || questionBusy}
          />
          <button
            type="button"
            className="live2d-tutor-chat-btn"
            onClick={() => { handleAsk().catch(() => {}); }}
            disabled={!questionEnabled || questionBusy || !String(questionText || "").trim()}
          >
            {questionBusy ? "..." : "Ask"}
          </button>
          <button
            type="button"
            className={`live2d-tutor-chat-btn ${isVoiceInputActive ? "active" : ""}`.trim()}
            onClick={toggleVoiceInput}
            disabled={!questionEnabled || questionBusy}
            title="Voice input for tutor"
          >
            🎤
          </button>
          <button
            type="button"
            className="live2d-tutor-chat-btn"
            onClick={() => { if (typeof onReplayTts === "function") onReplayTts(); }}
            disabled={!canReplayTts || questionBusy}
            title="Replay tutor speech"
          >
            ↻
          </button>
          <button
            type="button"
            className="live2d-tutor-chat-btn"
            onClick={() => { if (typeof onStopSpeech === "function") onStopSpeech(); }}
            disabled={questionBusy}
            title="Stop tutor speech"
          >
            ■
          </button>
        </div>
        {questionStatus ? <div className="live2d-tutor-chat-status">{questionStatus}</div> : null}
        {voiceInputStatus ? <div className="live2d-tutor-chat-status">{voiceInputStatus}</div> : null}
      </div>
      {!isMobile && !isExpanded && (
        <button type="button" className="live2d-tutor-resizer" onPointerDown={handleResizeStart} aria-label="Resize tutor" />
      )}
    </div>
  );
};

export default Live2DTutor;
