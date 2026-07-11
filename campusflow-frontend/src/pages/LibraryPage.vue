<template>
  <section class="library-page module-page">
    <section class="content-panel library-toolbar">
      <div class="section-heading">
        <div>
          <h2>图书馆座位预约</h2>
          <p>开放时间 08:00-22:00，按日期和时间段查询后选择座位。</p>
        </div>
        <button class="ghost-action compact icon-text-action" type="button" :disabled="loading" @click="refreshAll">
          <RefreshCw :size="16" />
          刷新
        </button>
      </div>

      <form class="library-search-form" @submit.prevent="searchSeats">
        <label>
          日期
          <input v-model="query.date" type="date" :min="today" required />
        </label>
        <label>
          开始时间
          <select v-model="query.startTime">
            <option v-for="time in startTimes" :key="time" :value="time">{{ time }}</option>
          </select>
        </label>
        <label>
          结束时间
          <select v-model="query.endTime">
            <option v-for="time in endTimes" :key="time" :value="time">{{ time }}</option>
          </select>
        </label>
        <label>
          馆区
          <select v-model="query.area">
            <option value="A">A区 · 一楼自习区</option>
            <option value="B">B区 · 二楼阅览区</option>
            <option value="C">C区 · 三楼电子阅览区</option>
          </select>
        </label>
        <button class="primary-action icon-text-action" type="submit" :disabled="loading">
          <Search :size="16" />
          查询座位
        </button>
      </form>

      <p v-if="feedback.text" class="module-feedback" :class="feedback.type" role="status">
        {{ feedback.text }}
      </p>
    </section>

    <section class="library-summary" aria-label="座位查询概览">
      <div>
        <span>查询区域</span>
        <strong>{{ query.area }}区</strong>
      </div>
      <div>
        <span>可预约</span>
        <strong>{{ selectableCount }}</strong>
      </div>
      <div>
        <span>已占用</span>
        <strong>{{ unavailableCount }}</strong>
      </div>
      <div>
        <span>我的有效预约</span>
        <strong>{{ activeReservationCount }}</strong>
      </div>
    </section>

    <section class="module-grid two-columns library-workspace">
      <section class="content-panel seat-map">
        <div class="section-heading">
          <div>
            <h2>{{ query.area }}区座位</h2>
            <p>{{ query.date }} {{ query.startTime }}-{{ query.endTime }}</p>
          </div>
          <div class="seat-legend" aria-label="座位状态图例">
            <span><i class="available"></i>可预约</span>
            <span><i class="reserved"></i>已占用</span>
            <span><i class="time-blocked"></i>本人时段冲突</span>
          </div>
        </div>

        <p v-if="queryBlockReason" class="reservation-conflict-banner" role="status">
          <AlertTriangle :size="17" />
          {{ queryBlockReason }}
        </p>

        <div v-if="loading" class="empty-state">正在查询座位...</div>
        <div v-else-if="!seats.length" class="empty-state">当前条件下没有座位数据</div>
        <div v-else class="seat-grid library-seat-grid">
          <button
            v-for="seat in pagedSeats"
            :key="seat.seatId"
            type="button"
            class="seat-item"
            :class="[seat.status, { selected: selectedSeat?.seatId === seat.seatId, 'time-blocked': seat.available && queryBlockReason }]"
            :disabled="!seat.available || Boolean(queryBlockReason)"
            :title="seatTitle(seat)"
            @click="selectedSeat = seat"
          >
            <strong>{{ seat.seatId }}</strong>
            <span>{{ seat.floor }}楼 · {{ seat.area }}区</span>
          </button>
        </div>

        <div v-if="seats.length" class="pagination-bar library-pagination">
          <span>第 {{ seatPage }} / {{ seatTotalPages }} 页，共 {{ seats.length }} 个座位</span>
          <div>
            <button class="ghost-action compact" type="button" :disabled="seatPage <= 1" @click="seatPage--">上一页</button>
            <button class="ghost-action compact" type="button" :disabled="seatPage >= seatTotalPages" @click="seatPage++">下一页</button>
          </div>
        </div>
      </section>

      <aside class="library-side-column">
        <section class="content-panel reservation-confirm-panel">
          <div class="section-heading compact-heading">
            <div>
              <h2>预约确认</h2>
              <p>请核对座位与时间</p>
            </div>
          </div>

          <div v-if="selectedSeat" class="selected-seat-detail">
            <div class="selected-seat-number">
              <span>已选座位</span>
              <strong>{{ selectedSeat.seatId }}</strong>
            </div>
            <dl class="detail-list">
              <div><dt>区域</dt><dd>{{ selectedSeat.area }}区 {{ selectedSeat.floor }}楼</dd></div>
              <div><dt>日期</dt><dd>{{ query.date }}</dd></div>
              <div><dt>时间</dt><dd>{{ query.startTime }}-{{ query.endTime }}</dd></div>
            </dl>
            <button class="primary-action reservation-submit" type="button" :disabled="submitting" @click="confirmReservation">
              {{ submitting ? '正在预约...' : '确认预约' }}
            </button>
            <button class="text-action" type="button" @click="selectedSeat = null">取消选择</button>
          </div>
          <div v-else class="empty-state compact">请从左侧选择一个可预约座位</div>
        </section>

        <section class="content-panel my-reservations-panel">
          <div class="section-heading compact-heading">
            <div>
              <h2>我的预约</h2>
              <p>共 {{ reservations.length }} 条记录</p>
            </div>
          </div>

          <div v-if="historyLoading" class="empty-state compact">正在读取预约记录...</div>
          <div v-else-if="!reservations.length" class="empty-state compact">暂无预约记录</div>
          <div v-else class="reservation-history-list">
            <article v-for="item in reservations" :key="item.id" class="reservation-history-item">
              <div>
                <strong>{{ item.seatId }}</strong>
                <span>{{ item.date }} {{ item.startTime }}-{{ item.endTime }}</span>
              </div>
              <div class="reservation-row-actions">
                <span class="reservation-status" :class="item.status">{{ statusText(item.status) }}</span>
                <button
                  v-if="item.status === 'reserved'"
                  class="icon-action danger-icon-action"
                  type="button"
                  title="取消预约"
                  :disabled="cancellingId === item.id"
                  @click="cancelReservation(item)"
                >
                  <X :size="16" />
                </button>
              </div>
            </article>
          </div>
        </section>
      </aside>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { AlertTriangle, RefreshCw, Search, X } from 'lucide-vue-next'
import {
  cancelLibraryReservation,
  loadLibraryAvailability,
  loadLibraryReservations,
  reserveLibrarySeat
} from '../api/platform'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['add-todo', 'reservations-updated', 'notification-created'])

const today = formatLocalDate(new Date())
const seatPageSize = 24
const allTimes = Array.from({ length: 15 }, (_, index) => `${String(index + 8).padStart(2, '0')}:00`)
const query = reactive(createInitialReservationQuery())
const seats = ref([])
const reservations = ref([])
const selectedSeat = ref(null)
const loading = ref(false)
const historyLoading = ref(false)
const submitting = ref(false)
const cancellingId = ref(null)
const seatPage = ref(1)
const lastSearchKey = ref('')
const feedback = reactive({ text: '', type: '' })
let latestSearchId = 0

const startTimes = computed(() => allTimes.slice(0, -1))
const endTimes = computed(() => allTimes.filter(time => time > query.startTime))
const seatTotalPages = computed(() => Math.max(1, Math.ceil(seats.value.length / seatPageSize)))
const pagedSeats = computed(() => {
  const start = (seatPage.value - 1) * seatPageSize
  return seats.value.slice(start, start + seatPageSize)
})
const availableCount = computed(() => seats.value.filter(seat => seat.available).length)
const unavailableCount = computed(() => seats.value.filter(seat => !seat.available).length)
const activeReservationCount = computed(() => reservations.value.filter(item => item.status === 'reserved').length)
const conflictingReservation = computed(() => {
  return reservations.value.find(item => {
    return item.status === 'reserved' &&
      item.date === query.date &&
      timeRangesOverlap(query.startTime, query.endTime, item.startTime, item.endTime)
  })
})
const queryBlockReason = computed(() => {
  if (isQueryStartPast()) return '该预约开始时间已经过去，请选择今天稍后的时段或未来日期。'
  if (lastSearchKey.value && lastSearchKey.value !== reservationQueryKey(query)) return '查询条件已改变，请重新查询座位。'
  if (conflictingReservation.value) {
    const item = conflictingReservation.value
    return `您已预约 ${item.seatId}（${item.startTime}-${item.endTime}），当前时段存在冲突，不能重复预约。`
  }
  return ''
})

const selectableCount = computed(() => queryBlockReason.value ? 0 : availableCount.value)

watch(
  () => query.startTime,
  () => {
    if (query.endTime <= query.startTime) {
      query.endTime = endTimes.value[0] || '22:00'
    }
  }
)

watch(
  () => query.area,
  () => {
    seatPage.value = 1
    selectedSeat.value = null
    searchSeats()
  }
)

onMounted(refreshAll)

async function refreshAll() {
  await Promise.allSettled([searchSeats(), refreshHistory()])
}

async function searchSeats() {
  const searchId = ++latestSearchId
  const searchQuery = { ...query }
  loading.value = true
  selectedSeat.value = null
  seatPage.value = 1
  clearFeedback()
  try {
    const result = await loadLibraryAvailability(searchQuery)
    if (searchId !== latestSearchId) return
    seats.value = result.seats.filter(seat => seat.area === searchQuery.area)
    lastSearchKey.value = reservationQueryKey(searchQuery)
  } catch (error) {
    if (searchId !== latestSearchId) return
    seats.value = []
    lastSearchKey.value = ''
    showFeedback(toErrorMessage(error, '座位查询失败，请确认后端图书馆接口可用。'), 'error')
  } finally {
    if (searchId === latestSearchId) loading.value = false
  }
}

async function refreshHistory() {
  const userId = currentUserId()
  if (!userId) return
  historyLoading.value = true
  try {
    reservations.value = await loadLibraryReservations(userId)
    emit('reservations-updated', reservations.value)
  } catch (error) {
    showFeedback(toErrorMessage(error, '预约记录加载失败。'), 'error')
  } finally {
    historyLoading.value = false
  }
}

async function confirmReservation() {
  if (!selectedSeat.value || submitting.value) return
  if (queryBlockReason.value) {
    selectedSeat.value = null
    showFeedback(queryBlockReason.value, 'error')
    return
  }
  const currentSeat = seats.value.find(seat => seat.seatId === selectedSeat.value.seatId)
  if (!currentSeat?.available) {
    selectedSeat.value = null
    showFeedback('该座位已被占用，请重新选择。', 'error')
    await searchSeats()
    return
  }
  submitting.value = true
  clearFeedback()
  try {
    await reserveLibrarySeat(currentUserId(), {
      seatId: selectedSeat.value.seatId,
      date: query.date,
      startTime: query.startTime,
      endTime: query.endTime
    })
    const seatId = selectedSeat.value.seatId
    selectedSeat.value = null
    emit('add-todo', {
      title: `图书馆预约：${seatId}`,
      dueDate: query.date,
      category: '图书馆',
      source: '预约',
      priority: 'medium',
      note: `${query.startTime}-${query.endTime}，请按时到馆。`
    })
    emit('notification-created', {
      type: '图书馆预约',
      title: `${seatId} 预约成功`,
      content: `${query.date} ${query.startTime}-${query.endTime}，请按时到馆。`,
      link: 'library'
    })
    await Promise.all([searchSeats(), refreshHistory()])
    showFeedback(`${seatId} 预约成功。`, 'success')
  } catch (error) {
    const message = toErrorMessage(error, '预约失败，请稍后重试。')
    if (error?.response?.status === 409) await searchSeats()
    showFeedback(message, 'error')
  } finally {
    submitting.value = false
  }
}

async function cancelReservation(item) {
  if (!window.confirm(`确认取消 ${item.seatId} 在 ${item.date} ${item.startTime}-${item.endTime} 的预约？`)) return
  cancellingId.value = item.id
  clearFeedback()
  try {
    await cancelLibraryReservation(item.backendId || item.id, currentUserId())
    emit('notification-created', {
      type: '图书馆预约',
      title: `${item.seatId} 预约已取消`,
      content: `${item.date} ${item.startTime}-${item.endTime} 的预约已成功取消。`,
      link: 'library'
    })
    await Promise.all([searchSeats(), refreshHistory()])
    showFeedback(`${item.seatId} 的预约已取消。`, 'success')
  } catch (error) {
    showFeedback(toErrorMessage(error, '取消预约失败。'), 'error')
  } finally {
    cancellingId.value = null
  }
}

function currentUserId() {
  return props.currentUser.studentNo || props.currentUser.teacherNo || props.currentUser.username || props.currentUser.id || ''
}

function statusText(status) {
  return {
    reserved: '已预约',
    cancelled: '已取消',
    completed: '已完成',
    expired: '预约已结束'
  }[status] || status
}

function seatTitle(seat) {
  if (!seat.available) return `${seat.seatId} 已被占用`
  if (queryBlockReason.value) return queryBlockReason.value
  return seat.description || seat.seatId
}

function reservationQueryKey(value) {
  return [value.date, value.startTime, value.endTime, value.area].join('|')
}

function timeRangesOverlap(startTime, endTime, otherStartTime, otherEndTime) {
  return timeToMinutes(startTime) < timeToMinutes(otherEndTime) && timeToMinutes(endTime) > timeToMinutes(otherStartTime)
}

function timeToMinutes(value) {
  const [hour, minute] = String(value || '00:00').split(':').map(Number)
  return hour * 60 + minute
}

function isQueryStartPast() {
  if (query.date !== today) return query.date < today
  const now = new Date()
  return timeToMinutes(query.startTime) <= now.getHours() * 60 + now.getMinutes()
}

function createInitialReservationQuery() {
  const now = new Date()
  const nextHour = Math.max(8, now.getHours() + 1)
  if (nextHour >= 22) {
    const tomorrow = new Date(now)
    tomorrow.setDate(now.getDate() + 1)
    return { date: formatLocalDate(tomorrow), startTime: '09:00', endTime: '12:00', area: 'A' }
  }
  return {
    date: formatLocalDate(now),
    startTime: `${String(nextHour).padStart(2, '0')}:00`,
    endTime: `${String(Math.min(nextHour + 3, 22)).padStart(2, '0')}:00`,
    area: 'A'
  }
}

function showFeedback(text, type) {
  feedback.text = text
  feedback.type = type
}

function clearFeedback() {
  feedback.text = ''
  feedback.type = ''
}

function toErrorMessage(error, fallback) {
  const detail = String(error?.response?.data?.detail || '')
  if (error?.response?.status === 409) return detail || '该座位或当前时间段已被预约。'
  if (error?.response?.status === 404) return detail || '没有找到对应座位或用户。'
  return detail || fallback
}

function formatLocalDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
</script>
