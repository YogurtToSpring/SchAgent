<template>
  <section class="profile-page">
    <aside class="profile-card content-panel">
      <div class="profile-avatar">{{ initials }}</div>
      <h2>{{ currentUser.name }}</h2>
      <p>{{ roleText }} · {{ primaryOrg }}</p>
      <div class="profile-tags">
        <span>{{ currentUser.studentNo || currentUser.teacherNo || currentUser.username }}</span>
        <span>{{ currentUser.role }}</span>
      </div>
    </aside>

    <section class="content-panel profile-settings">
      <div class="module-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <form v-if="activeTab === 'profile'" class="settings-form" @submit.prevent>
        <label>
          姓名
          <input :value="currentUser.name" readonly />
        </label>
        <label>
          身份编号
          <input :value="currentUser.studentNo || currentUser.teacherNo || currentUser.username || '-'" readonly />
        </label>
        <label>
          所属组织
          <input :value="primaryOrg" readonly />
        </label>
        <label>
          联系邮箱
          <input v-model="settings.email" />
        </label>
        <label>
          联系电话
          <input v-model="settings.phone" />
        </label>
        <button class="primary-action compact" type="button">保存资料</button>
      </form>

      <form v-else-if="activeTab === 'account'" class="settings-form" @submit.prevent>
        <label>
          当前密码
          <input type="password" />
        </label>
        <label>
          新密码
          <input type="password" />
        </label>
        <label>
          登录设备
          <input value="Windows · 当前浏览器" readonly />
        </label>
        <button class="primary-action compact" type="button">更新账号</button>
      </form>

      <section v-else class="setting-list">
        <label>
          <span>
            <strong>显示助手思考过程</strong>
            <small>回答中保留可折叠思考区域</small>
          </span>
          <input v-model="settings.showReasoning" type="checkbox" />
        </label>
        <label>
          <span>
            <strong>默认收起工具轨迹</strong>
            <small>智能助手页面保持主对话优先</small>
          </span>
          <input v-model="settings.compactTrace" type="checkbox" />
        </label>
        <label>
          <span>
            <strong>待办提醒</strong>
            <small>首页和通知中心显示待处理事项</small>
          </span>
          <input v-model="settings.todoReminder" type="checkbox" />
        </label>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  classes: {
    type: Array,
    default: () => []
  }
})

const activeTab = ref('profile')
const tabs = [
  { key: 'profile', label: '个人资料' },
  { key: 'account', label: '账号设置' },
  { key: 'system', label: '系统设置' }
]

const settings = reactive({
  email: '',
  phone: '',
  showReasoning: true,
  compactTrace: true,
  todoReminder: true
})

const initials = computed(() => String(props.currentUser.name || 'U').slice(0, 1).toUpperCase())

const roleText = computed(() => {
  const map = {
    student: '学生',
    teacher: '教师',
    admin: '管理员'
  }
  return map[props.currentUser.role] || '用户'
})

const primaryOrg = computed(() => {
  if (props.currentUser.role === 'student') {
    return props.classes.find(item => item.id === props.currentUser.classId)?.name || '未分配班级'
  }
  if (props.currentUser.role === 'teacher') {
    return '教学管理'
  }
  return '平台管理'
})
</script>
