<script setup>
import enUS from 'ant-design-vue/es/locale/en_US'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useAgentStore } from '@/stores/agent'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import { onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ServerStartupLoader from '@/components/ServerStartupLoader.vue'

const agentStore = useAgentStore()
const userStore = useUserStore()
const themeStore = useThemeStore()
const { locale } = useI18n()

// Dynamically set Ant Design locale based on current language
const antLocale = computed(() => {
  return locale.value === 'zh' ? zhCN : enUS
})

onMounted(async () => {
  if (userStore.isLoggedIn) {
    await agentStore.initialize()
  }
})
</script>
<template>
  <a-config-provider :theme="themeStore.currentTheme" :locale="antLocale">
    <ServerStartupLoader />
    <router-view />
  </a-config-provider>
</template>
