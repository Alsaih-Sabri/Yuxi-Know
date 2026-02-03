<template>
  <div class="department-management">
    <!-- 头部区域 -->
    <div class="header-section">
      <div class="header-content">
        <h3 class="title">{{ $t('departmentManagement.title') }}</h3>
        <p class="description">{{ $t('departmentManagement.description') }}</p>
      </div>
      <a-button type="primary" @click="showAddDepartmentModal" class="add-btn">
        <template #icon><PlusOutlined /></template>
        {{ $t('departmentManagement.addDepartment') }}
      </a-button>
    </div>

    <!-- 主内容区域 -->
    <div class="content-section">
      <a-spin :spinning="departmentManagement.loading">
        <div v-if="departmentManagement.error" class="error-message">
          <a-alert type="error" :message="departmentManagement.error" show-icon />
        </div>

        <template v-if="departmentManagement.departments.length > 0">
          <a-table
            :dataSource="departmentManagement.departments"
            :columns="columns"
            :rowKey="(record) => record.id"
            :pagination="false"
            class="department-table"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <div class="department-name">
                  <span class="name-text">{{ record.name }}</span>
                </div>
              </template>
              <template v-if="column.key === 'description'">
                <span class="description-text">{{ record.description || '-' }}</span>
              </template>
              <template v-if="column.key === 'userCount'">
                <span>{{ record.user_count ?? 0 }} {{ $t('departmentManagement.memberCount') }}</span>
              </template>
              <template v-if="column.key === 'action'">
                <a-space>
                  <a-tooltip :title="$t('departmentManagement.editDepartment')">
                    <a-button
                      type="text"
                      size="small"
                      @click="showEditDepartmentModal(record)"
                      class="action-btn"
                    >
                      <EditOutlined />
                    </a-button>
                  </a-tooltip>
                  <a-tooltip :title="$t('departmentManagement.deleteDepartment')">
                    <a-button
                      type="text"
                      size="small"
                      danger
                      @click="confirmDeleteDepartment(record)"
                      :disabled="record.user_count > 0"
                      class="action-btn"
                    >
                      <DeleteOutlined />
                    </a-button>
                  </a-tooltip>
                </a-space>
              </template>
            </template>
          </a-table>
        </template>

        <div v-else class="empty-state">
          <a-empty :description="$t('departmentManagement.noDepartments')" />
        </div>
      </a-spin>
    </div>

    <!-- 部门表单模态框 -->
    <a-modal
      v-model:open="departmentManagement.modalVisible"
      :title="departmentManagement.modalTitle"
      @ok="handleDepartmentFormSubmit"
      :confirmLoading="departmentManagement.loading"
      @cancel="departmentManagement.modalVisible = false"
      :maskClosable="false"
      width="520px"
      class="department-modal"
    >
      <a-form layout="vertical" class="department-form">
        <a-form-item :label="$t('departmentManagement.departmentName')" required class="form-item">
          <a-input
            v-model:value="departmentManagement.form.name"
            :placeholder="$t('departmentManagement.departmentNamePlaceholder')"
            size="large"
            :maxlength="50"
          />
        </a-form-item>

        <a-form-item :label="$t('departmentManagement.deptDescription')" class="form-item">
          <a-textarea
            v-model:value="departmentManagement.form.description"
            :placeholder="$t('departmentManagement.descriptionPlaceholder')"
            :rows="3"
            :maxlength="255"
            show-count
          />
        </a-form-item>

        <a-divider v-if="!departmentManagement.editMode" />

        <template v-if="!departmentManagement.editMode">
          <div class="admin-section-title">
            <TeamOutlined />
            <span>{{ t('departmentManagement.departmentAdmin') }}</span>
          </div>
          <p class="admin-section-hint">
            {{ t('departmentManagement.adminCreationHint') }}
          </p>

          <a-form-item :label="t('departmentManagement.adminUserId')" required class="form-item">
            <a-input
              v-model:value="departmentManagement.form.adminUserId"
              :placeholder="t('departmentManagement.adminUserIdPlaceholder')"
              size="large"
              :maxlength="20"
              @blur="checkAdminUserId"
            />
            <div v-if="departmentManagement.form.userIdError" class="error-text">
              {{ departmentManagement.form.userIdError }}
            </div>
            <div v-else class="help-text">{{ t('departmentManagement.userIdLoginHint') }}</div>
          </a-form-item>

          <a-form-item :label="t('departmentManagement.password')" required class="form-item">
            <a-input-password
              v-model:value="departmentManagement.form.adminPassword"
              :placeholder="t('departmentManagement.passwordPlaceholder')"
              size="large"
              :maxlength="50"
            />
          </a-form-item>

          <a-form-item :label="t('departmentManagement.confirmPassword')" required class="form-item">
            <a-input-password
              v-model:value="departmentManagement.form.adminConfirmPassword"
              :placeholder="t('departmentManagement.confirmPasswordPlaceholder')"
              size="large"
              :maxlength="50"
            />
          </a-form-item>

          <a-form-item :label="t('departmentManagement.phoneOptional')" class="form-item">
            <a-input
              v-model:value="departmentManagement.form.adminPhone"
              :placeholder="t('departmentManagement.phonePlaceholder')"
              size="large"
              :maxlength="11"
            />
            <div v-if="departmentManagement.form.phoneError" class="error-text">
              {{ departmentManagement.form.phoneError }}
            </div>
          </a-form-item>
        </template>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { notification, Modal } from 'ant-design-vue'
import { departmentApi, apiSuperAdminGet } from '@/apis'
import { DeleteOutlined, EditOutlined, PlusOutlined, TeamOutlined } from '@ant-design/icons-vue'

const { t } = useI18n()

// 表格列定义
const columns = [
  {
    title: t('departmentManagement.departmentName'),
    dataIndex: 'name',
    key: 'name',
    width: 200
  },
  {
    title: t('departmentManagement.deptDescription'),
    dataIndex: 'description',
    key: 'description',
    ellipsis: true
  },
  {
    title: t('departmentManagement.memberCount'),
    dataIndex: 'user_count',
    key: 'userCount',
    width: 100,
    align: 'center'
  },
  {
    title: t('common.actions'),
    key: 'action',
    width: 120,
    align: 'center'
  }
]

// 部门管理状态
const departmentManagement = reactive({
  loading: false,
  departments: [],
  error: null,
  modalVisible: false,
  modalTitle: t('departmentManagement.addDepartment'),
  editMode: false,
  editDepartmentId: null,
  form: {
    name: '',
    description: '',
    adminUserId: '',
    adminPassword: '',
    adminConfirmPassword: '',
    adminPhone: '',
    userIdError: '',
    phoneError: ''
  }
})

// 获取部门列表
const fetchDepartments = async () => {
  try {
    departmentManagement.loading = true
    departmentManagement.error = null
    const departments = await departmentApi.getDepartments()
    departmentManagement.departments = departments
  } catch (error) {
    console.error(t('departmentManagement.loadDepartmentsFailed'), error)
    departmentManagement.error = t('departmentManagement.loadDepartmentsFailed')
  } finally {
    departmentManagement.loading = false
  }
}

// 打开添加部门模态框
const showAddDepartmentModal = () => {
  departmentManagement.modalTitle = t('departmentManagement.addDepartment')
  departmentManagement.editMode = false
  departmentManagement.editDepartmentId = null
  departmentManagement.form = {
    name: '',
    description: '',
    adminUserId: '',
    adminPassword: '',
    adminConfirmPassword: '',
    adminPhone: '',
    userIdError: '',
    phoneError: ''
  }
  departmentManagement.modalVisible = true
}

// 打开编辑部门模态框
const showEditDepartmentModal = (department) => {
  departmentManagement.modalTitle = t('departmentManagement.editDepartment')
  departmentManagement.editMode = true
  departmentManagement.editDepartmentId = department.id
  departmentManagement.form = {
    name: department.name,
    description: department.description || '',
    adminUserId: '',
    adminPassword: '',
    adminConfirmPassword: '',
    adminPhone: '',
    userIdError: '',
    phoneError: ''
  }
  departmentManagement.modalVisible = true
}

// 验证手机号格式
const validatePhoneNumber = (phone) => {
  if (!phone) {
    return true // 手机号可选
  }
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(phone)
}

// 监听手机号输入变化
watch(
  () => departmentManagement.form.adminPhone,
  (newPhone) => {
    departmentManagement.form.phoneError = ''
    if (newPhone && !validatePhoneNumber(newPhone)) {
      departmentManagement.form.phoneError = t('userManagement.phoneFormat')
    }
  }
)

// 检查管理员用户ID是否可用
const checkAdminUserId = async () => {
  const userId = departmentManagement.form.adminUserId.trim()
  departmentManagement.form.userIdError = ''

  if (!userId) {
    return
  }

  // 验证格式
  if (!/^[a-zA-Z0-9_]+$/.test(userId)) {
    departmentManagement.form.userIdError = '用户ID只能包含字母、数字和下划线'
    return
  }

  if (userId.length < 3 || userId.length > 20) {
    departmentManagement.form.userIdError = '用户ID长度必须在3-20个字符之间'
    return
  }

  // 检查是否已存在
  try {
    const result = await apiSuperAdminGet(`/api/auth/check-user-id/${userId}`)
    if (!result.is_available) {
      departmentManagement.form.userIdError = '该用户ID已被使用'
    }
  } catch (error) {
    console.error('检查用户ID失败:', error)
  }
}

// 处理部门表单提交
const handleDepartmentFormSubmit = async () => {
  try {
    // 验证部门名称
    if (!departmentManagement.form.name.trim()) {
      notification.error({ message: t('departmentManagement.nameRequired') })
      return
    }

    if (departmentManagement.form.name.trim().length < 2) {
      notification.error({ message: t('departmentManagement.nameMinLength') })
      return
    }

    // 验证管理员用户ID
    const adminUserId = departmentManagement.form.adminUserId.trim()
    if (!adminUserId) {
      notification.error({ message: t('departmentManagement.adminUserIdRequired') })
      return
    }

    if (!/^[a-zA-Z0-9_]+$/.test(adminUserId)) {
      notification.error({ message: t('departmentManagement.adminUserIdFormat') })
      return
    }

    if (adminUserId.length < 3 || adminUserId.length > 20) {
      notification.error({ message: t('departmentManagement.adminUserIdLength') })
      return
    }

    if (departmentManagement.form.userIdError) {
      notification.error({ message: t('departmentManagement.adminUserIdError') })
      return
    }

    // 验证密码
    if (!departmentManagement.form.adminPassword) {
      notification.error({ message: t('departmentManagement.adminPasswordRequired') })
      return
    }

    if (
      departmentManagement.form.adminPassword !== departmentManagement.form.adminConfirmPassword
    ) {
      notification.error({ message: t('departmentManagement.adminPasswordConfirm') })
      return
    }

    // 验证手机号
    if (
      departmentManagement.form.adminPhone &&
      !validatePhoneNumber(departmentManagement.form.adminPhone)
    ) {
      notification.error({ message: t('userManagement.phoneFormat') })
      return
    }

    departmentManagement.loading = true

    if (departmentManagement.editMode) {
      // 更新部门
      await departmentApi.updateDepartment(departmentManagement.editDepartmentId, {
        name: departmentManagement.form.name.trim(),
        description: departmentManagement.form.description.trim() || undefined
      })
      notification.success({ message: t('departmentManagement.updateDepartmentSuccess') })
    } else {
      // 创建部门，同时创建管理员
      await departmentApi.createDepartment({
        name: departmentManagement.form.name.trim(),
        description: departmentManagement.form.description.trim() || undefined,
        admin_user_id: adminUserId,
        admin_password: departmentManagement.form.adminPassword,
        admin_phone: departmentManagement.form.adminPhone || undefined
      })

      notification.success({ message: t('departmentManagement.addDepartmentSuccess', { adminUserId }) })
    }

    // 重新获取部门列表
    await fetchDepartments()
    departmentManagement.modalVisible = false
  } catch (error) {
    console.error('部门操作失败:', error)
    notification.error({
      message: '操作失败',
      description: error.message || '请稍后重试'
    })
  } finally {
    departmentManagement.loading = false
  }
}

// 删除部门
const confirmDeleteDepartment = (department) => {
  Modal.confirm({
    title: t('departmentManagement.deleteDepartmentConfirm', { name: department.name }),
    content: t('departmentManagement.deleteDepartmentDescription'),
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        departmentManagement.loading = true
        await departmentApi.deleteDepartment(department.id)
        notification.success({ message: t('departmentManagement.deleteDepartmentSuccess') })
        // 重新获取部门列表
        await fetchDepartments()
      } catch (error) {
        console.error('删除部门失败:', error)
        notification.error({
          message: '删除失败',
          description: error.message || '请稍后重试'
        })
      } finally {
        departmentManagement.loading = false
      }
    }
  })
}

// 在组件挂载时获取部门列表
onMounted(() => {
  fetchDepartments()
})
</script>

<style lang="less" scoped>
.department-management {
  margin-top: 12px;
  min-height: 50vh;

  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;

    .header-content {
      flex: 1;

      .description {
        font-size: 14px;
        color: var(--gray-600);
        margin: 0;
        line-height: 1.4;
      }
    }
  }

  .content-section {
    overflow: hidden;

    .error-message {
      padding: 16px 24px;
    }

    .empty-state {
      padding: 60px 20px;
      text-align: center;
    }

    .department-table {
      :deep(.ant-table-thead > tr > th) {
        background: var(--gray-50);
        font-weight: 500;
        padding: 8px 12px;
      }

      :deep(.ant-table-tbody > tr > td) {
        padding: 8px 12px;
      }

      .department-name {
        .name-text {
          font-weight: 500;
          color: var(--gray-900);
        }
      }

      .description-text {
        color: var(--gray-600);
      }

      .action-btn {
        padding: 4px 8px;
        border-radius: 6px;
        transition: all 0.2s ease;

        &:hover {
          background: var(--gray-25);
        }
      }
    }
  }
}

.department-modal {
  :deep(.ant-modal-header) {
    padding: 20px 24px;
    border-bottom: 1px solid var(--gray-150);

    .ant-modal-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--gray-900);
    }
  }

  :deep(.ant-modal-body) {
    padding: 24px;
  }

  .department-form {
    .form-item {
      margin-bottom: 20px;

      :deep(.ant-form-item-label) {
        padding-bottom: 4px;

        label {
          font-weight: 500;
          color: var(--gray-900);
        }
      }
    }
  }

  .error-text {
    color: var(--color-error-500);
    font-size: 12px;
    margin-top: 4px;
    line-height: 1.3;
  }

  .help-text {
    color: var(--gray-600);
    font-size: 12px;
    margin-top: 4px;
    line-height: 1.3;
  }
}
</style>
