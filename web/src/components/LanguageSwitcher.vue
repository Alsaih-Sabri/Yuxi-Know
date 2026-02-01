<template>
  <a-dropdown :trigger="['click']">
    <a-button type="text" class="language-btn">
      <globe-icon :size="18" />
      <span class="lang-text">{{ currentLangLabel }}</span>
    </a-button>
    <template #overlay>
      <a-menu @click="handleLanguageChange" :selectedKeys="[locale]">
        <a-menu-item key="en">
          <span class="lang-option">English</span>
        </a-menu-item>
        <a-menu-item key="zh">
          <span class="lang-option">中文</span>
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Globe as GlobeIcon } from 'lucide-vue-next'

const { locale } = useI18n()

const currentLangLabel = computed(() => {
  return locale.value === 'zh' ? '中文' : 'EN'
})

const handleLanguageChange = ({ key }) => {
  locale.value = key
  localStorage.setItem('locale', key)
}
</script>

<style lang="less" scoped>
.language-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-600);
  padding: 4px 8px;
  height: auto;

  &:hover {
    color: var(--main-color);
    background-color: var(--gray-100);
  }

  .lang-text {
    font-size: 13px;
    font-weight: 500;
  }
}

.lang-option {
  font-size: 14px;
}
</style>
