<template>
  <main class="mobile-app-shell">
    <section class="phone-app-frame">
      <header class="app-topbar">
        <div class="act-pill">第 {{ currentAct }} 幕</div>
        <button class="ghost topbar-exit" @click="$emit('logout')">登出</button>
      </header>

      <div class="app-screen">
        <p v-if="flashMessage" :class="['flash', 'compact', flashType, 'screen-flash']">{{ flashMessage }}</p>

        <section v-if="activeTab === 'script'" class="app-page script-page">
          <div class="act-selector">
            <button
              v-for="script in scripts"
              :key="script.act"
              :class="['act-chip', { active: selectedScriptAct === script.act }]"
              @click="$emit('update:selectedScriptAct', script.act)"
            >
              第 {{ script.act }} 幕
            </button>
          </div>

          <div v-if="selectedScript" class="script-reader-body script-reader-body-full">
            <h3>{{ selectedScript.title }}</h3>
            <p>{{ selectedScript.content }}</p>
          </div>

          <p v-else class="muted center-muted">目前未有可閱讀劇本。</p>
        </section>

        <section v-else-if="activeTab === 'web'" class="app-page web-page">
          <div class="browser-shell browser-google">
            <div class="moon-search-brand">月光下的持刀者</div>
            <form class="search-form search-form-google" @submit.prevent="$emit('search-web')">
              <div class="search-input-wrap">
                <input
                  id="web-query"
                  :value="webQuery"
                  type="text"
                  placeholder="搜尋最多 3 個關鍵字，例如：花園 刀痕 晚宴"
                  @input="$emit('update:webQuery', $event.target.value)"
                />
                <button type="submit" class="search-icon-btn" :disabled="submitting" aria-label="搜尋">
                  <span>{{ submitting ? "…" : "⌕" }}</span>
                </button>
              </div>
            </form>
            <div class="results-scroll results-scroll-google">
              <article v-for="result in webResults" :key="result.url" class="google-result-card">
                <h3>{{ result.title }}</h3>
                <p>{{ result.snippet }}</p>
              </article>
              <p v-if="webSearched && webResults.length === 0" class="muted center-muted">目前已開放幕數內找不到相關結果。</p>
            </div>
          </div>
        </section>

        <section v-else-if="activeTab === 'twitter'" class="app-page twitter-page">
          <div class="browser-shell browser-twitter">
            <div class="twitter-brand-row">
              <div class="twitter-bird">t</div>
              <div class="twitter-wordmark">twitter</div>
            </div>
            <form class="search-form search-form-twitter" @submit.prevent="$emit('search-twitter')">
              <div class="search-input-wrap">
                <input
                  id="twitter-username"
                  :value="twitterUsername"
                  type="text"
                  placeholder="輸入使用者名稱，例如：moon_garden"
                  @input="$emit('update:twitterUsername', $event.target.value)"
                />
                <button type="submit" class="search-icon-btn" :disabled="submitting" aria-label="搜尋">
                  <span>{{ submitting ? "…" : "⌕" }}</span>
                </button>
              </div>
            </form>
          </div>
          <div class="results-scroll results-scroll-twitter">
            <article
              v-for="tweet in twitterResults"
              :key="`${tweet.username}-${tweet.posted_at}-${tweet.content}`"
              class="tweet-card tweet-card-a14"
            >
              <div class="tweet-head tweet-head-a14">
                <h3>{{ tweet.displayName || tweet.display_name }} <span>{{ tweet.postedAt || tweet.posted_at }}</span></h3>
              </div>
              <p>{{ tweet.content }}</p>
              <div v-if="tweet.replyContent || tweet.reply_content" class="tweet-reply-box">
                <p>Reply:</p>
                <div>{{ tweet.replyContent || tweet.reply_content }}</div>
              </div>
            </article>
            <p v-if="twitterSearched && twitterResults.length === 0" class="muted center-muted">這個帳號在目前幕數沒有公開內容。</p>
          </div>
        </section>

        <section v-else class="app-page whatsapp-page">
          <div class="chat-phone-header">
            <div class="chat-phone-titlebar">
              <div class="chat-contact-block">
                <h3>{{ activeContactName }}</h3>
                <input
                  id="chat-phone"
                  class="chat-phone-inline-input"
                  :value="chatPhone"
                  type="text"
                  placeholder="輸入號碼"
                  :readonly="isChatPhoneLocked"
                  @input="$emit('update:chatPhone', $event.target.value)"
                />
              </div>
              <button
                type="button"
                class="ghost chat-header-end"
                :class="{ hangup: isChatConnected }"
                :disabled="!isChatConnected && !isChatCallReady"
                @click="isChatConnected ? $emit('end-chat') : $emit('connect-chat')"
                :aria-label="isChatConnected ? '結束對話' : '開始對話'"
              >
                {{ isChatConnected ? "✕" : "✆" }}
              </button>
            </div>
          </div>

          <div v-if="isChatConnected" class="card chat-card phone-chat-card">
            <div class="chat-thread chat-thread-scrollable">
              <div
                v-for="message in chatMessages"
                :key="message.id"
                :class="['bubble', message.sender]"
              >
                {{ message.text }}
              </div>
            </div>

            <form class="chat-form chat-form-phone" @submit.prevent="$emit('send-chat')">
              <div class="message-input-wrap">
                <input
                  :value="chatMessage"
                  type="text"
                  placeholder="輸入問題，例如：花園、刀痕、圍巾"
                  @input="$emit('update:chatMessage', $event.target.value)"
                />
                <button type="submit" class="message-send-btn" :disabled="submitting || !chatPhone">
                  {{ submitting ? "…" : "➤" }}
                </button>
              </div>
            </form>
          </div>
          <p v-else class="chat-empty call-empty-state">請先輸入號碼，然後按右邊通話圖示開始對話。</p>
        </section>
      </div>

      <nav class="bottom-tabbar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['bottom-tab', { active: activeTab === tab.key }]"
          @click="$emit('update:activeTab', tab.key)"
        >
          <span>{{ tab.label }}</span>
        </button>
      </nav>
    </section>
  </main>
</template>

<script setup>
defineProps({
  activeContactName: { type: String, default: "WhatsApp 對話" },
  activeTab: { type: String, default: "script" },
  activeTabLabel: { type: String, default: "" },
  chatMessage: { type: String, default: "" },
  chatMessages: { type: Array, default: () => [] },
  chatPhone: { type: String, default: "" },
  contacts: { type: Array, default: () => [] },
  currentAct: { type: Number, default: 1 },
  flashMessage: { type: String, default: "" },
  flashType: { type: String, default: "info" },
  hasActiveChat: { type: Boolean, default: false },
  isChatCallReady: { type: Boolean, default: false },
  isChatConnected: { type: Boolean, default: false },
  isChatPhoneLocked: { type: Boolean, default: false },
  scripts: { type: Array, default: () => [] },
  selectedScript: { type: Object, default: null },
  selectedScriptAct: { type: Number, default: 1 },
  submitting: { type: Boolean, default: false },
  tabs: { type: Array, default: () => [] },
  twitterResults: { type: Array, default: () => [] },
  twitterSearched: { type: Boolean, default: false },
  twitterUsername: { type: String, default: "" },
  webQuery: { type: String, default: "" },
  webResults: { type: Array, default: () => [] },
  webSearched: { type: Boolean, default: false },
});

defineEmits([
  "connect-chat",
  "end-chat",
  "logout",
  "search-twitter",
  "search-web",
  "send-chat",
  "update:activeTab",
  "update:chatMessage",
  "update:chatPhone",
  "update:selectedScriptAct",
  "update:twitterUsername",
  "update:webQuery",
]);
</script>
