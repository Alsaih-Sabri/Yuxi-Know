<template>
  <div class="basic-settings-section">
    <h3 class="section-title">{{ $t('basicSettings.retrievalConfig') }}</h3>
    <div class="settings-panel">
      <div class="setting-row two-cols">
        <div class="col-item">
          <div class="setting-label">{{ items?.default_model?.des || $t('basicSettings.defaultChatModel') }}</div>
          <div class="setting-content">
            <ModelSelectorComponent
              @select-model="handleChatModelSelect"
              :model_spec="configStore.config?.default_model"
              :placeholder="$t('basicSettings.selectDefaultModel')"
            />
          </div>
        </div>
        <div class="col-item">
          <div class="setting-label">{{ items?.fast_model.des }}</div>
          <div class="setting-content">
            <ModelSelectorComponent
              @select-model="handleFastModelSelect"
              :model_spec="configStore.config?.fast_model"
              :placeholder="$t('basicSettings.selectModel')"
            />
          </div>
        </div>
      </div>
      <div class="setting-row two-cols">
        <div class="col-item">
          <div class="setting-label">{{ items?.embed_model.des }}</div>
          <div class="setting-content">
            <EmbeddingModelSelector
              :value="configStore.config?.embed_model"
              @change="handleChange('embed_model', $event)"
              style="width: 100%"
            />
          </div>
        </div>
        <div class="col-item">
          <div class="setting-label">{{ items?.reranker.des }}</div>
          <div class="setting-content">
            <a-select
              class="full-width"
              :value="configStore.config?.reranker"
              @change="handleChange('reranker', $event)"
              :placeholder="$t('basicSettings.selectRerankerModel')"
            >
              <a-select-option v-for="(name, idx) in rerankerChoices" :key="idx" :value="name"
                >{{ name }}
              </a-select-option>
            </a-select>
          </div>
        </div>
      </div>
    </div>

    <h3 class="section-title">{{ $t('basicSettings.contentGuardConfig') }}</h3>
    <div class="section">
      <div class="card">
        <span class="label">{{ items?.enable_content_guard.des }}</span>
        <a-switch
          :checked="configStore.config?.enable_content_guard"
          @change="handleChange('enable_content_guard', $event)"
        />
      </div>
      <div class="card" v-if="configStore.config?.enable_content_guard">
        <span class="label">{{ items?.enable_content_guard_llm.des }}</span>
        <a-switch
          :checked="configStore.config?.enable_content_guard_llm"
          @change="handleChange('enable_content_guard_llm', $event)"
        />
      </div>
      <div
        class="card card-select"
        v-if="
          configStore.config?.enable_content_guard && configStore.config?.enable_content_guard_llm
        "
      >
        <span class="label">{{ items?.content_guard_llm_model.des }}</span>
        <ModelSelectorComponent
          @select-model="handleContentGuardModelSelect"
          :model_spec="configStore.config?.content_guard_llm_model"
          :placeholder="$t('basicSettings.selectModel')"
        />
      </div>
    </div>

    <!-- 服务链接部分 -->
    <h3 v-if="userStore.isAdmin" class="section-title">{{ $t('basicSettings.serviceLinks') }}</h3>
    <div v-if="userStore.isAdmin">
      <p class="service-description">
        {{ $t('basicSettings.serviceDescription') }}
      </p>
      <div class="services-grid">
        <div class="service-link-card">
          <div class="service-info">
            <h4>{{ $t('basicSettings.services.neo4j.title') }}</h4>
            <p>{{ $t('basicSettings.services.neo4j.description') }}</p>
          </div>
          <a-button
            type="default"
            @click="openLink('http://localhost:7474/')"
            :icon="h(GlobalOutlined)"
          >
            {{ $t('basicSettings.visit') }}
          </a-button>
        </div>

        <div class="service-link-card">
          <div class="service-info">
            <h4>{{ $t('basicSettings.services.api.title') }}</h4>
            <p>{{ $t('basicSettings.services.api.description') }}</p>
          </div>
          <a-button
            type="default"
            @click="openLink('http://localhost:5050/docs')"
            :icon="h(GlobalOutlined)"
          >
            {{ $t('basicSettings.visit') }}
          </a-button>
        </div>

        <div class="service-link-card">
          <div class="service-info">
            <h4>{{ $t('basicSettings.services.minio.title') }}</h4>
            <p>{{ $t('basicSettings.services.minio.description') }}</p>
          </div>
          <a-button
            type="default"
            @click="openLink('http://localhost:9001')"
            :icon="h(GlobalOutlined)"
          >
            {{ $t('basicSettings.visit') }}
          </a-button>
        </div>

        <div class="service-link-card">
          <div class="service-info">
            <h4>{{ $t('basicSettings.services.milvus.title') }}</h4>
            <p>{{ $t('basicSettings.services.milvus.description') }}</p>
          </div>
          <a-button
            type="default"
            @click="openLink('http://localhost:9091/webui/')"
            :icon="h(GlobalOutlined)"
          >
            {{ $t('basicSettings.visit') }}
          </a-button>
        </div>

        <div class="service-link-card">
          <div class="service-info">
            <h4>{{ $t('basicSettings.services.sqlite.title') }}</h4>
            <p>{{ $t('basicSettings.services.sqlite.description') }}</p>
          </div>
          <a-button
            type="default"
            @click="openLink('http://localhost:9092/')"
            :icon="h(GlobalOutlined)"
          >
            {{ $t('basicSettings.visit') }}
          </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/config'
import { useUserStore } from '@/stores/user'
import { GlobalOutlined } from '@ant-design/icons-vue'
import ModelSelectorComponent from '@/components/ModelSelectorComponent.vue'
import EmbeddingModelSelector from '@/components/EmbeddingModelSelector.vue'

const { t, locale } = useI18n()
const configStore = useConfigStore()
const userStore = useUserStore()

// Get config items with language-specific descriptions
const items = computed(() => {
  const configItems = configStore.config._config_items
  if (!configItems) return {}
  
  // Transform items to use language-specific description
  const transformed = {}
  for (const [key, value] of Object.entries(configItems)) {
    transformed[key] = {
      ...value,
      des: locale.value === 'en' ? value.des_en || value.des : value.des_zh || value.des
    }
  }
  return transformed
})

const rerankerChoices = computed(() => {
  return Object.keys(configStore?.config?.reranker_names || {}) || []
})

const preHandleChange = (key, e) => {
  return true
}

const handleChange = (key, e) => {
  if (!preHandleChange(key, e)) {
    return
  }
  configStore.setConfigValue(key, e)
}

const handleChanges = (items) => {
  for (const key in items) {
    if (!preHandleChange(key, items[key])) {
      return
    }
  }
  configStore.setConfigValues(items)
}

const handleChatModelSelect = (spec) => {
  if (typeof spec === 'string' && spec) {
    configStore.setConfigValue('default_model', spec)
  }
}

const handleFastModelSelect = (spec) => {
  if (typeof spec === 'string' && spec) {
    configStore.setConfigValue('fast_model', spec)
  }
}

const handleContentGuardModelSelect = (spec) => {
  if (typeof spec === 'string' && spec) {
    configStore.setConfigValue('content_guard_llm_model', spec)
  }
}

const openLink = (url) => {
  window.open(url, '_blank')
}
</script>

<style lang="less" scoped>
.basic-settings-section {
  .settings-content {
    max-width: 100%;
  }

  .section-title {
    color: var(--gray-900);
    font-size: 16px;
    font-weight: 600;
    margin: 24px 0 0 0;
    padding-bottom: 8px;

    &:first-child {
      margin-top: 12px;
    }
  }

  .service-description {
    color: var(--gray-600);
    font-size: 14px;
    margin: 0 0 16px 0;
    line-height: 1.5;
  }

  .section {
    background-color: var(--gray-0);
    padding: 10px 16px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    border: 1px solid var(--gray-150);
  }

  .settings-panel {
    background-color: var(--gray-50);
    border: 1px solid var(--gray-200);
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .setting-row {
    display: flex;
    flex-direction: column;
    gap: 8px;

    &.two-cols {
      flex-direction: row;
      gap: 20px;
    }

    .col-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
    }
  }

  .setting-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--gray-700);
  }

  .setting-content {
    width: 100%;

    .full-width {
      width: 100%;
    }
  }

  .card {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .label {
      margin-right: 20px;
      font-weight: 500;
      color: var(--gray-800);
      flex-shrink: 0;
      min-width: 140px;
    }

    &.card-select {
      align-items: flex-start;
      gap: 12px;

      .label {
        margin-right: 0;
        margin-top: 6px;
      }
    }
  }

  .services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    margin-top: 16px;
  }

  .service-link-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    border: 1px solid var(--gray-150);
    border-radius: 8px;
    background: var(--gray-0);
    transition: all 0.2s;
    min-height: 70px;

    &:hover {
      box-shadow: 0 1px 8px var(--gray-200);
      border-color: var(--main-200);
    }

    .service-info {
      flex: 1;
      margin-right: 16px;

      h4 {
        margin: 0 0 4px 0;
        color: var(--gray-900);
        font-size: 15px;
        font-weight: 600;
      }

      p {
        margin: 0;
        color: var(--gray-600);
        font-size: 13px;
        line-height: 1.4;
      }
    }
  }
}
</style>
