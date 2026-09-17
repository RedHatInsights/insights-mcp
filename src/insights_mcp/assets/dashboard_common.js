function showError(msg) {
    const el = document.getElementById("alert");
    el.textContent = msg;
    el.classList.remove("hidden");
}

function hideError() {
    document.getElementById("alert").classList.add("hidden");
}

async function callTool(name, args) {
    if (!window.mcpApp) { showError("MCP App not connected"); return null; }
    try {
        const result = await window.mcpApp.callServerTool({ name, arguments: args });
        const text = result.content?.find(c => c.type === "text")?.text;
        if (!text) { showError("No response from server"); return null; }
        try { return JSON.parse(text); } catch { showError(text); return null; }
    } catch (e) {
        showError(e.message || "Tool call failed");
        return null;
    }
}

function severityLabel(impact) {
    if (typeof impact === "string") return impact;
    const map = { 7: "Critical", 5: "Important", 4: "Moderate", 2: "Low", 1: "None", 0: "NotSet" };
    return map[impact] || "Unknown";
}

function severityClass(impact) {
    const label = (typeof impact === "string" ? impact : severityLabel(impact)).toLowerCase();
    const map = { critical: "severity-critical", important: "severity-important", moderate: "severity-moderate", low: "severity-low", none: "severity-none", notset: "severity-none" };
    return map[label] || "severity-none";
}

function renderPageButtons(current, total, containerEl) {
    const show = new Set([1, total, current, current - 1, current + 1]);
    if (current > 3) show.add(current - 2);
    if (current < total - 2) show.add(current + 2);
    const sorted = [...show].filter(p => p >= 1 && p <= total).sort((a, b) => a - b);
    let html = `<button class="btn btn-back" onclick="goToPage(${current - 1})" ${current === 1 ? 'disabled' : ''}>&laquo;</button>`;
    let prev = 0;
    for (const p of sorted) {
        if (prev && p - prev > 1) html += `<span class="page-ellipsis">...</span>`;
        html += `<button class="btn btn-page ${p === current ? 'btn-secondary' : 'btn-back'}" onclick="goToPage(${p})">${p}</button>`;
        prev = p;
    }
    html += `<button class="btn btn-back" onclick="goToPage(${current + 1})" ${current === total ? 'disabled' : ''}>&raquo;</button>`;
    containerEl.innerHTML = html;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function connectMcpApp(appName, appVersion, onToolResult) {
    import("https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps").then(module => {
        const App = module.App || module.default?.App || module.default;
        const app = new (App.App || App)({ name: appName, version: appVersion });
        app.connect();
        window.mcpApp = app;

        app.onhostcontextchanged = (ctx) => {
            const theme = ctx?.theme || "light";
            document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light");
        };

        app.ontoolresult = (result) => {
            const sc = result.structuredContent;
            if (sc && sc.query) {
                onToolResult(sc.query);
            }
        };
    }).catch(err => {
        showError("Failed to load MCP Apps SDK: " + err.message);
    });
}
