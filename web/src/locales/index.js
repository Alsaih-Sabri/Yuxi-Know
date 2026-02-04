import { createI18n } from 'vue-i18n'
import en from './en.json'
import zh from './zh.json'

const messages = {
  en,
  zh
}

// Get saved language from localStorage or default to English
// This runs synchronously before app mount
function getDefaultLocale() {
  // Check localStorage first (user preference)
  try {
    const saved = localStorage.getItem('locale')
    if (saved && messages[saved]) {
      return saved
    }
  } catch {
    // localStorage might not be available
  }

  // Default to English (users can switch language using the language switcher)
  return 'en'
}

// Determine locale once at module load time
const initialLocale = getDefaultLocale()

const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages,
  sync: true,
  globalInjection: true,
  warnHtmlMessage: false
})

export default i18n
