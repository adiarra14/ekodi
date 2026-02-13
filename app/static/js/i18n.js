/**
 * Ekodi i18n (Internationalization) Module
 * Supports: Bambara (bm), French (fr), English (en)
 */

class I18n {
  constructor(defaultLocale = 'bm') {
    this.locale = defaultLocale;
    this.translations = {};
    this.listeners = [];
  }

  async init() {
    const locales = ['bm', 'fr', 'en'];
    const promises = locales.map(async (loc) => {
      try {
        const resp = await fetch(`/static/i18n/${loc}.json`);
        this.translations[loc] = await resp.json();
      } catch (e) {
        console.warn(`Failed to load locale ${loc}:`, e);
        this.translations[loc] = {};
      }
    });
    await Promise.all(promises);

    // Restore saved locale
    const saved = localStorage.getItem('ekodi-locale');
    if (saved && this.translations[saved]) {
      this.locale = saved;
    }

    this.apply();
  }

  t(key) {
    return this.translations[this.locale]?.[key] || this.translations['en']?.[key] || key;
  }

  setLocale(locale) {
    if (!this.translations[locale]) return;
    this.locale = locale;
    localStorage.setItem('ekodi-locale', locale);
    this.apply();
    this.listeners.forEach(fn => fn(locale));
  }

  onChange(fn) {
    this.listeners.push(fn);
  }

  apply() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = this.t(key);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.placeholder = this.t(key);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.title = this.t(key);
    });
    document.documentElement.lang = this.locale;
  }
}

// Export as global
window.i18n = new I18n('bm');
