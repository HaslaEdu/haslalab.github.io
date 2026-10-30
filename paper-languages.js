/* Available problem-paper languages, independent of the interface language. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PaperLanguages = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const labels = {en:'English',ko:'한국어',ru:'Русский',zh:'中文',hu:'Magyar',de:'Deutsch',fr:'Français',es:'Español',pt:'Português',pl:'Polski',it:'Italiano',ja:'日本語',uk:'Українська',et:'Eesti',fi:'Suomi',sv:'Svenska',cs:'Čeština',sk:'Slovenčina',ro:'Română',bg:'Български',tr:'Türkçe',id:'Bahasa Indonesia'};
  const code = value => /^[a-z]{2}$/.test(String(value).toLowerCase()) ? String(value).toLowerCase() : value === 'original' ? value : '';
  const path = value => typeof value === 'string' && value.length <= 2000 &&
    (/^(?:pdfx?\/[a-z]+\/)?[A-Za-z0-9][A-Za-z0-9_.-]{2,100}\.pdf$/.test(value) || /^https:\/\/[^\s<>"'|]+$/i.test(value));
  function label(language, ui) {
    return labels[language] || (language === 'original' ? (ui === 'ko' ? '원문' : 'Original language') : String(language).toUpperCase());
  }
  function files(slot) {
    if (!slot || typeof slot !== 'object') return {};
    const out = {};
    for (const [language, file] of Object.entries(slot.papers || {})) {
      const normalized = code(language);
      if (normalized && path(file)) out[normalized] = file;
    }
    if (path(slot.paper)) {
      const suffix = /_([A-Z]{2})\.pdf$/.exec(slot.paper);
      const language = code(slot.paperLang || (suffix && suffix[1])) || 'original';
      out[language] = slot.paper;
    }
    if (slot.ko && path(slot.ko.paper)) out.ko = slot.ko.paper;
    return out;
  }
  function normalize(raw, count) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw) || !Number.isInteger(count) || count < 1 || count > 4) return {};
    const out = {};
    for (const [language, pages] of Object.entries(raw)) {
      const normalized = code(language);
      if (normalized && Array.isArray(pages) && pages.length === count && pages.every(path)) out[normalized] = pages.slice();
    }
    return out;
  }
  function bundle(slots, ui) {
    if (!Array.isArray(slots) || !slots.length) return {papers:{}, language:''};
    const options = slots.map(files), papers = {};
    for (const language of Object.keys(options[0])) {
      if (options.every(option => option[language])) papers[language] = options.map(option => option[language]);
    }
    // A session with mixed source languages still has its published papers.
    if (!Object.keys(papers).length && slots.every(slot => path(slot.paper))) papers.original = slots.map(slot => slot.paper);
    const language = papers[ui] ? ui : papers.en ? 'en' : Object.keys(papers)[0] || '';
    return {papers, language};
  }
  return {label, files, normalize, bundle};
});
