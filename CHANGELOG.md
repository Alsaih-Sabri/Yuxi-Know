# Changelog - ParseMind Improvements

## Recent Improvements (February 2026)

### 🎨 Rebranding to ParseMind
- **Renamed** from "Yuxi-Know" (语析) to **ParseMind**
- **New tagline**: "Parse Knowledge, Power Intelligence"
- **Updated branding** across all frontend and backend configurations
- **New favicon**: Modern lettermark design representing AI knowledge parsing
- **Updated** page titles, footer, and all brand references

### 🌍 Complete English Localization
- **Translated** all Chinese text to English throughout the application
- **Fixed** dashboard file type distribution labels
- **Translated** MCP server form labels and placeholders
- **Updated** error messages from Chinese to English
- **Translated** backend error messages (chat stream service, routers)
- **Translated** console log messages and comments
- **Updated** info store default values and fallbacks

### ♿ Accessibility Improvements
- **Fixed** Content Security Policy (CSP) issues
  - Added `worker-src 'self' blob:` to allow web workers
  - Configured `script-src` with `'unsafe-eval'` for framework compatibility
- **Resolved** form accessibility warnings
  - Added `id` attributes to all form inputs in AgentConfigSidebar
  - Added `id` attributes to MCP server form inputs
  - Added `id` attributes to user management form inputs
  - Added `formItemId` prop to ModelSelectorComponent
  - Fixed label `for` attribute mismatches for better autofill and screen reader support

### 🐛 Bug Fixes
- **Fixed** "发生错误: interrupted" error message appearing in Chinese
  - Updated `src/services/chat_stream_service.py`
  - Updated `server/routers/chat_router.py`
  - Updated `server/utils/migrate.py`
- **Fixed** batch delete messages in database store
- **Fixed** CSS compatibility warnings for `line-clamp` property

### 📝 Code Quality
- **Translated** all Chinese comments to English in:
  - Dashboard components (KnowledgeStatsComponent, DashboardView)
  - Agent components (AgentMessageComponent, useAgentStreamHandler)
  - Store files (info.js, database.js)
- **Updated** backend configuration template (`info.template.yaml`)
- **Improved** code maintainability with consistent English documentation

### 🔧 Technical Improvements
- **Updated** frontend branding in `web/src/stores/info.js`
- **Updated** backend branding in `src/config/static/info.template.yaml`
- **Updated** page title in `web/index.html`
- **Updated** login view fallback values
- **Maintained** hot-reload functionality for development

---

## How to Apply These Changes

1. **Restart the backend** to load new configuration:
   ```bash
   docker compose restart api-dev
   ```

2. **Hard refresh** your browser to see the new branding:
   - Windows/Linux: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

3. All changes are immediately visible after refresh!

---

## Contributors
- Improvements made in collaboration with AI assistant
- Focus on internationalization, accessibility, and user experience

