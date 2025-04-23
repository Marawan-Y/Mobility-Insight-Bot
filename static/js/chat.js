document.addEventListener("DOMContentLoaded", () => {
    renderMarkdown();
    scrollToBottom();
  });
  
  function renderMarkdown() {
    document.querySelectorAll('[data-markdown="true"]').forEach(el => {
      el.innerHTML = marked.parse(el.textContent);
    });
  }
  
  function scrollToBottom() {
    const anchor = document.getElementById("bottom-anchor");
    if (anchor) anchor.scrollIntoView({ behavior: 'smooth' });
  }
  
  // Observe new messages
  const observer = new MutationObserver(() => {
    renderMarkdown();
    scrollToBottom();
  });
  observer.observe(document.getElementById("chat-container"), { childList: true });
  