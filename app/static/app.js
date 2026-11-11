const messagesEl = document.getElementById("messages");
const welcomeEl = document.getElementById("welcome");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const statusEl = document.getElementById("status");
let conversationId = crypto.randomUUID();

function addMessage(role, content) {
  welcomeEl.hidden = true;
  const item = document.createElement("div");
  item.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "S";
  const body = document.createElement("div");
  body.className = "message-content";
  body.textContent = content;
  item.append(avatar, body);
  messagesEl.appendChild(item);
  item.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message || sendButton.disabled) return;
  statusEl.textContent = "";
  addMessage("user", message);
  input.value = "";
  sendButton.disabled = true;
  const typing = document.createElement("div");
  typing.className = "message";
  typing.id = "typing";
  typing.textContent = "StudyBuddy is thinking…";
  messagesEl.appendChild(typing);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, message })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to send your message.");
    addMessage("assistant", data.reply);
  } catch (error) {
    statusEl.textContent = error.message || "A network error occurred. Please try again.";
  } finally {
    document.getElementById("typing")?.remove();
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.textContent));
});
document.getElementById("new-chat").addEventListener("click", () => {
  conversationId = crypto.randomUUID();
  messagesEl.replaceChildren();
  statusEl.textContent = "";
  welcomeEl.hidden = false;
  input.focus();
});
