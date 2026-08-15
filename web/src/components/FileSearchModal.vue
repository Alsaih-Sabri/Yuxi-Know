<template>
  <Teleport to="body">
    <div v-if="open" class="file-search-overlay" @mousedown.self="close">
      <section
        class="file-search-modal"
        role="dialog"
        aria-modal="true"
        aria-label="搜索文件"
        @keydown.down.prevent="moveSelection(1)"
        @keydown.up.prevent="moveSelection(-1)"
        @keydown.enter.prevent="confirmSelection"
        @keydown.esc.prevent="close"
      >
        <div class="file-search-input-row">
          <input
            ref="searchInputRef"
            v-model="searchText"
            class="file-search-input"
            type="text"
            :placeholder="placeholder"
            autocomplete="off"
            aria-label="搜索文件"
          />
          <button type="button" class="file-search-close" aria-label="关闭" @click="close">
            <X :size="20" />
          </button>
        </div>

        <div class="file-search-body">
          <div v-if="isSearching && results.length === 0" class="file-search-skeleton">
            <div v-for="index in 5" :key="index" class="skeleton-row">
              <span class="skeleton-dot"></span>
              <span class="skeleton-lines">
                <i></i>
                <i></i>
              </span>
            </div>
          </div>

          <div v-else-if="results.length > 0" class="file-search-results">
            <button
              v-for="(item, index) in results"
              :key="item.path"
              type="button"
              class="file-search-result"
              :class="{ selected: selectedIndex === index }"
              @mouseenter="selectedIndex = index"
              @click="selectResult(item)"
            >
              <FileTypeIcon :name="item.name" :size="18" class="result-icon" />
              <span class="result-main">
                <span class="result-title">
                  <template v-for="(part, partIndex) in splitName(item)" :key="partIndex">
                    <mark v-if="part.match">{{ part.text }}</mark>
                    <span v-else>{{ part.text }}</span>
                  </template>
                </span>
                <span class="result-path">{{ item.path }}</span>
              </span>
              <span class="result-date">{{ formatResultDate(item.modified_at) }}</span>
            </button>
          </div>

          <div v-else-if="searchError" class="file-search-error">{{ searchError }}</div>

          <div v-else-if="!isSearching" class="file-search-empty">未找到相关文件</div>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, onUnmounted, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import dayjs, { parseToShanghai } from '@/utils/time'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'

/**
 * 通用文件搜索弹窗，样式与对话搜索（ConversationSearchModal）保持一致。
 * 通过 search 属性注入具体搜索实现，选中后向父组件抛出 select 事件。
 */
const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  placeholder: {
    type: String,
    default: '搜索文件...'
  },
  search: {
    type: Function,
    required: true
  }
})

const emit = defineEmits(['update:open', 'select'])

const searchInputRef = ref(null)
const searchText = ref('')
const results = ref([])
const selectedIndex = ref(0)
const isSearching = ref(false)
const searchError = ref('')
let searchTimer = null
let searchRequestId = 0

const trimmedSearchText = ref('')

const resetState = () => {
  searchRequestId += 1
  searchText.value = ''
  trimmedSearchText.value = ''
  results.value = []
  selectedIndex.value = 0
  isSearching.value = false
  searchError.value = ''
}

const close = () => {
  emit('update:open', false)
}

const moveSelection = (delta) => {
  if (!results.value.length) return
  selectedIndex.value = (selectedIndex.value + delta + results.value.length) % results.value.length
  nextTick(() => {
    document.querySelector('.file-search-result.selected')?.scrollIntoView({ block: 'nearest' })
  })
}

const confirmSelection = () => {
  const item = results.value[selectedIndex.value]
  if (item) selectResult(item)
}

const selectResult = (item) => {
  if (!item?.path) return
  emit('select', item)
  close()
}

const searchFiles = async (query) => {
  const requestId = ++searchRequestId
  isSearching.value = true
  searchError.value = ''
  try {
    const response = await props.search(query)
    if (requestId !== searchRequestId) return
    results.value = response?.entries || []
    selectedIndex.value = 0
  } catch (error) {
    if (requestId === searchRequestId) {
      console.warn('搜索文件失败:', error)
      results.value = []
      searchError.value = error?.message || '搜索失败，请重试'
    }
  } finally {
    if (requestId === searchRequestId) isSearching.value = false
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      resetState()
      await nextTick()
      searchInputRef.value?.focus()
    }
  }
)

watch(searchText, (text) => {
  const query = text.trim()
  trimmedSearchText.value = query
  clearTimeout(searchTimer)
  if (!query) {
    // 作废在途请求，避免清空输入后陈旧结果回填
    searchRequestId += 1
    results.value = []
    isSearching.value = false
    return
  }
  searchTimer = setTimeout(() => searchFiles(query), 250)
})

onUnmounted(() => clearTimeout(searchTimer))

const formatResultDate = (value) => {
  const parsed = parseToShanghai(value)
  if (!parsed) return ''
  if (parsed.year() === dayjs().year()) return parsed.format('M月D日')
  return parsed.format('YYYY-MM-DD')
}

// 名称中命中关键词的部分高亮展示
const splitName = (item) => {
  const name = item?.name || ''
  const query = trimmedSearchText.value
  if (!query) return [{ text: name, match: false }]

  const lowerName = name.toLowerCase()
  const lowerQuery = query.toLowerCase()
  const parts = []
  let cursor = 0
  let matchIndex = lowerName.indexOf(lowerQuery)
  while (matchIndex >= 0) {
    if (matchIndex > cursor) parts.push({ text: name.slice(cursor, matchIndex), match: false })
    parts.push({ text: name.slice(matchIndex, matchIndex + query.length), match: true })
    cursor = matchIndex + query.length
    matchIndex = lowerName.indexOf(lowerQuery, cursor)
  }
  if (cursor < name.length) parts.push({ text: name.slice(cursor), match: false })
  return parts
}
</script>

<style lang="less" scoped>
.file-search-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 18vh 16px 24px;
  background: color-mix(in srgb, var(--gray-0) 72%, transparent);
  backdrop-filter: blur(2px);
}

.file-search-modal {
  width: min(680px, calc(100vw - 32px));
  max-height: min(620px, 72vh);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  background: var(--gray-0);
  box-shadow:
    0 24px 60px var(--shadow-1),
    0 2px 12px var(--shadow-0);
}

.file-search-input-row {
  display: flex;
  align-items: center;
  min-height: 62px;
  border-bottom: 1px solid var(--gray-100);
}

.file-search-input {
  flex: 1 1 auto;
  min-width: 0;
  height: 62px;
  padding: 0 18px;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--gray-1000);
  font-size: 18px;
  line-height: 24px;

  &::placeholder {
    color: var(--gray-400);
  }
}

.file-search-close {
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  margin-right: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;

  &:hover,
  &:focus-visible {
    background: var(--gray-50);
    color: var(--gray-900);
    outline: none;
  }
}

.file-search-body {
  min-height: 280px;
  max-height: calc(72vh - 63px);
  overflow-y: auto;
  padding: 8px;
  scrollbar-width: thin;
}

.file-search-result {
  width: 100%;
  min-height: 60px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--gray-900);
  cursor: pointer;
  text-align: left;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease;

  &:hover,
  &.selected,
  &:focus-visible {
    background: var(--gray-50);
    outline: none;
  }
}

.result-icon {
  flex: 0 0 18px;
  color: var(--gray-700);
}

.result-main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-title {
  overflow: hidden;
  color: var(--gray-1000);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;

  mark {
    padding: 0;
    background: color-mix(in srgb, var(--main-color) 14%, transparent);
    color: var(--main-700);
  }
}

.result-path {
  overflow: hidden;
  color: var(--gray-600);
  font-size: 13px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-date {
  flex: 0 0 auto;
  align-self: center;
  color: var(--gray-500);
  font-size: 13px;
  line-height: 18px;
}

.file-search-skeleton {
  padding: 8px 14px;
}

.skeleton-row {
  height: 58px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.skeleton-dot {
  flex: 0 0 16px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--gray-100);
}

.skeleton-lines {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;

  i {
    height: 8px;
    border-radius: 999px;
    background: var(--gray-100);

    &:first-child {
      width: 190px;
    }

    &:last-child {
      width: min(390px, 72%);
    }
  }
}

.file-search-empty {
  padding: 48px 16px;
  color: var(--gray-500);
  font-size: 14px;
  text-align: center;
}

.file-search-error {
  padding: 48px 16px;
  color: var(--color-error-500, #ff4d4f);
  font-size: 14px;
  text-align: center;
}

@media (max-width: 640px) {
  .file-search-overlay {
    padding-top: 12vh;
  }

  .file-search-input {
    font-size: 16px;
  }
}
</style>
