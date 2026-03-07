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

// ---------- Login UI elements (มีเฉพาะหน้า index.html) ----------
const loginModal = $("#loginModal");
const loginUser = $("#loginUser");
const loginPin = $("#loginPin");
const loginBtn = $("#loginBtn");
const loginCancel = $("#loginCancel");
const loginErr = $("#loginErr");
const loginHint = $("#loginHint");

// ✅ Segmented mode (User/Admin) ใช้ CSS เดียวกับงานเสี่ยง 100%
const modeUser = $("#modeUser");   // radio
const modeAdmin = $("#modeAdmin"); // radio

// ✅ Admin input wrap
const adminUserWrap = $("#adminUserWrap");
const loginAdminUser = $("#loginAdminUser");

const loginChip = $("#loginChip");
const loginName = $("#loginName");
const logoutBtn = $("#logoutBtn");

let state = { jobs: [], overdueMinutes: 120, updatedAt: null };

// ===== New job flash control =====
let hasLoadedOnce = false;
const flashUntil = new Map(); // jobId -> timestamp(ms) ที่แฟลชถึงเมื่อไหร่
const FLASH_MS = 5000;

// สถานะล็อกอิน
let currentUser = null;
let currentRole = "user"; // "user" | "admin"

// -------------------- Utils --------------------
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
  const t = new Date();
  const datePart = t.toLocaleDateString('th-TH', { year:'numeric', month:'numeric', day:'numeric' });
  const timePart = t.toLocaleTimeString('th-TH', { hour:'2-digit', minute:'2-digit', hour12:false });
  lastUpdated.textContent = `${datePart} ${timePart}`;
}

// ✅ escapeHtml ที่ถูกต้อง
function escapeHtml(str){
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// -------------------- Login helpers --------------------
function setAdminMode(on){
  // แสดง/ซ่อนช่องพิมพ์ admin
  if(adminUserWrap) adminUserWrap.style.display = on ? "block" : "none";

  // เปิด/ปิด dropdown user
  if(loginUser) loginUser.disabled = !!on;

  // เคลียร์ช่องที่ไม่ใช้ + โฟกัส
  if(on){
    if(loginUser) loginUser.value = "";
    if(loginAdminUser) loginAdminUser.value = "";   // ✅ บังคับให้ว่าง ต้องพิมพ์เอง
    setTimeout(()=> loginAdminUser?.focus(), 50);
  }else{
    if(loginAdminUser) loginAdminUser.value = "";
    setTimeout(()=> loginUser?.focus(), 50);
  }
}

function showLogin(msg){
  if(isKiosk) return;
  if(!loginModal) return;

  if(loginErr) loginErr.style.display = "none";
  if(loginHint) loginHint.textContent = msg || "กรุณาเลือกชื่อผู้ใช้และกรอก PIN 6 หลัก";

  // ✅ reset โหมดกลับเป็น User ทุกครั้งที่เปิด modal (กันค้าง)
  if(modeUser) modeUser.checked = true;
  if(modeAdmin) modeAdmin.checked = false;
  setAdminMode(false);

  if(loginAdminUser) loginAdminUser.value = ""; // ✅ กันค่าค้าง

  loginModal.style.display = "block";
  setTimeout(()=> loginPin?.focus(), 50);
}

function hideLogin(){
  if(!loginModal) return;
  loginModal.style.display = "none";
  if(loginPin) loginPin.value = "";
  if(loginErr) loginErr.style.display = "none";
}

function setLoginState(user, role){
  currentUser = user || null;
  currentRole = role || "user";

  if(loginChip) loginChip.style.display = currentUser ? "inline-flex" : "none";
  if(loginName){
    loginName.textContent = currentUser
      ? (currentRole === "admin" ? `${currentUser} (Admin)` : currentUser)
      : "";
  }
  if(logoutBtn) logoutBtn.style.display = currentUser ? "inline-flex" : "none";

  // requester auto-fill เป็นผู้ล็อกอิน และล็อกไว้กันผิดคน
  const requester = $("#requester");
  if(requester && !isKiosk){
    if(currentUser){
      requester.value = currentUser;

      const hasOpt = Array.from(requester.options || [])
        .some(o => (o.value === currentUser) || (o.text === currentUser));

      if(!hasOpt){
        const opt = document.createElement("option");
        opt.value = currentUser;
        opt.textContent = currentUser;
        requester.appendChild(opt);
      }
      requester.value = currentUser;
      requester.disabled = true;
    }else{
      requester.disabled = false;
    }
  }
}

function isAdmin(){
  return currentRole === "admin";
}

async function apiMe(){
  const res = await fetch('/api/me', { cache:'no-store' });
  if(res.status === 401) return null;
  if(!res.ok) return null;
  const data = await res.json().catch(()=> null);
  if(!data || !data.ok) return null;
  return data; // {ok:true, user:'...', role:'admin'|'user'}
}

async function apiLogin(user, pin){
  const res = await fetch('/api/login', {
    method:'POST',
    headers:{ 'Content-Type':'application/json' },
    body: JSON.stringify({ user, pin })
  });
  const data = await res.json().catch(()=> ({}));
  if(!res.ok) throw new Error(data?.error || "login failed");
  return data;
}

async function apiLogout(){
  await fetch('/api/logout', { method:'POST' }).catch(()=>{});
  setLoginState(null, "user");
  showToast("ออกจากระบบแล้ว");
  renderJobs(); // เผื่อ admin logout แล้วปุ่มปิดต้องหาย
}

// -------------------- Login binding --------------------
function bindLoginUI(){
  if(!loginModal || isKiosk) return;

  // init
  setAdminMode(false);

  // เปลี่ยนโหมดตาม segmented (radio)
  modeUser?.addEventListener("change", ()=> setAdminMode(false));
  modeAdmin?.addEventListener("change", ()=> setAdminMode(true));

  loginBtn?.addEventListener("click", async ()=>{
    const adminMode = !!modeAdmin?.checked;

    // ✅ user = dropdown, admin = input (admin บังคับ lower-case เพื่อ match users.json)
    let u = adminMode
      ? (loginAdminUser?.value || "").trim().toLowerCase()
      : (loginUser?.value || "").trim();

    const p = (loginPin?.value || "").trim();

    if(loginErr) loginErr.style.display = "none";

    if(!u || !p){
      if(loginErr){
        loginErr.textContent = adminMode
          ? "กรุณาพิมพ์ชื่อ Admin และกรอก PIN"
          : "กรุณาเลือกชื่อ และกรอก PIN";
        loginErr.style.display = "block";
      }
      return;
    }

    if(!/^\d{6}$/.test(p)){
      if(loginErr){
        loginErr.textContent = "PIN ต้องเป็นตัวเลข 6 หลัก";
        loginErr.style.display = "block";
      }
      return;
    }

    try{
      // login
      await apiLogin(u, p);

      // ดึง role หลัง login (สำคัญสำหรับ admin)
      const me = await apiMe().catch(()=> null);
      setLoginState(me?.user || u, me?.role || "user");

      hideLogin();
      showToast(`เข้าสู่ระบบแล้ว: ${me?.user || u}`);

      // หลัง login ให้ render ใหม่ทันที
      renderJobs();
      renderSummary();
      renderKPIs();

    }catch(e){
      const msg = String(e?.message || e);
      if(loginErr){
        loginErr.textContent = msg.includes("pin") ? "PIN ไม่ถูกต้อง" : "ชื่อหรือ PIN ไม่ถูกต้อง";
        loginErr.style.display = "block";
      }
    }
  });

  // ยกเลิกได้ -> โหมดดูอย่างเดียว
  loginCancel?.addEventListener("click", ()=>{
    hideLogin();
    showToast("โหมดดูอย่างเดียว: หากต้องการเปิด/ปิดงาน กรุณาเข้าสู่ระบบ");
  });

  // Enter เพื่อ login
  loginPin?.addEventListener("keydown", (e)=>{
    if(e.key === "Enter"){
      e.preventDefault();
      loginBtn?.click();
    }
  });

  logoutBtn?.addEventListener("click", ()=>{
    apiLogout();
  });
}

function ensureLoggedInOrPrompt(){
  if(isKiosk) return true;
  if(currentUser) return true;
  showLogin("กรุณาเข้าสู่ระบบก่อนใช้งาน (PIN 6 หลัก) — กดยกเลิกเพื่อดูข้อมูลอย่างเดียวได้");
  return false;
}

// -------------------- Rendering --------------------
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

    // เช็คว่างานนี้ยังอยู่ในช่วงแฟลชไหม
    const id = String(job.id);
    const until = flashUntil.get(id) || 0;
    const isFlash = Date.now() < until;

    // เคลียร์รายการที่หมดอายุแล้ว (ช่วยไม่ให้ Map โตเรื่อย ๆ)
    if(!isFlash && until){
      flashUntil.delete(id);
    }

    card.className = `card ${job.riskType} ${overdue ? "overdue" : ""} ${isFlash ? "flash" : ""}`;

    const badgeClass = job.riskType === "confined" ? "confined" : "height";
    const overdueBadge = overdue
      ? `<span class="badge overdue"><span class="dot"></span> เกินเวลา</span>`
      : "";

    const detailsBlock = job.details
      ? `<div>รายละเอียด : <b>${escapeHtml(job.details)}</b></div>`
      : "";

    // ✅ เจ้าของงาน = openedBy (งานใหม่) หรือ requester (งานเก่า)
    const owner = (job.openedBy || job.requester || "").trim();

    // ✅ admin ปิดได้ทุกงาน, user ปิดได้เฉพาะของตัวเอง
    const canClose = (!isKiosk) && (currentUser && (isAdmin() || owner === currentUser));

    const closeBtn = canClose
      ? `<button type="button" class="close" data-id="${job.id}">ปิดงาน</button>`
      : "";

    card.innerHTML = `
      <div class="card-top">
        <div class="badges">
          <span class="badge ${badgeClass}"><span class="dot"></span> ${getRiskLabel(job.riskType)}</span>
          <span class="badge dept">หน่วยงาน: <b style="color:var(--text)">${escapeHtml(job.department)}</b></span>
          ${overdueBadge}
        </div>
        ${closeBtn}
      </div>

      <h3>${escapeHtml(job.point)}</h3>

      <div class="meta">
        <div>มาตรการ : <b>${escapeHtml(job.control || "-")}</b></div>
        <div>ผู้เปิดงาน : <b>${escapeHtml(job.requester || "-")}</b></div>
        ${detailsBlock}
      </div>

      <div class="kv">
        <div>เริ่ม : <b>${thTime(job.startedAtISO)} น.</b></div>
        <div>เปิดงานมา : <b class="elapsed" data-id="${job.id}">${formatDuration(secondsSince(job.startedAtISO))}</b></div>
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
      <td><span class="count ${c===0 ? "zero" : ""}">${c}</span></td>
      <td><span class="count ${h===0 ? "zero" : ""}">${h}</span></td>
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

  // --- detect new jobs (หลังโหลดครั้งแรกเท่านั้น) ---
  const prevIds = new Set((state.jobs || []).map(j => String(j.id)));
  const nextIds = new Set((data.jobs || []).map(j => String(j.id)));

  if(hasLoadedOnce){
    for(const id of nextIds){
      if(!prevIds.has(id)){
        flashUntil.set(id, Date.now() + FLASH_MS); // แฟลช 5 วิ
      }
    }
  }else{
    hasLoadedOnce = true; // โหลดครั้งแรกไม่แฟลช
  }

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

  // 401 -> เด้ง login
  if(res.status === 401){
    if(!isKiosk){
      setLoginState(null, "user");
      showLogin("กรุณาเข้าสู่ระบบก่อนใช้งาน (PIN 6 หลัก) — กดยกเลิกเพื่อดูข้อมูลอย่างเดียวได้");
    }
    throw new Error('unauthorized');
  }

  const data = await res.json().catch(()=> ({}));

  // 403 -> ไม่ใช่ owner/admin
  if(res.status === 403){
    throw new Error(data?.error || "forbidden");
  }

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

    if(!ensureLoggedInOrPrompt()) return;

    const riskType = document.querySelector('input[name="riskType"]:checked')?.value || "confined";
    const department = $("#department")?.value;
    const point = $("#workPoint")?.value.trim();
    const control = $("#control")?.value.trim();
    const requester = currentUser || $("#requester")?.value;
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
    if(!ensureLoggedInOrPrompt()) return;

    try{
      await apiPost('/api/config', { overdueMinutes: Number(overdueMinutesInput.value || 120) });
      await apiGetStatus();
    }catch(err){
      showToast(String(err.message || err));
    }
  });
}

function bindCloseButtons(){
  if(!jobsList || isKiosk) return;

  jobsList.addEventListener('click', async (e) => {
    const btn = e.target.closest('.close');
    if(!btn) return;

    if(!ensureLoggedInOrPrompt()) return;

    const id = btn.dataset.id;
    if(!id) return;

    btn.disabled = true;
    try{
      await closeJob(id);
    }catch(err){
      const msg = String(err.message || err);
      if(msg.includes("forbidden")){
        showToast("ปิดงานไม่ได้: ต้องเป็นคนเปิดงานเท่านั้น (หรือ Admin)");
      }else{
        showToast(msg);
      }
    }finally{
      btn.disabled = false;
    }
  });
}

function applyRiskTheme(){
  const confined = document.getElementById("riskConfined");
  const height = document.getElementById("riskHeight");

  // ถ้าไม่เจอ radio (เช่น หน้า kiosk) ไม่ต้องทำอะไร
  if(!confined || !height) return;

  const set = () => {
    const type = (document.querySelector('input[name="riskType"]:checked')?.value) || "confined";
    document.body.dataset.risk = type; // "confined" | "height"
  };

  confined.addEventListener("change", set);
  height.addEventListener("change", set);
  set(); // เรียกครั้งแรกตอนโหลดหน้า
}

// -------------------- Boot --------------------
async function boot(){
  setStartTimeDefault();
  applyRiskTheme();
  bindForm();
  bindCloseButtons();
  bindLoginUI();

  // โหลดสถานะงาน
  apiGetStatus().catch(()=>{});
  setInterval(()=> apiGetStatus().catch(()=>{}), 2000);
  setInterval(tickElapsed, 1000);

  // หน้า operator: เช็ค login แล้วเด้ง login ทันที (ยกเลิกได้)
  if(!isKiosk){
    const me = await apiMe().catch(()=> null);
    setLoginState(me?.user || null, me?.role || "user");

    if(!me){
      showLogin("กรุณาเข้าสู่ระบบก่อนใช้งาน (PIN 6 หลัก) — กดยกเลิกเพื่อดูข้อมูลอย่างเดียวได้");
    }
  }
}

boot();