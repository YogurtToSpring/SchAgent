<template>
  <div class="platform-shell">
    <aside class="platform-sidebar" aria-label="平台导航">
      <div class="platform-brand">
        <div class="brand-mark">CF</div>
        <div>
          <strong>CampusFlow</strong>
          <span>校园智能服务平台</span>
        </div>
      </div>

      <nav class="platform-nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          :class="{ active: activeView === item.key }"
          @click="$emit('navigate', item.key)"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-user">
        <div class="user-avatar">{{ userInitial }}</div>
        <div>
          <strong>{{ currentUser.name }}</strong>
          <span>{{ roleText }}</span>
        </div>
      </div>
    </aside>

    <section class="platform-main">
      <header class="platform-topbar">
        <div>
          <h1>{{ currentTitle }}</h1>
          <p>{{ topbarSubtitle }}</p>
        </div>

        <div class="topbar-user-menu">
          <div class="user-avatar">{{ userInitial }}</div>
          <div class="user-identity">
            <strong>{{ currentUser.name }}</strong>
            <span>{{ roleText }}</span>
          </div>
          <button class="ghost-action" type="button" @click="$emit('logout')">退出</button>
        </div>
      </header>

      <div class="platform-content" :class="{ 'assistant-content': activeView === 'assistant' }">
        <slot></slot>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Bell,
  Bot,
  BookOpen,
  CalendarDays,
  CheckSquare,
  Files,
  GraduationCap,
  Home,
  ListChecks,
  MessageSquareText,
  ShieldCheck,
  UserRound,
  UsersRound
} from 'lucide-vue-next'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  activeView: {
    type: String,
    required: true
  }
})

defineEmits(['navigate', 'logout'])

const navItems = computed(() => {
  const commonItems = [
    { key: 'dashboard', label: '首页工作台', icon: Home },
    { key: 'profile', label: '我的信息', icon: UserRound },
    { key: 'todos', label: '待办事项', icon: CheckSquare },
    { key: 'notifications', label: '通知消息', icon: Bell },
    { key: 'files', label: '文件中心', icon: Files },
    { key: 'assistant', label: 'SchAgent', icon: Bot }
  ]

  if (props.currentUser.role === 'student') {
    return [
      ...commonItems.slice(0, 3),
      { key: 'schedule', label: '我的课表', icon: CalendarDays },
      { key: 'course-selection', label: '学生选课', icon: ListChecks },
      { key: 'grades', label: '成绩系统', icon: GraduationCap },
      { key: 'library', label: '图书馆预约', icon: BookOpen },
      { key: 'forum', label: '校园论坛', icon: MessageSquareText },
      ...commonItems.slice(3)
    ]
  }

  if (props.currentUser.role === 'teacher') {
    return [
      ...commonItems.slice(0, 3),
      { key: 'classes', label: '班级与课程', icon: UsersRound },
      { key: 'schedule', label: '教学课表', icon: CalendarDays },
      { key: 'forum', label: '校园论坛', icon: MessageSquareText },
      ...commonItems.slice(3)
    ]
  }

  if (props.currentUser.role === 'admin') {
    return [
      ...commonItems.slice(0, 3),
      { key: 'classes', label: '班级与课程', icon: UsersRound },
      { key: 'schedule', label: '全校课表', icon: CalendarDays },
      { key: 'forum', label: '论坛审核', icon: MessageSquareText },
      ...commonItems.slice(3),
      { key: 'admin', label: '管理后台', icon: ShieldCheck }
    ]
  }

  return commonItems
})

const roleText = computed(() => {
  const map = {
    teacher: '教师',
    student: '学生',
    admin: '管理员'
  }
  return map[props.currentUser.role] || '用户'
})

const userInitial = computed(() => {
  return String(props.currentUser.name || 'U').slice(0, 1).toUpperCase()
})

const currentTitle = computed(() => {
  return navItems.value.find(item => item.key === props.activeView)?.label || '校园平台'
})

const topbarSubtitle = computed(() => {
  if (props.activeView === 'dashboard') return '今日课程、待办和消息'
  if (props.activeView === 'assistant') return 'SchAgent 基于当前身份和页面数据执行任务'
  return `${roleText.value}视角 · ${props.currentUser.name}`
})
</script>
