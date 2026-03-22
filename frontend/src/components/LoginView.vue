<template>
  <main class="mobile-app-shell">
    <section class="phone-app-frame static-phone-screen">
      <div class="static-screen-body">
        <div class="a1-entry-card">
          <h1 class="login-title">月光下的持刀者</h1>
          <form class="login-form a1-login-form" @submit.prevent="$emit('submit')">
            <div class="search-input-wrap login-input-wrap">
              <input
                id="passkey"
                :value="passkey"
                type="password"
                placeholder="輸入 passkey"
                autocomplete="off"
                @input="$emit('update:passkey', $event.target.value)"
              />
              <button type="submit" class="search-icon-btn login-enter-btn" :disabled="submitting" aria-label="進入">
                <span>{{ submitting ? "…" : "➜" }}</span>
              </button>
            </div>
          </form>
          <p v-if="flashMessage" :class="['flash', flashType]">{{ flashMessage }}</p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
defineProps({
  flashMessage: { type: String, default: "" },
  flashType: { type: String, default: "info" },
  passkey: { type: String, default: "" },
  submitting: { type: Boolean, default: false },
});

defineEmits(["submit", "update:passkey"]);
</script>
