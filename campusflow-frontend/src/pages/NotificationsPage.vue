<template>
  <section class="notifications-page module-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>通知与消息</h2>
          <p>{{ unreadCount }} 条未读</p>
        </div>
        <button class="ghost-action" type="button" @click="$emit('mark-all-read')">全部已读</button>
      </div>

      <div class="message-list">
        <article
          v-for="notice in notifications"
          :key="notice.id"
          class="notice-item"
          :class="{ unread: notice.status === 'unread' }"
        >
          <div>
            <span>{{ notice.type }}</span>
            <strong>{{ notice.title }}</strong>
            <small>{{ notice.time }}</small>
          </div>
          <button class="ghost-action" type="button" @click="$emit('open-notice', notice)">
            {{ notice.status === 'unread' ? '查看' : '打开' }}
          </button>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  notifications: {
    type: Array,
    required: true
  }
})

defineEmits(['mark-all-read', 'open-notice'])

const unreadCount = computed(() => props.notifications.filter(item => item.status === 'unread').length)
</script>
