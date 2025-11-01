const defaultApiUrl = window.location.hostname.includes("localhost")
  ? "http://localhost:8000"
  : "https://sistema-de-optimizacion-logistica.onrender.com";

const CONFIG = window.APP_CONFIG || {
  apiBaseUrl: defaultApiUrl,
  mapboxToken: "",
};

const state = {
  token: null,
  trucks: [],
  stops: [],
  map: null,
  mapLayers: [],
  markers: [],
};

const colors = ["#2563eb", "#16a34a", "#f97316", "#dc2626", "#8b5cf6", "#0ea5e9"];

const selectors = {
  loginForm: document.getElementById("login-form"),
  registerForm: document.getElementById("register-form"),
  truckForm: document.getElementById("truck-form"),
  stopForm: document.getElementById("stop-form"),
  truckList: document.getElementById("truck-list"),
  stopList: document.getElementById("stop-list"),
  authSection: document.getElementById("auth-section"),
  builderSection: document.getElementById("builder-section"),
  historySection: document.getElementById("history-section"),
  resultsSection: document.getElementById("results-section"),
  summary: document.getElementById("summary"),
  assignments: document.getElementById("assignments"),
  historyList: document.getElementById("history-list"),
  optimizeBtn: document.getElementById("optimize-btn"),
  resetBtn: document.getElementById("reset-btn"),
  executionDate: document.getElementById("execution-date"),
  tabLogin: document.getElementById("tab-login"),
  tabRegister: document.getElementById("tab-register"),
  loginFormElem: document.getElementById("login-form"),
  registerFormElem: document.getElementById("register-form"),
};

const formatDateTimeCentral = (value) => {
  if (!value) return "Fecha no disponible";
  const date = new Date(value);
  return new Intl.DateTimeFormat("es-ES", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZone: "America/Chicago",
  }).format(date);
};

const apiFetch = async (url, options = {}) => {
  const headers = options.headers || {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  headers["Content-Type"] = "application/json";

  const response = await fetch(`${CONFIG.apiBaseUrl}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Error al comunicar con el servidor");
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
};

const switchTab = (target) => {
  const forms = document.querySelectorAll("#auth-section .form");
  forms.forEach((form) => form.classList.remove("active"));

  if (target === "login") {
    selectors.tabLogin.classList.add("active");
    selectors.tabRegister.classList.remove("active");
    selectors.loginForm.classList.add("active");
  } else {
    selectors.tabRegister.classList.add("active");
    selectors.tabLogin.classList.remove("active");
    selectors.registerForm.classList.add("active");
  }
};

const notify = (message, type = "info") => {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("visible"), 50);
  setTimeout(() => {
    toast.classList.remove("visible");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
};

const renderList = (container, items, formatter) => {
  container.innerHTML = "";
  items.forEach((item, index) => {
    const li = document.createElement("li");
    li.className = "chip";
    li.innerHTML = formatter(item, index);
    container.appendChild(li);
  });
};

const renderTrucks = () => {
  renderList(selectors.truckList, state.trucks, (truck, index) => {
    return `
      <span><strong>${truck.name}</strong> - ${truck.start} -> ${truck.end}</span>
      <button class="remove" data-index="${index}" data-type="truck" title="Eliminar">x</button>
    `;
  });
};

const renderStops = () => {
  renderList(selectors.stopList, state.stops, (stop, index) => {
    return `
      <span>${stop.address}</span>
      <button class="remove" data-index="${index}" data-type="stop" title="Eliminar">x</button>
    `;
  });
};

const clearMap = () => {
  if (!state.map) return;
  state.mapLayers.forEach((layerId) => {
    if (state.map.getLayer(layerId)) {
      state.map.removeLayer(layerId);
    }
    if (state.map.getSource(layerId)) {
      state.map.removeSource(layerId);
    }
  });
  state.mapLayers = [];
  state.markers.forEach((marker) => marker.remove());
  state.markers = [];
};

const renderMap = (assignments) => {
  if (!state.map || !assignments.length) return;
  clearMap();

  const bounds = new mapboxgl.LngLatBounds();

  assignments.forEach((assignment, index) => {
    const color = colors[index % colors.length];
    const sourceId = `route-${index}`;

    let geometry = assignment.geometry;
    if (!geometry || !geometry.coordinates || !geometry.coordinates.length) {
      const coords = assignment.stops
        .filter((stop) => stop.longitude !== null && stop.latitude !== null)
        .map((stop) => [stop.longitude, stop.latitude]);
      geometry = { type: "LineString", coordinates: coords };
    }

    if (!geometry.coordinates.length) {
      return;
    }

    state.map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {},
        geometry,
      },
    });
    state.map.addLayer({
      id: sourceId,
      type: "line",
      source: sourceId,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": color, "line-width": 5, "line-opacity": 0.8 },
    });
    state.mapLayers.push(sourceId);

    assignment.stops.forEach((stop, stopIndex) => {
      if (stop.longitude === null || stop.latitude === null) return;
      bounds.extend([stop.longitude, stop.latitude]);
      const el = document.createElement("div");
      el.className = "marker";
      el.style.backgroundColor = color;
      el.textContent = stopIndex;
      state.markers.push(
        new mapboxgl.Marker(el)
          .setLngLat([stop.longitude, stop.latitude])
          .setPopup(new mapboxgl.Popup({ offset: 24 }).setHTML(`<strong>${assignment.truck_name}</strong><br/>${stop.address}`))
          .addTo(state.map)
      );
    });
  });

  if (!bounds.isEmpty()) {
    state.map.fitBounds(bounds, { padding: 40 });
  }
};

const renderSummary = (summary, unassigned) => {
  selectors.summary.innerHTML = `
    <p><strong>Camiones utilizados:</strong> ${summary.trucks_needed}</p>
    <p><strong>Distancia total:</strong> ${summary.total_distance_km} km</p>
    <p><strong>Duraci\u00f3n estimada:</strong> ${summary.total_duration_minutes} minutos</p>
    <p><strong>Paradas sin asignar:</strong> ${summary.unassigned_stops}</p>
  `;

  if (unassigned && unassigned.length) {
    const list = unassigned.map((stop) => `<li>${stop.address}</li>`).join("");
    selectors.summary.innerHTML += `<details><summary>Paradas sin asignar</summary><ul>${list}</ul></details>`;
  }
};

const renderAssignments = (assignments) => {
  selectors.assignments.innerHTML = "";
  assignments.forEach((assignment, index) => {
    const routeCard = document.createElement("div");
    routeCard.className = "route-card";
    const assignedStopsList =
      assignment.assigned_stops && assignment.assigned_stops.length
        ? assignment.assigned_stops
            .map(
              (stop, idx) =>
                `<li><span class="badge">${idx + 1}</span> ${stop.address}</li>`
            )
            .join("")
        : `<li>Sin paradas de recolección asignadas</li>`;
    const stopsList = assignment.stops
      .map(
        (stop) =>
      `<li><strong>${Math.round(stop.eta_minutes ?? 0)} min</strong> - ${stop.address}</li>`
      )
      .join("");
    routeCard.innerHTML = `
      <h4>${assignment.truck_name} - ${assignment.zone_label}</h4>
      <p><strong>Duraci\u00f3n:</strong> ${assignment.total_duration_minutes} min - <strong>Distancia:</strong> ${assignment.total_distance_km} km</p>
      <a href="${assignment.google_maps_link}" target="_blank" rel="noopener">Ver en Google Maps</a>
      <div class="assigned-section">
        <p class="section-title">Paradas de recolección</p>
        <ul class="assigned-list">${assignedStopsList}</ul>
      </div>
      <div class="route-section">
        <p class="section-title">Recorrido completo</p>
        <ul>${stopsList}</ul>
      </div>
    `;
    selectors.assignments.appendChild(routeCard);
  });
};

const renderHistory = (history) => {
  selectors.historyList.innerHTML = "";
  history.forEach((record) => {
    const li = document.createElement("li");
    const formatted = formatDateTimeCentral(record.run_date);
  const routes = record.truck_assignments
    .map(
      (route) => {
        const assigned =
          route.assigned_stops && route.assigned_stops.length
            ? `<ul class="history-assigned">${route.assigned_stops
                .map((stop) => `<li>${stop.address}</li>`)
                .join("")}</ul>`
            : `<p class="history-no-stops">Sin paradas asignadas</p>`;
        return `<li>${route.truck_name}: <a href="${route.google_maps_link}" target="_blank" rel="noopener">Google Maps</a>${assigned}</li>`;
      }
      )
      .join("");
    li.innerHTML = `
      <p><strong>${formatted}</strong> - ${record.execution_date ?? "Fecha no definida"}</p>
      <ul>${routes}</ul>
    `;
    selectors.historyList.appendChild(li);
  });
};

const fetchHistory = async () => {
  try {
    const history = await apiFetch("/api/routes/history", { method: "GET" });
    renderHistory(history || []);
    selectors.historySection.classList.toggle("hidden", !history.length);
  } catch (error) {
    console.error(error);
  }
};

const handleLogin = async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const data = Object.fromEntries(formData.entries());
  try {
    const token = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
      headers: { "Content-Type": "application/json" },
    });
    state.token = token.access_token;
    selectors.authSection.classList.add("hidden");
    selectors.builderSection.classList.remove("hidden");
  selectors.resultsSection.classList.remove("hidden");
  requestAnimationFrame(() => {
    if (state.map) {
      state.map.resize();
    }
  });
  await fetchHistory();
    notify("Ses\u00f3n iniciada correctamente", "success");
  } catch (error) {
    notify("No se pudo iniciar sesi\u00f3n. Revisa tus credenciales.", "error");
  }
};

const handleRegister = async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const data = Object.fromEntries(formData.entries());
  try {
    await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
      headers: { "Content-Type": "application/json" },
    });
    notify("Cuenta creada, ahora inicia sesi\u00f3n.", "success");
    switchTab("login");
  } catch (error) {
    notify("No se pudo registrar el usuario.", "error");
  }
};

const handleAddTruck = (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const name = formData.get("name")?.trim();
  const start = formData.get("start")?.trim();
  const end = formData.get("end")?.trim();

  if (!name || !start || !end) return;
  state.trucks.push({ id: crypto.randomUUID(), name, start, end });
  renderTrucks();
  event.target.reset();
};

const handleAddStop = (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const address = formData.get("address")?.trim();
  if (!address) return;
  state.stops.push({ id: crypto.randomUUID(), address });
  renderStops();
  event.target.reset();
};

const handleRemoveItem = (event) => {
  if (!event.target.matches(".remove")) return;
  const type = event.target.dataset.type;
  const index = Number(event.target.dataset.index);
  if (Number.isNaN(index)) return;
  if (type === "truck") {
    state.trucks.splice(index, 1);
    renderTrucks();
  } else if (type === "stop") {
    state.stops.splice(index, 1);
    renderStops();
  }
};

const handleOptimize = async () => {
  if (!state.trucks.length) {
    notify("Agrega al menos un cami\u00f3n", "warning");
    return;
  }
  if (!state.stops.length) {
    notify("Agrega paradas antes de optimizar", "warning");
    return;
  }

  selectors.optimizeBtn.disabled = true;
  selectors.optimizeBtn.textContent = "Optimizando...";

  const payload = {
    trucks: state.trucks.map((truck) => ({
      id: truck.id,
      name: truck.name,
      start_address: truck.start,
      end_address: truck.end,
    })),
    stops: state.stops.map((stop) => ({ id: stop.id, address: stop.address })),
    execution_date: selectors.executionDate.value || null,
  };

  try {
    const result = await apiFetch("/api/routes/optimize", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderSummary(result.summary, result.unassigned);
    renderAssignments(result.assignments);
    renderMap(result.assignments);
    if (state.map) {
      setTimeout(() => state.map.resize(), 50);
    }
    await fetchHistory();
    notify("Optimizaci\u00f3n completada", "success");
  } catch (error) {
    notify("La optimizaci\u00f3n fall\u00f3. Revisa la consola o los datos.", "error");
    console.error(error);
  } finally {
    selectors.optimizeBtn.disabled = false;
    selectors.optimizeBtn.textContent = "Optimizar rutas";
  }
};

const handleReset = () => {
  state.trucks = [];
  state.stops = [];
  renderTrucks();
  renderStops();
  clearMap();
  selectors.summary.innerHTML = "";
  selectors.assignments.innerHTML = "";
  notify("Configuraci\u00f3n reiniciada", "info");
};

const setupMap = () => {
  if (!CONFIG.mapboxToken || CONFIG.mapboxToken === "YOUR_MAPBOX_TOKEN") {
    console.warn("Configura tu token de Mapbox en config.js");
    return;
  }
  mapboxgl.accessToken = CONFIG.mapboxToken;
  state.map = new mapboxgl.Map({
    container: "map",
    style: "mapbox://styles/mapbox/streets-v12",
    center: [-94.8467, 39.7686],
    zoom: 11,
  });
  state.map.addControl(new mapboxgl.NavigationControl());

  state.map.on("load", () => {
    state.map.resize();
  });
  window.addEventListener("resize", () => {
    if (state.map) {
      state.map.resize();
    }
  });
  setTimeout(() => {
    if (state.map) {
      state.map.resize();
    }
  }, 100);

  const mapParent = document.getElementById("map-container");
  if (mapParent && "ResizeObserver" in window) {
    const observer = new ResizeObserver(() => {
      if (state.map) {
        state.map.resize();
      }
    });
    observer.observe(mapParent);
  }
};

const init = () => {
  setupMap();

  selectors.tabLogin.addEventListener("click", () => switchTab("login"));
  selectors.tabRegister.addEventListener("click", () => switchTab("register"));
  selectors.loginForm.addEventListener("submit", handleLogin);
  selectors.registerForm.addEventListener("submit", handleRegister);
  selectors.truckForm.addEventListener("submit", handleAddTruck);
  selectors.stopForm.addEventListener("submit", handleAddStop);
  selectors.truckList.addEventListener("click", handleRemoveItem);
  selectors.stopList.addEventListener("click", handleRemoveItem);
  selectors.optimizeBtn.addEventListener("click", handleOptimize);
  selectors.resetBtn.addEventListener("click", handleReset);
};

document.addEventListener("DOMContentLoaded", init);
