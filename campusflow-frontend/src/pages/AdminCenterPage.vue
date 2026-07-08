<template>
  <section class="admin-center-page module-page">
    <div class="overview-grid compact-grid">
      <article class="metric-card">
        <span>用户</span>
        <strong>{{ students.length }}</strong>
        <p>学生数据</p>
      </article>
      <article class="metric-card">
        <span>班级</span>
        <strong>{{ classes.length }}</strong>
        <p>教学组织</p>
      </article>
      <article class="metric-card">
        <span>课程</span>
        <strong>{{ courses.length }}</strong>
        <p>课表数据</p>
      </article>
      <article class="metric-card">
        <span>待审核</span>
        <strong>{{ pendingPosts.length }}</strong>
        <p>论坛内容</p>
      </article>
    </div>

    <section class="module-grid two-columns">
      <section class="content-panel">
        <div class="section-heading">
          <div>
            <h2>系统操作</h2>
            <p>管理基础数据、公告和审核任务。</p>
          </div>
        </div>
        <div class="admin-actions">
          <button class="ghost-action" type="button" @click="$emit('navigate', 'classes')">班级管理</button>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'forum')">论坛审核</button>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'notifications')">系统公告</button>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'files')">文件中心</button>
        </div>
      </section>

      <section class="content-panel">
        <div class="section-heading">
          <div>
            <h2>最近操作</h2>
            <p>平台关键操作记录。</p>
          </div>
        </div>
        <div class="message-list">
          <article v-for="log in logs" :key="log.id" class="notice-item">
            <div>
              <span>{{ log.actor }}</span>
              <strong>{{ log.action }}</strong>
              <small>{{ log.time }}</small>
            </div>
          </article>
        </div>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  classes: {
    type: Array,
    required: true
  },
  students: {
    type: Array,
    required: true
  },
  courses: {
    type: Array,
    required: true
  },
  posts: {
    type: Array,
    required: true
  },
  logs: {
    type: Array,
    required: true
  }
})

defineEmits(['navigate'])

const pendingPosts = computed(() => props.posts.filter(item => item.status === 'review'))
</script>
