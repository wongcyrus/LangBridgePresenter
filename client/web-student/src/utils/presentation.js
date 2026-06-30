const LANGUAGE_CODE_MAP = {
  en: "en-US",
  zh: "zh-CN",
  yue: "yue-HK",
  "en-US": "en-US",
  "zh-CN": "zh-CN",
  "yue-HK": "yue-HK",
};

export function canonicalLanguageCode(languageCode, fallback = "en-US") {
  if (!languageCode) return fallback;
  return LANGUAGE_CODE_MAP[languageCode] || languageCode;
}

export function pickBestLanguage(availableLanguages, preferredLanguage) {
  if (!Array.isArray(availableLanguages) || availableLanguages.length === 0) {
    return null;
  }

  const canonical = canonicalLanguageCode(preferredLanguage, preferredLanguage);
  if (availableLanguages.includes(preferredLanguage)) return preferredLanguage;
  if (availableLanguages.includes(canonical)) return canonical;

  const fuzzyMatch = availableLanguages.find(
    (lang) => lang.startsWith(preferredLanguage) || preferredLanguage.startsWith(lang)
  );
  return fuzzyMatch || availableLanguages[0];
}

export function normalizeLanguageSelection(currentLanguage, availableLanguages) {
  return pickBestLanguage(availableLanguages, currentLanguage);
}

export function parseNumericIds(ids) {
  return ids
    .map((id) => parseInt(id, 10))
    .filter((id) => Number.isInteger(id))
    .sort((a, b) => a - b);
}

export function normalizeBroadcastStatus(status) {
  if (!status) return null;
  return {
    status: status.status || "unknown",
    reason: status.reason || "",
    courseId: status.course_id || status.courseId || null,
    presentationId: status.presentation_id || status.current_presentation_id || null,
    slideId: status.slide_id || status.current_slide_id || null,
    presenterIds: status.presenter_ids || status.presenterIds || [],
    broadcastCourseIds: status.broadcast_course_ids || status.broadcastCourseIds || [],
    registryUpdated: status.registry_updated ?? status.registryUpdated ?? null,
  };
}

export function formatBroadcastStatusLabel(status) {
  if (!status) return "Waiting for broadcast";
  if (status.status === "broadcasted") return "Broadcast live";
  if (status.status === "skipped") {
    return status.reason ? `Skipped: ${status.reason}` : "Skipped";
  }
  return status.status;
}

export function buildSlideNarration({
  presentationId,
  slideId,
  title,
  text,
  sourceContext,
  hasVisual = false,
}) {
  const parts = [];

  if (presentationId || slideId) {
    parts.push(
      [presentationId ? `Presentation ${presentationId}` : null, slideId ? `slide ${slideId}` : null]
        .filter(Boolean)
        .join(", ")
    );
  }

  const cleanTitle = (title || "").trim();
  if (cleanTitle) parts.push(`Title: ${cleanTitle}`);

  const cleanText = (text || "").trim();
  if (cleanText) parts.push(`Text: ${cleanText}`);

  const cleanContext = (sourceContext || "").trim();
  if (cleanContext && cleanContext !== cleanText) {
    parts.push(`Speaker notes: ${cleanContext}`);
  }

  if (hasVisual) {
    parts.push("Visual content is available on this slide.");
  }

  if (parts.length === 0) {
    return "No narratable content is available for this slide.";
  }

  return parts.join(". ");
}
