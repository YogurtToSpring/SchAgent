<template>
  <main class="login-page">
    <section class="login-hero">
      <div class="brand-mark large">CF</div>
      <h1>CampusFlow 校园智能服务平台</h1>
      <p>模拟学校信息平台，把班级、课表、天气和智能体助手放在同一个业务系统里。</p>
    </section>

    <section class="login-panel" aria-label="登录面板">
      <div>
        <h2>{{ mode === 'login' ? '登录平台' : '注册账号' }}</h2>
        <p>{{ mode === 'login' ? '请选择身份并输入账号密码。后端不可用时仍可使用演示账号。' : '填写基础身份信息，注册成功后会自动进入平台。' }}</p>
      </div>

      <div class="auth-tabs" role="tablist" aria-label="登录注册切换">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button type="button" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
      </div>

      <div v-if="mode === 'login'" class="demo-accounts">
        <button type="button" @click="fillAccount('teacher')">
          <span>教师管理员</span>
          <small>123 / 123456</small>
        </button>
        <button type="button" @click="fillAccount('student')">
          <span>普通学生</span>
          <small>2024001 / 123456</small>
        </button>
        <button type="button" @click="fillAccount('admin')">
          <span>系统管理员</span>
          <small>123456 / 123456</small>
        </button>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <label>
          身份
          <select v-model="role">
            <option value="teacher">教师管理员</option>
            <option value="student">普通学生</option>
            <option value="admin">系统管理员</option>
          </select>
        </label>
        <label v-if="mode === 'register'">
          姓名
          <input v-model="name" autocomplete="name" placeholder="请输入真实姓名" />
        </label>
        <label>
          账号
          <input v-model="username" autocomplete="username" placeholder="学号 / 教师编号 / 管理员编号" />
        </label>
        <label v-if="mode === 'register' && role === 'student'">
          班级
          <input v-model="className" placeholder="例如 弘毅班" />
        </label>
        <label>
          密码
          <input
            v-model="password"
            autocomplete="current-password"
            placeholder="123456"
            type="password"
          />
        </label>

        <p v-if="error" class="form-error">{{ error }}</p>

        <button class="primary-action" type="submit" :disabled="loading">
          {{ loading ? processingText : submitText }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { demoUsers } from '../data/platformData'
import { loginPlatformUser, registerPlatformUser } from '../api/platform'

const emit = defineEmits(['login'])

const mode = ref('login')
const role = ref('teacher')
const name = ref('')
const username = ref('123')
const password = ref('123456')
const className = ref('弘毅班')
const error = ref('')
const loading = ref(false)
const submitText = computed(() => (mode.value === 'login' ? '进入平台' : '注册并进入'))
const processingText = computed(() => (mode.value === 'login' ? '正在登录...' : '正在注册...'))

function switchMode(nextMode) {
  mode.value = nextMode
  error.value = ''
  if (nextMode === 'register') {
    password.value = ''
  } else {
    password.value = '123456'
  }
}

function fillAccount(nextRole) {
  role.value = nextRole
  const accounts = {
    teacher: '123',
    student: '2024001',
    admin: '123456'
  }
  username.value = accounts[nextRole]
  password.value = '123456'
  error.value = ''
}

async function submit() {
  if (!username.value.trim() || !password.value) {
    error.value = '请输入账号和密码。'
    return
  }
  if (mode.value === 'register' && !name.value.trim()) {
    error.value = '请输入姓名。'
    return
  }
  if (mode.value === 'register' && role.value === 'student' && !className.value.trim()) {
    error.value = '请输入学生班级。'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const user = mode.value === 'login'
      ? await loginPlatformUser({
          role: role.value,
          username: username.value,
          password: password.value
        })
      : await registerPlatformUser({
          role: role.value,
          name: name.value,
          username: username.value,
          password: password.value,
          className: className.value
        })
    emit('login', user)
  } catch (err) {
    if (mode.value === 'register') {
      error.value = '注册失败，请确认账号没有被占用，或后端服务已启动。'
      return
    }

    const fallbackUser = demoUsers.find(
      item => item.username === username.value.trim() && item.password === password.value
    )

    if (fallbackUser) {
      emit('login', { ...fallbackUser })
      return
    }

    error.value = '登录失败，请确认身份、账号和密码是否正确。'
  } finally {
    loading.value = false
  }
}
</script>
