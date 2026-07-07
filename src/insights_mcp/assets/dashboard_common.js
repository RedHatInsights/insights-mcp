(function () {
    "use strict";

    const MCP_APPS_SDK_URL = "__INSIGHTS_MCP_APPS_SDK_URL__";

    function showError(msg) {
        const el = document.getElementById("alert");
        el.textContent = msg;
        el.classList.remove("hidden");
    }

    function hideError() {
        document.getElementById("alert").classList.add("hidden");
    }

    async function callTool(name, args) {
        if (!window.mcpApp) {
            showError("MCP App not connected");
            return null;
        }
        try {
            const result = await window.mcpApp.callServerTool({ name, arguments: args });
            const text = result.content?.find(c => c.type === "text")?.text;
            if (!text) {
                showError("No response from server");
                return null;
            }
            try {
                return JSON.parse(text);
            } catch {
                showError(text);
                return null;
            }
        } catch (e) {
            showError(e.message || "Tool call failed");
            return null;
        }
    }

    function severityLabel(impact) {
        if (typeof impact === "string") {
            return impact;
        }
        const map = { 7: "Critical", 5: "Important", 4: "Moderate", 2: "Low", 1: "None", 0: "NotSet" };
        return map[impact] || "Unknown";
    }

    function severityClass(impact) {
        const label = (typeof impact === "string" ? impact : severityLabel(impact)).toLowerCase();
        const map = {
            critical: "severity-critical",
            important: "severity-important",
            moderate: "severity-moderate",
            low: "severity-low",
            none: "severity-none",
            notset: "severity-none",
        };
        return map[label] || "severity-none";
    }

    function parseToolResultArray(result) {
        const sc = result.structuredContent;
        if (sc) {
            const arr = sc.results || sc.data;
            if (arr && Array.isArray(arr)) {
                return arr;
            }
        }

        const text = result.content?.find(c => c.type === "text")?.text;
        if (!text) {
            return null;
        }

        try {
            let data = JSON.parse(text);
            if (data.content && Array.isArray(data.content)) {
                const innerText = data.content.find(c => c.type === "text")?.text;
                if (innerText) {
                    try {
                        data = JSON.parse(innerText);
                    } catch {
                        /* keep outer parsed data */
                    }
                }
            }
            const arr = data.results || data.data;
            if (arr && Array.isArray(arr)) {
                return arr;
            }
        } catch {
            /* initial result may not be JSON */
        }
        return null;
    }

    function renderPageButtons(current, total) {
        const container = document.getElementById("page-buttons");
        const show = new Set([1, total, current, current - 1, current + 1]);
        if (current > 3) {
            show.add(current - 2);
        }
        if (current < total - 2) {
            show.add(current + 2);
        }

        const sorted = [...show].filter(p => p >= 1 && p <= total).sort((a, b) => a - b);
        let html = `<button class="btn btn-back" onclick="goToPage(${current - 1})" ${current === 1 ? "disabled" : ""}>&laquo;</button>`;
        let prev = 0;
        for (const p of sorted) {
            if (prev && p - prev > 1) {
                html += `<span class="page-ellipsis">...</span>`;
            }
            html += `<button class="btn ${p === current ? "btn-secondary" : "btn-back"} btn-page" onclick="goToPage(${p})">${p}</button>`;
            prev = p;
        }
        html += `<button class="btn btn-back" onclick="goToPage(${current + 1})" ${current === total ? "disabled" : ""}>&raquo;</button>`;
        container.innerHTML = html;
    }

    function renderCveDetailHtml(cveId, attrs, footerHtml) {
        const impact = attrs.impact || 0;
        const cvss3 = attrs.cvss3_score || "N/A";
        const cvss2 = attrs.cvss2_score || "N/A";
        const published = attrs.public_date ? new Date(attrs.public_date).toLocaleDateString() : "N/A";
        const modified = attrs.modified_date ? new Date(attrs.modified_date).toLocaleDateString() : "N/A";
        const desc = attrs.description || "No description available.";
        const advisories = attrs.advisories_list || [];
        const redhatUrl = `https://access.redhat.com/security/cve/${cveId}`;

        return (
            `<div class="detail-description-wrap">`
            + `<p class="detail-description">${desc}</p>`
            + `</div>`
            + `<div class="detail-grid">`
            + `<span class="detail-label">Severity</span>`
            + `<span class="detail-value"><span class="severity ${severityClass(impact)}">${severityLabel(impact)}</span></span>`
            + `<span class="detail-label">CVSS 3</span>`
            + `<span class="detail-value cvss">${cvss3}</span>`
            + `<span class="detail-label">CVSS 2</span>`
            + `<span class="detail-value cvss">${cvss2}</span>`
            + `<span class="detail-label">Published</span>`
            + `<span class="detail-value">${published}</span>`
            + `<span class="detail-label">Modified</span>`
            + `<span class="detail-value">${modified}</span>`
            + `<span class="detail-label">Red Hat</span>`
            + `<span class="detail-value"><a href="${redhatUrl}" target="_blank">${redhatUrl}</a></span>`
            + (advisories.length
                ? `<span class="detail-label">Advisories</span><span class="detail-value">${advisories.map(a => `<a href="${a}" target="_blank">${a.split("/").pop()}</a>`).join(", ")}</span>`
                : "")
            + `</div>`
            + (footerHtml || "")
        );
    }

    function connectMcpApp(appName, onToolResult) {
        import(MCP_APPS_SDK_URL).then(module => {
            const App = module.App || module.default?.App || module.default;
            const app = new (App.App || App)({ name: appName, version: "1.0.0" });
            app.connect();
            window.mcpApp = app;

            app.onhostcontextchanged = (ctx) => {
                const theme = ctx?.theme || "light";
                document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light");
            };

            app.ontoolresult = onToolResult;
        }).catch(err => {
            showError("Failed to load MCP Apps SDK: " + err.message);
        });
    }

    window.InsightsDashboard = {
        showError,
        hideError,
        callTool,
        severityLabel,
        severityClass,
        parseToolResultArray,
        renderPageButtons,
        renderCveDetailHtml,
        connectMcpApp,
    };
})();
