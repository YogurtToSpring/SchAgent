<template>
  <section class="forum-page module-page">
    <section class="module-toolbar content-panel">
      <div>
        <h2>校园论坛</h2>
        <p>{{ visiblePosts.length }} 条内容</p>
      </div>
      <button class="primary-action compact" type="button" @click="posting = !posting">
        {{ posting ? '收起' : '发布帖子' }}
      </button>
    </section>

    <form v-if="posting" class="content-panel post-form" @submit.prevent="submitPost">
      <select v-model="draft.channel">
        <option v-for="channel in channels" :key="channel">{{ channel }}</option>
      </select>
      <input v-model="draft.title" placeholder="标题" />
      <textarea v-model="draft.summary" rows="3" placeholder="正文摘要"></textarea>
      <button class="primary-action compact" type="submit">发布</button>
    </form>

    <section class="module-grid two-columns">
      <aside class="content-panel side-filter">
        <button
          v-for="channel in availableChannels"
          :key="channel"
          type="button"
          :class="{ active: activeChannel === channel }"
          @click="activeChannel = channel"
        >
          <span>{{ channel }}</span>
          <strong>{{ countByChannel(channel) }}</strong>
        </button>
      </aside>

      <section class="content-panel forum-list">
        <article
          v-for="post in visiblePosts"
          :key="post.id"
          class="post-card"
          :class="{ review: post.status === 'review' }"
        >
          <div>
            <span class="channel-badge">{{ post.channel }}</span>
            <h3>{{ post.title }}</h3>
            <p>{{ post.summary }}</p>
            <small>{{ post.author }} · {{ post.replies }} 回复 · {{ post.likes }} 赞</small>
          </div>
          <div v-if="currentUser.role === 'admin' && post.status === 'review'" class="post-actions">
            <button class="ghost-action" type="button" @click="$emit('review-post', post.id)">通过</button>
          </div>
        </article>
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
  posts: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['add-post', 'review-post'])

const channels = ['学习交流', '校园生活', '失物招领', '二手交易', '社团活动']
const activeChannel = ref('全部')
const posting = ref(false)
const draft = reactive({
  channel: '学习交流',
  title: '',
  summary: ''
})

const availableChannels = computed(() => {
  const base = ['全部', ...channels]
  if (props.currentUser.role === 'admin') base.push('待审核')
  return base
})

const visiblePosts = computed(() => {
  if (activeChannel.value === '待审核') return props.posts.filter(item => item.status === 'review')
  if (activeChannel.value === '全部') {
    return props.currentUser.role === 'admin'
      ? props.posts
      : props.posts.filter(item => item.status === 'published')
  }
  return props.posts.filter(item => item.channel === activeChannel.value && (props.currentUser.role === 'admin' || item.status === 'published'))
})

function submitPost() {
  if (!draft.title.trim()) return
  emit('add-post', {
    channel: draft.channel,
    title: draft.title.trim(),
    summary: draft.summary.trim() || '暂无摘要',
    author: props.currentUser.name,
    role: props.currentUser.role,
    replies: 0,
    likes: 0,
    status: props.currentUser.role === 'admin' || props.currentUser.role === 'teacher' ? 'published' : 'review'
  })
  draft.title = ''
  draft.summary = ''
  posting.value = false
}

function countByChannel(channel) {
  if (channel === '全部') return props.posts.filter(item => props.currentUser.role === 'admin' || item.status === 'published').length
  if (channel === '待审核') return props.posts.filter(item => item.status === 'review').length
  return props.posts.filter(item => item.channel === channel && (props.currentUser.role === 'admin' || item.status === 'published')).length
}
</script>
