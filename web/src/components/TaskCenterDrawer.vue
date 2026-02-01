<template>
  <a-drawer :open="isOpen" :width="620" :title="$t('taskCenter.title')" placement="right" @close="handleClose">
    <div class="task-center">
      <div class="task-toolbar">
        <div class="task-filter-group">
          <a-segmented v-model:value="statusFilter" :options="taskFilterOptions" />
        </div>
        <div class="task-toolbar-actions">
          <a-button type="text" @click="handleRefresh" :loading="loadingState"> {{ $t('taskCenter.refresh') }} </a-button>
        </div>
      </div>

      <a-alert
        v-if="lastErrorState"
        type="error"
        show-icon
        class="task-alert"
        :message="lastErrorState.message || $t('taskCenter.loadFailed')"
      />

      <div v-if="hasTasks" class="task-list">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-card"
          :class="taskCardClasses(task)"
          @click="handleTaskCardClick(task)"
        >
          <!-- 状态指示器 -->
          <div class="task-card-status-indicator" :class="`status-${task.status}`">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusLabel(task.status) }}</span>
          </div>

          <div class="task-card-header">
            <div class="task-card-info">
              <div class="task-card-title">{{ task.name }}</div>
              <div class="task-card-meta">
                <span class="task-card-id">#{{ formatTaskId(task.id) }}</span>
                <span class="task-card-type">{{ taskTypeLabel(task.type) }}</span>
                <span v-if="getTaskDuration(task)" class="task-card-duration">{{
                  getTaskDuration(task)
                }}</span>
              </div>
            </div>
          </div>

          <!-- 进度信息 -->
          <div v-if="!isTaskCompleted(task)" class="task-card-progress">
            <a-progress
              :percent="Math.round(task.progress || 0)"
              :status="progressStatus(task.status)"
              :stroke-width="4"
              :show-info="false"
            />
            <span class="progress-text">{{ Math.round(task.progress || 0) }}%</span>
          </div>
          <div v-if="task.message && !isTaskCompleted(task)" class="task-card-message">
            {{ task.message }}
          </div>
          <div v-if="task.error" class="task-card-error">
            {{ task.error }}
          </div>

          <!-- 底部信息 -->
          <div class="task-card-footer">
            <div class="task-card-times">
              <span v-if="task.started_at">{{ $t('taskCenter.started') }} {{ formatTime(task.started_at, 'short') }}</span>
              <span v-if="task.completed_at"
                >· {{ $t('taskCenter.finished') }} {{ formatTime(task.completed_at, 'short') }}</span
              >
              <span v-if="!task.started_at">{{ $t('taskCenter.created') }} {{ formatTime(task.created_at, 'short') }}</span>
            </div>
            <div class="task-card-actions">
              <a-button type="text" size="small" @click.stop="handleDetail(task.id)">
                {{ $t('taskCenter.details') }}
              </a-button>
              <a-button
                type="text"
                size="small"
                danger
                v-if="canCancel(task)"
                @click.stop="handleCancel(task.id)"
              >
                {{ $t('taskCenter.cancel') }}
              </a-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="task-empty">
        <div class="task-empty-icon">🗂️</div>
        <div class="task-empty-title">{{ $t('taskCenter.noTasks') }}</div>
        <div class="task-empty-subtitle">
          {{ $t('taskCenter.noTasksHint') }}
        </div>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { computed, h, onBeforeUnmount, watch, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Modal } from 'ant-design-vue'
import { useTaskerStore } from '@/stores/tasker'
import { storeToRefs } from 'pinia'
import { formatFullDateTime, formatRelative, parseToShanghai } from '@/utils/time'

const { t } = useI18n()

const taskerStore = useTaskerStore()
const {
  isDrawerOpen,
  sortedTasks,
  loading,
  lastError,
  activeCount,
  totalCount,
  successCount,
  failedCount
} = storeToRefs(taskerStore)
const isOpen = isDrawerOpen

const tasks = computed(() => sortedTasks.value)
const loadingState = computed(() => Boolean(loading.value))
const lastErrorState = computed(() => lastError.value)
const statusFilter = ref('all')
const inProgressCount = computed(() => activeCount.value || 0)
const completedCount = computed(() => successCount.value || 0)
const failedTaskCount = computed(() => failedCount.value || 0)
const totalTaskCount = computed(() => totalCount.value || 0)
const taskFilterOptions = computed(() => [
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        t('taskCenter.all'),
        h('span', { class: 'filter-count' }, totalTaskCount.value)
      ]),
    value: 'all'
  },
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        t('taskCenter.inProgress'),
        h('span', { class: 'filter-count' }, inProgressCount.value)
      ]),
    value: 'active'
  },
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        t('taskCenter.completed'),
        h('span', { class: 'filter-count' }, completedCount.value)
      ]),
    value: 'success'
  },
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        t('taskCenter.failed'),
        h('span', { class: 'filter-count' }, failedTaskCount.value)
      ]),
    value: 'failed'
  }
])

const filteredTasks = computed(() => {
  const list = tasks.value
  switch (statusFilter.value) {
    case 'active':
      return list.filter((task) => ACTIVE_CLASS_STATUSES.has(task.status))
    case 'success':
      return list.filter((task) => task.status === 'success')
    case 'failed':
      return list.filter((task) => FAILED_STATUSES.has(task.status))
    default:
      return list
  }
})

const hasTasks = computed(() => filteredTasks.value.length > 0)

const ACTIVE_CLASS_STATUSES = new Set(['pending', 'queued', 'running'])
const FAILED_STATUSES = new Set(['failed', 'cancelled'])
const TASK_TYPE_LABELS = computed(() => ({
  knowledge_ingest: t('taskCenter.knowledgeIngest'),
  knowledge_rechunks: t('taskCenter.knowledgeRechunks'),
  graph_task: t('taskCenter.graphTask'),
  agent_job: t('taskCenter.agentJob')
}))

function taskCardClasses(task) {
  return {
    'task-card--active': ACTIVE_CLASS_STATUSES.has(task.status),
    'task-card--success': task.status === 'success',
    'task-card--failed': task.status === 'failed'
  }
}

function taskTypeLabel(type) {
  if (!type) return t('taskCenter.backgroundTask')
  return TASK_TYPE_LABELS.value[type] || type
}

function formatTaskId(id) {
  if (!id) return '--'
  return id.slice(0, 8)
}

watch(
  isOpen,
  (open) => {
    if (open) {
      taskerStore.loadTasks()
      taskerStore.startPolling()
    } else {
      taskerStore.stopPolling()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  taskerStore.stopPolling()
})

function handleClose() {
  taskerStore.closeDrawer()
}

function handleRefresh() {
  taskerStore.loadTasks()
}

function handleTaskCardClick(task) {
  console.log('Task clicked:', task)
}

function handleDetail(taskId) {
  const task = tasks.value.find((item) => item.id === taskId)
  if (!task) {
    return
  }
  const detail = h('div', { class: 'task-detail' }, [
    h('p', [h('strong', `${t('taskCenter.status')}: `), statusLabel(task.status)]),
    h('p', [h('strong', `${t('taskCenter.progress')}: `), `${Math.round(task.progress || 0)}%`]),
    h('p', [h('strong', `${t('taskCenter.updatedAt')}: `), formatTime(task.updated_at)]),
    h('p', [h('strong', `${t('taskCenter.description')}: `), task.message || '-']),
    h('p', [h('strong', `${t('taskCenter.error')}: `), task.error || '-'])
  ])
  Modal.info({
    title: task.name,
    width: 520,
    content: detail
  })
}

function handleCancel(taskId) {
  taskerStore.cancelTask(taskId)
}

function formatTime(value, mode = 'full') {
  if (!value) return '-'
  if (mode === 'short') {
    return formatRelative(value)
  }
  return formatFullDateTime(value)
}

function getTaskDuration(task) {
  if (!task.started_at || !task.completed_at) return null
  try {
    const start = parseToShanghai(task.started_at)
    const end = parseToShanghai(task.completed_at)
    if (!start || !end) {
      return null
    }

    const diffSeconds = Math.max(0, Math.floor(end.diff(start, 'second')))
    const hours = Math.floor(diffSeconds / 3600)
    const minutes = Math.floor((diffSeconds % 3600) / 60)
    const seconds = diffSeconds % 60

    if (hours > 0) {
      return `${hours}${t('taskCenter.hours')}${minutes}${t('taskCenter.minutes')}`
    }
    if (minutes > 0) {
      return `${minutes}${t('taskCenter.minutes')}${seconds}${t('taskCenter.seconds')}`
    }
    if (seconds > 0) {
      return `${seconds}${t('taskCenter.seconds')}`
    }
    return t('taskCenter.lessThan1Second')
  } catch {
    return null
  }
}

function isTaskCompleted(task) {
  return ['success', 'failed', 'cancelled'].includes(task.status)
}

function statusLabel(status) {
  const map = {
    pending: t('taskCenter.pending'),
    queued: t('taskCenter.queued'),
    running: t('taskCenter.running'),
    success: t('taskCenter.success'),
    failed: t('taskCenter.failed'),
    cancelled: t('taskCenter.cancelled')
  }
  return map[status] || status
}

function statusColor(status) {
  const map = {
    pending: 'blue',
    queued: 'blue',
    running: 'processing',
    success: 'green',
    failed: 'red',
    cancelled: 'gray'
  }
  return map[status] || 'default'
}

function progressStatus(status) {
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'normal'
  return 'active'
}

function canCancel(task) {
  return ['pending', 'running', 'queued'].includes(task.status) && !task.cancel_requested
}
</script>
<style scoped lang="less">
.task-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.task-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
  flex-wrap: wrap;
}

.task-filter-group {
  flex-shrink: 0;
}

.task-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

:deep(.filter-count) {
  margin-left: 2px;
  font-size: 12px;
  color: var(--gray-400);
}

.task-toolbar-actions :deep(.ant-btn) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 10px;
}

.task-alert {
  margin-bottom: 4px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 10px;
  padding: 14px 16px;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
}

.task-card:hover {
  border-color: var(--gray-300);
  box-shadow: 0 2px 8px var(--shadow-1);
}

/* 状态指示器 */
.task-card-status-indicator {
  position: absolute;
  top: 14px;
  right: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-pending .status-dot {
  background: var(--color-info-500);
}
.status-pending .status-text {
  color: var(--color-info-500);
}

.status-queued .status-dot {
  background: var(--color-info-500);
}
.status-queued .status-text {
  color: var(--color-info-500);
}

.status-running .status-dot {
  background: var(--color-success-500);
  animation: pulse 1.5s ease-in-out infinite;
}
.status-running .status-text {
  color: var(--color-success-500);
}

.status-success .status-dot {
  background: var(--color-success-500);
}
.status-success .status-text {
  color: var(--color-success-500);
}

.status-failed .status-dot {
  background: var(--color-error-500);
}
.status-failed .status-text {
  color: var(--color-error-500);
}

.status-cancelled .status-dot {
  background: var(--gray-500);
}
.status-cancelled .status-text {
  color: var(--gray-600);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(0.9);
  }
}

.task-card-header {
  padding-right: 80px; /* 为状态指示器留出空间 */
}

.task-card-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.task-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-900);
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
}

.task-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gray-500);
}

.task-card-id {
  font-family: 'SF Mono', 'Monaco', monospace;
  letter-spacing: 0.03em;
}

.task-card-type {
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--gray-100);
  font-size: 11px;
}

.task-card-duration {
  color: var(--gray-400);
}

.task-card-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-card-progress :deep(.ant-progress) {
  flex: 1;
}

.progress-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-500);
  min-width: 36px;
  text-align: right;
}

.task-card-message,
.task-card-error {
  font-size: 13px;
  line-height: 1.45;
  border-radius: 6px;
  padding: 10px 12px;
}

.task-card-message {
  background: var(--gray-100);
  color: var(--gray-800);
}

.task-card-error {
  background: var(--color-error-50);
  color: var(--color-error-500);
}

.task-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 4px;
  border-top: 1px solid var(--gray-100);
}

.task-card-times {
  display: flex;
  gap: 6px;
  font-size: 12px;
  color: var(--gray-400);
}

.task-card-actions {
  display: flex;
  gap: 2px;
}

.task-card-actions :deep(.ant-btn) {
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  color: var(--gray-500);
}

.task-card-actions :deep(.ant-btn:hover) {
  color: var(--gray-700);
  background: var(--gray-50);
}

.task-empty {
  margin-top: 32px;
  padding: 40px 30px;
  border-radius: 16px;
  background: var(--gray-50);
  border: 1px dashed var(--gray-300);
  text-align: center;
  color: var(--gray-600);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.task-empty-icon {
  font-size: 28px;
}

.task-empty-title {
  font-size: 16px;
  font-weight: 600;
}

.task-empty-subtitle {
  font-size: 13px;
  max-width: 320px;
  line-height: 1.5;
  color: var(--gray-400);
}
</style>
