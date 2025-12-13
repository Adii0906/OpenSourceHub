const programsGrid = document.getElementById("programs-grid");
const filterButtons = document.querySelectorAll(".filter-chip");
const subscribeForm = document.getElementById("subscribe-form");
const subscribeEmail = document.getElementById("subscribe-email");
const subscribeStatus = document.getElementById("subscribe-status");
const scrollProgramsBtn = document.getElementById("scroll-programs");
const scrollChatBtn = document.getElementById("scroll-chat");

// Sidebar AI Mentor elements
const aiMentorSidebar = document.getElementById("ai-mentor-sidebar");
const sidebarOverlay = document.getElementById("sidebar-overlay");
const navbarAiMentorBtn = document.getElementById("navbar-ai-mentor");
const sidebarCloseBtn = document.getElementById("sidebar-close");
const sidebarInput = document.getElementById("sidebar-agent-input");
const sidebarSendBtn = document.getElementById("sidebar-send");
const sidebarMessages = document.getElementById("sidebar-messages");

let currentDifficultyFilter = "";
const API_BASE = "http://localhost:8000";

// Sidebar AI Mentor toggle functionality
function toggleAiMentorSidebar() {
  aiMentorSidebar.classList.toggle("active");
  sidebarOverlay.classList.toggle("active");
  if (aiMentorSidebar.classList.contains("active")) {
    setTimeout(() => sidebarInput.focus(), 300);
  }
}

function closeAiMentorSidebar() {
  aiMentorSidebar.classList.remove("active");
  sidebarOverlay.classList.remove("active");
}

// Event listeners for sidebar toggle
navbarAiMentorBtn.addEventListener("click", toggleAiMentorSidebar);
sidebarCloseBtn.addEventListener("click", closeAiMentorSidebar);
sidebarOverlay.addEventListener("click", closeAiMentorSidebar);

// Navbar smooth scroll navigation
function initNavbarLinks() {
  const navLinks = document.querySelectorAll('.nav-link:not(.nav-ai-mentor-btn)');
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = link.getAttribute('href').substring(1);
      const targetElement = document.getElementById(targetId);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
}

// Reminder management
function getReminders() {
  const reminders = localStorage.getItem('programReminders');
  return reminders ? JSON.parse(reminders) : {};
}

function saveReminders(reminders) {
  localStorage.setItem('programReminders', JSON.stringify(reminders));
}

function toggleReminder(programId, programName, deadline) {
  const reminders = getReminders();
  const reminderKey = `program_${programId}`;
  
  if (reminders[reminderKey]) {
    // Remove reminder
    delete reminders[reminderKey];
    saveReminders(reminders);
    updateReminderButton(programId, false);
    showNotification(`Reminder removed for ${programName}`, 'info');
  } else {
    // Add reminder
    reminders[reminderKey] = {
      programId,
      programName,
      deadline,
      createdAt: new Date().toISOString()
    };
    saveReminders(reminders);
    updateReminderButton(programId, true);
    showNotification(`Reminder set for ${programName}! Deadline: ${deadline}`, 'success');
  }
}

function updateReminderButton(programId, isSet) {
  const btn = document.querySelector(`.reminder-btn[data-program-id="${programId}"]`);
  if (btn) {
    if (isSet) {
      btn.classList.add('reminder-active');
      btn.querySelector('.reminder-text').textContent = 'Reminder Set';
    } else {
      btn.classList.remove('reminder-active');
      btn.querySelector('.reminder-text').textContent = 'Set Reminder';
    }
  }
}

function showNotification(message, type = 'success') {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  // Animate in
  setTimeout(() => notification.classList.add('show'), 10);
  
  // Remove after 3 seconds
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

function checkReminders() {
  const reminders = getReminders();
  const now = new Date();
  
  Object.values(reminders).forEach(reminder => {
    // Parse deadline (simplified - in production, use proper date parsing)
    const deadlineStr = reminder.deadline;
    // This is a simplified check - you'd want proper date parsing
    console.log(`Reminder for ${reminder.programName}: ${deadlineStr}`);
  });
}

// Update reminder button states when rendering
function updateReminderButtons() {
  const reminders = getReminders();
  Object.keys(reminders).forEach(key => {
    const programId = reminders[key].programId;
    updateReminderButton(programId, true);
  });
}

scrollProgramsBtn.addEventListener("click", () => {
  document.getElementById("programs-section").scrollIntoView({ behavior: "smooth" });
});

scrollChatBtn.addEventListener("click", () => {
  document.getElementById("chat-section").scrollIntoView({ behavior: "smooth" });
  setTimeout(() => {
    agentInput.focus();
  }, 500);
});

async function loadProgramsFromCache() {
  // Load programs from local cache when API is unavailable.
  try {
    const response = await fetch('./programs-cache.json');
    if (response.ok) {
      const data = await response.json();
      console.log('Loaded programs from cache:', data.length);
      return data;
    }
  } catch (error) {
    console.error('Error loading from cache:', error);
  }
  return null;
}

async function loadPrograms(difficulty = "") {
  try {
    // Show loading state
    programsGrid.innerHTML = '<div class="program-card" style="grid-column: 1 / -1; text-align: center; padding: 40px;"><p>Loading programs...</p></div>';

    let url = `${API_BASE}/programs`;
    if (difficulty) url += `?difficulty=${encodeURIComponent(difficulty)}`;

    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    const data = await res.json();
    console.log('Loaded programs:', data.length);
    console.log('Programs data:', data);

    if (!data || data.length === 0) {
      // Try loading from cache
      const cachedData = await loadProgramsFromCache();
      if (cachedData && cachedData.length > 0) {
        console.log('Using cached programs data');
        renderPrograms(cachedData);
        return;
      }

      programsGrid.innerHTML = `
        <div class="program-card" style="grid-column: 1 / -1; text-align: center;">
          <p>No programs found for this filter.</p>
        </div>
      `;
      return;
    }

    renderPrograms(data);
  } catch (error) {
    console.error('Error loading programs from API:', error);

    // Try loading from cache as fallback
    const cachedData = await loadProgramsFromCache();
    if (cachedData && cachedData.length > 0) {
      console.log('Falling back to cached programs data');
      renderPrograms(cachedData);
      return;
    }

    // Show comprehensive fallback message with sample programs
    programsGrid.innerHTML = `
      <div class="program-card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
        <h3 style="color: #374151; margin-bottom: 16px;">Programs Temporarily Unavailable</h3>
        <p style="color: #6b7280; margin-bottom: 20px;">
          We're currently updating our program database. Here are some popular open-source programs to explore:
        </p>
        <div style="display: grid; gap: 16px; max-width: 600px; margin: 0 auto;">
          <div style="text-align: left; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb;">
            <h4 style="margin: 0 0 8px 0; color: #111827;">Google Summer of Code (GSoC)</h4>
            <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">Paid internship program with open source organizations. Applications typically open in March.</p>
            <a href="https://summerofcode.withgoogle.com/" target="_blank" style="color: #6366f1; text-decoration: none; font-weight: 500;">Learn more →</a>
          </div>
          <div style="text-align: left; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb;">
            <h4 style="margin: 0 0 8px 0; color: #111827;">Hacktoberfest</h4>
            <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">Month-long celebration of open source. Submit pull requests to participating repositories.</p>
            <a href="https://hacktoberfest.com/" target="_blank" style="color: #6366f1; text-decoration: none; font-weight: 500;">Learn more →</a>
          </div>
          <div style="text-align: left; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb;">
            <h4 style="margin: 0 0 8px 0; color: #111827;">Outreachy</h4>
            <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">Paid internships in open source and open science. Open to applicants worldwide.</p>
            <a href="https://www.outreachy.org/" target="_blank" style="color: #6366f1; text-decoration: none; font-weight: 500;">Learn more →</a>
          </div>
        </div>
        <p style="color: #9ca3af; font-size: 0.8rem; margin-top: 20px;">
          <em>The full program list will be available shortly. Please check back later.</em>
        </p>
      </div>
    `;
  }
}

function renderPrograms(programs) {
  programsGrid.innerHTML = "";
  if (!programs.length) {
    programsGrid.innerHTML =
      '<div class="program-card"><p>No programs found for this filter.</p></div>';
    return;
  }
  programs.forEach((p, index) => {
    const card = document.createElement("article");
    card.className = "program-card";
    card.style.opacity = "0";
    
    const difficultyClass =
      {
        beginner: "difficulty-beginner",
        intermediate: "difficulty-intermediate",
        advanced: "difficulty-advanced",
      }[p.difficulty] || "";
    
    const programType = p.program_type || "Open Source";
    const opensIn = p.opens_in || "";
    const tags = p.tags || [];
    
    const tagsHTML = tags.map(tag => 
      `<span class="program-tag">${tag}</span>`
    ).join("");
    
    const datesHTML = `
      ${opensIn ? `
        <div class="date-item">
          <span class="date-icon">📅</span>
          <span>Opens in ${opensIn}</span>
        </div>
      ` : ''}
      <div class="date-item">
        <span class="date-icon">⏰</span>
        <span>Deadline: ${p.deadline}</span>
      </div>
    `;
    
    card.innerHTML = `
      <div class="program-header">
        <div class="program-name">${p.name}</div>
        <span class="program-type-badge">${programType}</span>
      </div>
      <div class="program-desc">${p.description}</div>
      <div class="program-tags">
        <span class="difficulty-pill ${difficultyClass}">${p.difficulty.charAt(0).toUpperCase() + p.difficulty.slice(1)}</span>
        ${tagsHTML}
      </div>
      <div class="program-dates">
        ${datesHTML}
      </div>
      <div class="program-action">
        <button class="reminder-btn" data-program-id="${p.id}" onclick="event.stopPropagation(); toggleReminder(${p.id}, '${p.name.replace(/'/g, "\\'")}', '${p.deadline.replace(/'/g, "\\'")}')">
          <span class="reminder-icon">🔔</span>
          <span class="reminder-text">Set Reminder</span>
        </button>
        <a href="${p.official_site}" target="_blank" class="program-link" onclick="event.stopPropagation()">
          Apply Now
          <span class="program-link-icon">↗</span>
        </a>
      </div>
    `;
    
    // Make entire card clickable
    card.addEventListener('click', (e) => {
      // Don't trigger if clicking on the link or reminder button
      if (e.target.tagName !== 'A' && !e.target.closest('a') && 
          e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
        window.open(p.official_site, '_blank');
      }
    });
    
    programsGrid.appendChild(card);
    
    // Animate card entrance with anime.js
    anime({
      targets: card,
      opacity: [0, 1],
      translateY: [30, 0],
      delay: index * 100,
      duration: 600,
      easing: 'easeOutQuad'
    });
  });
  
  // Update reminder button states after rendering
  setTimeout(updateReminderButtons, 100);
}


filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const difficulty = btn.getAttribute("data-difficulty") || "";
    currentDifficultyFilter = difficulty;
    loadPrograms(difficulty);
  });
});

async function sendAgentMessage() {
  const message = sidebarInput.value.trim();
  if (!message) return;
  
  if (!sidebarInput || !sidebarMessages) {
    console.error('Chat elements not found');
    return;
  }
  
  addSidebarMessage(message, "user");
  sidebarInput.value = "";
  sidebarSendBtn.disabled = true;
  
  addSidebarMessage("Thinking...", "agent");
  const thinkingNode = sidebarMessages.lastElementChild;

  try {
    const res = await fetch(`${API_BASE}/agent-chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        difficulty_filter: currentDifficultyFilter || null,
      }),
    });
    
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    
    const data = await res.json();
    thinkingNode.textContent = data.reply || "Here are some programs to explore.";
    
    if (Array.isArray(data.suggested_programs) && data.suggested_programs.length > 0) {
      renderPrograms(data.suggested_programs);
    }
  } catch (e) {
    console.error('Chat error:', e);
    thinkingNode.textContent =
      "Sorry, something went wrong. Please try again.";
  } finally {
    sidebarSendBtn.disabled = false;
    sidebarInput.focus();
  }
}

function addSidebarMessage(text, sender) {
  const messageEl = document.createElement("div");
  messageEl.className = `sidebar-message sidebar-message-${sender}`;
  messageEl.style.marginBottom = "12px";
  messageEl.style.padding = "10px 12px";
  messageEl.style.borderRadius = "8px";
  messageEl.style.wordWrap = "break-word";
  
  if (sender === "user") {
    messageEl.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
    messageEl.style.color = "white";
    messageEl.style.marginLeft = "auto";
    messageEl.style.maxWidth = "85%";
    messageEl.style.textAlign = "right";
  } else {
    messageEl.style.background = "#f0f0f0";
    messageEl.style.color = "#333";
    messageEl.style.marginRight = "auto";
    messageEl.style.maxWidth = "85%";
  }
  
  messageEl.textContent = text;
  sidebarMessages.appendChild(messageEl);
  sidebarMessages.scrollTop = sidebarMessages.scrollHeight;
}

sidebarInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendAgentMessage();
  }
});
sidebarSendBtn.addEventListener("click", sendAgentMessage);

subscribeForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  subscribeStatus.textContent = "";
  const email = subscribeEmail.value.trim();
  if (!email) return;
  try {
    const res = await fetch(`${API_BASE}/subscribe-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (data.status === "subscribed") {
      subscribeStatus.textContent = "Subscribed successfully";
      subscribeStatus.style.color = "#16a34a";
      subscribeEmail.value = "";
    } else if (data.status === "already_subscribed") {
      subscribeStatus.textContent = "You are already subscribed.";
      subscribeStatus.style.color = "#92400e";
    } else {
      subscribeStatus.textContent = "Unable to subscribe right now.";
      subscribeStatus.style.color = "#b91c1c";
    }
  } catch {
    subscribeStatus.textContent = "Failed to subscribe. Try again later.";
    subscribeStatus.style.color = "#b91c1c";
  }
});

// Initialize animations and load programs
function initializePage() {
  // Wait for anime.js to load
  if (typeof anime === 'undefined') {
    setTimeout(initializePage, 100);
    return;
  }
  
  // Animate hero elements
  anime({
    targets: '.hero-title',
    opacity: [0, 1],
    translateY: [-30, 0],
    duration: 1000,
    easing: 'easeOutQuad'
  });
  
  anime({
    targets: '.hero-subtitle',
    opacity: [0, 1],
    translateY: [-20, 0],
    delay: 200,
    duration: 800,
    easing: 'easeOutQuad'
  });
  
  anime({
    targets: '.info-item',
    opacity: [0, 1],
    scale: [0.8, 1],
    delay: anime.stagger(100, {start: 400}),
    duration: 600,
    easing: 'easeOutBack'
  });
  
  anime({
    targets: '.hero-cta',
    opacity: [0, 1],
    translateY: [20, 0],
    delay: 800,
    duration: 600,
    easing: 'easeOutQuad'
  });
  
  // Animate feature cards when in view
  const observerOptions = {
    threshold: 0.2,
    rootMargin: '0px 0px -100px 0px'
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        anime({
          targets: entry.target,
          opacity: [0, 1],
          translateY: [30, 0],
          duration: 600,
          easing: 'easeOutQuad'
        });
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);
  
  document.querySelectorAll('.feature-card, .benefit-item').forEach(el => {
    observer.observe(el);
  });
  
  // Initialize navbar links
  initNavbarLinks();
  
  // Load programs
  loadPrograms();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializePage);
} else {
  initializePage();
}
