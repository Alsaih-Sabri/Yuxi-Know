<template>
  <div class="mcp-servers">
    <!-- 头部区域 -->
    <div class="header-section">
      <div class="header-content">
        <h3 class="title">{{ $t('mcpServers.title') }}</h3>
        <p class="description">
          {{ $t('mcpServers.description') }}
        </p>
      </div>
      <a-button type="primary" @click="showAddModal" class="add-btn">
        <template #icon><PlusOutlined /></template>
        {{ $t('mcpServers.buttons.addServer') }}
      </a-button>
    </div>

    <!-- 统计信息 -->
    <div class="stats-section" v-if="servers.length > 0">
      <span class="stats-text">
        {{ $t('mcpServers.stats.configured', { count: servers.length, http: httpCount, sse: sseCount, stdio: stdioCount }) }}
      </span>
    </div>

    <!-- 主内容区域 -->
    <div class="content-section">
      <a-spin :spinning="loading">
        <div v-if="error" class="error-message">
          <a-alert type="error" :message="error" show-icon />
        </div>

        <div class="cards-container">
          <div v-if="servers.length === 0" class="empty-state">
            <a-empty :description="$t('mcpServers.empty.noServers')">
              <a-button type="primary" @click="showAddModal">{{ $t('mcpServers.buttons.addServer') }}</a-button>
            </a-empty>
          </div>
          <div v-else class="server-cards-grid">
            <div
              v-for="server in servers"
              :key="server.name"
              class="server-card"
              :class="{ disabled: !server.enabled }"
            >
              <div class="card-header">
                <div class="server-info">
                  <span class="server-icon">{{ server.icon || '🔌' }}</span>
                  <div class="server-basic-info">
                    <h4 class="server-name" @click="showDetailModal(server)">{{ server.name }}</h4>
                    <div class="server-transport">
                      <a-tag size="small" class="transport-tag">
                        {{ server.transport }}
                      </a-tag>
                    </div>
                  </div>
                </div>
                <a-switch
                  :checked="server.enabled"
                  @change="handleToggleServer(server)"
                  :loading="toggleLoading === server.name"
                />
              </div>

              <div class="card-content">
                <div class="server-description">
                  {{ server.description || $t('mcpServers.empty.noDescription') }}
                </div>
              </div>

              <div class="card-actions">
                <a-tooltip :title="$t('mcpServers.buttons.viewDetails')">
                  <a-button
                    type="text"
                    size="small"
                    @click="showDetailModal(server)"
                    class="action-btn"
                  >
                    <EyeOutlined />
                    <span>{{ $t('mcpServers.buttons.details') }}</span>
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('mcpServers.buttons.testConnection')">
                  <a-button
                    type="text"
                    size="small"
                    @click="handleTestServer(server)"
                    class="action-btn"
                    :loading="testLoading === server.name"
                  >
                    <ApiOutlined v-if="testLoading !== server.name" />
                    <span>{{ $t('mcpServers.buttons.test') }}</span>
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('mcpServers.buttons.editConfig')">
                  <a-button
                    type="text"
                    size="small"
                    @click="showEditModal(server)"
                    class="action-btn"
                  >
                    <EditOutlined />
                    <span>{{ $t('mcpServers.buttons.edit') }}</span>
                  </a-button>
                </a-tooltip>
                <a-tooltip
                  :title="server.created_by === 'system' ? $t('mcpServers.buttons.cannotDeleteBuiltin') : $t('mcpServers.buttons.deleteServer')"
                >
                  <a-button
                    type="text"
                    size="small"
                    danger
                    :disabled="server.created_by === 'system'"
                    @click="confirmDeleteServer(server)"
                    class="action-btn"
                  >
                    <DeleteOutlined />
                    <span>{{ $t('mcpServers.buttons.delete') }}</span>
                  </a-button>
                </a-tooltip>
              </div>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <!-- 添加/编辑服务器模态框 -->
    <a-modal
      v-model:open="formModalVisible"
      :title="editMode ? $t('mcpServers.modal.editTitle') : $t('mcpServers.modal.addTitle')"
      @ok="handleFormSubmit"
      :confirmLoading="formLoading"
      @cancel="formModalVisible = false"
      :maskClosable="false"
      width="560px"
      class="server-modal"
    >
      <!-- 模式切换 -->
      <div class="mode-switch">
        <a-radio-group v-model:value="formMode" button-style="solid" size="small">
          <a-radio-button value="form">{{ $t('mcpServers.modal.formMode') }}</a-radio-button>
          <a-radio-button value="json">{{ $t('mcpServers.modal.jsonMode') }}</a-radio-button>
        </a-radio-group>
      </div>

      <!-- 表单模式 -->
      <a-form v-if="formMode === 'form'" layout="vertical" class="server-form">
        <a-form-item :label="$t('mcpServers.form.serverName')" required class="form-item">
          <a-input
            v-model:value="form.name"
            placeholder="请输入服务器名称（唯一标识）"
            :disabled="editMode"
          />
        </a-form-item>

        <a-form-item label="描述" class="form-item">
          <a-input v-model:value="form.description" placeholder="请输入服务器描述" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="传输类型" required class="form-item">
              <a-select v-model:value="form.transport">
                <a-select-option value="streamable_http">streamable_http</a-select-option>
                <a-select-option value="sse">sse</a-select-option>
                <a-select-option value="stdio">stdio</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="图标" class="form-item">
              <a-input v-model:value="form.icon" placeholder="输入 emoji，如 🧠" :maxlength="2" />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- HTTP 类型 -->
        <template v-if="form.transport === 'streamable_http' || form.transport === 'sse'">
          <a-form-item label="服务器 URL" required class="form-item">
            <a-input v-model:value="form.url" placeholder="https://example.com/mcp" />
          </a-form-item>

          <a-form-item label="HTTP 请求头" class="form-item">
            <a-textarea
              v-model:value="form.headersText"
              placeholder='JSON 格式，如：{"Authorization": "Bearer xxx"}'
              :rows="3"
            />
          </a-form-item>

          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="HTTP 超时（秒）" class="form-item">
                <a-input-number
                  v-model:value="form.timeout"
                  :min="1"
                  :max="300"
                  style="width: 100%"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="SSE 读取超时（秒）" class="form-item">
                <a-input-number
                  v-model:value="form.sse_read_timeout"
                  :min="1"
                  :max="300"
                  style="width: 100%"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <!-- StdIO 类型 -->
        <template v-if="form.transport === 'stdio'">
          <a-form-item label="命令" required class="form-item">
            <a-input v-model:value="form.command" placeholder="例如：npx 或 /path/to/server" />
          </a-form-item>

          <a-form-item label="参数" class="form-item">
            <a-select
              v-model:value="form.args"
              mode="tags"
              placeholder="输入参数后回车添加，如：-m"
              style="width: 100%"
            />
          </a-form-item>
        </template>

        <a-form-item label="标签" class="form-item">
          <a-select
            v-model:value="form.tags"
            mode="tags"
            placeholder="输入标签后回车添加"
            style="width: 100%"
          />
        </a-form-item>
      </a-form>

      <!-- JSON 模式 -->
      <div v-else class="json-mode">
        <a-textarea
          v-model:value="jsonContent"
          :rows="15"
          placeholder='请输入 JSON 配置，格式如：
{
  "name": "my-server",
  "transport": "streamable_http",
  "url": "https://example.com/mcp",
  "description": "服务器描述",
  "headers": {"Authorization": "Bearer xxx"},
  "tags": ["工具", "AI"]
}'
          class="json-textarea"
        />
        <div class="json-actions">
          <a-button size="small" @click="formatJson">格式化</a-button>
          <a-button size="small" @click="parseJsonToForm">解析到表单</a-button>
        </div>
      </div>
    </a-modal>

    <!-- 服务器详情模态框 -->
    <McpServerDetailModal
      v-model:visible="detailModalVisible"
      :server="selectedServer"
      @update="handleServerUpdate"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { notification, Modal } from 'ant-design-vue'

const { t } = useI18n()
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ApiOutlined
} from '@ant-design/icons-vue'
import { mcpApi } from '@/apis/mcp_api'
import McpServerDetailModal from './McpServerDetailModal.vue'

// 状态
const loading = ref(false)
const error = ref(null)
const servers = ref([])
const toggleLoading = ref(null)
const testLoading = ref(null)

// 表单相关
const formModalVisible = ref(false)
const formLoading = ref(false)
const formMode = ref('form')
const editMode = ref(false)
const jsonContent = ref('')
const form = reactive({
  name: '',
  description: '',
  transport: 'streamable_http',
  url: '',
  command: '',
  args: [],
  headersText: '',
  timeout: null,
  sse_read_timeout: null,
  tags: [],
  icon: ''
})

// 详情模态框
const detailModalVisible = ref(false)
const selectedServer = ref(null)

// 计算属性
const httpCount = computed(
  () => servers.value.filter((s) => s.transport === 'streamable_http').length
)
const sseCount = computed(() => servers.value.filter((s) => s.transport === 'sse').length)
const stdioCount = computed(() => servers.value.filter((s) => s.transport === 'stdio').length)

// 获取服务器列表
const fetchServers = async () => {
  try {
    loading.value = true
    error.value = null
    const result = await mcpApi.getMcpServers()
    if (result.success) {
      servers.value = result.data || []
    } else {
      error.value = result.message || '获取服务器列表失败'
    }
  } catch (err) {
    console.error('获取服务器列表失败:', err)
    error.value = err.message || '获取服务器列表失败'
  } finally {
    loading.value = false
  }
}

// 显示添加模态框
const showAddModal = () => {
  editMode.value = false
  formMode.value = 'form'
  Object.assign(form, {
    name: '',
    description: '',
    transport: 'streamable_http',
    url: '',
    command: '',
    args: [],
    headersText: '',
    timeout: null,
    sse_read_timeout: null,
    tags: [],
    icon: ''
  })
  jsonContent.value = ''
  formModalVisible.value = true
}

// 显示编辑模态框
const showEditModal = (server) => {
  editMode.value = true
  formMode.value = 'form'
  Object.assign(form, {
    name: server.name,
    description: server.description || '',
    transport: server.transport,
    url: server.url || '',
    command: server.command || '',
    args: server.args || [],
    headersText: server.headers ? JSON.stringify(server.headers, null, 2) : '',
    timeout: server.timeout,
    sse_read_timeout: server.sse_read_timeout,
    tags: server.tags || [],
    icon: server.icon || ''
  })
  formModalVisible.value = true
}

// 显示详情模态框
const showDetailModal = (server) => {
  selectedServer.value = server
  detailModalVisible.value = true
}

// 处理表单提交
const handleFormSubmit = async () => {
  try {
    formLoading.value = true

    let data
    if (formMode.value === 'json') {
      try {
        data = JSON.parse(jsonContent.value)
      } catch {
        notification.error({ message: 'JSON 格式错误' })
        return
      }
    } else {
      // 解析 headers
      let headers = null
      if (form.headersText.trim()) {
        try {
          headers = JSON.parse(form.headersText)
        } catch {
          notification.error({ message: '请求头 JSON 格式错误' })
          return
        }
      }

      data = {
        name: form.name,
        description: form.description || null,
        transport: form.transport,
        url: form.url || null,
        command: form.command || null,
        args: form.args.length > 0 ? form.args : null,
        headers,
        timeout: form.timeout || null,
        sse_read_timeout: form.sse_read_timeout || null,
        tags: form.tags.length > 0 ? form.tags : null,
        icon: form.icon || null
      }
    }

    // 校验必填字段
    if (!data.name?.trim()) {
      notification.error({ message: '服务器名称不能为空' })
      return
    }
    if (!data.transport) {
      notification.error({ message: '请选择传输类型' })
      return
    }
    // HTTP 类型校验 URL
    if (['sse', 'streamable_http'].includes(data.transport)) {
      if (!data.url?.trim()) {
        notification.error({ message: 'HTTP 类型必须填写服务器 URL' })
        return
      }
    }
    // StdIO 类型校验 command
    if (data.transport === 'stdio') {
      if (!data.command?.trim()) {
        notification.error({ message: 'StdIO 类型必须填写命令' })
        return
      }
    }

    if (editMode.value) {
      const result = await mcpApi.updateMcpServer(data.name, data)
      if (result.success) {
        notification.success({ message: '服务器更新成功' })
      } else {
        notification.error({ message: result.message || '更新失败' })
        return
      }
    } else {
      const result = await mcpApi.createMcpServer(data)
      if (result.success) {
        notification.success({ message: '服务器创建成功' })
      } else {
        notification.error({ message: result.message || '创建失败' })
        return
      }
    }

    formModalVisible.value = false
    await fetchServers()
  } catch (err) {
    console.error('操作失败:', err)
    notification.error({ message: err.message || '操作失败' })
  } finally {
    formLoading.value = false
  }
}

// 切换服务器启用状态
const handleToggleServer = async (server) => {
  try {
    toggleLoading.value = server.name
    const result = await mcpApi.toggleMcpServer(server.name)
    if (result.success) {
      notification.success({ message: result.message })
      await fetchServers()
    } else {
      notification.error({ message: result.message || '操作失败' })
    }
  } catch (err) {
    console.error('切换状态失败:', err)
    notification.error({ message: err.message || '操作失败' })
  } finally {
    toggleLoading.value = null
  }
}

// 测试服务器连接
const handleTestServer = async (server) => {
  try {
    testLoading.value = server.name
    const result = await mcpApi.testMcpServer(server.name)
    if (result.success) {
      notification.success({ message: result.message })
    } else {
      notification.warning({ message: result.message || '连接失败' })
    }
  } catch (err) {
    console.error('测试连接失败:', err)
    notification.error({ message: err.message || '测试失败' })
  } finally {
    testLoading.value = null
  }
}

// 确认删除服务器
const confirmDeleteServer = (server) => {
  // system 创建的服务器不允许删除
  if (server.created_by === 'system') {
    notification.warning({
      message: '无法删除系统服务器',
      description: '系统内置的 MCP 服务器无法删除，如需停用可切换禁用开关。'
    })
    return
  }

  Modal.confirm({
    title: '确认删除服务器',
    content: `确定要删除服务器 "${server.name}" 吗？此操作不可撤销。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        const result = await mcpApi.deleteMcpServer(server.name)
        if (result.success) {
          notification.success({ message: '服务器删除成功' })
          await fetchServers()
        } else {
          notification.error({ message: result.message || '删除失败' })
        }
      } catch (err) {
        console.error('删除失败:', err)
        notification.error({ message: err.message || '删除失败' })
      }
    }
  })
}

// 处理服务器更新（来自详情模态框）
const handleServerUpdate = () => {
  fetchServers()
}

// 格式化 JSON
const formatJson = () => {
  try {
    const obj = JSON.parse(jsonContent.value)
    jsonContent.value = JSON.stringify(obj, null, 2)
  } catch {
    notification.error({ message: 'JSON 格式错误，无法格式化' })
  }
}

// 解析 JSON 到表单
const parseJsonToForm = () => {
  try {
    const obj = JSON.parse(jsonContent.value)
    Object.assign(form, {
      name: obj.name || '',
      description: obj.description || '',
      transport: obj.transport || 'streamable_http',
      url: obj.url || '',
      command: obj.command || '',
      args: obj.args || [],
      headersText: obj.headers ? JSON.stringify(obj.headers, null, 2) : '',
      timeout: obj.timeout || null,
      sse_read_timeout: obj.sse_read_timeout || null,
      tags: obj.tags || [],
      icon: obj.icon || ''
    })
    formMode.value = 'form'
    notification.success({ message: '已解析到表单' })
  } catch {
    notification.error({ message: 'JSON 格式错误' })
  }
}

// 初始化
onMounted(() => {
  fetchServers()
})
</script>

<style lang="less" scoped>
.mcp-servers {
  margin-top: 12px;
  min-height: 50vh;

  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    .header-content {
      flex: 1;

      .description {
        font-size: 14px;
        color: var(--gray-600);
        margin: 0;
        line-height: 1.4;
        margin-bottom: 16px;
      }
    }
  }

  .stats-section {
    margin-bottom: 16px;

    .stats-text {
      font-size: 13px;
      color: var(--gray-600);
    }
  }

  .content-section {
    overflow: hidden;

    .error-message {
      padding: 16px 0;
    }

    .cards-container {
      .empty-state {
        padding: 60px 20px;
        text-align: center;
      }

      .server-cards-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;

        .server-card {
          background: var(--gray-0);
          border: 1px solid var(--gray-150);
          border-radius: 8px;
          padding: 10px 16px;
          padding-bottom: 8px;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

          &:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            border-color: var(--gray-200);
          }

          &.disabled {
            opacity: 0.6;
          }

          .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;

            .server-info {
              display: flex;
              align-items: center;
              gap: 12px;

              .server-icon {
                font-size: 24px;
              }

              .server-basic-info {
                .server-name {
                  margin: 0 0 4px 0;
                  font-size: 15px;
                  font-weight: 600;
                  color: var(--gray-900);
                  cursor: pointer;
                  transition: color 0.2s ease;

                  &:hover {
                    color: var(--color-primary);
                  }
                }

                .server-transport {
                  .transport-tag {
                    background: var(--gray-100);
                    border: none;
                    color: var(--gray-600);
                    border-radius: 4px;
                  }
                }
              }
            }
          }

          .card-content {
            min-height: 44px;

            .server-description {
              font-size: 13px;
              color: var(--gray-600);
              line-height: 1.4;
              display: -webkit-box;
              -webkit-line-clamp: 2;
              line-clamp: 2;
              -webkit-box-orient: vertical;
              overflow: hidden;
              text-overflow: ellipsis;
            }
          }

          .card-actions {
            display: flex;
            justify-content: flex-end;
            gap: 6px;
            padding-top: 8px;
            border-top: 1px solid var(--gray-25);

            .action-btn {
              display: flex;
              align-items: center;
              gap: 4px;
              padding: 4px 8px;
              border-radius: 6px;
              transition: all 0.2s ease;
              font-size: 12px;

              span {
                font-size: 12px;
              }

              &:hover {
                background: var(--gray-25);
              }

              &.ant-btn-dangerous:hover {
                background: var(--gray-25);
                border-color: var(--color-error-500);
                color: var(--color-error-500);
              }
            }
          }
        }
      }
    }
  }
}

.server-modal {
  .mode-switch {
    margin-bottom: 16px;
    text-align: right;
  }

  .server-form {
    .form-item {
      margin-bottom: 16px;
    }
  }

  .json-mode {
    .json-textarea {
      font-family: 'Monaco', 'Consolas', monospace;
      font-size: 13px;
    }

    .json-actions {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }
  }
}
</style>
