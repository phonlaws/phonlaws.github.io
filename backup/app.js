const DEPARTMENTS = ["Crusher","RM1","RM2","Petcoke Mill","Pfister","Kiln1","Kiln2"];

const $ = (sel) => document.querySelector(sel);

const isKiosk = document.body.classList.contains('mode-kiosk');

const form = $("#openForm");
const jobsList = $("#jobsList");
const jobsEmpty = $("#jobsEmpty");
const summaryBody = $("#summaryBody");

const kpiOpen = $("#kpiOpen");
const kpiOver = $("#kpiOver");
const lastUpdated = $("#lastUpdated");

const overdueMinutesInput = $("#overdueMinutes");
const toast = $("#toast");

let state = { jobs: [], overdueMinutes: 120, updatedAt: null };

function thTime(iso){
  return new Date(iso).toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
}

function secondsSince(iso){
  const ms = Date.now() - new Date(iso).getTime();
  return Math.max(0, Math.floor(ms / 1000));
}

function formatDuration(seconds){
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
}

function getRiskLabel(type){
  return type === "confined" ? "ที่อับอากาศ" : "ที่สูง";
}

function overdueMinutes(){
  if(!overdueMinutesInput || isKiosk) return Number(state.overdueMinutes || 120);
  const v = Number(overdueMinutesInput.value ?? state.overdueMinutes ?? 120);
  return Math.max(1, Math.min(9999, isFinite(v) ? v : 120));
}

function isOverdue(job){
  return secondsSince(job.startedAtISO) >= overdueMinutes() * 60;
}

function showToast(msg){
  if(!toast) return;
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(()=> toast.classList.remove("show"), 1600);
}

function setLastUpdateLabel(){
  if(!lastUpdated) return;
  
    const t = new Date(); // เวลาปัจจุบันของเครื่อง (ใช้เป็น “เวลาที่เว็บรีเฟรชล่าสุด”)

    const datePart = t.toLocaleDateString('th-TH', {
      year: 'numeric',
     month: 'numeric',
      day: 'numeric'
    });

    const timePart = t.toLocaleTimeString('th-TH', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });

    lastUpdated.textContent = `${datePart} ${timePart}`;
    }

function renderKPIs(){
  const openCount = state.jobs.length;
  const overdueCount = state.jobs.filter(isOverdue).length;
  if(kpiOpen) kpiOpen.textContent = openCount;
  if(kpiOver) kpiOver.textContent = overdueCount;
}

function renderJobs(){
  if(!jobsList || !jobsEmpty) return;

  jobsList.innerHTML = "";
  jobsEmpty.style.display = state.jobs.length ? "none" : "block";

  state.jobs.forEach(job => {
    const overdue = isOverdue(job);
    const card = document.createElement("div");
    card.className = `card ${job.riskType} ${overdue ? "overdue" : ""}`;

    const badgeClass = job.riskType === "confined" ? "confined" : "height";
    const overdueBadge = overdue
      ? `<span class=\"badge overdue\"><span class=\"dot\"></span> เกินเวลา</span>`
      : "";

    const detailsBlock = job.details
      ? `<div>รายละเอียด : <b>${escapeHtml(job.details)}</b></div>`
      : "";

    const closeBtn = isKiosk ? "" : `<button type=\"button\" class=\"close\" data-id=\"${job.id}\">ปิดงาน</button>`;

    card.innerHTML = `
      <div class=\"card-top\">
        <div class=\"badges\">
          <span class=\"badge ${badgeClass}\"><span class=\"dot\"></span> ${getRiskLabel(job.riskType)}</span>
          <span class=\"badge dept\">หน่วยงาน: <b style=\"color:var(--text)\">${escapeHtml(job.department)}</b></span>
          ${overdueBadge}
        </div>
        ${closeBtn}
      </div>

      <h3>${escapeHtml(job.point)}</h3>

      <div class=\"meta\">
        <div>มาตรการ : <b>${escapeHtml(job.control || "-")}</b></div>
        <div>ผู้เปิดงาน : <b>${escapeHtml(job.requester || "-")}</b></div>
        ${detailsBlock}
      </div>

      <div class=\"kv\">
        <div>เริ่ม : <b>${thTime(job.startedAtISO)} น.</b></div>
        <div>เปิดงานมา : <b class=\"elapsed\" data-id=\"${job.id}\">${formatDuration(secondsSince(job.startedAtISO))}</b></div>
      </div>
    `;

    jobsList.appendChild(card);
  });

  renderKPIs();
}

function renderSummary(){
  if(!summaryBody) return;

  const counts = {};
  DEPARTMENTS.forEach(d => counts[d] = {confined:0, height:0});

  state.jobs.forEach(j => {
    if(!counts[j.department]) counts[j.department] = {confined:0, height:0};
    counts[j.department][j.riskType] += 1;
  });

  summaryBody.innerHTML = "";
  DEPARTMENTS.forEach(dept => {
    const c = counts[dept].confined;
    const h = counts[dept].height;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${dept}</td>
      <td><span class=\"count ${c===0 ? "zero" : ""}\">${c}</span></td>
      <td><span class=\"count ${h===0 ? "zero" : ""}\">${h}</span></td>
    `;
    summaryBody.appendChild(tr);
  });
}

function tickElapsed(){
  document.querySelectorAll(".elapsed").forEach(el => {
    const id = el.dataset.id;
    const job = state.jobs.find(j => String(j.id) === String(id));
    if(job) el.textContent = formatDuration(secondsSince(job.startedAtISO));
  });

  const cards = document.querySelectorAll(".card");
  cards.forEach((card, idx) => {
    const job = state.jobs[idx];
    if(!job) return;
    card.classList.toggle("overdue", isOverdue(job));
  });

  renderKPIs();
}

async function apiGetStatus(){
  const res = await fetch('/api/status', { cache: 'no-store' });
  if(!res.ok) throw new Error('status');
  const data = await res.json();
  state = data;

  if(overdueMinutesInput && !isKiosk){
    overdueMinutesInput.value = String(state.overdueMinutes ?? 120);
  }

  setLastUpdateLabel();
  renderJobs();
  renderSummary();
  renderKPIs();
}

async function apiPost(url, payload){
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(()=> ({}));
  if(!res.ok) throw new Error(data?.error || 'error');
  return data;
}

async function openJob(payload){
  const data = await apiPost('/api/open', payload);
  state = data;
  setLastUpdateLabel();
  renderJobs();
  renderSummary();
  renderKPIs();
  showToast(`เปิดงานแล้ว: ${payload.department} • ${getRiskLabel(payload.riskType)} • ${payload.point}`);
}

async function closeJob(id){
  const data = await apiPost('/api/close', { id });
  state = data;
  setLastUpdateLabel();
  renderJobs();
  renderSummary();
  renderKPIs();
  showToast('ปิดงานแล้ว');
}

function setStartTimeDefault(){
  const t = new Date();
  const hh = String(t.getHours()).padStart(2,"0");
  const mm = String(t.getMinutes()).padStart(2,"0");
  const startTime = $("#startTime");
  if(startTime) startTime.value = `${hh}:${mm}`;
}

function bindForm(){
  if(!form) return;

  const clearBtn = $("#clearForm");
  clearBtn?.addEventListener("click", () => {
    form.reset();
    setStartTimeDefault();
    $("#riskConfined") && ($("#riskConfined").checked = true);
    showToast('ล้างข้อมูลแล้ว');
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const riskType = document.querySelector('input[name="riskType"]:checked')?.value || "confined";
    const department = $("#department")?.value;
    const point = $("#workPoint")?.value.trim();
    const control = $("#control")?.value.trim();
    const requester = $("#requester")?.value;
    const details = $("#details")?.value.trim();
    const startTime = $("#startTime")?.value;

    if(!department){ showToast('กรุณาเลือกหน่วยงาน'); return; }
    if(!point){ showToast('กรุณากรอกจุดงาน'); return; }

    let startedAt = new Date();
    if(startTime){
      const [hh, mm] = startTime.split(':').map(Number);
      startedAt.setHours(hh, mm, 0, 0);
    }

    const overdueMinutesValue = Number(overdueMinutesInput?.value || 120);

    try{
      await openJob({
        riskType,
        department,
        point,
        control,
        requester,
        details,
        startedAtISO: startedAt.toISOString(),
        overdueMinutes: overdueMinutesValue
      });

      $("#workPoint").value = '';
      $("#control").value = '';
      $("#details").value = '';

    }catch(err){
      showToast(String(err.message || err));
    }
  });

  overdueMinutesInput?.addEventListener('change', async () => {
    try{
      await apiPost('/api/config', { overdueMinutes: Number(overdueMinutesInput.value || 120) });
      await apiGetStatus();
    }catch(err){
      showToast('ตั้งค่าไม่สำเร็จ');
    }
  });
}

function bindCloseButtons(){
  if(!jobsList || isKiosk) return;
  jobsList.addEventListener('click', async (e) => {
    const btn = e.target.closest('.close');
    if(!btn) return;
    const id = btn.dataset.id;
    if(!id) return;
    btn.disabled = true;
    try{
      await closeJob(id);
    }catch(err){
      showToast(String(err.message || err));
    }finally{
      btn.disabled = false;
    }
  });
}

function escapeHtml(str){
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

setStartTimeDefault();
bindForm();
bindCloseButtons();
apiGetStatus().catch(()=>{});
setInterval(()=> apiGetStatus().catch(()=>{}), 2000);
setInterval(tickElapsed, 1000);
