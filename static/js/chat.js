document.addEventListener("DOMContentLoaded", () => {
  renderMarkdown();
  scrollToBottom();
});

function renderMarkdown() {
  document.querySelectorAll('[data-markdown]')
    .forEach(el => el.innerHTML = marked.parse(el.textContent));
}

function scrollToBottom() {
  const anchor = document.getElementById("bottom-anchor");
  if (anchor) anchor.scrollIntoView({ behavior: 'smooth' });
}

const observer = new MutationObserver(() => {
  renderMarkdown();
  scrollToBottom();
});
const container = document.getElementById("chat-container");
if (container) observer.observe(container, { childList: true });