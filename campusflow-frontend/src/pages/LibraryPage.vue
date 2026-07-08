<template>
  <section class="library-page module-page">
    <section class="content-panel library-toolbar">
      <div class="section-heading">
        <div>
          <h2>图书馆预约</h2>
          <p>选择日期、时段和馆区后预约可用座位。</p>
        </div>
      </div>
      <div class="reservation-controls">
        <input v-model="selectedDate" type="date" />
        <select v-model="selectedTime">
          <option>09:00-12:00</option>
          <option>14:00-17:00</option>
          <option>18:00-21:00</option>
        </select>
        <select v-model="selectedLibrary">
          <option value="">全部馆区</option>
          <option v-for="library in libraries" :key="library">{{ library }}</option>
        </select>
      </div>
    </section>

    <section class="module-grid two-columns">
      <section class="content-panel seat-map">
        <div class="section-heading">
          <div>
            <h2>可预约座位</h2>
            <p>{{ availableSeats.length }} 个座位可选</p>
          </div>
        </div>

        <div class="seat-grid">
          <button
            v-for="seat in filteredSeats"
            :key="seat.id"
            type="button"
            class="seat-item"
            :class="seat.status"
            :disabled="seat.status !== 'available'"
            @click="selectedSeat = seat"
          >
            <strong>{{ seat.seatNo }}</strong>
            <span>{{ seat.floor }} · {{ seat.area }}</span>
          </button>
        </div>
      </section>

      <aside class="content-panel reservation-panel">
        <div v-if="selectedSeat">
          <h2>{{ selectedSeat.library }}</h2>
          <p>{{ selectedSeat.floor }} {{ selectedSeat.area }} {{ selectedSeat.seatNo }}</p>
          <dl class="detail-list">
            <div>
              <dt>日期</dt>
              <dd>{{ selectedDate || '今天' }}</dd>
            </div>
            <div>
              <dt>时间</dt>
              <dd>{{ selectedTime }}</dd>
            </div>
          </dl>
          <button class="primary-action" type="button" @click="reserveSeat">确认预约</button>
        </div>

        <div v-else>
          <h2>我的预约</h2>
          <article v-for="item in reservations" :key="item.id" class="reservation-item">
            <strong>{{ item.target }}</strong>
            <span>{{ item.time }}</span>
          </article>
          <div v-if="!reservations.length" class="empty-state compact">暂无预约</div>
        </div>
      </aside>
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  seats: {
    type: Array,
    required: true
  },
  reservations: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['reserve-seat', 'add-todo'])

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const selectedTime = ref('14:00-17:00')
const selectedLibrary = ref('')
const selectedSeat = ref(null)

const libraries = computed(() => [...new Set(props.seats.map(item => item.library))])

const filteredSeats = computed(() => {
  return props.seats.filter(item => {
    const libraryMatched = !selectedLibrary.value || item.library === selectedLibrary.value
    const timeMatched = item.time === selectedTime.value
    return libraryMatched && timeMatched
  })
})

const availableSeats = computed(() => filteredSeats.value.filter(item => item.status === 'available'))

function reserveSeat() {
  if (!selectedSeat.value) return
  const reservation = {
    type: '座位',
    target: `${selectedSeat.value.library} ${selectedSeat.value.seatNo}`,
    time: `${selectedDate.value} ${selectedTime.value}`,
    status: 'active'
  }
  emit('reserve-seat', reservation)
  emit('add-todo', {
    title: `图书馆预约：${reservation.target}`,
    dueDate: reservation.time,
    category: '图书馆',
    source: '预约',
    priority: 'medium',
    note: '预约开始前确认到馆。'
  })
  selectedSeat.value = null
}
</script>
