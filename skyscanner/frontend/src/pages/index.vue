<template>
  <div class="landing">
    <v-progress-circular
      indeterminate
      color="primary"
      size="40"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  void router.replace('/events')
})
</script>

<style scoped>
.landing {
  display: flex;
  align-items: center;
  justify-content: center;
  min-block-size: 100vh;
}
</style>
