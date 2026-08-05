<template>
  <div class="not-found">
    <div class="error-code">404</div>
    <p>页面不存在</p>
    <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  color: var(--color-text-secondary);
}
.error-code {
  font-size: 96px;
  font-weight: 700;
  color: var(--color-primary);
  opacity: 0.3;
}
p {
  font-size: var(--font-size-lg);
  margin: 16px 0 32px;
}
</style>