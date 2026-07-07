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

      <div class="future-modules">
        <div class="panel-title">后续可扩展</div>
        <span>成绩系统</span>
        <span>论坛系统</span>
        <span>会议模块</span>
      </div>
    </aside>

    <section class="platform-main">
      <header class="platform-topbar">
        <div>
          <h1>{{ currentTitle }}</h1>
          <p>{{ roleText }} · {{ currentUser.name }}</p>
        </div>
        <button class="ghost-action" type="button" @click="$emit('logout')">退出登录</button>
      </header>

      <div class="platform-content" :class="{ 'assistant-content': activeView === 'assistant' }">
        <slot></slot>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bot, CalendarDays, Home, UsersRound } from 'lucide-vue-next'

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
  const baseItems = [
    { key: 'dashboard', label: '首页概览', icon: Home },
    { key: 'schedule', label: props.currentUser.role === 'teacher' ? '班级课表' : '我的课表', icon: CalendarDays },
    { key: 'assistant', label: '智能助手', icon: Bot }
  ]

  if (props.currentUser.role === 'teacher') {
    baseItems.splice(1, 0, { key: 'classes', label: '班级管理', icon: UsersRound })
  }

  return baseItems
})

const roleText = computed(() => (props.currentUser.role === 'teacher' ? '教师管理员' : '普通学生'))

const currentTitle = computed(() => {
  return navItems.value.find(item => item.key === props.activeView)?.label || '校园平台'
})
</script>
