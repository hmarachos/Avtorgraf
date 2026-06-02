const state = {
  sessionId: localStorage.getItem("avtorgraf_session_id") || "",
  role: "ГИП",
};

const messages = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const question = document.querySelector("#question");
const sendButton = document.querySelector("#sendButton");
const mode = document.querySelector("#mode");
const refs = document.querySelector("#references");
const statusNode = document.querySelector("#status");
const docsStatus = document.querySelector("#docsStatus");

function addMessage(role, content) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "Вы" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  article.append(avatar, bubble);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function setLoading(loading) {
  sendButton.disabled = loading;
  sendButton.textContent = loading ? "Ищу..." : "Отправить";
}

function renderReferences(items) {
  refs.innerHTML = "";
  if (!items || items.length === 0) {
    refs.className = "empty";
    refs.textContent = "LightRAG не вернул отдельный список источников. Проверьте ссылки внутри текста ответа.";
    return;
  }

  refs.className = "";
  items.forEach((item) => {
    const node = document.createElement("div");
    node.className = "reference";
    const title = document.createElement("strong");
    title.textContent = item.title || "Источник";
    const snippet = document.createElement("p");
    snippet.textContent = item.snippet || item.source || "Без фрагмента";
    node.append(title, snippet);
    refs.append(node);
  });
}

async function ask(text) {
  const composedQuestion = `[Роль: ${state.role}] ${text}`;
  addMessage("user", text);
  setLoading(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId || null,
        question: composedQuestion,
        mode: mode.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Ошибка запроса");
    }

    state.sessionId = payload.session_id;
    localStorage.setItem("avtorgraf_session_id", state.sessionId);
    addMessage("assistant", `${payload.answer}\n\nВремя LightRAG: ${(payload.elapsed_ms / 1000).toFixed(1)} с`);
    renderReferences(payload.references);
  } catch (error) {
    addMessage("assistant", `Не удалось получить ответ: ${error.message}`);
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;
  question.value = "";
  ask(text);
});

document.querySelector("#quickGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button) return;
  question.value = button.dataset.question;
  question.focus();
});

document.querySelectorAll(".role-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".role-tabs button").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    state.role = button.dataset.role;
  });
});

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    const ok = payload.lightrag && payload.lightrag.ok;
    statusNode.className = `status ${ok ? "ok" : "bad"}`;
    statusNode.querySelector("span:last-child").textContent = ok ? "LightRAG online" : "LightRAG offline";
  } catch {
    statusNode.className = "status bad";
    statusNode.querySelector("span:last-child").textContent = "Нет связи";
  }
}

async function refreshDocuments() {
  docsStatus.textContent = "Загрузка...";
  try {
    const [docsResponse, pipelineResponse] = await Promise.all([
      fetch("/api/documents"),
      fetch("/api/documents/pipeline_status"),
    ]);
    const docs = await docsResponse.json();
    const pipeline = await pipelineResponse.json();
    docsStatus.textContent = JSON.stringify({ documents: docs, pipeline }, null, 2);
  } catch (error) {
    docsStatus.textContent = error.message;
  }
}

document.querySelector("#refreshDocs").addEventListener("click", refreshDocuments);
refreshHealth();
setInterval(refreshHealth, 30000);
