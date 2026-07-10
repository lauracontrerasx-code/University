const STORE = "study-flow-data-v1";
const routes = ["home", "tasks", "subjects", "grades"];
let state = load();
let currentRoute = "home";

function applyTheme(theme) {
  const dark = theme === "dark";
  document.body.classList.toggle("dark", dark);
  localStorage.setItem("study-flow-theme", dark ? "dark" : "light");
  const button = document.querySelector("#theme-button");
  button.textContent = dark ? "☀" : "☾";
  button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
}

function seed() {
  return {
    subjects: [
      { id: "calculus", name: "Calculus I", professor: "Dr. Rivera", schedule: "Mon / Wed · 8:00 AM", semester: 2 },
      { id: "programming", name: "Programming Fundamentals", professor: "Prof. Gomez", schedule: "Tue / Thu · 10:00 AM", semester: 1 },
      { id: "writing", name: "Academic Writing", professor: "Prof. Martinez", schedule: "Friday · 2:00 PM", semester: 1 }
    ],
    categories: [
      { id: "cat-1", subjectId: "calculus", name: "Exams", weight: 50 }, { id: "cat-2", subjectId: "calculus", name: "Problem sets", weight: 30 }, { id: "cat-3", subjectId: "calculus", name: "Quizzes", weight: 20 },
      { id: "cat-4", subjectId: "programming", name: "Programming", weight: 40 }, { id: "cat-5", subjectId: "programming", name: "Quizzes", weight: 25 }, { id: "cat-6", subjectId: "programming", name: "Final project", weight: 35 },
      { id: "cat-7", subjectId: "writing", name: "Essays", weight: 60 }, { id: "cat-8", subjectId: "writing", name: "Participation", weight: 20 }, { id: "cat-9", subjectId: "writing", name: "Final portfolio", weight: 20 }
    ],
    tasks: [
      { id: "task-1", subjectId: "calculus", categoryId: "cat-2", title: "Problem set 2", due: datePlus(3), status: "pending", grade: null, notes: "Exercises 1–20." },
      { id: "task-2", subjectId: "programming", categoryId: "cat-4", title: "Mini project proposal", due: datePlus(5), status: "in progress", grade: null, notes: "Describe app idea and data model." },
      { id: "task-3", subjectId: "writing", categoryId: "cat-7", title: "Essay draft", due: datePlus(8), status: "submitted", grade: null, notes: "Waiting for feedback." },
      { id: "task-4", subjectId: "calculus", categoryId: "cat-3", title: "Quiz 1", due: datePlus(-2), status: "graded", grade: 4.2, notes: "Good work." }
    ],
    topics: [
      { id: "topic-1", subjectId: "calculus", name: "Limits and continuity", status: "studying", notes: "Review epsilon-delta examples." },
      { id: "topic-2", subjectId: "programming", name: "Python functions", status: "seen", notes: "Practice with small exercises." }
    ]
  };
}

function load() { try { return JSON.parse(localStorage.getItem(STORE)) || seed(); } catch { return seed(); } }
function save() { localStorage.setItem(STORE, JSON.stringify(state)); }
function uid(prefix) { return `${prefix}-${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`; }
function datePlus(days) { const d = new Date(); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); }
function esc(value = "") { return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }
function subject(id) { return state.subjects.find(item => item.id === id); }
function category(id) { return state.categories.find(item => item.id === id); }
function formatDate(value) { return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(`${value}T12:00:00`)); }
function dueLabel(value) { const delta = Math.round((new Date(`${value}T12:00:00`) - new Date(new Date().toDateString())) / 86400000); return delta === 0 ? "Today" : delta === 1 ? "Tomorrow" : delta < 0 ? `${Math.abs(delta)}d overdue` : `In ${delta} days`; }
function statusBadge(status) { return `<span class="badge status-${esc(status).replaceAll(" ", "-")}">${esc(status)}</span>`; }
function toast(message) { const el = document.querySelector("#toast"); el.textContent = message; el.classList.add("show"); clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 2400); }

function courseGrades(subjectId) {
  const rows = state.categories.filter(item => item.subjectId === subjectId).map(item => {
    const graded = state.tasks.filter(task => task.categoryId === item.id && Number.isFinite(task.grade));
    const average = graded.length ? graded.reduce((sum, task) => sum + Number(task.grade), 0) / graded.length : null;
    return { ...item, average, count: graded.length };
  });
  const graded = rows.filter(row => row.average !== null);
  const grade = graded.length ? graded.reduce((sum, row) => sum + row.average * row.weight, 0) / graded.reduce((sum, row) => sum + row.weight, 0) : null;
  return { rows, grade, configured: rows.reduce((sum, row) => sum + Number(row.weight), 0), gradedWeight: graded.reduce((sum, row) => sum + Number(row.weight), 0) };
}

function render() {
  document.querySelector("#app").innerHTML = ({ home: homePage, tasks: tasksPage, subjects: subjectsPage, grades: gradesPage })[currentRoute]();
  document.querySelectorAll(".nav-link").forEach(button => button.classList.toggle("active", button.dataset.route === currentRoute));
  bindPageEvents();
}

function homePage() {
  const open = state.tasks.filter(task => ["pending", "in progress"].includes(task.status)).sort((a, b) => a.due.localeCompare(b.due));
  const next = open[0];
  const completed = state.tasks.filter(task => ["submitted", "graded"].includes(task.status)).length;
  return `<section class="stack"><div class="page-heading"><div><h2>Good to see you</h2><p>Your study plan, in one place.</p></div></div>
    <article class="card hero"><div class="hero-row"><div><p>${next ? "Next deadline" : "You are all caught up"}</p><span class="hero-value">${next ? esc(dueLabel(next.due)) : "Nice!"}</span><strong>${next ? esc(next.title) : "No open tasks"}</strong></div>${next ? statusBadge(next.status) : ""}</div></article>
    <div class="metric-grid"><article class="metric"><span>Open tasks</span><strong>${open.length}</strong></article><article class="metric"><span>Completed tasks</span><strong>${completed}</strong></article></div>
    <div class="row"><h3 class="section-title">Coming up</h3><button class="button-secondary small" data-route="tasks">View all</button></div>
    ${open.length ? `<div class="list">${open.slice(0, 4).map(taskCard).join("")}</div>` : empty("No open tasks. Add one with the + button.")}</section><button class="fab" data-action="add-task" aria-label="Add task">+</button>`;
}

function taskCard(task) { const s = subject(task.subjectId); return `<button class="list-button" data-action="edit-task" data-id="${task.id}"><div class="row"><span class="task-title">${esc(task.title)}</span>${statusBadge(task.status)}</div><div class="task-meta"><span>${esc(s?.name || "No subject")}</span><span>${esc(formatDate(task.due))} · ${esc(dueLabel(task.due))}</span></div></button>`; }
function tasksPage() { const tasks = [...state.tasks].sort((a, b) => a.due.localeCompare(b.due)); return `<section class="stack"><div class="page-heading"><div><h2>Tasks</h2><p>Everything you need to submit.</p></div></div>${tasks.length ? `<div class="list">${tasks.map(taskCard).join("")}</div>` : empty("No tasks yet.")}</section><button class="fab" data-action="add-task" aria-label="Add task">+</button>`; }
function subjectsPage() { return `<section class="stack"><div class="page-heading"><div><h2>Subjects</h2><p>Courses, topics, and grading.</p></div></div><div class="list">${state.subjects.map(subjectCard).join("")}</div></section><button class="fab" data-action="add-subject" aria-label="Add subject">+</button>`; }
function subjectCard(item) { const data = courseGrades(item.id); const topics = state.topics.filter(topic => topic.subjectId === item.id); return `<button class="list-button subject-card" data-action="subject-detail" data-id="${item.id}"><div class="subject-title"><span class="task-title">${esc(item.name)}</span><span class="grade">${data.grade === null ? "—" : data.grade.toFixed(2)}</span></div><div class="task-meta"><span>${esc(item.schedule || "No schedule")}</span><span>${topics.length} topic${topics.length === 1 ? "" : "s"}</span></div><div class="progress"><span style="width:${Math.min(100, data.configured)}%"></span></div></button>`; }
function gradesPage() { return `<section class="stack"><div class="page-heading"><div><h2>Grades</h2><p>Calculated from graded tasks.</p></div></div>${state.subjects.map(item => { const data = courseGrades(item.id); return `<article class="card"><div class="card-head"><div><h3>${esc(item.name)}</h3><p class="muted">${data.gradedWeight}% of ${data.configured}% graded</p></div><span class="grade">${data.grade === null ? "—" : data.grade.toFixed(2)}</span></div><div class="progress"><span style="width:${data.configured ? (data.gradedWeight / data.configured) * 100 : 0}%"></span></div></article>`; }).join("")}</section>`; }
function empty(text) { return `<div class="empty">${esc(text)}</div>`; }

function openSheet(title, body) { const sheet = document.querySelector("#sheet"); sheet.innerHTML = `<div class="sheet"><div class="sheet-header"><h2>${esc(title)}</h2><button type="button" class="close" data-action="close" aria-label="Close">×</button></div>${body}</div>`; sheet.showModal(); sheet.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => action(button.dataset.action, button.dataset.id))); sheet.querySelectorAll("form[data-form]").forEach(form => form.addEventListener("submit", submitForm)); sheet.querySelector("input, select, textarea")?.focus(); }
function subjectOptions(selected = "") { return state.subjects.map(item => `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>${esc(item.name)}</option>`).join(""); }
function categoryOptions(subjectId, selected = "") { return `<option value="">No category</option>${state.categories.filter(item => item.subjectId === subjectId).map(item => `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>${esc(item.name)} (${item.weight}%)</option>`).join("")}`; }

function taskForm(task = {}) { const currentSubject = task.subjectId || state.subjects[0]?.id || ""; openSheet(task.id ? "Edit task" : "New task", `<form class="form" data-form="task"><input type="hidden" name="id" value="${esc(task.id || "")}"><label>Subject<select required name="subjectId">${subjectOptions(currentSubject)}</select></label><label>Category<select name="categoryId">${categoryOptions(currentSubject, task.categoryId)}</select></label><label>Task name<input required name="title" value="${esc(task.title || "")}" placeholder="e.g. Read chapter 3"></label><div class="form-grid"><label>Due date<input required type="date" name="due" value="${esc(task.due || datePlus(1))}"></label><label>Status<select name="status">${["pending", "in progress", "submitted", "graded"].map(value => `<option ${task.status === value ? "selected" : ""}>${value}</option>`).join("")}</select></label></div><label>Grade (optional, 1.0–5.0)<input type="number" min="1" max="5" step="0.1" name="grade" value="${task.grade ?? ""}"></label><label>Notes or link<textarea name="notes">${esc(task.notes || "")}</textarea></label><div class="form-actions"><button class="button" type="submit">Save task</button>${task.id ? `<button class="button-danger" type="button" data-action="delete-task" data-id="${task.id}">Delete</button>` : ""}</div></form>`); document.querySelector('[name="subjectId"]').addEventListener("change", event => { document.querySelector('[name="categoryId"]').innerHTML = categoryOptions(event.target.value); }); }
function subjectForm(item = {}) { openSheet(item.id ? "Edit subject" : "New subject", `<form class="form" data-form="subject"><input type="hidden" name="id" value="${esc(item.id || "")}"><label>Subject name<input required name="name" value="${esc(item.name || "")}"></label><div class="form-grid"><label>Semester<input type="number" min="1" max="20" name="semester" value="${item.semester || 1}"></label><label>Schedule<input name="schedule" value="${esc(item.schedule || "")}" placeholder="Mon · 8 AM"></label></div><label>Professor<input name="professor" value="${esc(item.professor || "")}"></label><div class="form-actions"><button class="button" type="submit">Save subject</button>${item.id ? `<button class="button-danger" type="button" data-action="delete-subject" data-id="${item.id}">Delete</button>` : ""}</div></form>`); }
function detailSheet(id) { const item = subject(id); if (!item) return; const data = courseGrades(id), tasks = state.tasks.filter(task => task.subjectId === id), topics = state.topics.filter(topic => topic.subjectId === id); openSheet(item.name, `<div class="stack"><div class="card"><div class="card-head"><div><p class="muted">Current grade</p><span class="grade">${data.grade === null ? "No grades" : data.grade.toFixed(2)}</span></div><button type="button" class="button-secondary small" data-action="edit-subject" data-id="${id}">Edit</button></div><p class="muted">${esc(item.professor || "No professor added")} · ${esc(item.schedule || "No schedule")}</p></div><div><div class="row"><h3 class="section-title">Grading categories</h3><button type="button" class="button-secondary small" data-action="add-category" data-id="${id}">Add</button></div><div class="list">${data.rows.map(row => `<button type="button" class="list-button" data-action="edit-category" data-id="${row.id}"><div class="row"><span class="task-title">${esc(row.name)}</span><span>${row.weight}%</span></div><div class="task-meta"><span>${row.count} graded item${row.count === 1 ? "" : "s"}</span><span>${row.average === null ? "No grades" : row.average.toFixed(2)}</span></div></button>`).join("") || empty("No categories.")}</div></div><div><div class="row"><h3 class="section-title">Topics</h3><button type="button" class="button-secondary small" data-action="add-topic" data-id="${id}">Add</button></div><div class="list">${topics.map(topic => `<button type="button" class="list-button" data-action="edit-topic" data-id="${topic.id}"><div class="row"><span class="task-title">${esc(topic.name)}</span>${statusBadge(topic.status)}</div></button>`).join("") || empty("No topics yet.")}</div></div><div><h3 class="section-title">Tasks</h3><div class="list">${tasks.map(taskCard).join("") || empty("No tasks for this subject.")}</div></div></div>`); }
function categoryForm(item = {}, subjectId) { openSheet(item.id ? "Edit category" : "New category", `<form class="form" data-form="category"><input type="hidden" name="id" value="${esc(item.id || "")}"><input type="hidden" name="subjectId" value="${subjectId}"><label>Category name<input required name="name" value="${esc(item.name || "")}"></label><label>Weight (%)<input required type="number" min="0" max="100" step="0.1" name="weight" value="${item.weight ?? ""}"></label><div class="form-actions"><button class="button" type="submit">Save category</button>${item.id ? `<button class="button-danger" type="button" data-action="delete-category" data-id="${item.id}">Delete</button>` : ""}</div></form>`); }
function topicForm(item = {}, subjectId) { openSheet(item.id ? "Edit topic" : "New topic", `<form class="form" data-form="topic"><input type="hidden" name="id" value="${esc(item.id || "")}"><input type="hidden" name="subjectId" value="${subjectId}"><label>Topic name<input required name="name" value="${esc(item.name || "")}"></label><label>Status<select name="status">${["pending", "studying", "seen"].map(value => `<option ${item.status === value ? "selected" : ""}>${value}</option>`).join("")}</select></label><label>Notes<textarea name="notes">${esc(item.notes || "")}</textarea></label><div class="form-actions"><button class="button" type="submit">Save topic</button>${item.id ? `<button class="button-danger" type="button" data-action="delete-topic" data-id="${item.id}">Delete</button>` : ""}</div></form>`); }

function bindPageEvents() { document.querySelectorAll("[data-route]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.route))); document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => action(button.dataset.action, button.dataset.id))); document.querySelectorAll("form[data-form]").forEach(form => form.addEventListener("submit", submitForm)); }
function navigate(route) { if (!routes.includes(route)) return; currentRoute = route; render(); window.scrollTo({ top: 0, behavior: "smooth" }); }
function action(name, id) { if (name === "close") return document.querySelector("#sheet").close(); if (name === "add-task") return taskForm(); if (name === "edit-task") return taskForm(state.tasks.find(item => item.id === id)); if (name === "add-subject") return subjectForm(); if (name === "edit-subject") return subjectForm(subject(id)); if (name === "subject-detail") return detailSheet(id); if (name === "add-category") return categoryForm({}, id); if (name === "edit-category") { const item = category(id); return categoryForm(item, item.subjectId); } if (name === "add-topic") return topicForm({}, id); if (name === "edit-topic") { const item = state.topics.find(topic => topic.id === id); return topicForm(item, item.subjectId); } if (name.startsWith("delete-")) deleteItem(name.slice(7), id); }
function submitForm(event) { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); const type = event.currentTarget.dataset.form; if (type === "task") { const grade = values.grade === "" ? null : Number(values.grade); if (grade !== null && (grade < 1 || grade > 5)) return toast("Grade must be between 1.0 and 5.0."); const item = { ...values, id: values.id || uid("task"), grade }; upsert("tasks", item); } if (type === "subject") upsert("subjects", { ...values, id: values.id || uid("subject"), semester: Number(values.semester) }); if (type === "category") { const item = { ...values, id: values.id || uid("category"), weight: Number(values.weight) }; const total = state.categories.filter(category => category.subjectId === item.subjectId && category.id !== item.id).reduce((sum, category) => sum + category.weight, 0) + item.weight; if (total > 100) return toast("Category weights cannot exceed 100%."); upsert("categories", item); } if (type === "topic") upsert("topics", { ...values, id: values.id || uid("topic") }); save(); document.querySelector("#sheet").close(); render(); window.scrollTo(0, 0); toast("Saved"); }
function upsert(collection, item) { const index = state[collection].findIndex(existing => existing.id === item.id); if (index >= 0) state[collection][index] = item; else state[collection].push(item); }
function deleteItem(type, id) { const labels = { task: "task", subject: "subject and all its data", category: "category", topic: "topic" }; if (!confirm(`Delete this ${labels[type]}? This cannot be undone.`)) return; if (type === "subject") { state.subjects = state.subjects.filter(item => item.id !== id); state.categories = state.categories.filter(item => item.subjectId !== id); state.tasks = state.tasks.filter(item => item.subjectId !== id); state.topics = state.topics.filter(item => item.subjectId !== id); } if (type === "category") { state.categories = state.categories.filter(item => item.id !== id); state.tasks = state.tasks.map(item => item.categoryId === id ? { ...item, categoryId: "" } : item); } if (type === "task") state.tasks = state.tasks.filter(item => item.id !== id); if (type === "topic") state.topics = state.topics.filter(item => item.id !== id); save(); document.querySelector("#sheet").close(); render(); toast("Deleted"); }
function menu() { openSheet("Your data", `<div class="menu-list"><button type="button" data-action="export">Export backup</button><button type="button" data-action="import">Import backup</button><button type="button" data-action="reset">Restore sample data</button></div><input id="import-file" type="file" accept="application/json" hidden>`); document.querySelector('[data-action="export"]').onclick = exportData; document.querySelector('[data-action="import"]').onclick = () => document.querySelector("#import-file").click(); document.querySelector("#import-file").onchange = importData; document.querySelector('[data-action="reset"]').onclick = () => { if (confirm("Replace your local data with the sample data?")) { state = seed(); save(); document.querySelector("#sheet").close(); render(); toast("Sample data restored"); } }; }
function exportData() { const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([JSON.stringify(state, null, 2)], { type: "application/json" })); link.download = `study-flow-backup-${new Date().toISOString().slice(0, 10)}.json`; link.click(); URL.revokeObjectURL(link.href); toast("Backup downloaded"); }
function importData(event) { const file = event.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => { try { const incoming = JSON.parse(reader.result); if (!["subjects", "categories", "tasks", "topics"].every(key => Array.isArray(incoming[key]))) throw Error(); state = incoming; save(); document.querySelector("#sheet").close(); render(); toast("Backup imported"); } catch { toast("That file is not a Study Flow backup."); } }; reader.readAsText(file); }

document.querySelector("#menu-button").addEventListener("click", menu);
document.querySelector("#theme-button").addEventListener("click", () => applyTheme(document.body.classList.contains("dark") ? "light" : "dark"));
applyTheme(localStorage.getItem("study-flow-theme") || "light");
if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js"));
render();
