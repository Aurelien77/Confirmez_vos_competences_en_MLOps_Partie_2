let token = null;
let historyData = [];

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("loginUsername").addEventListener("keypress", function(e) {
        if (e.key === "Enter") login();
    });
    document.getElementById("loginPassword").addEventListener("keypress", function(e) {
        if (e.key === "Enter") login();
    });
});

function toggleAuth() {
    const isRegister = document.getElementById("authSwitch").checked;
    document.getElementById("loginSection").classList.toggle("hidden", isRegister);
    document.getElementById("registerSection").classList.toggle("hidden", !isRegister);
    document.getElementById("authResult").classList.add("hidden");
}

function toggleSection(id) {
    document.getElementById(id).classList.toggle("hidden");
}

async function register() {
    const username = document.getElementById("regUsername").value.trim();
    const password = document.getElementById("regPassword").value;
    if (username.length < 3) return showAuthResult("Nom d'utilisateur trop court (min 3)", true);
    if (password.length < 6) return showAuthResult("Mot de passe trop court (min 6)", true);
    if (password.length > 72) return showAuthResult("Mot de passe trop long (max 72)", true);

    const res = await fetch("/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
    });
    const data = await res.json();
    showAuthResult(res.ok ? `Compte créé (${username})` : (data.detail || "Erreur"), !res.ok);
}

async function login() {
    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;
    const res = await fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
    });
    const data = await res.json();
    if (res.ok) {
        token = data.access_token;
        document.getElementById("switchContainer").classList.add("hidden");
        document.getElementById("loginSection").classList.add("hidden");
        document.getElementById("registerSection").classList.add("hidden");
        document.getElementById("profileToggleBtn").classList.remove("hidden");
        document.getElementById("historyToggleBtn").classList.remove("hidden");
        document.getElementById("predictSection").classList.remove("hidden");
        
        const isAdmin = data.is_admin === true || data.role === "admin";
        
        const badge = document.getElementById("userBadge");
        badge.innerText = `Connecté : ${username}${isAdmin ? " (Admin)" : ""}`;
        badge.classList.remove("hidden");
        
        document.getElementById("userInfo").innerText = `Connecté : ${username}${isAdmin ? " (Admin)" : ""}`;
        document.getElementById("authResult").classList.add("hidden");
        
        if (isAdmin) {
            document.getElementById("adminToggleBtn").classList.remove("hidden");
        }
    } else {
        showAuthResult(data.detail || "Erreur de connexion", true);
    }
}

function logout() {
    token = null;
    ["profileSection", "historySection", "adminSection", "predictSection"].forEach(id => {
        document.getElementById(id).classList.add("hidden");
    });
    ["profileToggleBtn", "historyToggleBtn", "adminToggleBtn"].forEach(id => {
        document.getElementById(id).classList.add("hidden");
    });
    document.getElementById("userBadge").classList.add("hidden");
    document.getElementById("switchContainer").classList.remove("hidden");
    document.getElementById("loginSection").classList.remove("hidden");
    document.getElementById("authSwitch").checked = false;
    toggleAuth();
    document.getElementById("authResult").classList.add("hidden");
    document.getElementById("result").classList.add("hidden");
}

async function changePassword() {
    if (!token) return;
    const oldPassword = document.getElementById("oldPassword").value;
    const newPassword = document.getElementById("newPassword").value;
    if (newPassword.length < 6) return showPasswordResult("Nouveau mot de passe trop court", true);

    const res = await fetch("/change-password", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token}`},
        body: JSON.stringify({old_password: oldPassword, new_password: newPassword})
    });
    const data = await res.json();
    showPasswordResult(res.ok ? data.message : (data.detail || "Erreur"), !res.ok);
}

async function predict() {
    if (!token) return alert("Connectez-vous d'abord");
    const clientId = document.getElementById("clientId").value;
    const resultDiv = document.getElementById("result");
    resultDiv.classList.remove("hidden");
    resultDiv.innerHTML = "Chargement...";

    try {
        const res = await fetch("/predict", {
            method: "POST",
            headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token}`},
            body: JSON.stringify({client_id: parseInt(clientId)})
        });
        const data = await res.json();
        if (!res.ok) {
            resultDiv.innerHTML = `<span class="error">${data.detail || "Erreur"}</span>`;
            return;
        }
        resultDiv.innerHTML = `
            <strong>Client :</strong> ${data.client_id || "N/A"}<br>
            <strong>Probabilité de défaut :</strong> ${(data.probabilite_defaut * 100).toFixed(2)} %<br>
            <strong>Risque :</strong> ${data.risque === 1 ? "Élevé" : "Faible"}
        `;
    } catch (e) {
        resultDiv.innerHTML = `<span class="error">Erreur de communication</span>`;
    }
}

async function loadHistory(sort = "recent") {
    if (!token) return;
    try {
        const res = await fetch("/my-predictions", {headers: {"Authorization": `Bearer ${token}`}});
        if (!res.ok) throw new Error("Erreur serveur");
        const data = await res.json();
        historyData = data.predictions || [];

        if (sort === "proba_desc") {
            historyData.sort((a, b) => (b.probabilite_defaut || 0) - (a.probabilite_defaut || 0));
        } else if (sort === "proba_asc") {
            historyData.sort((a, b) => (a.probabilite_defaut || 0) - (b.probabilite_defaut || 0));
        }

        const div = document.getElementById("historyContent");
        if (historyData.length === 0) {
            div.innerHTML = "Aucune prédiction.";
            return;
        }
        div.innerHTML = historyData.map(p => `
            <div class="log-item">
                ${new Date(p.timestamp).toLocaleString()} — Client: ${p.client_id || "N/A"} 
                — ${(p.probabilite_defaut * 100).toFixed(1)}% — Risque: ${p.risque ?? "N/A"}
            </div>
        `).join("");
    } catch (e) {
        document.getElementById("historyContent").innerHTML = `<span class="error">Impossible de charger l'historique</span>`;
    }
}

async function loadAdminDashboard() {
    if (!token) return;
    try {
        const res = await fetch("/admin/dashboard", {headers: {"Authorization": `Bearer ${token}`}});
        if (!res.ok) {
            document.getElementById("adminContent").innerHTML = "<span class='error'>Accès refusé ou erreur serveur</span>";
            return;
        }
        const data = await res.json();
        const m = data.metrics;
        document.getElementById("adminContent").innerHTML = `
            <strong>Métriques (24 dernières heures)</strong><br>
            Total appels : ${m.total_24h}<br>
            Latence moyenne : ${m.avg_latency_ms} ms<br>
            Probabilité moyenne : ${(m.avg_proba*100).toFixed(2)} %<br>
            Erreurs : ${m.errors_24h}<br><br>
            <strong>Derniers logs</strong><br>
            ${data.logs.slice(0, 15).map(l => `
                <div class="log-item">${l.username} — ${l.client_id || "N/A"} — ${(l.probabilite_defaut*100).toFixed(1)}%</div>
            `).join("")}
        `;
    } catch (e) {
        document.getElementById("adminContent").innerHTML = `<span class="error">Erreur de chargement</span>`;
    }
}

async function openDriftReport() {
    if (!token) return alert("Connectez-vous d'abord");
    
    const win = window.open("", "_blank");
    win.document.write("<h2>Chargement du rapport...</h2>");
    
    try {
        const res = await fetch("/admin/drift", {
            headers: {"Authorization": `Bearer ${token}`}
        });
        
        if (!res.ok) {
            win.document.body.innerHTML = `<h2>Erreur ${res.status}</h2><p>Accès refusé ou erreur serveur</p>`;
            return;
        }
        
        const html = await res.text();
        win.document.open();
        win.document.write(html);
        win.document.close();
    } catch (e) {
        win.document.body.innerHTML = "<h2>Erreur de communication</h2>";
    }
}

function showAuthResult(msg, isError) {
    const div = document.getElementById("authResult");
    div.classList.remove("hidden");
    div.innerHTML = isError ? `<span class="error">${msg}</span>` : msg;
}

function showPasswordResult(msg, isError) {
    const div = document.getElementById("passwordResult");
    div.classList.remove("hidden");
    div.innerHTML = isError ? `<span class="error">${msg}</span>` : msg;
}