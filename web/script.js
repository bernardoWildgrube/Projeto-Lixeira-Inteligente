const API_BASE = `${window.location.origin}/api`;

let map = null;
let markers = {};
let lixeirasCache = [];

const appView = document.getElementById("app-view");
const loginView = document.getElementById("login-view");

function isPainelPage() {
    return document.body.classList.contains("dashboard-body");
}

function isLoggedIn() {
    return localStorage.getItem("lixeiraLoggedIn") === "true";
}

function showApp() {
    if (loginView) loginView.hidden = true;
    if (appView) appView.hidden = false;
    if (isPainelPage()) carregarTudo();
}

function showLogin() {
    if (loginView) loginView.hidden = false;
    if (appView) appView.hidden = true;
}

async function api(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Erro ao comunicar com a API");
    }
    return response.json();
}

function initMap() {
    if (!isPainelPage() || map) return;

    if (typeof L === "undefined") {
        document.getElementById("map").innerHTML = "<p class='error'>Mapa indisponivel. Verifique a internet.</p>";
        return;
    }

    map = L.map("map", { scrollWheelZoom: true }).setView([-28.2628, -52.4075], 15);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
    }).addTo(map);

    setTimeout(() => map.invalidateSize(), 150);
}

function calcularPercentual(total, utilizada) {
    const capacidadeTotal = Math.max(1, Number(total) || 1);
    const capacidadeUtilizada = Math.min(Math.max(0, Number(utilizada) || 0), capacidadeTotal);
    const ocupada = (capacidadeUtilizada / capacidadeTotal) * 100;
    return {
        ocupada,
        livre: 100 - ocupada,
        capacidadeLivre: capacidadeTotal - capacidadeUtilizada,
    };
}

function badgeNivel(nivel) {
    if (nivel >= 85) return "danger";
    if (nivel >= 65) return "warn";
    return "ok";
}

function formatDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("pt-BR");
}

function popupHtml(lixeira) {
    const lat = Number(lixeira.latitude);
    const lng = Number(lixeira.longitude);
    const googleUrl = `https://www.google.com/maps?q=${lat},${lng}`;
    return `
        <strong>${lixeira.nome}</strong><br>
        ${lixeira.endereco}<br>
        Ocupada: ${Number(lixeira.nivel_ocupacao).toFixed(0)}%<br>
        Livre: ${Number(lixeira.espaco_livre).toFixed(0)}%<br>
        Tampa: ${lixeira.tampa_status}<br>
        Status: ${lixeira.status_operacional}<br>
        <a href="${googleUrl}" target="_blank" rel="noreferrer">Abrir no Google Maps</a>
    `;
}

function atualizarMapa(lixeiras) {
    initMap();
    if (!map || typeof L === "undefined") return;

    const ativos = new Set();
    lixeiras.forEach((lixeira) => {
        ativos.add(String(lixeira.id));
        const lat = Number(lixeira.latitude);
        const lng = Number(lixeira.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        const nivel = Number(lixeira.nivel_ocupacao);
        const markerColor = badgeNivel(nivel) === "danger" ? "red" : badgeNivel(nivel) === "warn" ? "yellow" : "green";
        const icon = L.divIcon({
            className: `map-pin ${markerColor}`,
            html: `<span>${nivel.toFixed(0)}%</span>`,
            iconSize: [44, 44],
            iconAnchor: [22, 22],
        });

        if (!markers[lixeira.id]) {
            markers[lixeira.id] = L.marker([lat, lng], { icon }).addTo(map);
        } else {
            markers[lixeira.id].setLatLng([lat, lng]);
            markers[lixeira.id].setIcon(icon);
        }
        markers[lixeira.id].bindPopup(popupHtml(lixeira));
    });

    Object.keys(markers).forEach((id) => {
        if (!ativos.has(id)) {
            map.removeLayer(markers[id]);
            delete markers[id];
        }
    });

    const pontos = lixeiras
        .map((lixeira) => [Number(lixeira.latitude), Number(lixeira.longitude)])
        .filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng));

    if (pontos.length > 0) {
        map.fitBounds(L.latLngBounds(pontos).pad(0.2));
    }
}

function renderAlertas(lixeiras) {
    const alertas = lixeiras.filter((lixeira) => lixeira.alertas.length > 0);
    document.getElementById("total-alertas").textContent = alertas.length;
    const container = document.getElementById("alertas");

    if (alertas.length === 0) {
        container.innerHTML = "<p class='empty'>Nenhum alerta ativo.</p>";
        return;
    }

    container.innerHTML = alertas.map((lixeira) => `
        <article class="alert-item ${Number(lixeira.nivel_ocupacao) >= 85 ? "danger" : ""}">
            <strong>${lixeira.nome}</strong>
            <p>${lixeira.alertas.join(" | ")}</p>
            <small>${formatDate(lixeira.ultima_atualizacao)}</small>
        </article>
    `).join("");
}

function renderCards(lixeiras) {
    const container = document.getElementById("lixeiras-cards");
    if (lixeiras.length === 0) {
        container.innerHTML = "<p class='empty'>Nenhuma lixeira cadastrada.</p>";
        return;
    }

    container.innerHTML = lixeiras.map((lixeira) => `
        <article class="trash-card">
            <div class="card-top">
                <div>
                    <span class="eyebrow">${lixeira.identificador}</span>
                    <h3>${lixeira.nome}</h3>
                </div>
                <span class="badge ${badgeNivel(Number(lixeira.nivel_ocupacao))}">
                    ${Number(lixeira.nivel_ocupacao).toFixed(0)}% cheia
                </span>
            </div>
            <p>${lixeira.endereco}</p>
            <div class="progress">
                <span style="width: ${Number(lixeira.nivel_ocupacao)}%"></span>
            </div>
            <dl class="info-grid">
                <div><dt>Total</dt><dd>${Number(lixeira.capacidade_total).toFixed(1)}</dd></div>
                <div><dt>Usada</dt><dd>${Number(lixeira.capacidade_utilizada).toFixed(1)}</dd></div>
                <div><dt>Falta</dt><dd>${Number(lixeira.capacidade_livre).toFixed(1)}</dd></div>
                <div><dt>Livre</dt><dd>${Number(lixeira.espaco_livre).toFixed(0)}%</dd></div>
                <div><dt>Tampa</dt><dd>${lixeira.tampa_status}</dd></div>
                <div><dt>Status</dt><dd>${lixeira.status_operacional}</dd></div>
            </dl>
            <div class="actions">
                <button class="secondary" onclick="editarLixeira(${lixeira.id})">Editar</button>
                <button class="danger-button" onclick="excluirLixeira(${lixeira.id})">Excluir</button>
            </div>
        </article>
    `).join("");
}

function renderPainelResumo(lixeiras) {
    const container = document.getElementById("painel-resumo");
    if (!container) return;

    const cheias = lixeiras.filter((lixeira) => Number(lixeira.nivel_ocupacao) >= 85);
    const tampasAbertas = lixeiras.filter((lixeira) => lixeira.tampa_status === "aberta");
    const inativas = lixeiras.filter((lixeira) => lixeira.status_operacional === "inativa");
    const criticas = [...cheias, ...tampasAbertas, ...inativas]
        .filter((lixeira, index, array) => array.findIndex((item) => item.id === lixeira.id) === index);

    container.innerHTML = `
        <article class="overview-card">
            <span class="eyebrow">Coleta</span>
            <h3>${cheias.length} lixeira(s) quase cheias</h3>
            <p>Priorize os pontos com ocupacao acima de 85%.</p>
        </article>
        <article class="overview-card">
            <span class="eyebrow">Tampas</span>
            <h3>${tampasAbertas.length} tampa(s) abertas</h3>
            <p>Verifique lixeiras que podem estar abertas indevidamente.</p>
        </article>
        <article class="overview-card">
            <span class="eyebrow">Operacao</span>
            <h3>${inativas.length} lixeira(s) inativas</h3>
            <p>Acompanhe equipamentos fora de operacao.</p>
        </article>
        <article class="overview-card wide">
            <span class="eyebrow">Atencao</span>
            <h3>Pontos prioritarios</h3>
            ${criticas.length === 0
                ? "<p>Nenhum ponto critico no momento.</p>"
                : `<div class="priority-list">${criticas.map((lixeira) => `
                    <div>
                        <strong>${lixeira.nome}</strong>
                        <span>${Number(lixeira.nivel_ocupacao).toFixed(0)}% cheia | ${lixeira.tampa_status} | ${lixeira.status_operacional}</span>
                    </div>
                `).join("")}</div>`
            }
        </article>
    `;
}

function atualizarResumo(lixeiras) {
    document.getElementById("total-lixeiras").textContent = lixeiras.length;
    document.getElementById("total-ativas").textContent = lixeiras.filter((lixeira) => lixeira.status_operacional === "ativa").length;
}

async function carregarTudo() {
    try {
        const lixeiras = await api("/lixeiras");
        lixeirasCache = lixeiras;
        atualizarResumo(lixeiras);
        renderPainelResumo(lixeiras);
        renderAlertas(lixeiras);
        renderCards(lixeiras);
        atualizarMapa(lixeiras);
    } catch (error) {
        console.error(error);
        document.getElementById("alertas").innerHTML = `<p class="error">Erro ao carregar dados da API em ${API_BASE}.</p>`;
    }
}

function limparFormulario() {
    document.getElementById("lixeira-form").reset();
    document.getElementById("lixeira-id").value = "";
    document.getElementById("capacidade_total").value = "100";
    document.getElementById("capacidade_utilizada").value = "0";
    document.getElementById("form-title").textContent = "Cadastrar lixeira";
    document.getElementById("cancel-edit").hidden = true;
    atualizarPreviewCapacidade();
}

function abrirAba(nome) {
    document.querySelectorAll(".nav-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === nome);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === `tab-${nome}`);
    });
    if (nome === "mapa") {
        setTimeout(() => {
            if (map) map.invalidateSize();
            atualizarMapa(lixeirasCache);
        }, 100);
    }
}

function atualizarPreviewCapacidade() {
    const total = document.getElementById("capacidade_total").value;
    const utilizada = document.getElementById("capacidade_utilizada").value;
    const calculo = calcularPercentual(total, utilizada);
    document.getElementById("ocupacao-preview").textContent =
        `${calculo.ocupada.toFixed(0)}% cheia | ${calculo.livre.toFixed(0)}% livre`;
}

window.editarLixeira = function editarLixeira(id) {
    const lixeira = lixeirasCache.find((item) => item.id === id);
    if (!lixeira) return;

    document.getElementById("lixeira-id").value = lixeira.id;
    document.getElementById("identificador").value = lixeira.identificador;
    document.getElementById("nome").value = lixeira.nome;
    document.getElementById("endereco").value = lixeira.endereco;
    document.getElementById("latitude").value = lixeira.latitude;
    document.getElementById("longitude").value = lixeira.longitude;
    document.getElementById("capacidade_total").value = lixeira.capacidade_total;
    document.getElementById("capacidade_utilizada").value = lixeira.capacidade_utilizada;
    document.getElementById("tampa_status").value = lixeira.tampa_status;
    document.getElementById("status_operacional").value = lixeira.status_operacional;
    document.getElementById("form-title").textContent = "Editar lixeira";
    document.getElementById("cancel-edit").hidden = false;
    atualizarPreviewCapacidade();
    abrirAba("cadastro");
};

window.excluirLixeira = async function excluirLixeira(id) {
    if (!confirm("Excluir esta lixeira?")) return;
    await api(`/lixeiras/${id}`, { method: "DELETE" });
    await carregarTudo();
    abrirAba("lixeiras");
};

function iniciarLoginSeExistir() {
    const form = document.getElementById("login-form");
    if (!form || isPainelPage()) return;

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const usuario = document.getElementById("usuario").value.trim();
        const senha = document.getElementById("senha").value;
        if (usuario === "admin" && senha === "senha123") {
            localStorage.setItem("lixeiraLoggedIn", "true");
            window.location.href = "/painel.html";
        } else {
            const erro = document.getElementById("login-error");
            erro.textContent = "Usuario ou senha incorretos. Use admin e senha123.";
            erro.hidden = false;
        }
    });
}

function iniciarPainelSeExistir() {
    if (!isPainelPage()) return;

    document.querySelectorAll(".nav-button").forEach((button) => {
        button.addEventListener("click", () => abrirAba(button.dataset.tab));
    });

    document.getElementById("refresh-button").addEventListener("click", carregarTudo);
    document.getElementById("cancel-edit").addEventListener("click", limparFormulario);
    document.getElementById("capacidade_total").addEventListener("input", atualizarPreviewCapacidade);
    document.getElementById("capacidade_utilizada").addEventListener("input", atualizarPreviewCapacidade);

    document.getElementById("lixeira-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const id = document.getElementById("lixeira-id").value;
        const payload = {
            identificador: document.getElementById("identificador").value.trim(),
            nome: document.getElementById("nome").value.trim(),
            endereco: document.getElementById("endereco").value.trim(),
            latitude: Number(document.getElementById("latitude").value),
            longitude: Number(document.getElementById("longitude").value),
            capacidade_total: Number(document.getElementById("capacidade_total").value),
            capacidade_utilizada: Number(document.getElementById("capacidade_utilizada").value),
            tampa_status: document.getElementById("tampa_status").value,
            status_operacional: document.getElementById("status_operacional").value,
        };

        if (id) {
            await api(`/lixeiras/${id}`, { method: "PUT", body: JSON.stringify(payload) });
        } else {
            await api("/lixeiras", { method: "POST", body: JSON.stringify(payload) });
        }

        limparFormulario();
        await carregarTudo();
        abrirAba("lixeiras");
    });

    initMap();
    atualizarPreviewCapacidade();
    carregarTudo();
}

iniciarLoginSeExistir();
iniciarPainelSeExistir();

setInterval(() => {
    if (isPainelPage()) carregarTudo();
}, 10000);
