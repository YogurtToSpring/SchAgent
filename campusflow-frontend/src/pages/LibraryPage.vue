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
        <strong>{{ availableCount }}</strong>
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
          </div>
        </div>

        <div v-if="loading" class="empty-state">正在查询座位...</div>
        <div v-else-if="!seats.length" class="empty-state">当前条件下没有座位数据</div>
        <div v-else class="seat-grid library-seat-grid">
          <button
            v-for="seat in visibleSeats"
            :key="seat.seatId"
            type="button"
            class="seat-item"
            :class="[seat.status, { selected: selectedSeat?.seatId === seat.seatId }]"
            :disabled="!seat.available"
            :title="seat.description || seat.seatId"
            @click="selectedSeat = seat"
          >
            <strong>{{ seat.seatId }}</strong>
            <span>{{ seat.floor }}楼 · {{ seat.area }}区</span>
          </button>
        </div>

        <button
          v-if="visibleSeats.length < seats.length"
          class="ghost-action load-more-action"
          type="button"
          @click="visibleLimit += 48"
        >
          显示更多（剩余 {{ seats.length - visibleSeats.length }} 个）
        </button>
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
import { RefreshCw, Search, X } from 'lucide-vue-next'
import {
  cancelLibraryReservation,
  loadLibraryAvailability,
  loadLibraryReservations,
  refreshLibraryReservationStatuses,
  reserveLibrarySeat
} from '../api/platform'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['add-todo', 'reservations-updated'])

const today = formatLocalDate(new Date())
const allTimes = Array.from({ length: 15 }, (_, index) => `${String(index + 8).padStart(2, '0')}:00`)
const query = reactive({
  date: today,
  startTime: '09:00',
  endTime: '12:00',
  area: 'A'
})
const seats = ref([])
const reservations = ref([])
const selectedSeat = ref(null)
const loading = ref(false)
const historyLoading = ref(false)
const submitting = ref(false)
const cancellingId = ref(null)
const visibleLimit = ref(48)
const feedback = reactive({ text: '', type: '' })

const startTimes = computed(() => allTimes.slice(0, -1))
const endTimes = computed(() => allTimes.filter(time => time > query.startTime))
const visibleSeats = computed(() => seats.value.slice(0, visibleLimit.value))
const availableCount = computed(() => seats.value.filter(seat => seat.available).length)
const unavailableCount = computed(() => seats.value.filter(seat => !seat.available).length)
const activeReservationCount = computed(() => reservations.value.filter(item => item.status === 'reserved').length)

watch(
  () => query.startTime,
  () => {
    if (query.endTime <= query.startTime) {
      query.endTime = endTimes.value[0] || '22:00'
    }
  }
)

onMounted(refreshAll)

async function refreshAll() {
  await Promise.allSettled([searchSeats(), refreshHistory()])
}

async function searchSeats() {
  loading.value = true
  selectedSeat.value = null
  visibleLimit.value = 48
  clearFeedback()
  try {
    const result = await loadLibraryAvailability(query)
    seats.value = result.seats
  } catch (error) {
    seats.value = []
    showFeedback(toErrorMessage(error, '座位查询失败，请确认后端图书馆接口可用。'), 'error')
  } finally {
    loading.value = false
  }
}

async function refreshHistory() {
  const userId = currentUserId()
  if (!userId) return
  historyLoading.value = true
  try {
    await refreshLibraryReservationStatuses().catch(() => null)
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
    await Promise.all([searchSeats(), refreshHistory()])
    showFeedback(`${seatId} 预约成功。`, 'success')
  } catch (error) {
    showFeedback(toErrorMessage(error, '预约失败，请稍后重试。'), 'error')
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
    completed: '已完成'
  }[status] || status
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
