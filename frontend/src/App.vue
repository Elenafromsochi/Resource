<template>
  <div class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Telegram Channel Manager</p>
        <h1>Channel management</h1>
        <p class="subtitle">
          Add, delete, and review channels from one place.
        </p>
      </div>
      <div class="api-pill">API: {{ apiBase }}</div>
    </header>

    <section class="card">
      <h2>Add a channel</h2>
      <form class="form" @submit.prevent="createChannel">
        <label>
          Username or link
          <input
            v-model="form.username"
            placeholder="@channel or https://t.me/channel"
            required
          />
        </label>
        <label>
          Name (optional)
          <input v-model="form.name" placeholder="Channel name" />
        </label>
        <button type="submit" :disabled="loading">Add</button>
      </form>
      <p class="hint">
        If TELEGRAM_API_ID and TELEGRAM_API_HASH are configured, the server
        will resolve details via Telethon.
      </p>
    </section>

    <section class="card">
      <div class="card-header">
        <div>
          <h2>Channel list</h2>
          <p class="muted">Total: {{ channels.length }}</p>
        </div>
        <button type="button" class="secondary" @click="fetchChannels">
          Refresh
        </button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else>
        <ul v-if="channels.length" class="channel-list">
          <li v-for="channel in channels" :key="channel.id">
            <div class="channel-info">
              <strong>{{ channel.name }}</strong>
              <span class="meta">@{{ channel.username }}</span>
            </div>
            <button type="button" class="danger" @click="deleteChannel(channel.id)">
              Delete
            </button>
          </li>
        </ul>
        <p v-else class="empty">No channels yet.</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const channels = ref([]);
const loading = ref(false);
const error = ref("");
const form = ref({
  username: "",
  name: "",
});

const fetchChannels = async () => {
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(`${apiBase}/api/channels`);
    if (!response.ok) {
      throw new Error("Unable to load channels.");
    }
    const data = await response.json();
    channels.value = data.items || [];
  } catch (err) {
    error.value = err.message || "Load error.";
  } finally {
    loading.value = false;
  }
};

const createChannel = async () => {
  if (!form.value.username.trim()) {
    error.value = "Channel username is required.";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(`${apiBase}/api/channels`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: form.value.username,
        name: form.value.name || null,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to add channel.");
    }

    form.value = { username: "", name: "" };
    await fetchChannels();
  } catch (err) {
    error.value = err.message || "Create error.";
  } finally {
    loading.value = false;
  }
};

const deleteChannel = async (id) => {
  const confirmed = window.confirm("Delete this channel?");
  if (!confirmed) {
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(`${apiBase}/api/channels/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to delete channel.");
    }
    await fetchChannels();
  } catch (err) {
    error.value = err.message || "Delete error.";
  } finally {
    loading.value = false;
  }
};

onMounted(fetchChannels);
</script>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.hero {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.eyebrow {
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.12em;
  color: #6b7280;
  margin: 0 0 8px;
}

.subtitle {
  margin: 8px 0 0;
  color: #4b5563;
}

.api-pill {
  align-self: flex-start;
  background: #111827;
  color: #f9fafb;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12px;
}

.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  margin-bottom: 20px;
}

.form {
  display: grid;
  gap: 16px;
  margin-top: 12px;
}

label {
  display: grid;
  gap: 8px;
  font-size: 14px;
  color: #374151;
}

input {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
}

button {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary {
  background: #e5e7eb;
  color: #111827;
}

.danger {
  background: #ef4444;
}

.hint {
  margin-top: 12px;
  color: #6b7280;
  font-size: 13px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.muted {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.channel-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}

.channel-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.channel-info {
  display: grid;
  gap: 4px;
}

.meta {
  font-size: 13px;
  color: #6b7280;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  padding: 10px 12px;
  border-radius: 10px;
  margin-bottom: 12px;
}

.loading {
  color: #6b7280;
}

.empty {
  color: #6b7280;
  margin: 0;
}

@media (min-width: 768px) {
  .hero {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
