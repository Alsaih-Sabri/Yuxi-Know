<template>
  <div class="dashboard-container">
    <!-- Top Status Bar -->

    <!-- Modern Top Statistics Bar -->
    <div class="modern-stats-header">
      <StatusBar />
      <StatsOverviewComponent :basic-stats="basicStats" />
    </div>

    <!-- Main Content Area with Grid Layout -->
    <div class="dashboard-grid">
      <!-- Call Statistics Module - Occupies 2x1 grid -->
      <CallStatsComponent :loading="loading" ref="callStatsRef" />

      <!-- User Activity Analysis - Occupies 1x1 grid -->
      <div class="grid-item user-stats">
        <UserStatsComponent
          :user-stats="allStatsData?.users"
          :loading="loading"
          ref="userStatsRef"
        />
      </div>

      <!-- AI Agent Analysis - Occupies 1x1 grid -->
      <div class="grid-item agent-stats">
        <AgentStatsComponent
          :agent-stats="allStatsData?.agents"
          :loading="loading"
          ref="agentStatsRef"
        />
      </div>

      <!-- Tool Call Monitoring - Occupies 1x1 grid -->
      <div class="grid-item tool-stats">
        <ToolStatsComponent
          :tool-stats="allStatsData?.tools"
          :loading="loading"
          ref="toolStatsRef"
        />
      </div>

      <!-- Knowledge Base Usage - Occupies 1x1 grid -->
      <div class="grid-item knowledge-stats">
        <KnowledgeStatsComponent
          :knowledge-stats="allStatsData?.knowledge"
          :loading="loading"
          ref="knowledgeStatsRef"
        />
      </div>

      <!-- Conversation Records - Occupies 1x1 grid -->
      <div class="grid-item conversations">
        <a-card class="conversations-section" :title="$t('dashboard.conversationRecords')" :loading="loading">
          <template #extra>
            <a-space>
              <a-input
                v-model:value="filters.user_id"
                :placeholder="$t('dashboard.userId')"
                size="small"
                style="width: 120px"
                @change="handleFilterChange"
              />
              <a-select
                v-model:value="filters.status"
                :placeholder="$t('dashboard.status')"
                size="small"
                style="width: 100px"
                @change="handleFilterChange"
              >
                <a-select-option value="active">{{ $t('dashboard.active') }}</a-select-option>
                <a-select-option value="deleted">{{ $t('dashboard.deleted') }}</a-select-option>
                <a-select-option value="all">{{ $t('dashboard.all') }}</a-select-option>
              </a-select>
              <a-button size="small" @click="loadConversations" :loading="loading"> {{ $t('dashboard.refresh') }} </a-button>
              <a-button size="small" @click="feedbackModal.show()"> {{ $t('dashboard.feedbackDetails') }} </a-button>
            </a-space>
          </template>

          <a-table
            :columns="conversationColumns"
            :data-source="conversations"
            :loading="loading"
            :pagination="conversationPagination"
            @change="handleTableChange"
            row-key="thread_id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <a
                  @click="handleViewDetail(record)"
                  class="conversation-title"
                  :class="{ loading: loadingDetail }"
                  >{{ record.title || $t('dashboard.unnamedConversation') }}</a
                >
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'red'" size="small">
                  {{ record.status === 'active' ? $t('dashboard.active') : $t('dashboard.deleted') }}
                </a-tag>
              </template>
              <template v-if="column.key === 'updated_at'">
                <span class="time-text">{{ formatDate(record.updated_at) }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button
                  type="link"
                  size="small"
                  @click="handleViewDetail(record)"
                  :loading="loadingDetail"
                >
                  {{ $t('dashboard.details') }}
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </div>

    <!-- Feedback Modal -->
    <FeedbackModalComponent ref="feedbackModal" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { dashboardApi } from '@/apis/dashboard_api'
import dayjs, { parseToShanghai } from '@/utils/time'

// Import child components
import StatusBar from '@/components/StatusBar.vue'
import UserStatsComponent from '@/components/dashboard/UserStatsComponent.vue'
import ToolStatsComponent from '@/components/dashboard/ToolStatsComponent.vue'
import KnowledgeStatsComponent from '@/components/dashboard/KnowledgeStatsComponent.vue'
import AgentStatsComponent from '@/components/dashboard/AgentStatsComponent.vue'
import CallStatsComponent from '@/components/dashboard/CallStatsComponent.vue'
import StatsOverviewComponent from '@/components/dashboard/StatsOverviewComponent.vue'
import FeedbackModalComponent from '@/components/dashboard/FeedbackModalComponent.vue'

const { t } = useI18n()

// Component references
const feedbackModal = ref(null)

// Statistics data - Using new reactive structure
const basicStats = ref({})
const allStatsData = ref({
  users: null,
  tools: null,
  knowledge: null,
  agents: null
})

// Filters
const filters = reactive({
  user_id: '',
  agent_id: '',
  status: 'active'
})

// Conversation list
const conversations = ref([])
const loading = ref(false)
const loadingDetail = ref(false)

// Call statistics child component reference
const callStatsRef = ref(null)

// Pagination
const conversationPagination = reactive({
  current: 1,
  pageSize: 8,
  total: 0,
  showSizeChanger: false,
  showQuickJumper: false,
  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`
})

// Table column definitions
const conversationColumns = computed(() => [
  {
    title: t('dashboard.conversationTitle'),
    dataIndex: 'title',
    key: 'title',
    ellipsis: true
  },
  {
    title: t('dashboard.user'),
    dataIndex: 'user_id',
    key: 'user_id',
    width: '80px',
    ellipsis: true
  },
  {
    title: t('dashboard.messageCount'),
    dataIndex: 'message_count',
    key: 'message_count',
    width: '60px',
    align: 'center'
  },
  {
    title: t('dashboard.status'),
    dataIndex: 'status',
    key: 'status',
    width: '70px',
    align: 'center'
  },
  {
    title: t('dashboard.updatedAt'),
    dataIndex: 'updated_at',
    key: 'updated_at',
    width: '120px'
  },
  {
    title: t('dashboard.actions'),
    key: 'actions',
    width: '60px',
    align: 'center'
  }
])

// Child component references
const userStatsRef = ref(null)
const toolStatsRef = ref(null)
const knowledgeStatsRef = ref(null)
const agentStatsRef = ref(null)

// Load statistics data - Using parallel API calls
const loadAllStats = async () => {
  loading.value = true
  try {
    // Use parallel API calls to get all statistics data
    const response = await dashboardApi.getAllStats()

    // Update basic statistics data
    basicStats.value = response.basic

    // Update detailed statistics data
    allStatsData.value = {
      users: response.users,
      tools: response.tools,
      knowledge: response.knowledge,
      agents: response.agents
    }

    console.log('Dashboard data loaded:', response)
    message.success(t('dashboard.dataLoadSuccess'))
  } catch (error) {
    console.error('Failed to load statistics data:', error)
    message.error(t('dashboard.dataLoadFailed'))

    // If parallel request fails, try loading basic data separately
    try {
      const basicResponse = await dashboardApi.getStats()
      basicStats.value = basicResponse
      message.warning(t('dashboard.detailedDataFailed'))
    } catch (basicError) {
      console.error('Failed to load basic statistics data:', basicError)
      message.error(t('dashboard.dataLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}

// Keep original loadStats function for backward compatibility
const loadStats = loadAllStats

// Load conversation list
const loadConversations = async () => {
  try {
    const params = {
      user_id: filters.user_id || undefined,
      agent_id: filters.agent_id || undefined,
      status: filters.status,
      limit: conversationPagination.pageSize,
      offset: (conversationPagination.current - 1) * conversationPagination.pageSize
    }

    const response = await dashboardApi.getConversations(params)
    conversations.value = response
    // Note: Since backend doesn't return total count, temporarily set to current data length
    conversationPagination.total = response.length
  } catch (error) {
    console.error('Failed to load conversation list:', error)
    message.error(t('dashboard.conversationLoadFailed'))
  }
}

// Date formatting
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const parsed = parseToShanghai(dateString)
  if (!parsed) return '-'
  const now = dayjs().tz('Asia/Shanghai')
  const diffDays = now.startOf('day').diff(parsed.startOf('day'), 'day')

  if (diffDays === 0) {
    return parsed.format('HH:mm')
  }
  if (diffDays === 1) {
    return t('time.yesterday')
  }
  if (diffDays < 7) {
    return t('time.daysAgo', { n: diffDays })
  }
  return parsed.format('MM-DD')
}

// View conversation details
const handleViewDetail = async (record) => {
  try {
    loadingDetail.value = true
    const detail = await dashboardApi.getConversationDetail(record.thread_id)
    console.log(detail)
  } catch (error) {
    console.error('Failed to get conversation details:', error)
    message.error(t('dashboard.detailLoadFailed'))
  } finally {
    loadingDetail.value = false
  }
}

// Handle filter changes
const handleFilterChange = () => {
  conversationPagination.current = 1
  loadConversations()
}

// Handle table changes
const handleTableChange = (pag) => {
  conversationPagination.current = pag.current
  conversationPagination.pageSize = pag.pageSize
  loadConversations()
}

// Cleanup function - Clean up all child component chart instances
const cleanupCharts = () => {
  if (userStatsRef.value?.cleanup) userStatsRef.value.cleanup()
  if (toolStatsRef.value?.cleanup) userStatsRef.value.cleanup()
  if (knowledgeStatsRef.value?.cleanup) knowledgeStatsRef.value.cleanup()
  if (agentStatsRef.value?.cleanup) agentStatsRef.value.cleanup()
  if (callStatsRef.value?.cleanup) callStatsRef.value.cleanup()
}

// Initialize
onMounted(() => {
  loadAllStats()
  loadConversations()
})

// Clean up charts on component unmount
onUnmounted(() => {
  cleanupCharts()
})
</script>

<style scoped lang="less">
.dashboard-container {
  // padding: 0 24px 24px 24px;
  background-color: var(--gray-25);
  min-height: calc(100vh - 64px);
  overflow-x: hidden;
}

// Dashboard specific grid layout
.dashboard-grid {
  display: grid;
  padding: 16px;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
  margin-bottom: 24px;
  min-height: 600px;

  .grid-item {
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 300px;
    background-color: transparent;
    border: none;
    transition: all 0.2s ease;

    &:hover {
      .conversations-section,
      .call-stats-section {
        border-color: var(--gray-200);
        box-shadow: 0 1px 3px 0 var(--shadow-100);
      }
    }

    // Large page layout: First row 2x1 + 1x1, second row 3x1x1
    &.call-stats {
      grid-column: 1 / 3;
      grid-row: 1 / 2;
      min-height: 400px;
    }

    &.user-stats {
      grid-column: 3 / 4;
      grid-row: 1 / 2;
      min-height: 400px;
    }

    &.agent-stats {
      grid-column: 1 / 2;
      grid-row: 2 / 3;
      min-height: 350px;
    }

    &.tool-stats {
      grid-column: 2 / 3;
      grid-row: 2 / 3;
      min-height: 350px;
    }

    &.knowledge-stats {
      grid-column: 3 / 4;
      grid-row: 2 / 3;
      min-height: 350px;
    }

    &.conversations {
      grid-column: 1 / 4;
      grid-row: 3 / 4;
      min-height: 300px;
    }
  }
}

// Dashboard specific card styles
.conversations-section,
.call-stats-section {
  background-color: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  transition: all 0.2s ease;
  box-shadow: none;

  &:hover {
    background-color: var(--gray-25);
    border-color: var(--gray-200);
    box-shadow: 0 1px 3px 0 var(--shadow-100);
  }

  :deep(.ant-card-head) {
    border-bottom: 1px solid var(--gray-200);
    min-height: 56px;
    padding: 0 20px;
    background-color: var(--gray-0);

    .ant-card-head-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--gray-1000);
    }
  }

  :deep(.ant-card-body) {
    padding: 16px 20px;
    background-color: var(--gray-0);
  }

  :deep(.ant-card-extra) {
    .ant-space {
      gap: 8px;
    }
  }
}

// Dashboard specific placeholder styles
.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--gray-600);

  .placeholder-icon {
    width: 64px;
    height: 64px;
    background-color: var(--gray-100);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;

    .icon {
      width: 32px;
      height: 32px;
      color: var(--gray-500);
    }
  }

  .placeholder-text {
    font-size: 18px;
    font-weight: 600;
    color: var(--gray-800);
    margin-bottom: 8px;
  }

  .placeholder-subtitle {
    font-size: 14px;
    color: var(--gray-600);
  }
}

// Dashboard specific conversation record styles
.conversations-section {
  .conversation-title {
    color: var(--main-500);
    text-decoration: none;
    font-weight: 500;
    font-size: 13px;
    transition: color 0.2s ease;

    &:hover {
      color: var(--main-600);
      text-decoration: underline;
    }
  }

  .time-text {
    color: var(--gray-600);
    font-size: 12px;
  }
}

// Call statistics module styles
.call-stats-section {
  .call-stats-container {
    .call-summary {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;

      .summary-card {
        background: linear-gradient(135deg, var(--gray-50) 0%, var(--gray-100) 100%);
        border: 1px solid var(--gray-200);
        border-radius: 8px;
        padding: 12px;
        text-align: center;

        .summary-value {
          font-size: 16px;
          font-weight: 600;
          color: var(--gray-800);
          margin-bottom: 4px;
        }

        .summary-label {
          font-size: 11px;
          color: var(--gray-500);
          font-weight: 500;
        }
      }
    }

    .chart-container {
      .chart {
        width: 100%;
        height: 280px;
        border-radius: 8px;
        overflow: hidden;
      }
    }
  }

  :deep(.ant-card-extra) {
    .ant-space {
      gap: 8px;
    }
  }
}

// Dashboard specific responsive design
@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
    gap: 16px;

    .grid-item {
      // Small page layout: First row 2x1, second and third rows are 2x1x1 each
      &.call-stats {
        grid-column: 1 / 3;
        grid-row: 1 / 2;
        min-height: 350px;
      }

      &.user-stats {
        grid-column: 1 / 2;
        grid-row: 2 / 3;
        min-height: 300px;
      }

      &.agent-stats {
        grid-column: 2 / 3;
        grid-row: 2 / 3;
        min-height: 300px;
      }

      &.tool-stats {
        grid-column: 1 / 2;
        grid-row: 3 / 4;
        min-height: 300px;
      }

      &.knowledge-stats {
        grid-column: 2 / 3;
        grid-row: 3 / 4;
        min-height: 300px;
      }

      &.conversations {
        grid-column: 1 / 3;
        grid-row: 4 / 5;
        min-height: 300px;
      }
    }
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: 12px;

    .grid-item {
      &.call-stats,
      &.agent-stats,
      &.user-stats,
      &.tool-stats,
      &.knowledge-stats,
      &.conversations {
        grid-column: 1 / 2;
        grid-row: auto;
        min-height: 300px;
      }
    }
  }

  .call-stats-section {
    .call-stats-container {
      .call-summary {
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;

        .summary-card {
          padding: 12px;

          .summary-value {
            font-size: 18px;
          }

          .summary-label {
            font-size: 11px;
          }
        }
      }

      .chart-container {
        .chart {
          height: 200px;
        }
      }
    }
  }

  .placeholder-content {
    height: 150px;

    .placeholder-icon {
      width: 48px;
      height: 48px;
      margin-bottom: 12px;

      .icon {
        width: 24px;
        height: 24px;
      }
    }

    .placeholder-text {
      font-size: 16px;
    }

    .placeholder-subtitle {
      font-size: 12px;
    }
  }
}
</style>
