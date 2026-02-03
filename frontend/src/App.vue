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
      <section class="card span-2">
        <div class="card-header">
          <div>
            <h2>Prompt management</h2>
            <p class="muted">Create and maintain system prompts for analysis.</p>
          </div>
          <button type="button" class="secondary" @click="fetchPrompts">
            Refresh
          </button>
        </div>

        <div v-if="promptError" class="error">{{ promptError }}</div>
        <div v-if="promptLoading" class="loading">Loading...</div>
        <div v-else class="split">
          <div class="panel">
            <h3>Create prompt</h3>
            <form class="form" @submit.prevent="createPrompt">
              <label>
                Prompt name
                <input
                  v-model="promptForm.name"
                  placeholder="Weekly summary"
                  required
                />
              </label>
              <label>
                System prompt content
                <textarea
                  v-model="promptForm.content"
                  rows="5"
                  placeholder="Write the full system instruction."
                  required
                ></textarea>
              </label>
              <button type="submit" :disabled="promptLoading">Add prompt</button>
            </form>
          </div>
          <div class="panel">
            <h3>Existing prompts</h3>
            <ul v-if="prompts.length" class="prompt-list">
              <li v-for="prompt in prompts" :key="prompt.id">
                <div class="prompt-info">
                  <div class="prompt-title">
                    <strong>{{ prompt.name }}</strong>
                    <span class="meta">#{{ prompt.id }}</span>
                  </div>
                  <p class="prompt-content">{{ prompt.content }}</p>
                </div>
                <div class="prompt-actions">
                  <button
                    type="button"
                    class="secondary"
                    @click="selectPrompt(prompt.id)"
                  >
                    Use
                  </button>
                  <button
                    type="button"
                    class="secondary"
                    @click="startEditPrompt(prompt)"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    class="icon-button danger"
                    @click="deletePrompt(prompt.id)"
                    aria-label="Delete prompt"
                    title="Delete"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path
                        d="M9 3h6l1 2h5v2H3V5h5l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9z"
                      />
                    </svg>
                  </button>
                </div>
                <div v-if="promptEditingId === prompt.id" class="prompt-edit">
                  <form class="form" @submit.prevent="updatePrompt">
                    <label>
                      Prompt name
                      <input v-model="promptEditForm.name" required />
                    </label>
                    <label>
                  System prompt content
                      <textarea v-model="promptEditForm.content" rows="4" required></textarea>
                    </label>
                    <div class="inline-actions">
                      <button type="submit" :disabled="promptLoading">Save</button>
                      <button
                        type="button"
                        class="secondary"
                        @click="cancelEditPrompt"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              </li>
            </ul>
            <p v-else class="empty">No prompts yet.</p>
          </div>
        </div>
      </section>
    </div>

    <div class="grid">
      <section class="card span-2">
        <div class="card-header">
          <div>
            <h2>Hashtag analysis</h2>
            <p class="muted">
              Run analysis, review hashtags, and add selected ones to the database.
            </p>
          </div>
        </div>

        <form class="form form-grid" @submit.prevent="runAnalysis">
          <label>
            Prompt
            <select v-model="analysisForm.promptId" :disabled="!prompts.length" required>
              <option value="" disabled>Select a prompt</option>
              <option
                v-for="prompt in prompts"
                :key="prompt.id"
                :value="String(prompt.id)"
              >
                {{ prompt.name }}
              </option>
            </select>
          </label>
          <label>
            Start date
            <div class="date-field">
              <input type="datetime-local" v-model="analysisStartPicker" required />
            </div>
          </label>
          <label>
            End date
            <div class="date-field">
              <input type="datetime-local" v-model="analysisEndPicker" required />
            </div>
          </label>
          <label>
            Max messages per channel
            <input
              type="number"
              min="1"
              v-model="analysisForm.maxMessagesPerChannel"
              placeholder="Optional"
            />
          </label>
          <label class="toggle">
            <input type="checkbox" v-model="analysisForm.limitToChannels" />
            Limit to selected channels
          </label>
          <button type="submit" :disabled="analysisLoading || !prompts.length">
            Run analysis
          </button>
        </form>

        <div class="channel-selector" :class="{ disabled: !analysisForm.limitToChannels }">
          <div class="selector-header">
            <div>
              <strong>Channels to analyze</strong>
              <p class="muted">Pick specific channels or analyze all.</p>
            </div>
            <div class="selector-actions">
              <button
                type="button"
                class="secondary compact"
                :disabled="!analysisForm.limitToChannels"
                @click="selectAllChannels"
              >
                Select all
              </button>
              <button
                type="button"
                class="secondary compact"
                :disabled="!analysisForm.limitToChannels"
                @click="clearSelectedChannels"
              >
                Clear
              </button>
            </div>
          </div>
          <div v-if="channels.length" class="table-block">
            <table class="data-table compact-table">
              <thead>
                <tr>
                  <th class="table-check">Select</th>
                  <th>Channel</th>
                  <th>Username / ID</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="channel in channels" :key="channel.id">
                  <td class="table-check">
                    <input
                      type="checkbox"
                      :value="channel.id"
                      v-model="analysisForm.channelIds"
                      :disabled="!analysisForm.limitToChannels"
                    />
                  </td>
                  <td>
                    <span class="cell-title">
                      {{ channel.title || channel.username || channel.id }}
                    </span>
                  </td>
                  <td class="cell-subtle">
                    <span v-if="channel.username">@{{ channel.username }}</span>
                    <span v-else>ID: {{ channel.id }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty">No channels available yet.</p>
          <p
            v-if="analysisForm.limitToChannels && !analysisForm.channelIds.length"
            class="hint"
          >
            Select at least one channel or disable the limit.
          </p>
        </div>

        <div v-if="analysisError" class="error">{{ analysisError }}</div>
        <div v-if="analysisLoading" class="loading">Running analysis...</div>

        <div v-else-if="analysisResult" class="analysis-result">
          <div class="analysis-summary">
            <div>
              <p class="label">Prompt</p>
              <strong>{{ analysisPromptName }}</strong>
            </div>
            <div>
              <p class="label">Total messages</p>
              <strong>{{ analysisResult.total_messages }}</strong>
            </div>
            <div>
              <p class="label">Channels</p>
              <strong>{{ analysisResult.channels.length }}</strong>
            </div>
            <div>
              <p class="label">Date range</p>
              <strong>
                {{ formatTimestamp(analysisResult.start_date) }} -
                {{ formatTimestamp(analysisResult.end_date) }}
              </strong>
            </div>
          </div>
          <div v-if="analysisChannelRows.length" class="table-block">
            <table class="data-table compact-table">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Username / ID</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="channel in analysisChannelRows" :key="channel.id">
                  <td>
                    <span class="cell-title">
                      {{ channel.title || (channel.username ? `@${channel.username}` : channel.id) }}
                    </span>
                  </td>
                  <td class="cell-subtle">
                    <span v-if="channel.username">@{{ channel.username }}</span>
                    <span v-else>ID: {{ channel.id }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="analysis-actions">
            <button
              type="button"
              class="secondary compact"
              :disabled="analysisAddLoading"
              @click="selectAllNewHashtags"
            >
              Select all new
            </button>
            <button
              type="button"
              class="secondary compact"
              :disabled="analysisAddLoading"
              @click="clearSelectedHashtags"
            >
              Clear
            </button>
            <button
              type="button"
              class="compact"
              :disabled="analysisAddLoading || !analysisSelectedCount"
              @click="addSelectedHashtags"
            >
              Add selected ({{ analysisSelectedCount }})
            </button>
          </div>
          <div v-if="analysisAddError" class="error">{{ analysisAddError }}</div>
          <div v-if="analysisAddSummary" class="success">{{ analysisAddSummary }}</div>

          <table v-if="analysisHashtags.length" class="data-table">
            <thead>
              <tr>
                <th class="table-check">Select</th>
                <th>Hashtag</th>
                <th>Count</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in analysisHashtags" :key="item.tag">
                <td class="table-check">
                  <input v-if="item.in_db" type="checkbox" checked disabled />
                  <input
                    v-else
                    type="checkbox"
                    :value="item.tag"
                    v-model="analysisSelectedTags"
                    :disabled="analysisAddLoading"
                  />
                </td>
                <td>
                  <strong>{{ item.tag }}</strong>
                </td>
                <td class="cell-subtle">{{ item.count }}</td>
                <td>
                  <span class="badge" :class="item.in_db ? 'badge-in' : 'badge-new'">
                    {{ item.in_db ? "In DB" : "New" }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">No hashtags found in this range.</p>
        </div>
      </section>
    </div>

    <div class="grid">
      <section class="card span-2">
        <div class="card-header">
          <div>
            <h2>Participants</h2>
            <p class="muted">Total: {{ participantsTotal }}</p>
          </div>
          <button type="button" class="secondary" @click="fetchParticipants">
            Refresh
          </button>
        </div>

        <div v-if="participantError" class="error">{{ participantError }}</div>
        <div v-if="participantLoading" class="loading">Loading...</div>
        <div v-else>
          <table v-if="participants.length" class="data-table">
            <thead>
              <tr>
                <th>Participant</th>
                <th>Username / ID</th>
                <th>Bio</th>
                <th class="table-actions">Action</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="participant in participants" :key="participant.user_id">
                <tr>
                  <td>
                    <div class="avatar-stack">
                      <img
                        v-if="participant.photo_url"
                        :src="participant.photo_url"
                        :alt="participant.display_name || participant.username || participant.user_id"
                        class="avatar"
                      />
                      <div v-else class="avatar-placeholder">
                        {{ getParticipantInitials(participant) }}
                      </div>
                      <div>
                        <div class="cell-title">
                          {{ participant.display_name || participant.username || participant.user_id }}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td class="cell-subtle">
                    <span v-if="participant.username">@{{ participant.username }}</span>
                    <span v-else>ID: {{ participant.user_id }}</span>
                  </td>
                  <td class="cell-subtle">{{ previewBio(participant.about) }}</td>
                  <td class="table-actions">
                    <button
                      type="button"
                      class="secondary compact"
                      @click="toggleParticipantDetails(participant.user_id)"
                    >
                      {{ expandedParticipantId === participant.user_id ? "Hide" : "Details" }}
                    </button>
                  </td>
                </tr>
                <tr v-if="expandedParticipantId === participant.user_id">
                  <td colspan="4">
                    <div class="detail-panel">
                      <div v-if="participantDetailsLoading[participant.user_id]" class="loading">
                        Loading details...
                      </div>
                      <div v-else>
                        <div class="detail-grid">
                          <div>
                            <p class="label">Name</p>
                            <strong>
                              {{ participant.display_name || participant.username || participant.user_id }}
                            </strong>
                          </div>
                          <div>
                            <p class="label">Username</p>
                            <span v-if="participant.username">@{{ participant.username }}</span>
                            <span v-else class="cell-subtle">No username</span>
                          </div>
                          <div>
                            <p class="label">User ID</p>
                            <span>{{ participant.user_id }}</span>
                          </div>
                        </div>
                        <div class="detail-block">
                          <p class="label">Bio</p>
                          <p class="detail-text">{{ participant.about || "No bio" }}</p>
                        </div>
                      </div>
                      <div
                        v-if="participantDetailsError[participant.user_id]"
                        class="error"
                      >
                        {{ participantDetailsError[participant.user_id] }}
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
          <p v-else class="empty">No participants found yet.</p>
          <div class="pagination">
            <button
              type="button"
              class="secondary"
              :disabled="!hasPreviousParticipantPage"
              @click="prevParticipants"
            >
              Prev
            </button>
            <span class="pagination-info">
              Page {{ participantPage }} of {{ participantTotalPages }}
            </span>
            <button
              type="button"
              class="secondary"
              :disabled="!hasNextParticipantPage"
              @click="nextParticipants"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>

    <div class="grid">
      <section class="card">
        <div class="card-header">
          <div>
            <h2>Add a channel</h2>
          </div>
          <div class="header-actions">
            <button
              type="button"
              class="secondary compact"
              :disabled="channelImportLoading"
              @click="importDialogChannels"
            >
              {{ channelImportLoading ? "Importing..." : "Import dialogs" }}
            </button>
          </div>
        </div>
        <div v-if="channelImportError" class="error">{{ channelImportError }}</div>
        <div v-if="channelImportSummary" class="success">{{ channelImportSummary }}</div>
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
          <table v-if="channelSearchResults.length" class="data-table compact-table">
            <thead>
              <tr>
                <th>Channel</th>
                <th>Username / ID</th>
                <th class="table-actions">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="channel in channelSearchResults" :key="channel.id">
                <td>
                  <div class="cell-title">
                    {{ channel.title || channel.username || channel.id }}
                  </div>
                  <div v-if="channel.description" class="cell-subtle">
                    {{ channel.description }}
                  </div>
                </td>
                <td class="cell-subtle">
                  <span v-if="channel.username">@{{ channel.username }}</span>
                  <span v-else>ID: {{ channel.id }}</span>
                </td>
                <td class="table-actions">
                  <button
                    type="button"
                    class="secondary compact"
                    :disabled="!channel.username || channelLoading"
                    @click="addFromSearch(channel)"
                  >
                    Add
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
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
          <table v-if="channels.length" class="data-table">
            <thead>
              <tr>
                <th>Channel</th>
                <th>Username / ID</th>
                <th class="table-actions">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="channel in channels" :key="channel.id">
                <td>
                  <span class="cell-title">
                    {{ channel.title || channel.username || channel.id }}
                  </span>
                </td>
                <td class="cell-subtle">
                  <span v-if="channel.username">@{{ channel.username }}</span>
                  <span v-else>ID: {{ channel.id }}</span>
                </td>
                <td class="table-actions">
                  <button
                    type="button"
                    class="icon-button danger"
                    @click="deleteChannel(channel.id)"
                    aria-label="Delete channel"
                    title="Delete"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path
                        d="M9 3h6l1 2h5v2H3V5h5l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9z"
                      />
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
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
          <table v-if="hashtags.length" class="data-table">
            <thead>
              <tr>
                <th>Hashtag</th>
                <th class="table-actions">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tag in hashtags" :key="tag.id">
                <td>
                  <span class="cell-title">{{ tag.tag }}</span>
                </td>
                <td class="table-actions">
                  <button
                    type="button"
                    class="icon-button danger"
                    @click="deleteHashtag(tag.id)"
                    aria-label="Delete hashtag"
                    title="Delete"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path
                        d="M9 3h6l1 2h5v2H3V5h5l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9z"
                      />
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
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
import { computed, nextTick, onMounted, ref } from "vue";

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
const channelImportLoading = ref(false);
const channelImportError = ref("");
const channelImportSummary = ref("");

const hashtags = ref([]);
const hashtagsTotal = ref(0);
const hashtagLoading = ref(false);
const hashtagError = ref("");
const hashtagForm = ref({
  tag: "",
});
const hashtagLimit = 12;
const hashtagOffset = ref(0);

const participants = ref([]);
const participantsTotal = ref(0);
const participantLoading = ref(false);
const participantError = ref("");
const participantLimit = 10;
const participantOffset = ref(0);
const expandedParticipantId = ref(null);
const participantDetailsLoading = ref({});
const participantDetailsError = ref({});

const prompts = ref([]);
const promptLoading = ref(false);
const promptError = ref("");
const promptForm = ref({
  name: "",
  content: "",
});
const promptEditingId = ref(null);
const promptEditForm = ref({
  name: "",
  content: "",
});

const analysisForm = ref({
  promptId: "",
  startDate: "",
  endDate: "",
  limitToChannels: false,
  channelIds: [],
  maxMessagesPerChannel: "",
});
const analysisResult = ref(null);
const analysisLoading = ref(false);
const analysisError = ref("");
const analysisSelectedTags = ref([]);
const analysisAddLoading = ref(false);
const analysisAddError = ref("");
const analysisAddSummary = ref("");

const hashtagPage = computed(() => Math.floor(hashtagOffset.value / hashtagLimit) + 1);
const hashtagTotalPages = computed(() =>
  Math.max(1, Math.ceil(hashtagsTotal.value / hashtagLimit))
);
const hasPreviousHashtagPage = computed(() => hashtagOffset.value > 0);
const hasNextHashtagPage = computed(
  () => hashtagOffset.value + hashtagLimit < hashtagsTotal.value
);

const participantPage = computed(
  () => Math.floor(participantOffset.value / participantLimit) + 1
);
const participantTotalPages = computed(() =>
  Math.max(1, Math.ceil(participantsTotal.value / participantLimit))
);
const hasPreviousParticipantPage = computed(() => participantOffset.value > 0);
const hasNextParticipantPage = computed(
  () => participantOffset.value + participantLimit < participantsTotal.value
);

const analysisHashtags = computed(() => analysisResult.value?.hashtags || []);
const analysisSelectedCount = computed(() => analysisSelectedTags.value.length);
const analysisPromptName = computed(() => {
  if (!analysisResult.value) {
    return "";
  }
  const matched = prompts.value.find((item) => item.id === analysisResult.value.prompt_id);
  if (matched) {
    return matched.name;
  }
  return `Prompt #${analysisResult.value.prompt_id}`;
});
const analysisChannelRows = computed(() => {
  if (!analysisResult.value) {
    return [];
  }
  const channelMap = new Map(channels.value.map((channel) => [channel.id, channel]));
  return analysisResult.value.channels.map((channelId) => {
    const channel = channelMap.get(channelId);
    if (channel) {
      return {
        id: channel.id,
        title: channel.title,
        username: channel.username,
      };
    }
    return { id: channelId, title: null, username: null };
  });
});

const pad2 = (number) => String(number).padStart(2, "0");

const formatRussianDateTime = (date) =>
  `${pad2(date.getDate())}.${pad2(date.getMonth() + 1)}.${date.getFullYear()} ` +
  `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;

const formatDateTimeLocal = (date) =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}` +
  `T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;

const parseRussianDateTime = (value) => {
  const match = String(value)
    .trim()
    .match(/^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})$/);
  if (!match) {
    return null;
  }
  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const date = new Date(year, month - 1, day, hour, minute);
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day ||
    date.getHours() !== hour ||
    date.getMinutes() !== minute
  ) {
    return null;
  }
  return date;
};

const parseDateTimeLocal = (value) => {
  const raw = String(value || "").trim();
  if (!raw) {
    return null;
  }
  const [datePart, timePart] = raw.split("T");
  if (!datePart || !timePart) {
    return null;
  }
  const [year, month, day] = datePart.split("-").map(Number);
  const timePieces = timePart.split(":");
  const hour = Number(timePieces[0]);
  const minute = Number(timePieces[1]);
  if ([year, month, day, hour, minute].some((item) => Number.isNaN(item))) {
    return null;
  }
  const date = new Date(year, month - 1, day, hour, minute);
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day ||
    date.getHours() !== hour ||
    date.getMinutes() !== minute
  ) {
    return null;
  }
  return date;
};

const parseDateTimeInput = (value) => {
  if (!value) {
    return null;
  }
  if (value instanceof Date) {
    return value;
  }
  const raw = String(value).trim();
  const russianDate = parseRussianDateTime(raw);
  if (russianDate) {
    return russianDate;
  }
  const localDate = parseDateTimeLocal(raw);
  if (localDate) {
    return localDate;
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
};

const analysisStartPicker = computed({
  get: () => {
    const date = parseDateTimeInput(analysisForm.value.startDate);
    return date ? formatDateTimeLocal(date) : "";
  },
  set: (value) => {
    const date = parseDateTimeLocal(value);
    analysisForm.value.startDate = date ? formatRussianDateTime(date) : "";
  },
});

const analysisEndPicker = computed({
  get: () => {
    const date = parseDateTimeInput(analysisForm.value.endDate);
    return date ? formatDateTimeLocal(date) : "";
  },
  set: (value) => {
    const date = parseDateTimeLocal(value);
    analysisForm.value.endDate = date ? formatRussianDateTime(date) : "";
  },
});

const preserveScrollPosition = async (action) => {
  const scrollY = window.scrollY;
  await action();
  await nextTick();
  if (window.scrollY !== scrollY) {
    window.scrollTo({ top: scrollY });
  }
};

const toApiDateTime = (value) => {
  if (!value) {
    return value;
  }
  const date = parseDateTimeInput(value);
  if (!date) {
    return value;
  }
  return date.toISOString();
};

const formatTimestamp = (value) => {
  const date = parseDateTimeInput(value);
  if (!date) {
    return value ? String(value) : "";
  }
  return formatRussianDateTime(date);
};

const previewBio = (value) => {
  const raw = String(value || "").trim();
  if (!raw) {
    return "No bio";
  }
  if (raw.length > 100) {
    return `${raw.slice(0, 100)}...`;
  }
  return raw;
};

const getParticipantInitials = (participant) => {
  const name = String(
    participant?.display_name || participant?.username || participant?.user_id || ""
  ).replace(/^@/, "");
  const cleaned = name.trim();
  if (!cleaned) {
    return "NA";
  }
  const parts = cleaned.split(/\s+/);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
};

const toggleParticipantDetails = (userId) => {
  if (expandedParticipantId.value === userId) {
    expandedParticipantId.value = null;
    return;
  }
  expandedParticipantId.value = userId;
  loadParticipantDetails(userId);
};

const updateParticipantRecord = (payload) => {
  const index = participants.value.findIndex(
    (participant) => participant.user_id === payload.user_id
  );
  if (index === -1) {
    return;
  }
  participants.value[index] = { ...participants.value[index], ...payload };
};

const setParticipantDetailState = (refMap, userId, value) => {
  refMap.value = { ...refMap.value, [userId]: value };
};

const loadParticipantDetails = async (userId) => {
  setParticipantDetailState(participantDetailsLoading, userId, true);
  setParticipantDetailState(participantDetailsError, userId, "");
  try {
    const response = await fetch(`${apiBase}/api/participants/${userId}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to load participant details.");
    }
    const data = await response.json();
    updateParticipantRecord(data);
  } catch (err) {
    setParticipantDetailState(
      participantDetailsError,
      userId,
      err.message || "Load error."
    );
  } finally {
    setParticipantDetailState(participantDetailsLoading, userId, false);
  }
};

const ensurePromptSelection = () => {
  if (!prompts.value.length) {
    analysisForm.value.promptId = "";
    return;
  }
  const current = String(analysisForm.value.promptId || "");
  const exists = prompts.value.some((prompt) => String(prompt.id) === current);
  if (!exists) {
    analysisForm.value.promptId = String(prompts.value[0].id);
  }
};

const syncSelectedChannels = () => {
  if (!analysisForm.value.channelIds.length) {
    return;
  }
  const available = new Set(channels.value.map((channel) => channel.id));
  analysisForm.value.channelIds = analysisForm.value.channelIds.filter((id) =>
    available.has(id)
  );
};

const initDateRange = () => {
  const now = new Date();
  const start = new Date(now);
  start.setDate(start.getDate() - 7);
  analysisForm.value.startDate = formatRussianDateTime(start);
  analysisForm.value.endDate = formatRussianDateTime(now);
};

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
    syncSelectedChannels();
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

const importDialogChannels = async () => {
  channelImportLoading.value = true;
  channelImportError.value = "";
  channelImportSummary.value = "";
  try {
    const response = await fetch(`${apiBase}/api/channels/import`, {
      method: "POST",
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to import channels.");
    }
    const data = await response.json();
    channelImportSummary.value = `Imported ${data.created} of ${data.total_found}. Skipped ${data.skipped}.`;
    await fetchChannels();
  } catch (err) {
    channelImportError.value = err.message || "Import error.";
  } finally {
    channelImportLoading.value = false;
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

const fetchPrompts = async () => {
  promptLoading.value = true;
  promptError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/prompts`);
    if (!response.ok) {
      throw new Error("Unable to load prompts.");
    }
    const data = await response.json();
    prompts.value = data.items || [];
    ensurePromptSelection();
  } catch (err) {
    promptError.value = err.message || "Load error.";
  } finally {
    promptLoading.value = false;
  }
};

const createPrompt = async () => {
  const name = promptForm.value.name.trim();
  const content = promptForm.value.content.trim();
  if (!name || !content) {
    promptError.value = "Prompt name and content are required.";
    return;
  }
  promptLoading.value = true;
  promptError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/prompts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        content,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to add prompt.");
    }

    const created = await response.json();
    promptForm.value = { name: "", content: "" };
    await fetchPrompts();
    analysisForm.value.promptId = String(created.id);
  } catch (err) {
    promptError.value = err.message || "Create error.";
  } finally {
    promptLoading.value = false;
  }
};

const startEditPrompt = (prompt) => {
  promptEditingId.value = prompt.id;
  promptEditForm.value = {
    name: prompt.name,
    content: prompt.content,
  };
};

const cancelEditPrompt = () => {
  promptEditingId.value = null;
  promptEditForm.value = { name: "", content: "" };
};

const updatePrompt = async () => {
  if (!promptEditingId.value) {
    return;
  }
  const name = promptEditForm.value.name.trim();
  const content = promptEditForm.value.content.trim();
  if (!name || !content) {
    promptError.value = "Prompt name and content are required.";
    return;
  }
  promptLoading.value = true;
  promptError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/prompts/${promptEditingId.value}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        content,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to update prompt.");
    }

    await fetchPrompts();
    cancelEditPrompt();
  } catch (err) {
    promptError.value = err.message || "Update error.";
  } finally {
    promptLoading.value = false;
  }
};

const deletePrompt = async (id) => {
  const confirmed = window.confirm("Delete this prompt?");
  if (!confirmed) {
    return;
  }
  promptLoading.value = true;
  promptError.value = "";
  try {
    const response = await fetch(`${apiBase}/api/prompts/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to delete prompt.");
    }
    if (promptEditingId.value === id) {
      cancelEditPrompt();
    }
    await fetchPrompts();
  } catch (err) {
    promptError.value = err.message || "Delete error.";
  } finally {
    promptLoading.value = false;
  }
};

const selectPrompt = (id) => {
  analysisForm.value.promptId = String(id);
};

const selectAllChannels = () => {
  analysisForm.value.channelIds = channels.value.map((channel) => channel.id);
};

const clearSelectedChannels = () => {
  analysisForm.value.channelIds = [];
};

const runAnalysis = async () => {
  analysisError.value = "";
  analysisAddError.value = "";
  analysisAddSummary.value = "";
  analysisSelectedTags.value = [];

  const promptId = Number(analysisForm.value.promptId);
  if (!promptId) {
    analysisError.value = "Select a prompt to run analysis.";
    return;
  }
  if (!analysisForm.value.startDate || !analysisForm.value.endDate) {
    analysisError.value = "Start and end date are required.";
    return;
  }
  const startDate = parseDateTimeInput(analysisForm.value.startDate);
  const endDate = parseDateTimeInput(analysisForm.value.endDate);
  if (!startDate || !endDate) {
    analysisError.value = "Invalid date range.";
    return;
  }
  if (endDate < startDate) {
    analysisError.value = "End date must be after start date.";
    return;
  }
  if (analysisForm.value.limitToChannels && !analysisForm.value.channelIds.length) {
    analysisError.value = "Select at least one channel or disable the limit.";
    return;
  }

  analysisLoading.value = true;
  analysisResult.value = null;
  try {
    const payload = {
      prompt_id: promptId,
      start_date: toApiDateTime(analysisForm.value.startDate),
      end_date: toApiDateTime(analysisForm.value.endDate),
    };
    if (analysisForm.value.limitToChannels) {
      payload.channel_ids = analysisForm.value.channelIds.map((id) => Number(id));
    }
    if (analysisForm.value.maxMessagesPerChannel) {
      payload.max_messages_per_channel = Number(analysisForm.value.maxMessagesPerChannel);
    }

    const response = await fetch(`${apiBase}/api/analysis/hashtags`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Unable to run analysis.");
    }

    const data = await response.json();
    analysisResult.value = data;
    analysisSelectedTags.value = [];
    await fetchParticipants();

  } catch (err) {
    analysisError.value = err.message || "Analysis error.";
  } finally {
    analysisLoading.value = false;
  }
};

const selectAllNewHashtags = () => {
  if (!analysisResult.value) {
    return;
  }
  analysisSelectedTags.value = analysisResult.value.hashtags
    .filter((item) => !item.in_db)
    .map((item) => item.tag);
};

const clearSelectedHashtags = () => {
  analysisSelectedTags.value = [];
};

const createHashtagByTag = async (tag) => {
  const response = await fetch(`${apiBase}/api/hashtags`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tag,
    }),
  });
  if (response.ok) {
    const data = await response.json();
    return { status: "added", tag: data.tag };
  }
  const payload = await response.json().catch(() => null);
  if (response.status === 409) {
    return { status: "exists", tag };
  }
  throw new Error(payload?.detail || "Unable to add hashtag.");
};

const addSelectedHashtags = async () => {
  if (!analysisResult.value) {
    return;
  }
  if (!analysisSelectedTags.value.length) {
    analysisAddError.value = "Select hashtags to add.";
    return;
  }

  analysisAddLoading.value = true;
  analysisAddError.value = "";
  analysisAddSummary.value = "";

  const added = [];
  const existing = [];
  const failed = [];

  try {
    for (const tag of analysisSelectedTags.value) {
      try {
        const result = await createHashtagByTag(tag);
        if (result.status === "added") {
          added.push(result.tag);
        } else if (result.status === "exists") {
          existing.push(tag);
        }
      } catch (err) {
        failed.push(tag);
      }
    }

    if (analysisResult.value) {
      const updated = new Set([...added, ...existing]);
      analysisResult.value = {
        ...analysisResult.value,
        hashtags: analysisResult.value.hashtags.map((item) =>
          updated.has(item.tag) ? { ...item, in_db: true } : item
        ),
      };
    }

    analysisSelectedTags.value = [];
    if (added.length || existing.length) {
      await fetchHashtags();
    }

    analysisAddSummary.value = `Added: ${added.length}. Already existed: ${existing.length}. Failed: ${failed.length}.`;
    if (failed.length) {
      analysisAddError.value = `Failed to add ${failed.length} hashtags.`;
    }
  } catch (err) {
    analysisAddError.value = err.message || "Unable to add hashtags.";
  } finally {
    analysisAddLoading.value = false;
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

const fetchParticipants = async () => {
  participantLoading.value = true;
  participantError.value = "";
  try {
    const response = await fetch(
      `${apiBase}/api/participants?limit=${participantLimit}&offset=${participantOffset.value}`
    );
    if (!response.ok) {
      throw new Error("Unable to load participants.");
    }
    const data = await response.json();
    participants.value = data.items || [];
    participantsTotal.value = data.total || 0;
  } catch (err) {
    participantError.value = err.message || "Load error.";
  } finally {
    participantLoading.value = false;
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
  await preserveScrollPosition(fetchHashtags);
};

const nextHashtags = async () => {
  if (!hasNextHashtagPage.value) {
    return;
  }
  hashtagOffset.value += hashtagLimit;
  await preserveScrollPosition(fetchHashtags);
};

const prevParticipants = async () => {
  if (!hasPreviousParticipantPage.value) {
    return;
  }
  participantOffset.value = Math.max(0, participantOffset.value - participantLimit);
  await preserveScrollPosition(fetchParticipants);
};

const nextParticipants = async () => {
  if (!hasNextParticipantPage.value) {
    return;
  }
  participantOffset.value += participantLimit;
  await preserveScrollPosition(fetchParticipants);
};

onMounted(() => {
  fetchChannels();
  fetchHashtags();
  fetchParticipants();
  fetchPrompts();
  initDateRange();
});
</script>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 14px 24px;
  display: grid;
  gap: 12px;
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
  gap: 10px;
}

.span-2 {
  grid-column: 1 / -1;
}

.card {
  background: #ffffff;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.card h2 {
  margin: 0;
  font-size: 16px;
}

.form {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

label {
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: #374151;
}

.date-field {
  display: grid;
  gap: 6px;
}

input:not([type="checkbox"]):not([type="radio"]) {
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
}

select,
textarea {
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  font: inherit;
}

textarea {
  resize: vertical;
}

button {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 7px 12px;
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

.split {
  display: grid;
  gap: 12px;
}

.panel {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
}

.prompt-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.prompt-list li {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 8px;
  display: grid;
  gap: 8px;
}

.prompt-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.prompt-content {
  margin: 6px 0 0;
  color: #4b5563;
  font-size: 12px;
  white-space: pre-wrap;
}

.prompt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.prompt-edit {
  border-top: 1px solid #e5e7eb;
  padding-top: 10px;
}

.inline-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.form-grid {
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  align-items: end;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
}

.channel-selector {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  background: #f9fafb;
}

.channel-selector.disabled {
  opacity: 0.6;
}

.selector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.selector-actions {
  display: flex;
  gap: 8px;
}

.analysis-result {
  margin-top: 10px;
}

.analysis-summary {
  display: grid;
  gap: 6px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.label {
  margin: 0 0 4px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
}

.analysis-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.badge-in {
  background: #d1fae5;
  color: #065f46;
}

.badge-new {
  background: #fef3c7;
  color: #92400e;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.muted {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.compact {
  padding: 6px 8px;
  font-size: 12px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th,
.data-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}

.data-table thead th {
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.06em;
  color: #6b7280;
  text-align: left;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.data-table tbody tr:hover {
  background: #f9fafb;
}

.compact-table th,
.compact-table td {
  padding-top: 5px;
  padding-bottom: 5px;
}

.table-actions {
  text-align: right;
  white-space: nowrap;
}

.table-check {
  width: 1%;
  text-align: center;
}

.cell-title {
  font-weight: 600;
  color: #111827;
}

.cell-subtle {
  font-size: 11px;
  color: #6b7280;
}

.table-block {
  margin-top: 8px;
}

.avatar-stack {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  object-fit: cover;
  background: #e5e7eb;
}

.avatar-placeholder {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: #e5e7eb;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.detail-panel {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.detail-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.detail-block {
  display: grid;
  gap: 6px;
}

.detail-text {
  margin: 0;
  color: #4b5563;
  font-size: 12px;
  white-space: pre-wrap;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}


.icon-button {
  padding: 4px;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
}

.icon-button svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
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

.success {
  background: #dcfce7;
  color: #166534;
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
  margin-top: 8px;
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

  .split {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
