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
