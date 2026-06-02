const state = {
  sessionId: localStorage.getItem("avtorgraf_session_id") || "",
  role: localStorage.getItem("avtorgraf_role") || "ГИП",
};

const messages = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const question = document.querySelector("#question");
const sendButton = document.querySelector("#sendButton");
const mode = document.querySelector("#mode");
const refs = document.querySelector("#references");
const statusNode = document.querySelector("#status");
const docsStatus = document.querySelector("#docsStatus");

/**
 * Простой парсер markdown для основного форматирования
 * Поддерживает форматирование документов и ссылок на пункты
 */
function markdownToHtml(text) {
  let html = text
    // Кодовые блоки (``` ... ```)
    .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
    // Встроенный код (`...`)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Ссылки на документы в bold квадратных скобках **[...]**
    // Примеры: **[СН 1.03.01-2019, п. 3.4]**, **[СТБ 1937-2022, раздел 2]**
    // Оставляем как часть текста (не оборачиваем в спец класс)
    .replace(/\*\*\[([^\]]+)\]\*\*/g, "<strong>[$1]</strong>")
    // Жирный текст (**...** или __...__) 
    .replace(/\*\*([^\*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    // Наклонный текст (*...* или _..._)
    .replace(/\*([^\*]+)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    // Списки (# - список)
    .replace(/^-\s+(.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
    // Заголовки (### Заголовок)
    .replace(/^###\s+(.+)$/gm, "<h4>$1</h4>")
    .replace(/^##\s+(.+)$/gm, "<h3>$1</h3>")
    .replace(/^#\s+(.+)$/gm, "<h2>$1</h2>")
    // Переносы строк (двойной Enter)
    .replace(/\n\n/g, "</p><p>")
    // Простые переносы
    .replace(/\n/g, "<br>");
  
  return `<p>${html}</p>`;
}

/**
 * Добавляет сообщение в чат (для пользователя и ошибок)
 */
function addMessage(role, content) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "Вы" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  
  if (role === "assistant") {
    // Для ошибок и других сообщений ассистента
    bubble.innerHTML = markdownToHtml(content);
  } else {
    // Для пользовательских сообщений просто текст
    bubble.textContent = content;
  }

  article.append(avatar, bubble);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

/**
 * Извлекает ссылки на документы из текста
 * Возвращает объект с очищенным HTML и массивом ссылок
 */
function extractReferencesFromText(text) {
  const references = [];
  const referencePattern = /\*\*\[([^\]]+)\]\*\*/g;
  
  let match;
  while ((match = referencePattern.exec(text)) !== null) {
    references.push(match[1]);
  }
  
  // Удаляем дубликаты
  const uniqueReferences = [...new Set(references)];
  
  return {
    html: text,
    references: uniqueReferences
  };
}

function setLoading(loading) {
  sendButton.disabled = loading;
  sendButton.textContent = loading ? "Ищу..." : "Отправить";
}

/**
 * Отображает список нормативных ссылок в боковой панели
 */
function renderReferences(items) {
  refs.innerHTML = "";
  if (!items || items.length === 0) {
    refs.className = "empty";
    refs.textContent = "Ссылки на документы отображаются внизу каждого ответа.";
    return;
  }

  refs.className = "";
  items.forEach((item) => {
    const node = document.createElement("div");
    node.className = "reference";
    
    const title = document.createElement("strong");
    title.textContent = item.title || "Источник";
    
    const snippet = document.createElement("p");
    snippet.textContent = item.snippet || item.source || "Без описания";
    
    node.append(title, snippet);
    refs.append(node);
  });
}

/**
 * Отправляет вопрос и получает ответ от LightRAG с поддержкой streaming
 */
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
        stream: true, // Включаем streaming режим
      }),
    });

    console.log("📡 Получили ответ, статус:", response.status);

    if (!response.ok && response.status !== 200) {
      const payload = await response.json();
      throw new Error(payload.error || `HTTP ${response.status}`);
    }

    // Создаем сообщение ассистента с динамическим контентом
    const assistantMessage = createAssistantMessage();

    if (response.headers.get("content-type")?.includes("application/x-ndjson")) {
      // Streaming режим (NDJSON)
      console.log("🌊 Начинаем обработку streaming...");
      await handleStreamingResponse(response, assistantMessage);
      console.log("✅ Streaming завершен");
    } else {
      // Fallback на обычный JSON режим
      console.log("📦 Обычный JSON режим");
      const payload = await response.json();
      handleRegularResponse(payload, assistantMessage);
    }
  } catch (error) {
    console.error("❌ Ошибка:", error);
    addMessage("assistant", `❌ Не удалось получить ответ: ${error.message}`);
  } finally {
    console.log("🎯 Завершаем запрос, отключаем loading");
    setLoading(false);
    console.log("✅ Кнопка сброшена, статус:", sendButton.textContent);
  }
}

/**
 * Создает новое сообщение ассистента в чате
 */
function createAssistantMessage() {
  const article = document.createElement("article");
  article.className = "message assistant";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = "";

  article.append(avatar, bubble);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;

  return {
    article: article,
    bubble: bubble,
    content: [],
    references: [],
  };
}

/**
 * Обрабатывает streaming ответ от сервера (NDJSON формат)
 */
async function handleStreamingResponse(response, assistantMessage) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let isDone = false;
  let processedDone = false;

  try {
    let iteration = 0;
    while (!isDone) {
      iteration++;
      console.log("🔄 handleStreamingResponse итерация", iteration);
      const { done, value } = await reader.read();

      if (done) {
        console.log("✅ reader.read() вернул done:", done);
        isDone = true;
      } else {
        buffer += decoder.decode(value, { stream: true });
      }
      
      // Обрабатываем строки по одной (NDJSON)
      const lines = buffer.split("\n");
      
      // Все строки кроме последней полные и готовы к обработке
      for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i].trim();
        if (line) {
          try {
            const data = JSON.parse(line);
            processNDJSONLine(line, assistantMessage);
            if (data.type === "done") {
              processedDone = true;
              isDone = true; // Принудительно завершаем цикл после done
              console.log("🛑 Принудительное завершение цикла после done");
            }
          } catch (e) {
            console.error("Ошибка парсинга NDJSON:", e, line);
            processedDone = false; // Убедимся что не true
          }
        }
      }
      
      // Последняя строка может быть неполной, сохраняем её
      buffer = lines[lines.length - 1];
    }

    // Обрабатываем оставшуюся часть буфера если есть
    if (buffer.trim() && !isDone) {
      try {
        const data = JSON.parse(buffer.trim());
        processNDJSONLine(buffer.trim(), assistantMessage);
        if (data.type === "done") {
          processedDone = true;
          isDone = true; // Принудительно завершаем цикл после done
          console.log("🛑 Принудительное завершение цикла после done (остаток буфера)");
        }
      } catch (e) {
        console.error("Ошибка парсинга последней строки:", e, buffer);
      }
    }
    
    return processedDone; // Возвращаем true если успешно дошли до done
  } catch (error) {
    console.error("Ошибка streaming:", error);
    assistantMessage.bubble.innerHTML = `<p>❌ Ошибка при получении ответа: ${error.message}</p>`;
    return false; // Ошибка
  } finally {
    console.log("🏁 handleStreamingResponse завершен, processedDone:", processedDone);
  }
}

/**
 * Обрабатывает одну NDJSON строку
 */
function processNDJSONLine(line, assistantMessage) {
  try {
    const data = JSON.parse(line);

    if (data.references) {
      // Первая строка с ссылками
      console.log("📚 Получены ссылки:", data.references.length);
      assistantMessage.references = data.references;
    } else if (data.type === "metadata") {
      // Метаданные
      console.log("📋 Метаданные сессии:", data.session_id);
      state.sessionId = data.session_id;
      localStorage.setItem("avtorgraf_session_id", state.sessionId);
    } else if (data.response) {
      // Контент ответа
      console.log("📝 Получен chunk:", data.response.substring(0, 50) + "...");
      assistantMessage.content.push(data.response);
      updateAssistantMessageContent(assistantMessage);
    } else if (data.type === "done") {
      // Ответ завершен - ЗДЕСЬ финализируем сообщение
      console.log("✅ Streaming завершен, финализируем сообщение");
      try {
        finalizeAssistantMessage(assistantMessage);
      } catch (e) {
        console.error("Ошибка при финализации сообщения:", e);
        assistantMessage.bubble.innerHTML = `<p>❌ Ошибка при формировании ответа: ${e.message}</p>`;
      }
    } else if (data.error) {
      // Ошибка
      console.error("⚠️ Ошибка из сервера:", data.error);
      throw new Error(data.error);
    }
  } catch (e) {
    console.error("Ошибка парсинга NDJSON:", e, line);
  }
}

/**
 * Обновляет контент сообщения ассистента во время streaming
 */
function updateAssistantMessageContent(assistantMessage) {
  const fullContent = assistantMessage.content.join(" ");
  const { html, references } = extractReferencesFromText(fullContent);
  assistantMessage.bubble.innerHTML = markdownToHtml(html);
  messages.scrollTop = messages.scrollHeight;
}

/**
 * Завершает сообщение ассистента и добавляет ссылки
 */
function finalizeAssistantMessage(assistantMessage) {
  // Проверяем что это сообщение еще не финализировано
  if (assistantMessage.finalized) {
    console.warn("⚠️ Сообщение уже финализировано, пропускаем");
    return;
  }
  
  assistantMessage.finalized = true;
  console.log("🔚 Финализируем сообщение. Ссылок:", assistantMessage.references.length);

  const fullContent = assistantMessage.content.join(" ");
  const { references: extractedRefs } = extractReferencesFromText(fullContent);

  // Если есть ссылки из streaming события, используем их
  const allReferences = assistantMessage.references.length > 0 
    ? assistantMessage.references 
    : extractedRefs.map(ref => ({ title: ref }));

  console.log("📍 Всего ссылок к отображению:", allReferences.length);

  // Ссылки не добавляем под ответом - они уже встроены в текст ответа
  console.log("✅ Ссылки встроены в текст ответа");

  // Делаем ссылки на документы кликабельными
  makeDocumentLinksClickable(assistantMessage.article);

  messages.scrollTop = messages.scrollHeight;
  console.log("✅ finalizeAssistantMessage завершена");
}

/**
 * Обрабатывает обычный (non-streaming) JSON ответ
 */
function handleRegularResponse(payload, assistantMessage) {
  if (payload.error) {
    throw new Error(payload.error);
  }

  state.sessionId = payload.session_id;
  localStorage.setItem("avtorgraf_session_id", state.sessionId);

  assistantMessage.content = [payload.answer];
  assistantMessage.references = payload.references || [];

  updateAssistantMessageContent(assistantMessage);
  finalizeAssistantMessage(assistantMessage);
}

/**
 * Обработчик отправки формы чата
 */
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;
  question.value = "";
  question.style.height = "auto"; // Сбрасываем высоту для следующего ввода
  ask(text);
});

/**
 * Обработчик быстрых вопросов
 */
document.querySelector("#quickGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button) return;
  question.value = button.dataset.question;
  question.focus();
});

/**
 * Обработчик выбора роли
 */
document.querySelectorAll(".role-tabs button").forEach((button) => {
  // Если это сохраненная роль, отметим её как активную
  if (button.dataset.role === state.role) {
    document.querySelectorAll(".role-tabs button").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
  }

  button.addEventListener("click", () => {
    document.querySelectorAll(".role-tabs button").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    state.role = button.dataset.role;
    localStorage.setItem("avtorgraf_role", state.role);
  });
});

/**
 * Проверяет статус здоровья приложения (LightRAG online/offline)
 */
async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    const ok = payload.lightrag && payload.lightrag.ok;
    statusNode.className = `status ${ok ? "ok" : "bad"}`;
    statusNode.querySelector("span:last-child").textContent = ok ? "✓ LightRAG online" : "✗ LightRAG offline";
  } catch {
    statusNode.className = "status bad";
    statusNode.querySelector("span:last-child").textContent = "✗ Нет связи";
  }
}

/**
 * Обновляет статус документов и pipeline LightRAG
 */
async function refreshDocuments() {
  docsStatus.textContent = "Загрузка...";
  try {
    const [docsResponse, pipelineResponse] = await Promise.all([
      fetch("/api/documents"),
      fetch("/api/documents/pipeline_status"),
    ]);
    const docs = await docsResponse.json();
    const pipeline = await pipelineResponse.json();
    
    // Форматируем вывод: список документов и статус pipeline
    let output = "";
    
    // Статус обработки - поддерживаем несколько форматов
    if (pipeline && pipeline.job_name) {
        output += `📊 Задача: ${pipeline.job_name}\n`;
    }
    if (pipeline && pipeline.status) {
        output += `⚙️ Статус: ${pipeline.status}\n`;
    }
    if (pipeline && pipeline.docs !== undefined) {
        output += `✅ Документов: ${pipeline.docs}\n`;
    }
    if (pipeline && pipeline.batchs !== undefined && pipeline.cur_batch !== undefined) {
        output += `📦 Пакетов: ${pipeline.cur_batch}/${pipeline.batchs}\n`;
    }
    if (pipeline && pipeline.autoscanned !== undefined) {
        output += `🔄 Автоподсказка: ${pipeline.autoscanned ? "вкл" : "выкл"}\n`;
    }
    if (pipeline && pipeline.busy !== undefined) {
        output += `⚡ Занят: ${pipeline.busy ? "да" : "нет"}\n`;
    }
    
    output += "\n📚 Документы в базе знаний:\n";
    output += "─".repeat(40) + "\n";
    
    // Обработка документов - поддерживаем LightRAG формат с statuses.processed
    if (docs && docs.statuses && Array.isArray(docs.statuses.processed)) {
      if (docs.statuses.processed.length === 0) {
        output += "(документы не загружены)\n";
      } else {
        docs.statuses.processed.forEach((doc, index) => {
          const name = doc.file_path || doc.id || "Без имени";
          const status = "processed";
          const content_length = doc.content_length ? ` (${doc.content_length} байт)` : "";
          output += `${index + 1}. ${name}${content_length}\n`;
        });
      }
    } else if (docs && docs.documents && Array.isArray(docs.documents)) {
      // Старый формат
      if (docs.documents.length === 0) {
        output += "(документы не загружены)\n";
      } else {
        docs.documents.forEach((doc, index) => {
          const name = doc.name || doc.file_path || "Без имени";
          const status = doc.status ? `[${doc.status}]` : "";
          output += `${index + 1}. ${name} ${status}\n`;
        });
      }
    } else if (docs && docs.data && Array.isArray(docs.data)) {
      // Альтернативный формат ответа
      if (docs.data.length === 0) {
        output += "(документы не загружены)\n";
      } else {
        docs.data.forEach((doc, index) => {
          const name = typeof doc === "string" ? doc : (doc.name || doc.file_path || "Без имени");
          output += `${index + 1}. ${name}\n`;
        });
      }
    } else {
      output += "(не удалось получить список)\n";
    }
    
    output += "─".repeat(40);
    docsStatus.textContent = output;
    docsStatus.style.whiteSpace = "pre";
    docsStatus.style.fontSize = "12px";
    docsStatus.style.lineHeight = "1.6";
  } catch (error) {
    docsStatus.textContent = `❌ Ошибка: ${error.message}`;
  }
}

/**
 * Инициализация обработчиков и периодических проверок
 */
document.querySelector("#refreshDocs").addEventListener("click", refreshDocuments);
refreshHealth();
setInterval(refreshHealth, 30000);


// ============================================================================
// Модальное окно для просмотра документов
// ============================================================================

const modal = document.querySelector("#documentModal");
const modalTitle = document.querySelector("#modalTitle");
const modalBody = document.querySelector("#modalBody");
const closeModalBtn = document.querySelector("#closeModal");

/**
 * Парсит ссылку на документ и извлекает название и пункт
 * Примеры:
 * - "СН 1.03.01-2019, п. 3.4" -> {doc: "СН 1.03.01-2019", section: "3.4"}
 * - "СТБ 1937-2022, раздел 2" -> {doc: "СТБ 1937-2022", section: "раздел 2"}
 * - "ТКП 45-5.04-274-2012" -> {doc: "ТКП 45-5.04-274-2012", section: null}
 */
function parseDocumentReference(refText) {
  // Удаляем квадратные скобки если есть
  refText = refText.replace(/^\[|\]$/g, "").trim();
  
  // Ищем паттерны с пунктами: ", п. X" или ", раздел X" и т.д.
  const patterns = [
    /^([^,]+),\s*п\.\s*(.+)$/i,           // "СН 1.03.01-2019, п. 3.4"
    /^([^,]+),\s*пункт\s*(.+)$/i,         // "СН 1.03.01-2019, пункт 3.4"
    /^([^,]+),\s*раздел\s*(.+)$/i,        // "СТБ 1937-2022, раздел 2"
    /^([^,]+),\s*глава\s*(.+)$/i,         // "Документ, глава 5"
    /^([^,]+),\s*приложение\s*(.+)$/i,    // "Документ, приложение А"
    /^([^,]+),\s*статья\s*(.+)$/i,        // "Документ, статья 10"
  ];
  
  for (const pattern of patterns) {
    const match = refText.match(pattern);
    if (match) {
      return {
        doc: match[1].trim(),
        section: match[2].trim(),
      };
    }
  }
  
  // Если не нашли паттерн, возвращаем весь текст как название документа
  return {
    doc: refText.trim(),
    section: null,
  };
}

/**
 * Открывает модальное окно с документом
 */
async function openDocumentModal(docName, section = null) {
  console.log("🔍 Открываем документ:", docName, "раздел:", section);
  
  // Показываем модальное окно сразу с индикатором загрузки
  modal.classList.add("active");
  modalTitle.textContent = docName;
  modalBody.innerHTML = "<p>⏳ Загрузка документа...</p>";
  
  try {
    // Запрашиваем документ с сервера
    const response = await fetch(`/api/documents/${encodeURIComponent(docName)}`);
    
    if (!response.ok) {
      let errMsg = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData && errorData.error) {
          errMsg = errorData.error;
        }
      } catch (e) {
        // Игнорируем ошибку парсинга JSON
      }
      throw new Error(errMsg);
    }
    
    const data = await response.json();
    console.log("📄 Получен документ:", data);
    
    // Отображаем содержимое
    if (data.content) {
      // Если контент в markdown, конвертируем в HTML
      modalBody.innerHTML = markdownToHtml(data.content);
    } else if (data.text) {
      modalBody.innerHTML = markdownToHtml(data.text);
    } else {
      modalBody.innerHTML = "<p>⚠️ Документ не содержит текста</p>";
    }
    
    // Если указан раздел, пытаемся прокрутить к нему
    if (section) {
      setTimeout(() => scrollToSection(section), 100);
    }
  } catch (error) {
    console.error("❌ Ошибка загрузки документа:", error);
    modalBody.innerHTML = `
      <p>❌ Не удалось загрузить документ</p>
      <p style="color: var(--muted); font-size: 14px;">${error.message}</p>
    `;
  }
}

/**
 * Пытается прокрутить к указанному разделу документа
 */
function scrollToSection(sectionId) {
  console.log("📍 Поиск раздела:", sectionId);
  
  // Нормализуем ID раздела для поиска
  const normalizedId = sectionId.toLowerCase().replace(/\s+/g, "");
  
  // Ищем заголовки, которые могут содержать этот раздел
  const headings = modalBody.querySelectorAll("h1, h2, h3, h4, h5, h6, p, strong");
  
  for (const heading of headings) {
    const text = heading.textContent.toLowerCase();
    
    // Проверяем различные варианты вхождения
    if (
      text.includes(sectionId.toLowerCase()) ||
      text.includes(normalizedId) ||
      text.includes(`п. ${sectionId}`) ||
      text.includes(`пункт ${sectionId}`) ||
      text.includes(`раздел ${sectionId}`)
    ) {
      console.log("✅ Найден раздел:", heading.textContent);
      
      // Подсвечиваем найденный элемент
      heading.classList.add("highlight-section");
      
      // Прокручиваем к элементу
      heading.scrollIntoView({ behavior: "smooth", block: "center" });
      
      // Убираем подсветку через 2 секунды
      setTimeout(() => {
        heading.classList.remove("highlight-section");
      }, 2000);
      
      return;
    }
  }
  
  console.warn("⚠️ Раздел не найден:", sectionId);
}

/**
 * Закрывает модальное окно
 */
function closeDocumentModal() {
  modal.classList.remove("active");
  modalBody.innerHTML = "";
}

// Обработчики событий для модального окна
closeModalBtn.addEventListener("click", closeDocumentModal);

// Закрытие по клику вне окна
modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    closeDocumentModal();
  }
});

// Закрытие по Escape
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && modal.classList.contains("active")) {
    closeDocumentModal();
  }
});

/**
 * Делает ссылки на документы кликабельными
 * Вызывается после рендеринга сообщения
 */
function makeDocumentLinksClickable(messageElement) {
  // Находим все ссылки в квадратных скобках внутри <strong>
  const strongElements = messageElement.querySelectorAll("strong");
  
  strongElements.forEach((strong) => {
    const text = strong.textContent;
    
    // Проверяем, что это ссылка на документ (содержит квадратные скобки)
    if (text.match(/^\[.+\]$/)) {
      // Делаем элемент кликабельным
      strong.classList.add("doc-reference");
      strong.style.cursor = "pointer";
      
      strong.addEventListener("click", (event) => {
        event.preventDefault();
        
        // Парсим ссылку
        const { doc, section } = parseDocumentReference(text);
        
        // Открываем модальное окно
        openDocumentModal(doc, section);
      });
    }
  });
  
  // Обрабатываем также ссылки в footer (reference-item)
  const referenceItems = messageElement.querySelectorAll(".reference-item");
  
  referenceItems.forEach((item) => {
    item.addEventListener("click", (event) => {
      event.preventDefault();
      
      // Парсим ссылку
      const { doc, section } = parseDocumentReference(item.textContent);
      
      // Открываем модальное окно
      openDocumentModal(doc, section);
    });
  });
}
