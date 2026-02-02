<template>
  <div class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Telegram Channel Manager</p>
        <h1>Channel management</h1>
        <p class="subtitle">
          Add, delete, and review channels and hashtags in one place.
        </p>
      </div>
      <div class="api-pill">API: {{ apiBase }}</div>
    </header>

    <div class="grid">
      <section class="card">
        <h2>Add a channel</h2>
        <form class="form" @submit.prevent="searchChannels">
          <label>
            Search in Telegram
            <input
              v-model="channelSearch.query"
              placeholder="Keywords, title, description"
            />
          </label>
          <button type="submit" class="secondary" :disabled="channelSearchLoading">
            Search
          </button>
        </form>
        <div v-if="channelSearchError" class="error">{{ channelSearchError }}</div>
        <div v-if="channelSearchLoading" class="loading">Searching...</div>
        <div v-else>
          <ul v-if="channelSearchResults.length" class="channel-list">
            <li v-for="channel in channelSearchResults" :key="channel.id">
              <div class="channel-info">
                <strong>{{ channel.title || channel.username || channel.id }}</strong>
                <span v-if="channel.username" class="meta">@{{ channel.username }}</span>
                <span v-else class="meta">ID: {{ channel.id }}</span>
                <span v-if="channel.description" class="meta">{{ channel.description }}</span>
              </div>
              <button
                type="button"
                class="secondary"
                :disabled="!channel.username || channelLoading"
                @click="addFromSearch(channel)"
              >
                Add
              </button>
            </li>
          </ul>
          <p v-else-if="channelSearchHasRun && !channelSearchError" class="empty">
            No channels found.
          </p>
        </div>

        <form class="form" @submit.prevent="createChannel">
          <label>
            Username or link
            <input
              v-model="channelForm.username"
              placeholder="@channel or https://t.me/channel"
              required
            />
          </label>
          <button type="submit" :disabled="channelLoading">Add</button>
        </form>
        <p class="hint">
          If TELEGRAM_API_ID and TELEGRAM_API_HASH are configured, the server
          will resolve details via Telethon.
        </p>
      </section>

      <section class="card">
        <h2>Add a hashtag</h2>
        <form class="form" @submit.prevent="createHashtag">
          <label>
            Hashtag
            <input v-model="hashtagForm.tag" placeholder="#news" required />
          </label>
          <button type="submit" :disabled="hashtagLoading">Add</button>
        </form>
        <p class="hint">
          Hashtags must start with #, use lowercase, and contain no spaces.
        </p>
      </section>
    </div>

    <div class="grid">
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

        <div v-if="channelError" class="error">{{ channelError }}</div>
        <div v-if="channelLoading" class="loading">Loading...</div>
        <div v-else>
          <ul v-if="channels.length" class="channel-list">
            <li v-for="channel in channels" :key="channel.id">
              <div class="channel-info">
                <strong>{{ channel.title || channel.username || channel.id }}</strong>
                <span v-if="channel.username" class="meta">@{{ channel.username }}</span>
                <span v-else class="meta">ID: {{ channel.id }}</span>
              </div>
              <button type="button" class="danger" @click="deleteChannel(channel.id)">
                Delete
              </button>
            </li>
          </ul>
          <p v-else class="empty">No channels yet.</p>
        </div>
      </section>

      <section class="card">
        <div class="card-header">
          <div>
            <h2>Hashtags</h2>
            <p class="muted">Total: {{ hashtagsTotal }}</p>
          </div>
          <button type="button" class="secondary" @click="fetchHashtags">
            Refresh
          </button>
        </div>

        <div v-if="hashtagError" class="error">{{ hashtagError }}</div>
        <div v-if="hashtagLoading" class="loading">Loading...</div>
        <div v-else>
          <ul v-if="hashtags.length" class="channel-list">
            <li v-for="tag in hashtags" :key="tag.id">
              <div class="channel-info">
                <strong>{{ tag.tag }}</strong>
              </div>
              <button type="button" class="danger" @click="deleteHashtag(tag.id)">
                Delete
              </button>
            </li>
          </ul>
          <p v-else class="empty">No hashtags yet.</p>
          <div class="pagination">
            <button
              type="button"
              class="secondary"
              :disabled="!hasPreviousHashtagPage"
              @click="prevHashtags"
            >
              Prev
            </button>
            <span class="pagination-info">
              Page {{ hashtagPage }} of {{ hashtagTotalPages }}
            </span>
            <button
              type="button"
              class="secondary"
              :disabled="!hasNextHashtagPage"
              @click="nextHashtags"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const channels = ref([]);
const channelLoading = ref(false);
const channelError = ref("");
const channelForm = ref({
  username: "",
});
const channelSearch = ref({
  query: "",
});
const channelSearchResults = ref([]);
const channelSearchLoading = ref(false);
const channelSearchError = ref("");
const channelSearchHasRun = ref(false);

const hashtags = ref([]);
const hashtagsTotal = ref(0);
const hashtagLoading = ref(false);
const hashtagError = ref("");
const hashtagForm = ref({
  tag: "",
});
const hashtagLimit = 12;
const hashtagOffset = ref(0);

const hashtagPage = computed(() => Math.floor(hashtagOffset.value / hashtagLimit) + 1);
const hashtagTotalPages = computed(() =>
  Math.max(1, Math.ceil(hashtagsTotal.value / hashtagLimit))
);
const hasPreviousHashtagPage = computed(() => hashtagOffset.value > 0);
const hasNextHashtagPage = computed(
  () => hashtagOffset.value + hashtagLimit < hashtagsTotal.value
);

const fetchChannels = async () => {
  channelLoading.value = true;
  channelError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/channels`);
    if (!response.ok) {
      throw new Error("Unable to load channels.");
    }
    const data = await response.json();
    channels.value = data.items || [];
  } catch (err) {
    channelError.value = err.message || "Load error.";
  } finally {
    channelLoading.value = false;
  }
};

const createChannel = async (overrideUsername) => {
  const hasOverride = typeof overrideUsername === "string";
  const username = hasOverride ? overrideUsername : channelForm.value.username;
  if (!username.trim()) {
    channelError.value = "Channel username is required.";
    return;
  }
  channelLoading.value = true;
  channelError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/channels`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to add channel.");
    }

    if (!hasOverride) {
      channelForm.value = { username: "" };
    }
    await fetchChannels();
  } catch (err) {
    channelError.value = err.message || "Create error.";
  } finally {
    channelLoading.value = false;
  }
};

const searchChannels = async () => {
  const query = channelSearch.value.query.trim();
  if (!query) {
    channelSearchError.value = "Search query is required.";
    channelSearchResults.value = [];
    channelSearchHasRun.value = false;
    return;
  }
  channelSearchLoading.value = true;
  channelSearchError.value = "";
  try {
    const response = await fetch(
      `${apiBase}/api/channels/search?q=${encodeURIComponent(query)}`
    );
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to search channels.");
    }
    const data = await response.json();
    channelSearchResults.value = data.items || [];
  } catch (err) {
    channelSearchError.value = err.message || "Search error.";
  } finally {
    channelSearchLoading.value = false;
    channelSearchHasRun.value = true;
  }
};

const addFromSearch = async (channel) => {
  if (!channel.username) {
    channelError.value = "Selected channel has no username.";
    return;
  }
  await createChannel(channel.username);
};

const deleteChannel = async (id) => {
  const confirmed = window.confirm("Delete this channel?");
  if (!confirmed) {
    return;
  }
  channelLoading.value = true;
  channelError.value = "";
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
    channelError.value = err.message || "Delete error.";
  } finally {
    channelLoading.value = false;
  }
};

const fetchHashtags = async () => {
  hashtagLoading.value = true;
  hashtagError.value = "";
  try {
    const response = await fetch(
      `${apiBase}/api/hashtags?limit=${hashtagLimit}&offset=${hashtagOffset.value}`
    );
    if (!response.ok) {
      throw new Error("Unable to load hashtags.");
    }
    const data = await response.json();
    hashtags.value = data.items || [];
    hashtagsTotal.value = data.total || 0;
  } catch (err) {
    hashtagError.value = err.message || "Load error.";
  } finally {
    hashtagLoading.value = false;
  }
};

const createHashtag = async () => {
  if (!hashtagForm.value.tag.trim()) {
    hashtagError.value = "Hashtag is required.";
    return;
  }
  hashtagLoading.value = true;
  hashtagError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/hashtags`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tag: hashtagForm.value.tag,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to add hashtag.");
    }

    hashtagForm.value = { tag: "" };
    hashtagOffset.value = 0;
    await fetchHashtags();
  } catch (err) {
    hashtagError.value = err.message || "Create error.";
  } finally {
    hashtagLoading.value = false;
  }
};

const deleteHashtag = async (id) => {
  const confirmed = window.confirm("Delete this hashtag?");
  if (!confirmed) {
    return;
  }
  hashtagLoading.value = true;
  hashtagError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/hashtags/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to delete hashtag.");
    }
    await fetchHashtags();
  } catch (err) {
    hashtagError.value = err.message || "Delete error.";
  } finally {
    hashtagLoading.value = false;
  }
};

const prevHashtags = async () => {
  if (!hasPreviousHashtagPage.value) {
    return;
  }
  hashtagOffset.value = Math.max(0, hashtagOffset.value - hashtagLimit);
  await fetchHashtags();
};

const nextHashtags = async () => {
  if (!hasNextHashtagPage.value) {
    return;
  }
  hashtagOffset.value += hashtagLimit;
  await fetchHashtags();
};

onMounted(() => {
  fetchChannels();
  fetchHashtags();
});
</script>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 16px 32px;
  display: grid;
  gap: 16px;
}

.hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.eyebrow {
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.12em;
  color: #6b7280;
  margin: 0 0 4px;
}

.subtitle {
  margin: 6px 0 0;
  color: #4b5563;
  font-size: 14px;
}

.api-pill {
  align-self: flex-start;
  background: #111827;
  color: #f9fafb;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
}

.grid {
  display: grid;
  gap: 12px;
}

.card {
  background: #ffffff;
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.card h2 {
  margin: 0;
  font-size: 16px;
}

.form {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

label {
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: #374151;
}

input {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
}

button {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
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
  margin-top: 8px;
  color: #6b7280;
  font-size: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  gap: 8px;
}

.muted {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.channel-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.channel-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  gap: 12px;
}

.channel-info {
  display: grid;
  gap: 2px;
}

.meta {
  font-size: 12px;
  color: #6b7280;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.loading {
  color: #6b7280;
  font-size: 12px;
}

.empty {
  color: #6b7280;
  margin: 0;
  font-size: 12px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
}

.pagination-info {
  font-size: 12px;
  color: #6b7280;
}

@media (min-width: 900px) {
  .hero {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }

  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
