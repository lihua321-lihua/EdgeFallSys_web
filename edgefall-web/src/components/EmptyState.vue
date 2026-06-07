<template>
  <div class="empty-state">
    <div class="empty-icon">{{ icon }}</div>
    <p>{{ text }}</p>
  </div>
</template>

<script setup>
/**
 * 空状态组件 - 无数据时的占位提示
 */
defineProps({
  icon: { type: String, default: '☕' },
  text: { type: String, default: '暂无数据' },
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl) 0;
  color: var(--color-text-light);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-sm);
}

p {
  font-size: var(--font-size-base);
  margin: 0;
}
</style>
