import http from "node:http";

const PORT = 3001;

let initialTasks = [
  { id: 1, title: "Review system architecture", priority: "High", completed: false },
  { id: 2, title: "Seed SQLite database", priority: "Medium", completed: true },
  { id: 3, title: "Update dependency lockfile", priority: "Low", completed: false }
];

let tasks = JSON.parse(JSON.stringify(initialTasks));

const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DevApp Task Manager</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
    .container { max-width: 600px; margin: 0 auto; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
    h1 { font-size: 24px; margin-top: 0; color: #38bdf8; }
    .toolbar { display: flex; gap: 8px; margin-bottom: 20px; }
    input, select, button { padding: 10px 14px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 14px; }
    button { background: #0284c7; border: none; font-weight: bold; cursor: pointer; }
    button:hover { background: #0369a1; }
    .task-list { list-style: none; padding: 0; margin: 0; }
    .task-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-bottom: 1px solid #334155; }
    .task-item.completed span { text-decoration: line-through; color: #94a3b8; }
    .badge { font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600; }
    .badge-active { background: #064e3b; color: #34d399; }
    .badge-completed { background: #312e81; color: #a5b4fc; }
    .btn-complete { background: #059669; font-size: 12px; padding: 6px 10px; margin-left: 8px; }
    .btn-delete { background: #dc2626; font-size: 12px; padding: 6px 10px; margin-left: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>DevApp Task Manager</h1>
    <p style="color: #94a3b8; font-size: 13px;">Isolated development target for prompt calibration (Invariant D13).</p>
    
    <div class="toolbar">
      <input type="text" id="task-title" aria-label="Task title" placeholder="New task description..." style="flex: 1;" />
      <select id="task-priority" aria-label="Task priority">
        <option value="High">High</option>
        <option value="Medium" selected>Medium</option>
        <option value="Low">Low</option>
      </select>
      <button id="add-btn" aria-label="Add Task">Add Task</button>
    </div>

    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <span id="task-count" style="font-size: 13px; color: #94a3b8;">Total tasks: 3</span>
      <div>
        <label for="priority-filter" style="font-size: 13px; color: #94a3b8; margin-right: 4px;">Filter:</label>
        <select id="priority-filter" aria-label="Filter by priority">
          <option value="All">All</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>
    </div>

    <ul class="task-list" id="tasks-container"></ul>
  </div>

  <script>
    let tasks = [
      { id: 1, title: "Review system architecture", priority: "High", completed: false },
      { id: 2, title: "Seed SQLite database", priority: "Medium", completed: true },
      { id: 3, title: "Update dependency lockfile", priority: "Low", completed: false }
    ];

    function render() {
      const filter = document.getElementById("priority-filter").value;
      const container = document.getElementById("tasks-container");
      container.innerHTML = "";

      const filtered = tasks.filter(t => filter === "All" || t.priority === filter);
      document.getElementById("task-count").textContent = "Total tasks: " + tasks.length;

      filtered.forEach(task => {
        const li = document.createElement("li");
        li.className = "task-item" + (task.completed ? " completed" : "");
        
        const info = document.createElement("div");
        info.innerHTML = "<span>" + task.title + "</span> " +
          "<span class='badge " + (task.completed ? "badge-completed" : "badge-active") + "' role='status'>" + 
          (task.completed ? "Completed" : "Active") + " (" + task.priority + ")</span>";

        const actions = document.createElement("div");
        if (!task.completed) {
          const btnComp = document.createElement("button");
          btnComp.className = "btn-complete";
          btnComp.textContent = "Complete Task";
          btnComp.setAttribute("aria-label", "Complete Task");
          btnComp.onclick = () => { task.completed = true; render(); };
          actions.appendChild(btnComp);
        }

        const btnDel = document.createElement("button");
        btnDel.className = "btn-delete";
        btnDel.textContent = "Delete Task";
        btnDel.setAttribute("aria-label", "Delete Task");
        btnDel.onclick = () => { tasks = tasks.filter(t => t.id !== task.id); render(); };
        actions.appendChild(btnDel);

        li.appendChild(info);
        li.appendChild(actions);
        container.appendChild(li);
      });
    }

    document.getElementById("add-btn").onclick = () => {
      const input = document.getElementById("task-title");
      const priority = document.getElementById("task-priority").value;
      if (!input.value.trim()) return;

      tasks.push({
        id: Date.now(),
        title: input.value.trim(),
        priority: priority,
        completed: false
      });
      input.value = "";
      render();
    };

    document.getElementById("priority-filter").onchange = render;
    render();
  </script>
</body>
</html>`;

const server = http.createServer((req, res) => {
  if (req.url === "/api/reset" && req.method === "POST") {
    tasks = JSON.parse(JSON.stringify(initialTasks));
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ success: true, tasks }));
    return;
  }

  res.writeHead(200, { "Content-Type": "text/html" });
  res.end(htmlContent);
});

server.listen(PORT, () => {
  console.log(`DevApp server listening on http://localhost:${PORT}`);
});
