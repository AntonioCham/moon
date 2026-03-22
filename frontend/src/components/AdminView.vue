<template>
  <main class="mobile-app-shell">
    <section class="phone-app-frame static-phone-screen">
      <div class="static-screen-body">
        <div class="admin-phone-card">
          <div class="admin-phone-head">
            <div class="act-pill">第 {{ currentAct }} 幕</div>
            <button class="ghost topbar-exit" @click="$emit('logout')">返回</button>
          </div>

          <form class="admin-phone-form" @submit.prevent="$emit('update-act')">
            <input
              id="act-input"
              :value="adminAct"
              type="number"
              min="1"
              @input="$emit('update:adminAct', Number($event.target.value))"
            />
            <button type="submit" :disabled="submitting">
              {{ submitting ? "更新中..." : "更新幕數" }}
            </button>
          </form>

          <p v-if="flashMessage" :class="['flash', flashType]">{{ flashMessage }}</p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
defineProps({
  adminAct: { type: Number, default: 1 },
  currentAct: { type: Number, default: 1 },
  flashMessage: { type: String, default: "" },
  flashType: { type: String, default: "info" },
  submitting: { type: Boolean, default: false },
});

defineEmits(["logout", "update-act", "update:adminAct"]);
</script>
