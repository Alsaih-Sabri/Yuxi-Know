<template>
  <div class="database-empty" v-if="!state.showPage">
    <a-empty>
      <template #description>
        <span> {{ $t('graph.enableHint') }} </span>
      </template>
    </a-empty>
  </div>
  <div class="graph-container layout-container" v-else>
    <HeaderComponent :title="$t('graph.title')">
      <template #actions>
        <div class="db-selector">
          <div class="status-wrapper">
            <div class="status-indicator" :class="graphStatusClass"></div>
            <span class="status-text">{{ graphStatusText }}</span>
          </div>
          <span class="label">{{ $t('graph.knowledgeBase') }}: </span>
          <a-select
            v-model:value="state.selectedDbId"
            style="width: 200px"
            :options="state.dbOptions"
            @change="handleDbChange"
            :loading="state.loadingDatabases"
            mode="combobox"
            :placeholder="$t('graph.selectOrInputKbId')"
          />
        </div>
        <!-- <a-button type="default" @click="openLink('http://localhost:7474/')" :icon="h(GlobalOutlined)">
          Neo4j 浏览器
        </a-button> -->
        <a-button v-if="isNeo4j" type="primary" @click="state.showModal = true"
          ><UploadOutlined /> {{ $t('graph.uploadFile') }}</a-button
        >
        <a-button v-else type="primary" @click="state.showUploadTipModal = true"
          ><UploadOutlined /> {{ $t('graph.uploadFile') }}</a-button
        >
        <a-button
          v-if="unindexedCount > 0"
          type="primary"
          @click="indexNodes"
          :loading="state.indexing"
        >
          <SyncOutlined v-if="!state.indexing" /> {{ $t('graph.indexNodes', { count: unindexedCount }) }}
        </a-button>
      </template>
    </HeaderComponent>

    <div class="container-outter">
      <GraphCanvas
        ref="graphRef"
        :graph-data="graph.graphData"
        :graph-info="formattedGraphInfo"
        :highlight-keywords="[state.searchInput]"
        @node-click="graph.handleNodeClick"
        @edge-click="graph.handleEdgeClick"
        @canvas-click="graph.handleCanvasClick"
      >
        <template #top>
          <div class="actions">
            <div class="actions-left">
              <a-input
                v-model:value="state.searchInput"
                :placeholder="$t('graph.searchPlaceholder')"
                style="width: 300px"
                @keydown.enter="onSearch"
                allow-clear
              >
                <template #suffix>
                  <component
                    :is="state.searchLoading ? LoadingOutlined : SearchOutlined"
                    @click="onSearch"
                  />
                </template>
              </a-input>
              <a-input
                v-model:value="sampleNodeCount"
                :placeholder="$t('graph.queryCount')"
                style="width: 100px"
                @keydown.enter="loadSampleNodes"
                :loading="graph.fetching"
              >
                <template #suffix>
                  <component
                    :is="graph.fetching ? LoadingOutlined : ReloadOutlined"
                    @click="loadSampleNodes"
                  />
                </template>
              </a-input>
            </div>
            <div class="actions-right">
              <a-button type="default" @click="exportGraphData" :icon="h(ExportOutlined)">
                {{ $t('graph.exportData') }}
              </a-button>
            </div>
          </div>
        </template>
        <template #content>
          <a-empty v-show="graph.graphData.nodes.length === 0" style="padding: 4rem 0" />
        </template>
      </GraphCanvas>
      <!-- 详情浮动卡片 -->
      <GraphDetailPanel
        :visible="graph.showDetailDrawer"
        :item="graph.selectedItem"
        :type="graph.selectedItemType"
        :nodes="graph.graphData.nodes"
        @close="graph.handleCanvasClick"
        style="width: 380px"
      />
    </div>

    <a-modal
      :open="state.showModal"
      :title="$t('graph.uploadFileTitle')"
      @ok="addDocumentByFile"
      @cancel="handleModalCancel"
      :ok-text="$t('graph.addToGraph')"
      :cancel-text="$t('graph.cancel')"
      :confirm-loading="state.processing"
      :ok-button-props="{ disabled: !hasValidFile }"
    >
      <div class="upload">
        <div class="note">
          <p>{{ $t('graph.uploadNote') }}</p>
        </div>
        <div class="upload-config">
          <div class="config-row">
            <label class="config-label">{{ $t('graph.embeddingModel') }}</label>
            <div class="config-field">
              <EmbeddingModelSelector
                v-model:value="state.embedModelName"
                :disabled="!embedModelConfigurable"
                :style="{ width: '100%' }"
              />
            </div>
          </div>
          <div v-if="!embedModelConfigurable" class="config-hint-row">
            {{ $t('graph.modelNotChangeable') }}
          </div>
          <div class="config-row">
            <label class="config-label">{{ $t('graph.batchSize') }}</label>
            <div class="config-field">
              <a-input-number
                v-model:value="state.batchSize"
                :min="1"
                :max="1000"
                style="width: 100%"
              />
            </div>
          </div>
          <div class="config-hint-row">{{ $t('graph.batchSizeHint') }}</div>
        </div>
        <a-upload-dragger
          class="upload-dragger"
          v-model:fileList="fileList"
          name="file"
          :fileList="fileList"
          :max-count="1"
          accept=".jsonl"
          action="/api/knowledge/files/upload?allow_jsonl=true"
          :headers="getAuthHeaders()"
          @change="handleFileUpload"
          @drop="handleDrop"
        >
          <p class="ant-upload-text">{{ $t('graph.dragOrClickUpload') }}</p>
          <p class="ant-upload-hint">{{ $t('graph.jsonlOnly') }}</p>
        </a-upload-dragger>
      </div>
    </a-modal>

    <!-- 上传提示弹窗 -->
    <a-modal
      :open="state.showUploadTipModal"
      :title="$t('graph.uploadTipTitle')"
      @cancel="() => (state.showUploadTipModal = false)"
      :footer="null"
      width="500px"
    >
      <div class="upload-tip-content">
        <a-alert
          :message="getUploadTipMessage()"
          type="info"
          show-icon
          style="margin-bottom: 16px"
        />
        <div v-if="!isNeo4j" class="upload-tip-actions">
          <p>{{ $t('graph.uploadTipNonNeo4j') }}</p>
          <div class="action-buttons">
            <a-button type="primary" @click="goToDatabasePage">
              <DatabaseOutlined /> {{ $t('graph.goToDatabase') }}
            </a-button>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, h } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { useConfigStore } from '@/stores/config'
import {
  UploadOutlined,
  SyncOutlined,
  GlobalOutlined,
  InfoCircleOutlined,
  SearchOutlined,
  ReloadOutlined,
  LoadingOutlined,
  HighlightOutlined,
  DatabaseOutlined,
  ExportOutlined
} from '@ant-design/icons-vue'
import HeaderComponent from '@/components/HeaderComponent.vue'
import { neo4jApi, unifiedApi } from '@/apis/graph_api'
import { useUserStore } from '@/stores/user'
import GraphCanvas from '@/components/GraphCanvas.vue'
import GraphDetailPanel from '@/components/GraphDetailPanel.vue'
import EmbeddingModelSelector from '@/components/EmbeddingModelSelector.vue'
import { useGraph } from '@/composables/useGraph'

const { t } = useI18n()
const configStore = useConfigStore()
const cur_embed_model = computed(() => configStore.config?.embed_model)
const modelMatched = computed(
  () =>
    !graphInfo?.value?.embed_model_name ||
    graphInfo.value.embed_model_name === cur_embed_model.value
)

const router = useRouter()
const graphRef = ref(null)
const graphInfo = ref(null)
const fileList = ref([])
const sampleNodeCount = ref(100)

const graph = reactive(useGraph(graphRef))

const state = reactive({
  loadingGraphInfo: false,
  loadingDatabases: false,
  searchInput: '',
  searchLoading: false,
  showModal: false,
  showInfoModal: false,
  showUploadTipModal: false,
  processing: false,
  indexing: false,
  showPage: true,
  selectedDbId: 'neo4j',
  dbOptions: [],
  lightragStats: null,
  embedModelName: '',
  batchSize: 40
})

const isNeo4j = computed(() => {
  return state.selectedDbId === 'neo4j'
})

const embedModelConfigurable = computed(() => {
  return graphInfo.value?.embed_model_configurable ?? true
})

// 检查是否有有效的已上传文件
const hasValidFile = computed(() => {
  return fileList.value.some((file) => file.status === 'done' && file.response?.file_path)
})

// 计算未索引节点数量
const unindexedCount = computed(() => {
  return graphInfo.value?.unindexed_node_count || 0
})

const formattedGraphInfo = computed(() => {
  if (isNeo4j.value) {
    return {
      node_count: graphInfo.value?.entity_count || 0,
      edge_count: graphInfo.value?.relationship_count || 0
    }
  } else {
    return {
      node_count: state.lightragStats?.total_nodes || 0,
      edge_count: state.lightragStats?.total_edges || 0
    }
  }
})

const loadDatabases = async () => {
  state.loadingDatabases = true
  try {
    const res = await unifiedApi.getGraphs()
    if (res.success && res.data) {
      state.dbOptions = res.data.map((db) => ({
        label: `${db.name} (${db.type})`,
        value: db.id,
        type: db.type
      }))

      // If no selection or invalid selection, select first
      if (!state.selectedDbId || !state.dbOptions.find((o) => o.value === state.selectedDbId)) {
        if (state.dbOptions.length > 0) {
          state.selectedDbId = state.dbOptions[0].value
        }
      }
    }
  } catch (error) {
    console.error('Failed to load databases:', error)
  } finally {
    state.loadingDatabases = false
  }
}

const handleDbChange = () => {
  // Clear current data
  graph.clearGraph()
  state.searchInput = ''
  state.lightragStats = null

  if (isNeo4j.value) {
    loadGraphInfo()
  } else {
    // Also load stats for LightRAG or KB
    loadLightRAGStats()
  }
  loadSampleNodes()
}

const loadLightRAGStats = () => {
  unifiedApi
    .getStats(state.selectedDbId)
    .then((res) => {
      if (res.success) {
        state.lightragStats = res.data
      }
    })
    .catch((e) => console.error(e))
}

const loadGraphInfo = () => {
  state.loadingGraphInfo = true
  neo4jApi
    .getInfo()
    .then((data) => {
      console.log(data)
      graphInfo.value = data.data
      if (graphInfo.value?.embed_model_name) {
        state.embedModelName = graphInfo.value.embed_model_name
      } else {
        // Default if not set (though backend usually sends default)
        state.embedModelName = cur_embed_model.value
      }
      state.loadingGraphInfo = false
    })
    .catch((error) => {
      console.error(error)
      message.error(error.message || t('graph.loadGraphFailed'))
      state.loadingGraphInfo = false
    })
}

const addDocumentByFile = () => {
  // 使用计算属性验证文件
  if (!hasValidFile.value) {
    message.error(t('graph.waitUpload'))
    return
  }

  if (!state.embedModelName) {
    message.error(t('graph.selectEmbedModel'))
    return
  }

  state.processing = true

  // 获取已上传的文件路径
  const uploadedFile = fileList.value.find(
    (file) => file.status === 'done' && file.response?.file_path
  )
  const filePath = uploadedFile?.response?.file_path

  // 再次验证文件路径
  if (!filePath) {
    message.error(t('graph.filePathFailed'))
    state.processing = false
    return
  }

  neo4jApi
    .addEntities(filePath, 'neo4j', state.embedModelName, state.batchSize)
    .then((data) => {
      if (data.status === 'success') {
        message.success(data.message)
        state.showModal = false
        // 清空文件列表
        fileList.value = []
        // 刷新图谱数据
        setTimeout(() => {
          loadGraphInfo()
          loadSampleNodes()
        }, 500)
      } else {
        throw new Error(data.message)
      }
    })
    .catch((error) => {
      console.error(error)
      message.error(error.message || t('graph.addFileFailed'))
    })
    .finally(() => (state.processing = false))
}

const loadSampleNodes = () => {
  graph.fetching = true

  unifiedApi
    .getSubgraph({
      db_id: state.selectedDbId,
      node_label: '*',
      max_nodes: sampleNodeCount.value
    })
    .then((data) => {
      // Normalize data structure if needed
      const result = data.data
      graph.updateGraphData(result.nodes, result.edges)
      console.log(graph.graphData)
    })
    .catch((error) => {
      console.error(error)
      message.error(error.message || t('graph.loadNodesFailed'))
    })
    .finally(() => (graph.fetching = false))
}

const onSearch = () => {
  if (state.searchLoading) {
    message.error(t('graph.pleaseWait'))
    return
  }

  if (isNeo4j.value && graphInfo?.value?.embed_model_name !== cur_embed_model.value) {
    // 可选：提示模型不一致
  }

  state.searchLoading = true

  unifiedApi
    .getSubgraph({
      db_id: state.selectedDbId,
      node_label: state.searchInput || '*',
      max_nodes: sampleNodeCount.value
    })
    .then((data) => {
      const result = data.data
      if (!result || !result.nodes || !result.edges) {
        throw new Error('返回数据格式不正确')
      }
      graph.updateGraphData(result.nodes, result.edges)
      if (graph.graphData.nodes.length === 0) {
        message.info(t('graph.noEntitiesFound'))
      }
      console.log(data)
      console.log(graph.graphData)
    })
    .catch((error) => {
      console.error('查询错误:', error)
      message.error(t('graph.queryError') + (error.message || ''))
    })
    .finally(() => (state.searchLoading = false))
}

onMounted(async () => {
  await loadDatabases()
  loadGraphInfo() // Load default (Neo4j) info
  loadSampleNodes()
})

const handleFileUpload = ({ file, fileList: newFileList }) => {
  // 更新文件列表
  fileList.value = newFileList

  // 如果上传失败，显示错误信息
  if (file.status === 'error') {
    message.error(t('graph.uploadFailed') + file.name)
  }

  // 如果上传成功，显示成功信息
  if (file.status === 'done' && file.response?.file_path) {
    message.success(t('graph.uploadSuccess') + file.name)
  }

  console.log('File upload status:', file.status, file.name)
  console.log('File list:', fileList.value)
}

const handleDrop = (event) => {
  console.log(event)
  console.log(fileList.value)
}

const handleModalCancel = () => {
  state.showModal = false
  // 重置文件列表
  fileList.value = []
}

const graphStatusClass = computed(() => {
  if (state.loadingGraphInfo) return 'loading'
  return graphInfo.value?.status === 'open' ? 'open' : 'closed'
})

const graphStatusText = computed(() => {
  if (state.loadingGraphInfo) return t('graph.loading')
  return graphInfo.value?.status === 'open' ? t('graph.connected') : t('graph.closed')
})

// 为未索引节点添加索引
const indexNodes = () => {
  // 判断 embed_model_name 是否相同
  if (!modelMatched.value) {
    message.error(
      t('graph.modelMismatch', { current: cur_embed_model.value, graph: graphInfo.value?.embed_model_name })
    )
    return
  }

  if (state.processing) {
    message.error(t('graph.processingWait'))
    return
  }

  state.indexing = true
  neo4jApi
    .indexEntities('neo4j')
    .then((data) => {
      message.success(data.message || t('graph.indexSuccess'))
      // 刷新图谱信息
      loadGraphInfo()
    })
    .catch((error) => {
      console.error(error)
      message.error(error.message || t('graph.indexFailed'))
    })
    .finally(() => {
      state.indexing = false
    })
}

const exportGraphData = () => {
  const dataStr = JSON.stringify(
    {
      nodes: graph.graphData.nodes,
      edges: graph.graphData.edges,
      graphInfo: isNeo4j.value ? graphInfo.value : state.lightragStats,
      source: state.selectedDbId,
      exportTime: new Date().toISOString()
    },
    null,
    2
  )

  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `graph-data-${state.selectedDbId}-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  message.success(t('graph.dataExported'))
}

const getAuthHeaders = () => {
  const userStore = useUserStore()
  return userStore.getAuthHeaders()
}

const openLink = (url) => {
  window.open(url, '_blank')
}

const getDatabaseName = () => {
  const selectedDb = state.dbOptions.find((db) => db.value === state.selectedDbId)
  return selectedDb ? selectedDb.label : state.selectedDbId
}

const getUploadTipMessage = () => {
  if (isNeo4j.value) {
    return t('graph.neo4jUploadTip')
  } else {
    const selectedDb = state.dbOptions.find((db) => db.value === state.selectedDbId)
    const dbType = selectedDb?.type || 'unknown'
    const dbName = selectedDb?.label || getDatabaseName()
    return t('graph.kbUploadTip', { type: dbType.toUpperCase(), name: dbName })
  }
}

const goToDatabasePage = () => {
  state.showUploadTipModal = false

  // 如果不是 Neo4j，需要找到对应的知识库 ID 并跳转
  if (!isNeo4j.value) {
    const selectedDb = state.dbOptions.find((db) => db.value === state.selectedDbId)
    if (selectedDb && selectedDb.type !== 'neo4j') {
      // 跳转到对应的知识库详情页面
      router.push(`/database/${state.selectedDbId}`)
    } else {
      // 如果找不到对应的数据库，跳转到数据库列表页面
      router.push('/database')
    }
  }
}
</script>

<style lang="less" scoped>
@graph-header-height: 55px;

.graph-container {
  padding: 0;
  background-color: var(--gray-0);

  .header-container {
    height: @graph-header-height;
  }
}

.db-selector {
  display: flex;
  align-items: center;
  margin-right: 20px;

  .label {
    font-size: 14px;
    margin-right: 8px;
  }
}

.status-wrapper {
  display: flex;
  align-items: center;
  margin-right: 16px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.status-text {
  margin-left: 8px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;

  &.loading {
    background-color: var(--color-warning-500);
    animation: pulse 1.5s infinite ease-in-out;
  }

  &.open {
    background-color: var(--color-success-500);
  }

  &.closed {
    background-color: var(--color-error-500);
  }
}

@keyframes pulse {
  0% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
  100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
}

.upload {
  margin-bottom: 20px;

  .upload-dragger {
    margin: 0px;
  }

  .upload-config {
    margin: 24px 0;
    padding: 16px;
    background-color: var(--gray-0);
    border-radius: 4px;

    .config-row {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      &:last-of-type {
        margin-bottom: 0;
      }

      .config-label {
        width: 100px;
        flex-shrink: 0;
        font-size: 14px;
        color: var(--color-text);
        text-align: right;
        margin-right: 16px;
      }

      .config-field {
        flex: 1;
        min-width: 0;
      }
    }

    .config-hint-row {
      margin-bottom: 16px;
      padding-left: 116px;
      font-size: 12px;
      color: var(--color-text-secondary);
      line-height: 1.5;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.container-outter {
  width: 100%;
  height: calc(100vh - @graph-header-height);
  overflow: hidden;
  background: var(--gray-10);

  .actions {
    display: flex;
    justify-content: space-between;
    margin: 20px 0;
    padding: 0 24px;
    width: 100%;
  }

  .tags {
    display: flex;
    gap: 8px;
  }
}

.actions {
  top: 0;

  .actions-left,
  .actions-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  :deep(.ant-input) {
    padding: 2px 10px;
  }

  button {
    height: 37px;
    box-shadow: none;
  }
}

.upload-tip-content {
  .upload-tip-actions {
    p {
      margin-bottom: 16px;
      color: var(--color-text-secondary);
    }
  }

  .action-buttons {
    display: flex;
    justify-content: center;
    margin-top: 20px;
  }
}
</style>
