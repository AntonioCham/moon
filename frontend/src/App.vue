<template>
  <div class="shell">
    <main v-if="loading" class="panel centered">
      <p>正在讀取遊戲資料...</p>
    </main>

    <LoginView
      v-else-if="!session.token"
      v-model:passkey="loginForm.passkey"
      :flash-message="flash.message"
      :flash-type="flash.type"
      :submitting="submitting"
      @submit="login"
    />

    <AdminView
      v-else-if="session.user.isAdmin"
      v-model:admin-act="adminForm.currentAct"
      :current-act="session.currentAct"
      :flash-message="flash.message"
      :flash-type="flash.type"
      :submitting="submitting"
      @logout="logout"
      @update-act="updateAct"
    />

    <PlayerView
      v-else
      v-model:active-tab="activeTab"
      v-model:selected-script-act="selectedScriptAct"
      v-model:web-query="webForm.query"
      v-model:twitter-username="twitterForm.username"
      v-model:chat-phone="chatForm.phone"
      v-model:chat-message="chatForm.message"
      :active-contact-name="activeContactName"
      :active-tab-label="activeTabLabel"
      :chat-messages="chatMessages"
      :contacts="playerData.contacts"
      :current-act="session.currentAct"
      :flash-message="flash.message"
      :flash-type="flash.type"
      :selected-script="selectedScript"
      :scripts="playerData.scripts"
      :submitting="submitting"
      :tabs="tabs"
      :twitter-results="twitterResults"
      :twitter-searched="twitterSearched"
      :web-results="webResults"
      :web-searched="webSearched"
      :has-active-chat="hasActiveChat"
      :is-chat-connected="isChatConnected"
      :is-chat-call-ready="isChatCallReady"
      :is-chat-phone-locked="isChatConnected"
      @connect-chat="connectChat"
      @logout="logout"
      @end-chat="endChat"
      @search-twitter="searchTwitter"
      @search-web="searchWeb"
      @send-chat="sendChat"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import AdminView from "./components/AdminView.vue";
import LoginView from "./components/LoginView.vue";
import PlayerView from "./components/PlayerView.vue";
import { api } from "./composables/useApi";

const storageKey = "moon-knife-session-token";
const loading = ref(true);
const submitting = ref(false);
const activeTab = ref("script");
const flash = reactive({ message: "", type: "info" });
const session = reactive({
  token: localStorage.getItem(storageKey) || "",
  user: { roleName: "", isAdmin: false },
  currentAct: 1,
});

const loginForm = reactive({ passkey: "" });
const adminForm = reactive({ currentAct: 1 });
const webForm = reactive({ query: "" });
const twitterForm = reactive({ username: "" });
const chatForm = reactive({ phone: "", message: "" });
const playerData = reactive({ scripts: [], contacts: [] });
const webResults = ref([]);
const twitterResults = ref([]);
const webSearched = ref(false);
const twitterSearched = ref(false);
const chatMessages = ref([]);
const selectedScriptAct = ref(1);
const isChatConnected = ref(false);

const tabs = [
  { key: "script", label: "劇本" },
  { key: "web", label: "搜尋" },
  { key: "twitter", label: "貼文" },
  { key: "chat", label: "電話" },
];

const activeTabLabel = computed(() => {
  const current = tabs.find((tab) => tab.key === activeTab.value);
  return current ? current.label : "";
});

const activeContactName = computed(() => {
  if (!isChatConnected.value) {
    return "WhatsApp";
  }
  const contact = playerData.contacts.find((item) => item.phone === chatForm.phone);
  return contact ? contact.name : "未知聯絡人";
});

const selectedScript = computed(() => {
  return playerData.scripts.find((script) => script.act === selectedScriptAct.value) || null;
});

const hasActiveChat = computed(() => chatMessages.value.length > 0);
const isChatCallReady = computed(() => chatForm.phone.trim().length > 0);

function setFlash(message, type = "info") {
  flash.message = message;
  flash.type = type;
}

async function restoreSession() {
  if (!session.token) {
    loading.value = false;
    return;
  }

  try {
    const data = await api("/api/session", { method: "GET" }, session.token);
    session.user = data.user;
    session.currentAct = data.currentAct;
    adminForm.currentAct = data.currentAct;
    if (!data.user.isAdmin) {
      await loadPlayerData();
    }
  } catch (error) {
    localStorage.removeItem(storageKey);
    session.token = "";
    setFlash("");
  } finally {
    loading.value = false;
  }
}

async function login() {
  submitting.value = true;
  setFlash("");
  try {
    const data = await api(
      "/api/login",
      {
        method: "POST",
        body: JSON.stringify(loginForm),
      },
      session.token,
    );
    session.token = data.token;
    session.user = data.user;
    session.currentAct = data.currentAct;
    adminForm.currentAct = data.currentAct;
    localStorage.setItem(storageKey, data.token);
    loginForm.passkey = "";
    if (data.user.isAdmin) {
      setFlash("");
    } else {
      await loadPlayerData();
      setFlash("");
    }
  } catch (error) {
    setFlash(error.message, "error");
  } finally {
    submitting.value = false;
  }
}

async function logout() {
  try {
    if (session.token) {
      await api("/api/logout", { method: "POST" }, session.token);
    }
  } catch (error) {
    console.error(error);
  }

  localStorage.removeItem(storageKey);
  session.token = "";
  session.user = { roleName: "", isAdmin: false };
  session.currentAct = 1;
  adminForm.currentAct = 1;
  playerData.scripts = [];
  playerData.contacts = [];
  webResults.value = [];
  twitterResults.value = [];
  chatMessages.value = [];
  chatForm.phone = "";
  chatForm.message = "";
  isChatConnected.value = false;
  selectedScriptAct.value = 1;
  activeTab.value = "script";
  setFlash("");
}

async function loadPlayerData() {
  const data = await api("/api/player/bootstrap", { method: "GET" }, session.token);
  session.currentAct = data.currentAct;
  playerData.scripts = data.scripts;
  playerData.contacts = data.contacts;
  selectedScriptAct.value = data.scripts.length > 0 ? data.scripts[data.scripts.length - 1].act : 1;
  endChat();
}

async function updateAct() {
  submitting.value = true;
  setFlash("");
  try {
    const data = await api(
      "/api/admin/current-act",
      {
        method: "POST",
        body: JSON.stringify({ current_act: adminForm.currentAct }),
      },
      session.token,
    );
    session.currentAct = data.currentAct;
    adminForm.currentAct = data.currentAct;
    setFlash(`${data.message}，目前為第 ${data.currentAct} 幕`, "success");
  } catch (error) {
    setFlash(error.message, "error");
  } finally {
    submitting.value = false;
  }
}

async function searchWeb() {
  submitting.value = true;
  setFlash("");
  try {
    const data = await api(
      "/api/player/search/web",
      {
        method: "POST",
        body: JSON.stringify({ query: webForm.query }),
      },
      session.token,
    );
    webResults.value = data.results;
    session.currentAct = data.currentAct;
    webSearched.value = true;
  } catch (error) {
    setFlash(error.message, "error");
  } finally {
    submitting.value = false;
  }
}

async function searchTwitter() {
  submitting.value = true;
  setFlash("");
  try {
    const username = encodeURIComponent(twitterForm.username);
    const data = await api(`/api/player/search/twitter?username=${username}`, { method: "GET" }, session.token);
    twitterResults.value = data.results;
    session.currentAct = data.currentAct;
    twitterSearched.value = true;
  } catch (error) {
    setFlash(error.message, "error");
  } finally {
    submitting.value = false;
  }
}

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function startChatHeader(contactName, phone) {
  chatMessages.value = [
    {
      id: createMessageId(),
      sender: "system",
      text: `${contactName} (${phone})`,
    },
  ];
}

function connectChat() {
  const normalizedPhone = chatForm.phone.trim();
  if (!normalizedPhone) {
    return;
  }
  const matchedContact = playerData.contacts.find((item) => item.phone === normalizedPhone);
  startChatHeader(matchedContact?.name || "未知聯絡人", normalizedPhone);
  isChatConnected.value = true;
}

function endChat() {
  chatMessages.value = [];
  chatForm.phone = "";
  chatForm.message = "";
  isChatConnected.value = false;
}

async function sendChat() {
  if (!isChatConnected.value || !chatForm.phone.trim() || !chatForm.message.trim()) {
    return;
  }

  const normalizedPhone = chatForm.phone.trim();
  const matchedContact = playerData.contacts.find((item) => item.phone === normalizedPhone);
  if (chatMessages.value.length === 0 || !chatMessages.value[0]?.text.includes(normalizedPhone)) {
    startChatHeader(matchedContact?.name || "未知聯絡人", normalizedPhone);
  }

  const text = chatForm.message.trim();
  chatMessages.value.push({
    id: createMessageId(),
    sender: "self",
    text,
  });
  chatForm.message = "";
  submitting.value = true;
  setFlash("");

  try {
    const data = await api(
      "/api/player/chat",
      {
        method: "POST",
        body: JSON.stringify({ phone: normalizedPhone, message: text }),
      },
      session.token,
    );
    session.currentAct = data.currentAct;
    await new Promise((resolve) => setTimeout(resolve, 550));
    chatMessages.value.push({
      id: createMessageId(),
      sender: "reply",
      text: data.reply,
    });
  } catch (error) {
    setFlash(error.message, "error");
  } finally {
    submitting.value = false;
  }
}

onMounted(restoreSession);
</script>
