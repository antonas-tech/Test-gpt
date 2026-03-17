const STORAGE_KEY = "pulseHabitData";

const welcomeCard = document.getElementById("welcomeCard");
const trackerCard = document.getElementById("trackerCard");
const welcomeForm = document.getElementById("welcomeForm");
const habitForm = document.getElementById("habitForm");
const habitInput = document.getElementById("habitInput");
const habitList = document.getElementById("habitList");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const greetingTitle = document.getElementById("greetingTitle");
const goalLine = document.getElementById("goalLine");
const resetBtn = document.getElementById("resetBtn");
const habitTemplate = document.getElementById("habitTemplate");

let state = {
  profile: null,
  habits: []
};

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.profile && Array.isArray(parsed.habits)) {
      state = parsed;
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function updateProgress() {
  const total = state.habits.length;
  const completed = state.habits.filter((habit) => habit.done).length;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  progressFill.style.width = `${percent}%`;
  progressText.textContent = `${percent}%`;
}

function renderHabits() {
  habitList.innerHTML = "";

  state.habits.forEach((habit) => {
    const node = habitTemplate.content.firstElementChild.cloneNode(true);
    const checkbox = node.querySelector(".habit-check");
    const text = node.querySelector(".habit-text");
    const deleteBtn = node.querySelector(".delete-btn");

    checkbox.checked = habit.done;
    text.textContent = habit.title;

    checkbox.addEventListener("change", () => {
      habit.done = checkbox.checked;
      saveState();
      updateProgress();
    });

    deleteBtn.addEventListener("click", () => {
      state.habits = state.habits.filter((item) => item.id !== habit.id);
      saveState();
      renderHabits();
      updateProgress();
    });

    habitList.append(node);
  });
}

function renderProfile() {
  if (!state.profile) {
    welcomeCard.classList.remove("hidden");
    trackerCard.classList.add("hidden");
    return;
  }

  welcomeCard.classList.add("hidden");
  trackerCard.classList.remove("hidden");

  greetingTitle.textContent = `${state.profile.name}, ваш фокус на сегодня`; 
  goalLine.textContent = `Цель: ${state.profile.goal} • План: ${state.profile.targetHabits} привычек`;

  renderHabits();
  updateProgress();
}

welcomeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(welcomeForm);

  state.profile = {
    name: String(formData.get("name") || "").trim(),
    goal: String(formData.get("goal") || "").trim(),
    targetHabits: Number(formData.get("targetHabits") || 5)
  };

  if (!state.profile.name || !state.profile.goal) return;

  if (state.habits.length === 0) {
    state.habits = [
      { id: crypto.randomUUID(), title: "Выпить стакан воды утром", done: false },
      { id: crypto.randomUUID(), title: "15 минут фокус-работы", done: false }
    ];
  }

  saveState();
  renderProfile();
});

habitForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const title = habitInput.value.trim();
  if (!title) return;

  state.habits.unshift({
    id: crypto.randomUUID(),
    title,
    done: false
  });

  habitInput.value = "";
  saveState();
  renderHabits();
  updateProgress();
});

resetBtn.addEventListener("click", () => {
  state = { profile: null, habits: [] };
  localStorage.removeItem(STORAGE_KEY);
  welcomeForm.reset();
  renderProfile();
});

loadState();
renderProfile();
