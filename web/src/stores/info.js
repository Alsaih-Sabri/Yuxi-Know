import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { brandApi } from '@/apis/system_api'

export const useInfoStore = defineStore('info', () => {
  // State
  const infoConfig = ref({})
  const isLoading = ref(false)
  const isLoaded = ref(false)
  const debugMode = ref(false)

  // Computed property - Organization info
  const organization = computed(
    () =>
      infoConfig.value.organization || {
        name: 'ParseMind',
        logo: '/favicon.svg',
        avatar: '/avatar.jpg'
      }
  )

  // Computed property - Branding info
  const branding = computed(
    () =>
      infoConfig.value.branding || {
        name: 'ParseMind',
        title: 'ParseMind',
        subtitle: 'Parse Knowledge, Power Intelligence',
        description: 'AI-powered knowledge base with intelligent parsing and knowledge graph technology'
      }
  )

  // Computed property - Features
  const features = computed(
    () =>
      infoConfig.value.features || [
        {
          label: 'GitHub Stars',
          value: '3200+',
          description: 'Recognition and support from developer community',
          icon: 'stars'
        },
        {
          label: 'Resolved Issues',
          value: '250+',
          description: 'Continuous improvement and problem-solving capability',
          icon: 'issues'
        },
        {
          label: 'Total Commits',
          value: '1200+',
          description: 'Active development iterations and feature updates',
          icon: 'commits'
        },
        {
          label: 'Open Source License',
          value: 'MIT License',
          description: 'Completely free, supports commercial use',
          icon: 'license'
        }
      ]
  )

  const actions = computed(
    () =>
      infoConfig.value.actions || [
        {
          name: 'Demo Video',
          icon: 'video',
          url: 'https://www.bilibili.com/video/BV1DF14BTETq'
        },
        {
          name: 'Documentation',
          icon: 'docs',
          url: 'https://xerrors.github.io/Yuxi-Know/'
        },
        {
          name: 'Submit Issue',
          icon: 'issue',
          url: 'https://github.com/xerrors/Yuxi-Know/issues/new/choose'
        },
        {
          name: 'Roadmap',
          icon: 'roadmap',
          url: 'https://github.com/xerrors/Yuxi-Know#roadmap'
        }
      ]
  )

  // Computed property - Footer info
  const footer = computed(
    () =>
      infoConfig.value.footer || {
        copyright: '© ParseMind 2025 [WIP] v0.12.138'
      }
  )

  // Action methods
  function setInfoConfig(newConfig) {
    infoConfig.value = newConfig
    isLoaded.value = true
  }

  function setDebugMode(enabled) {
    debugMode.value = enabled
  }

  function toggleDebugMode() {
    debugMode.value = !debugMode.value
  }

  async function loadInfoConfig(force = false) {
    // If already loaded and not forcing refresh, don't reload
    if (isLoaded.value && !force) {
      return infoConfig.value
    }

    try {
      isLoading.value = true
      const response = await brandApi.getInfoConfig()

      if (response.success && response.data) {
        setInfoConfig(response.data)
        console.debug('Info configuration loaded successfully:', response.data)
        return response.data
      } else {
        console.warn('Failed to load info configuration, using default config')
        return null
      }
    } catch (error) {
      console.error('Error loading info configuration:', error)
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function reloadInfoConfig() {
    try {
      isLoading.value = true
      const response = await brandApi.reloadInfoConfig()

      if (response.success && response.data) {
        setInfoConfig(response.data)
        console.debug('Info configuration reloaded successfully:', response.data)
        return response.data
      } else {
        console.warn('Failed to reload info configuration')
        return null
      }
    } catch (error) {
      console.error('Error reloading info configuration:', error)
      return null
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    infoConfig,
    isLoading,
    isLoaded,
    debugMode,

    // Computed properties
    organization,
    branding,
    features,
    footer,
    actions,

    // Methods
    setInfoConfig,
    setDebugMode,
    toggleDebugMode,
    loadInfoConfig,
    reloadInfoConfig
  }
})
