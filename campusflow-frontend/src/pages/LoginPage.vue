<template>
  <main class="login-page">
    <section class="login-hero">
      <div class="brand-mark large">CF</div>
      <h1>CampusFlow 校园智能服务平台</h1>
      <p>模拟学校信息平台，把班级、课表、天气和智能体助手放在同一个业务系统里。</p>
    </section>

    <section class="login-panel" aria-label="登录面板">
      <div>
        <h2>登录平台</h2>
        <p>请选择演示账号，也可以手动输入用户名和密码。</p>
      </div>

      <div class="demo-accounts">
        <button type="button" @click="fillAccount('teacher')">
          <span>教师管理员</span>
          <small>teacher / 123456</small>
        </button>
        <button type="button" @click="fillAccount('student')">
          <span>普通学生</span>
          <small>student / 123456</small>
        </button>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <label>
          用户名
          <input v-model="username" autocomplete="username" placeholder="teacher 或 student" />
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

        <button class="primary-action" type="submit">进入平台</button>
      </form>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { demoUsers } from '../data/platformData'

const emit = defineEmits(['login'])

const username = ref('teacher')
const password = ref('123456')
const error = ref('')

function fillAccount(role) {
  const user = demoUsers.find(item => item.role === role)
  username.value = user.username
  password.value = user.password
  error.value = ''
}

function submit() {
  const user = demoUsers.find(
    item => item.username === username.value.trim() && item.password === password.value
  )

  if (!user) {
    error.value = '用户名或密码不正确，请使用演示账号登录。'
    return
  }

  error.value = ''
  emit('login', { ...user })
}
</script>
