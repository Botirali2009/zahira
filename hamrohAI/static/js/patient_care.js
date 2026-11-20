/* Shared medication + diagnosis view. Both a linked doctor and the patient
 * themself load this page and call the same /api/v1/care/... endpoints —
 * the server decides who may write, this script doesn't know or care which
 * side is viewing. */
(function () {
  "use strict";

  const root = document.getElementById("care-root");
  if (!root) return;

  const patientId = root.dataset.patientId;
  const medicationsEl = document.getElementById("medications");
  const diagnosesEl = document.getElementById("diagnoses");
  const medicationForm = document.getElementById("medication-form");
  const medicationError = document.getElementById("medication-error");
  const trendEl = document.getElementById("trend-chart");

  const RISK_COLOUR = { red: "#dc2626", yellow: "#d97706", green: "#0d9488" };

  function renderTrend(trend) {
    const points = trend.points || [];
    if (points.length < 2) {
      trendEl.textContent =
        "Grafik uchun kamida ikkita baholash kerak (hozir " + points.length + ").";
      return;
    }

    const W = 520, H = 120, PAD = 14;
    const stepX = (W - PAD * 2) / (points.length - 1);
    const y = (score) => H - PAD - (Math.max(0, Math.min(100, score)) / 100) * (H - PAD * 2);
    const coords = points.map((p, i) => [PAD + i * stepX, y(p.risk_score)]);

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("class", "w-full h-32");

    [[34, "#fcd34d"], [67, "#fca5a5"]].forEach(([score, colour]) => {
      const line = document.createElementNS(svgNS, "line");
      line.setAttribute("x1", PAD); line.setAttribute("x2", W - PAD);
      line.setAttribute("y1", y(score)); line.setAttribute("y2", y(score));
      line.setAttribute("stroke", colour);
      line.setAttribute("stroke-dasharray", "4 4");
      svg.appendChild(line);
    });

    const path = document.createElementNS(svgNS, "polyline");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#0f766e");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("points", coords.map((c) => c.join(",")).join(" "));
    svg.appendChild(path);

    points.forEach((p, i) => {
      const dot = document.createElementNS(svgNS, "circle");
      dot.setAttribute("cx", coords[i][0]);
      dot.setAttribute("cy", coords[i][1]);
      dot.setAttribute("r", "4");
      dot.setAttribute("fill", RISK_COLOUR[p.risk_level] || RISK_COLOUR.green);
      const title = document.createElementNS(svgNS, "title");
      title.textContent = p.risk_score + "/100 · " + p.created_at;
      dot.appendChild(title);
      svg.appendChild(dot);
    });

    trendEl.innerHTML = "";
    trendEl.appendChild(svg);
    const caption = document.createElement("div");
    caption.className = "text-xs text-slate-500 mt-1";
    caption.textContent =
      points.length + " ta baholash · hozirgi ball: " + trend.current + "/100";
    trendEl.appendChild(caption);
  }

  if (trendEl) {
    api.get("/api/v1/care/patients/" + patientId + "/trend")
      .then(renderTrend)
      .catch((err) => { trendEl.textContent = err.message; });
  }

  function replaceChildren(el, nodes, emptyMessage) {
    el.innerHTML = "";
    if (!nodes.length) {
      const empty = document.createElement("p");
      empty.className = "text-sm text-slate-400";
      empty.textContent = emptyMessage;
      el.appendChild(empty);
      return;
    }
    nodes.forEach((n) => el.appendChild(n));
  }

  function renderMedication(med) {
    const row = document.createElement("div");
    row.className = "bg-white rounded-xl border border-slate-200 p-3 flex items-center justify-between gap-3";

    const left = document.createElement("div");
    const title = document.createElement("div");
    title.className = "font-medium text-sm";
    title.textContent = med.drug_name + (med.dose ? " — " + med.dose : "");
    const meta = document.createElement("div");
    meta.className = "text-xs text-slate-500";
    meta.textContent = med.times.join(", ") + (med.active ? "" : " · to'xtatilgan");
    left.appendChild(title);
    left.appendChild(meta);

    const btn = document.createElement("button");
    btn.className = "text-xs rounded-lg border border-slate-300 px-3 py-1.5 hover:bg-slate-100";
    btn.textContent = med.active ? "To'xtatish" : "Davom ettirish";
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await api.post(
          "/api/v1/care/patients/" + patientId + "/medications/" + med.id +
            (med.active ? "/stop" : "/resume"),
          {}
        );
        await refreshMedications();
      } catch (err) {
        btn.disabled = false;
      }
    });

    row.appendChild(left);
    row.appendChild(btn);
    return row;
  }

  async function refreshMedications() {
    const { medications } = await api.get("/api/v1/care/patients/" + patientId + "/medications");
    replaceChildren(medicationsEl, medications.map(renderMedication), "Hozircha dori yo'q.");
  }

  const DIAGNOSIS_STATUS_LABEL = { active: "Faol", closed: "Yopilgan" };

  function renderDiagnosis(item) {
    const d = item.diagnosis;
    const row = document.createElement("div");
    row.className = "bg-white rounded-xl border border-slate-200 p-3";

    const head = document.createElement("div");
    head.className = "flex items-center justify-between gap-3";
    const text = document.createElement("div");
    text.className = "text-sm";
    text.textContent = d.text;
    const badge = document.createElement("span");
    badge.className = "text-xs font-medium " + (d.status === "active" ? "text-teal-700" : "text-slate-400");
    badge.textContent = DIAGNOSIS_STATUS_LABEL[d.status] || d.status;
    head.appendChild(text);
    head.appendChild(badge);
    row.appendChild(head);

    if (item.files.length) {
      const files = document.createElement("div");
      files.className = "text-xs mt-2 space-x-3";
      item.files.forEach((f) => {
        const link = document.createElement("a");
        link.href = "/files/diagnosis-files/" + f.id;
        link.target = "_blank";
        link.className = "text-teal-700 hover:underline";
        link.textContent = f.original_filename;
        files.appendChild(link);
      });
      row.appendChild(files);
    }

    const toggle = document.createElement("button");
    toggle.className = "text-xs rounded-lg border border-slate-300 px-3 py-1.5 hover:bg-slate-100 mt-2";
    toggle.textContent = d.status === "active" ? "Yopish" : "Qayta ochish";
    toggle.addEventListener("click", async () => {
      toggle.disabled = true;
      try {
        await api.post(
          "/api/v1/care/patients/" + patientId + "/diagnoses/" + d.id + "/status",
          { status: d.status === "active" ? "closed" : "active" }
        );
        await refreshDiagnoses();
      } catch (err) {
        toggle.disabled = false;
      }
    });
    row.appendChild(toggle);

    return row;
  }

  async function refreshDiagnoses() {
    const { diagnoses } = await api.get("/api/v1/care/patients/" + patientId + "/diagnoses");
    replaceChildren(diagnosesEl, diagnoses.map(renderDiagnosis), "Hozircha tashxis yo'q.");
  }

  medicationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(medicationForm);
    const times = String(data.get("times") || "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    medicationError.classList.add("hidden");
    try {
      await api.post("/api/v1/care/patients/" + patientId + "/medications", {
        drug_name: data.get("drug_name"),
        dose: data.get("dose"),
        times: times,
        start_date: data.get("start_date"),
      });
      medicationForm.reset();
      await refreshMedications();
    } catch (err) {
      medicationError.textContent = err.message;
      medicationError.classList.remove("hidden");
    }
  });

  refreshMedications().catch(() => {});
  refreshDiagnoses().catch(() => {});
})();
