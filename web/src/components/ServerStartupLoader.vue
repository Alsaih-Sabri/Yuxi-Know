<template>
  <div v-if="isLoading" class="startup-loader-overlay">
    <div class="startup-loader-content">
      <div class="loader-spinner"></div>
      <h2 class="loader-title">{{ $t('startup.title') }}</h2>
      <p class="loader-message">{{ currentMessage }}</p>
      <div class="loader-progress">
        <div class="progress-bar" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="loader-hint">{{ $t('startup.hint') }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const isLoading = ref(false)
const progress = ref(0)
const currentMessage = ref('')

const messages = [
  'startup.connecting',
  'startup.loadingDatabase',
  'startup.initializingAgents',
  'startup.almostReady'
]

let messageInterval
let progressInterval
let pollHealthInterval

onMounted(async () => {
  // Check server health immediately
  const checkHealth = async () => {
    try {
      const response = await fetch('/api/system/health', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        return true
      }
    } catch (error) {
      // Server not ready yet
    }
    return false
  }

  // Initial check - only show loader if backend is not ready
  const initialCheck = await checkHealth()
  if (initialCheck) {
    // Backend is ready, don't show loader
    return
  }

  // Backend not ready, show loader
  isLoading.value = true
  let messageIndex = 0
  currentMessage.value = t(messages[0])

  // Update message every 5 seconds
  messageInterval = setInterval(() => {
    messageIndex = (messageIndex + 1) % messages.length
    currentMessage.value = t(messages[messageIndex])
  }, 5000)

  // Update progress bar
  progressInterval = setInterval(() => {
    if (progress.value < 90) {
      progress.value += 2
    }
  }, 500)

  // Poll every 2 seconds
  const maxAttempts = 60 // 2 minutes max
  let attempts = 0
  
  pollHealthInterval = setInterval(async () => {
    attempts++
    const ready = await checkHealth()
    
    if (ready || attempts >= maxAttempts) {
      clearInterval(pollHealthInterval)
      if (ready) {
        progress.value = 100
        setTimeout(() => {
          isLoading.value = false
          // Auto-refresh the page when server is ready
          window.location.reload()
        }, 500)
      } else {
        // Timeout - hide loader anyway
        isLoading.value = false
      }
    }
  }, 2000)
})

onUnmounted(() => {
  if (messageInterval) clearInterval(messageInterval)
  if (progressInterval) clearInterval(progressInterval)
  if (pollHealthInterval) clearInterval(pollHealthInterval)
})
</script>

<style lang="less" scoped>
.startup-loader-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #000000 0%, #023944 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.startup-loader-content {
  text-align: center;
  color: white;
  max-width: 500px;
  padding: 40px;
}

.loader-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 30px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loader-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 16px;
  color: white;
}

.loader-message {
  font-size: 16px;
  margin: 0 0 24px;
  color: rgba(255, 255, 255, 0.9);
  min-height: 24px;
}

.loader-progress {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-bar {
  height: 100%;
  background: white;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.loader-hint {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
}
</style>
