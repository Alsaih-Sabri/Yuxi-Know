<template>
  <div class="user-management">
    <!-- 头部区域 -->
    <div class="header-section">
      <div class="header-content">
        <h3 class="title">{{ $t('userManagement.title') }}</h3>
        <p class="description">{{ $t('userManagement.description') }}</p>
      </div>
      <a-button type="primary" @click="showAddUserModal" class="add-btn">
        <template #icon><PlusOutlined /></template>
        {{ $t('userManagement.addUser') }}
      </a-button>
    </div>

    <!-- 主内容区域 -->
    <div class="content-section">
      <a-spin :spinning="userManagement.loading">
        <div v-if="userManagement.error" class="error-message">
          <a-alert type="error" :message="userManagement.error" show-icon />
        </div>

        <div class="cards-container">
          <div v-if="userManagement.users.length === 0" class="empty-state">
            <a-empty :description="$t('userManagement.noUsers')" />
          </div>
          <div v-else class="user-cards-grid">
            <div v-for="user in userManagement.users" :key="user.id" class="user-card">
              <div class="card-header">
                <div class="user-info-main">
                  <div class="user-avatar">
                    <img
                      v-if="user.avatar"
                      :src="user.avatar"
                      :alt="user.username"
                      class="avatar-img"
                    />
                    <div v-else class="avatar-placeholder">
                      {{ user.username.charAt(0).toUpperCase() }}
                    </div>
                  </div>
                  <div class="user-info-content">
                    <div class="name-tag-row">
                      <h4 class="username">{{ user.username }}</h4>
                      <div class="tags-row">
                        <a-tag
                          v-if="userStore.isSuperAdmin && user.department_name"
                          class="dept-tag small-tag"
                        >
                          {{ user.department_name }}
                        </a-tag>
                        <a-tooltip :title="getRoleLabel(user.role)">
                          <span class="role-icon-wrapper" :class="getRoleClass(user.role)">
                            <UserLock v-if="user.role === 'superadmin'" :size="16" />
                            <UserStar v-else-if="user.role === 'admin'" :size="16" />
                            <User v-else :size="16" />
                          </span>
                        </a-tooltip>
                      </div>
                    </div>
                    <div class="user-id-row">ID: {{ user.user_id || '-' }}</div>
                  </div>
                </div>
              </div>

              <div class="card-content">
                <div class="info-item">
                  <span class="info-label">{{ $t('userManagement.phoneNumber') }}</span>
                  <span class="info-value phone-text">{{ user.phone_number || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">{{ $t('userManagement.createdAt') }}</span>
                  <span class="info-value time-text">{{ formatTime(user.created_at) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">{{ $t('userManagement.lastLogin') }}</span>
                  <span class="info-value time-text">{{ formatTime(user.last_login) }}</span>
                </div>
              </div>

              <div class="card-actions">
                <a-tooltip :title="$t('userManagement.editUser')">
                  <a-button
                    type="text"
                    size="small"
                    @click="showEditUserModal(user)"
                    class="action-btn"
                  >
                    <EditOutlined />
                    <span>{{ $t('userManagement.edit') }}</span>
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('userManagement.deleteUser')">
                  <a-button
                    type="text"
                    size="small"
                    danger
                    @click="confirmDeleteUser(user)"
                    :disabled="
                      user.id === userStore.userId ||
                      (user.role === 'superadmin' && userStore.userRole !== 'superadmin')
                    "
                    class="action-btn"
                  >
                    <DeleteOutlined />
                    <span>{{ $t('userManagement.delete') }}</span>
                  </a-button>
                </a-tooltip>
              </div>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <!-- 用户表单模态框 -->
    <a-modal
      v-model:open="userManagement.modalVisible"
      :title="userManagement.modalTitle"
      @ok="handleUserFormSubmit"
      :confirmLoading="userManagement.loading"
      @cancel="userManagement.modalVisible = false"
      :maskClosable="false"
      width="480px"
      class="user-modal"
    >
      <a-form layout="vertical" class="user-form">
        <a-form-item :label="$t('userManagement.username')" required class="form-item">
          <a-input
            v-model:value="userManagement.form.username"
            :placeholder="$t('userManagement.usernamePlaceholder')"
            size="large"
            @blur="validateAndGenerateUserId"
            :maxlength="20"
          />
          <div v-if="userManagement.form.usernameError" class="error-text">
            {{ userManagement.form.usernameError }}
          </div>
        </a-form-item>

        <!-- 显示自动生成的用户ID -->
        <a-form-item
          v-if="userManagement.form.generatedUserId || userManagement.editMode"
          :label="$t('userManagement.userId')"
          class="form-item"
        >
          <a-input
            :value="userManagement.form.generatedUserId"
            :placeholder="$t('userManagement.autoGenerated')"
            size="large"
            disabled
            :addon-before="userManagement.editMode ? $t('userManagement.existingId') : $t('userManagement.loginId')"
          />
          <div v-if="!userManagement.editMode" class="help-text">
            {{ $t('userManagement.userIdHint') }}
          </div>
          <div v-else class="help-text">{{ $t('userManagement.userIdEditHint') }}</div>
        </a-form-item>

        <!-- 手机号字段 -->
        <a-form-item :label="$t('userManagement.phoneNumberLabel')" class="form-item">
          <a-input
            v-model:value="userManagement.form.phoneNumber"
            :placeholder="$t('userManagement.phoneNumberPlaceholder')"
            size="large"
            :maxlength="11"
          />
          <div v-if="userManagement.form.phoneError" class="error-text">
            {{ userManagement.form.phoneError }}
          </div>
        </a-form-item>

        <template v-if="userManagement.editMode">
          <div class="password-toggle">
            <a-checkbox v-model:checked="userManagement.displayPasswordFields">
              {{ $t('userManagement.changePassword') }}
            </a-checkbox>
          </div>
        </template>

        <template v-if="!userManagement.editMode || userManagement.displayPasswordFields">
          <a-form-item :label="$t('userManagement.password')" required class="form-item">
            <a-input-password
              v-model:value="userManagement.form.password"
              :placeholder="$t('userManagement.passwordPlaceholder')"
              size="large"
            />
          </a-form-item>

          <a-form-item :label="$t('userManagement.confirmPassword')" required class="form-item">
            <a-input-password
              v-model:value="userManagement.form.confirmPassword"
              :placeholder="$t('userManagement.confirmPasswordPlaceholder')"
              size="large"
            />
          </a-form-item>
        </template>

        <a-form-item :label="$t('userManagement.role')" class="form-item">
          <a-select v-model:value="userManagement.form.role" size="large">
            <a-select-option value="user">{{ $t('userManagement.normalUser') }}</a-select-option>
            <a-select-option value="admin" v-if="userStore.isSuperAdmin">{{ $t('userManagement.admin') }}</a-select-option>
            <a-select-option value="superadmin" v-if="userStore.isSuperAdmin"
              >{{ $t('userManagement.superAdmin') }}</a-select-option
            >
          </a-select>
        </a-form-item>

        <!-- 部门选择器（仅超级管理员可见） -->
        <a-form-item v-if="userStore.isSuperAdmin" :label="$t('userManagement.department')" class="form-item">
          <a-select
            v-model:value="userManagement.form.departmentId"
            size="large"
            :placeholder="$t('userManagement.selectDepartment')"
          >
            <a-select-option
              v-for="dept in departmentManagement.departments"
              :key="dept.id"
              :value="dept.id"
            >
              {{ dept.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { notification, Modal } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { departmentApi } from '@/apis'
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { User, UserLock, UserStar } from 'lucide-vue-next'
import { formatDateTime } from '@/utils/time'

const { t } = useI18n()
const userStore = useUserStore()

// 用户管理相关状态
const userManagement = reactive({
  loading: false,
  users: [],
  error: null,
  modalVisible: false,
  modalTitle: t('userManagement.addUser'),
  editMode: false,
  editUserId: null,
  form: {
    username: '',
    generatedUserId: '', // 自动生成的user_id
    phoneNumber: '', // 手机号
    password: '',
    confirmPassword: '',
    role: 'user', // 默认角色
    departmentId: null, // 部门ID
    usernameError: '', // 用户名错误信息
    phoneError: '' // 手机号错误信息
  },
  displayPasswordFields: true // 编辑时是否显示密码字段
})

// 部门列表（仅超级管理员使用）
const departmentManagement = reactive({
  departments: []
})

// 获取部门列表
const fetchDepartments = async () => {
  if (!userStore.isSuperAdmin) return // 普通管理员不需要获取所有部门列表
  try {
    const departments = await departmentApi.getDepartments()
    departmentManagement.departments = departments
  } catch (error) {
    console.error(t('userManagement.getDepartmentsFailed'), error)
  }
}

// 添加验证用户名并生成user_id的函数
const validateAndGenerateUserId = async () => {
  const username = userManagement.form.username.trim()

  // 清空之前的错误和生成的ID
  userManagement.form.usernameError = t('userManagement.userIdExists')
  userManagement.form.generatedUserId = ''

  if (!username) {
    return
  }

  // 在编辑模式下，不需要重新生成user_id
  if (userManagement.editMode) {
    return
  }

  try {
    const result = await userStore.validateUsernameAndGenerateUserId(username)
    userManagement.form.generatedUserId = result.user_id
  } catch (error) {
    userManagement.form.usernameError = error.message || t('userManagement.checkUserIdFailed')
  }
}

// 验证手机号格式
const validatePhoneNumber = (phone) => {
  if (!phone) {
    return true // 手机号可选
  }

  // 中国大陆手机号格式验证
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(phone)
}

// 监听密码字段显示状态变化
watch(
  () => userManagement.displayPasswordFields,
  (newVal) => {
    // 当取消显示密码字段时，清空密码输入
    if (!newVal) {
      userManagement.form.password = ''
      userManagement.form.confirmPassword = ''
    }
  }
)

// 监听手机号输入变化
watch(
  () => userManagement.form.phoneNumber,
  (newPhone) => {
    userManagement.form.phoneError = ''

    if (newPhone && !validatePhoneNumber(newPhone)) {
      userManagement.form.phoneError = t('userManagement.phoneFormat')
    }
  }
)

// 格式化时间显示
const formatTime = (timeStr) => formatDateTime(timeStr)

// 获取用户列表
const fetchUsers = async () => {
  try {
    userManagement.loading = true
    const users = await userStore.getUsers()
    userManagement.users = users
    userManagement.error = null
  } catch (error) {
    console.error(t('userManagement.loadUsersFailed'), error)
    userManagement.error = t('userManagement.loadUsersFailed')
  } finally {
    userManagement.loading = false
  }
}

// 打开添加用户模态框
const showAddUserModal = () => {
  userManagement.modalTitle = t('userManagement.addUser')
  userManagement.editMode = false
  userManagement.editUserId = null
  userManagement.form = {
    username: '',
    generatedUserId: '',
    phoneNumber: '',
    password: '',
    confirmPassword: '',
    role: 'user', // 默认角色为普通用户
    departmentId: null,
    usernameError: '',
    phoneError: ''
  }
  userManagement.displayPasswordFields = true
  userManagement.modalVisible = true
}

// 打开编辑用户模态框
const showEditUserModal = (user) => {
  userManagement.modalTitle = `${t('userManagement.editUser')} - ${user.username}`
  userManagement.editMode = true
  userManagement.editUserId = user.id
  userManagement.form = {
    username: user.username,
    generatedUserId: user.user_id || '', // 编辑模式显示现有的user_id
    phoneNumber: user.phone_number || '',
    password: '',
    confirmPassword: '',
    role: user.role,
    departmentId: user.department_id || null,
    usernameError: '',
    phoneError: ''
  }
  userManagement.displayPasswordFields = false // 默认不显示密码字段
  userManagement.modalVisible = true
}

// 处理用户表单提交
const handleUserFormSubmit = async () => {
  try {
    // 简单验证
    if (!userManagement.form.username.trim()) {
      notification.error({ message: t('userManagement.usernameRequired') })
      return
    }

    // 验证用户名长度
    if (
      userManagement.form.username.trim().length < 2 ||
      userManagement.form.username.trim().length > 20
    ) {
      notification.error({ message: t('userManagement.usernameLength') })
      return
    }

    // 验证手机号
    if (userManagement.form.phoneNumber && !validatePhoneNumber(userManagement.form.phoneNumber)) {
      notification.error({ message: t('userManagement.phoneFormat') })
      return
    }

    if (userManagement.displayPasswordFields) {
      if (!userManagement.form.password) {
        notification.error({ message: t('userManagement.passwordRequired') })
        return
      }

      if (userManagement.form.password !== userManagement.form.confirmPassword) {
        notification.error({ message: t('userManagement.passwordMismatch') })
        return
      }
    }

    userManagement.loading = true

    // 根据模式决定创建还是更新用户
    if (userManagement.editMode) {
      // 创建更新数据对象
      const updateData = {
        username: userManagement.form.username.trim(),
        role: userManagement.form.role
      }

      // 添加手机号字段
      if (userManagement.form.phoneNumber) {
        updateData.phone_number = userManagement.form.phoneNumber
      }

      // 超级管理员可以修改部门
      if (userStore.isSuperAdmin && userManagement.form.departmentId) {
        updateData.department_id = userManagement.form.departmentId
      }

      // 如果显示了密码字段并且填写了密码，才更新密码
      if (userManagement.displayPasswordFields && userManagement.form.password) {
        updateData.password = userManagement.form.password
      }

      await userStore.updateUser(userManagement.editUserId, updateData)
      notification.success({ message: t('userManagement.updateUserSuccess') })
    } else {
      // 创建新用户
      const createData = {
        username: userManagement.form.username.trim(),
        password: userManagement.form.password,
        role: userManagement.form.role
      }

      // 超级管理员可以指定部门
      if (userStore.isSuperAdmin && userManagement.form.departmentId) {
        createData.department_id = userManagement.form.departmentId
      }

      // 添加手机号字段（如果填写了）
      if (userManagement.form.phoneNumber) {
        createData.phone_number = userManagement.form.phoneNumber
      }

      await userStore.createUser(createData)
      notification.success({ message: t('userManagement.addUserSuccess') })
    }

    // 重新获取用户列表
    await fetchUsers()
    userManagement.modalVisible = false
  } catch (error) {
    console.error(t('userManagement.operationFailed'), error)
    notification.error({
      message: t('userManagement.operationFailed'),
      description: error.message || t('userManagement.operationFailed')
    })
  } finally {
    userManagement.loading = false
  }
}

// 删除用户
const confirmDeleteUser = (user) => {
  // 自己不能删除自己
  if (user.id === userStore.userId) {
    notification.error({ message: t('userManagement.deleteSelfFailed') })
    return
  }

  // 确认对话框
  Modal.confirm({
    title: t('userManagement.deleteUserConfirm', { username: user.username }),
    content: t('userManagement.deleteUserDescription'),
    okText: t('userManagement.delete'),
    okType: 'danger',
    cancelText: t('userManagement.cancel'),
    async onOk() {
      try {
        userManagement.loading = true
        await userStore.deleteUser(user.id)
        notification.success({ message: t('userManagement.deleteUserSuccess') })
        // 重新获取用户列表
        await fetchUsers()
      } catch (error) {
        console.error(t('userManagement.deleteUserFailed'), error)
        notification.error({
          message: t('userManagement.deleteUserFailed'),
          description: error.message || t('userManagement.deleteUserFailed')
        })
      } finally {
        userManagement.loading = false
      }
    }
  })
}

// 角色显示辅助函数
const getRoleLabel = (role) => {
  switch (role) {
    case 'superadmin':
      return t('userManagement.superAdmin')
    case 'admin':
      return t('userManagement.admin')
    case 'user':
      return t('userManagement.normalUser')
    default:
      return role
  }
}

// 角色标签颜色
const getRoleColor = (role) => {
  switch (role) {
    case 'superadmin':
      return 'red'
    case 'admin':
      return 'blue'
    case 'user':
      return 'green'
    default:
      return 'default'
  }
}

const getRoleClass = (role) => {
  switch (role) {
    case 'superadmin':
      return 'role-superadmin'
    case 'admin':
      return 'role-admin'
    case 'user':
      return 'role-user'
    default:
      return 'role-default'
  }
}

// 在组件挂载时获取用户列表
onMounted(async () => {
  await fetchUsers()
  await fetchDepartments()
})
</script>

<style lang="less" scoped>
.user-management {
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

  .content-section {
    overflow: hidden;

    .error-message {
      padding: 16px 24px;
    }

    .cards-container {
      .empty-state {
        padding: 60px 20px;
        text-align: center;
      }

      .user-cards-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 16px;
        // padding: 16px;

        .user-card {
          background: var(--gray-0);
          border: 1px solid var(--gray-150);
          border-radius: 8px;
          padding: 12px 16px;
          padding-bottom: 6px;

          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

          &:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            border-color: var(--gray-200);
          }

          .card-header {
            margin-bottom: 10px;

            .user-info-main {
              display: flex;
              gap: 12px;
              align-items: center;

              .user-avatar {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--gray-50);
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                flex-shrink: 0;

                .avatar-img {
                  width: 100%;
                  height: 100%;
                  object-fit: cover;
                }

                .avatar-placeholder {
                  color: var(--gray-600);
                  font-weight: 500;
                  font-size: 14px;
                }
              }

              .user-info-content {
                flex: 1;
                min-width: 0;

                .name-tag-row {
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  margin-bottom: 2px;
                  flex-wrap: wrap;

                  .username {
                    margin: 0;
                    font-size: 15px;
                    font-weight: 600;
                    color: var(--gray-900);
                    line-height: 1.2;
                  }

                  .tags-row {
                    display: flex;
                    align-items: center;
                    gap: 6px;

                    .role-icon-wrapper {
                      display: flex;
                      align-items: center;
                      justify-content: center;
                      width: 20px;
                      height: 20px;
                      border-radius: 4px;

                      &.role-superadmin {
                        color: var(--color-error-700);
                        background: var(--color-error-50);
                      }
                      &.role-admin {
                        color: var(--color-info-700);
                        background: var(--color-info-50);
                      }
                      &.role-user {
                        color: var(--color-success-700);
                        background: var(--color-success-50);
                      }
                    }

                    .small-tag {
                      font-size: 12px;
                      height: 22px;
                      padding: 0 4px;
                      margin-right: 4px;
                    }
                  }
                }

                .user-id-row {
                  font-size: 12px;
                  color: var(--gray-500);
                  font-family: 'Monaco', 'Consolas', monospace;
                  line-height: 1.2;
                }
              }
            }
          }

          .card-content {
            .info-item {
              display: flex;
              justify-content: space-between;
              align-items: center;
              padding: 2px 0;
              border-bottom: 1px solid var(--gray-25);

              &:last-child {
                border-bottom: none;
              }

              .info-label {
                font-size: 12px;
                color: var(--gray-600);
                font-weight: 500;
                min-width: 70px;
              }

              .info-value {
                font-size: 12px;
                color: var(--gray-900);
                text-align: right;
                flex: 1;

                &.time-text {
                  color: var(--gray-700);
                }

                &.phone-text {
                  font-family: 'Monaco', 'Consolas', monospace;
                }
              }
            }
          }

          .card-actions {
            display: flex;
            justify-content: flex-end;
            gap: 6px;
            padding-top: 6px;
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

  .time-text {
    font-size: 13px;
    color: var(--gray-700);
  }

  .phone-text,
  .user-id-text {
    font-size: 13px;
    color: var(--gray-900);
    font-family: 'Monaco', 'Consolas', monospace;
  }
}

.user-modal {
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

  .user-form {
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

    .password-toggle {
      margin-bottom: 16px;

      :deep(.ant-checkbox-wrapper) {
        font-weight: 500;
        color: var(--gray-600);
      }
    }
  }
}
</style>
