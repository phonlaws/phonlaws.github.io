// ============================
// Half 1:50 Plan Calendar App
// Static + LocalStorage
// ============================

const LS_KEY = "half150_calendar_v1";        // status/notes
const LS_PLAN_KEY = "half150_plan_v1";       // generated plan (by date)
const DEFAULT_RACE_DATE = "2026-08-02";      // 2 Aug 2569
const LOCALE = "th-TH";

// ---- Utilities
const pad2 = (n) => String(n).padStart(2, "0");
const toISO = (d) => `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
const parseISO = (s) => {
  const [y,m,dd] = s.split("-").map(Number);
  return new Date(y, m-1, dd);
};
const addDays = (d, n) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};
const startOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);
const endOfMonth = (d) => new Date(d.getFullYear(), d.getMonth()+1, 0);

// Monday = 1..Sunday = 0 in JS; We want Monday-based week grid
const mondayOfWeek = (d) => {
  const x = new Date(d);
  const day = x.getDay(); // 0 Sun .. 6 Sat
  const diff = (day === 0 ? -6 : 1 - day);
  return addDays(x, diff);
};

const fmtDateThai = (d) =>
  d.toLocaleDateString(LOCALE, { weekday:"long", year:"numeric", month:"long", day:"numeric" });

// ---- Workout type color map
const TYPE_COLOR = {
  REST: "var(--rest)",
  E: "var(--e)",
  T: "var(--t)",
  I: "var(--i)",
  R: "var(--r)",
  HM: "var(--hm)",
  LONG: "var(--long)"
};

// ---- Default pace targets for goal 1:50
const TARGETS = {
  E:  "Easy (E): 5:48–6:56/กม.  | RPE 3–4/10 | คุยเป็นประโยคได้",
  T:  "Threshold (T): ~5:01/กม. | RPE 7/10 | 'เหนื่อยแต่คุมได้'",
  I:  "Interval (I): ~4:34/กม.  | RPE 8–9/10 | ช่วงสั้น พักพอ",
  R:  "Repetition (R): 200–400m เร็วกว่า I เล็กน้อย | เน้นฟอร์ม ไม่สปรินต์",
  HM: "Half pace (HM): ~5:13/กม. | รู้สึก 'เร็วแต่คุมได้'",
  LONG:"Long (E): คุมง่าย | HR cap 150–155 (ถ้าร้อน/HR drift) | ไม่เร่งท้าย"
};

// ---- Week-by-week plan (31 weeks) aligned to your plan: 5 running days + Long on Saturday
// Days: Tue Q1, Wed Easy, Thu Q2, Sat Long, Sun Recovery
// Mon + Fri = Rest/Strength (no run), but you can add optional short E if needed.
function buildWeekTemplates() {
  // Helper creators
  const W = (type, title, details, targets) => ({ type, title, details, targets });

  // A note about warmup/ankle
  const warmupNote =
`วอร์ม 10–12 นาที (สำคัญสำหรับตาตุ่ม)
- 5–6 นาทีแรกช้ามาก
- ขยับข้อเท้า/น่อง 2 นาที
- ค่อยเข้าเพซ`;

  // Weeks 1–31 data (based on the plan you asked earlier; can be edited anytime)
  // For simplicity: store only key workout prescriptions; easy days show ranges.
  const weeks = [
    // Phase A (W1–W8)
    { // W1
      tue: W("T","Q1: T 3×8′", `${warmupNote}\nT 3×8′ @T (พัก 2′ jog)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy + Strides", `Easy 45–60′ @E\nStrides 4–6×20″ (ลื่น ๆ ไม่สปรินต์)`, `${TARGETS.E}\n${TARGETS.R}`),
      thu: W("E","Easy (E)", `Easy 40–55′ @E (สบาย)\nถ้าร้อน/ล้า: คุม HR ไม่ให้ไหล`, TARGETS.E),
      sat: W("LONG","Long 13K", `Long 13K @Easy ล้วน\nไม่เร่งท้าย`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 6–8K", `Recovery 6–8K @Easy ช้ามาก`, TARGETS.E),
    },
    { // W2
      tue: W("T","Q1: T 4×1K", `${warmupNote}\n4×1K @T (พัก 1′ jog)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy + Strides", `Easy 45–60′ @E\nStrides 4–6×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      thu: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      sat: W("LONG","Long 14K", `Long 14K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 6–8K", `Recovery 6–8K @E`, TARGETS.E),
    },
    { // W3
      tue: W("T","Q1: Tempo 20′", `${warmupNote}\nTempo 20′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("R","Q2: 8×200m (R)", `${warmupNote}\n8×200m @R (พัก 200m jog)\nคูล 10′`, TARGETS.R),
      sat: W("LONG","Long 15K", `Long 15K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },
    { // W4 cutback
      tue: W("T","Q1: T 2×8′ (เบา)", `${warmupNote}\nT 2×8′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      thu: W("E","Easy (E)", `Easy 35–50′ @E`, TARGETS.E),
      sat: W("LONG","Long 12K (ผ่อน)", `Long 12K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 6–8K", `Recovery 6–8K @E`, TARGETS.E),
    },
    { // W5
      tue: W("T","Q1: T 3×10′", `${warmupNote}\nT 3×10′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy + Strides", `Easy 45–60′ @E\nStrides 4–6×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      thu: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      sat: W("LONG","Long 16K", `Long 16K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },
    { // W6
      tue: W("T","Q1: T 5×1K", `${warmupNote}\n5×1K @T (พัก 1′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("R","Q2: 6×400m (R)", `${warmupNote}\n6×400m @R (พัก 400m jog)\nคูล 10′`, TARGETS.R),
      sat: W("LONG","Long 17K", `Long 17K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },
    { // W7
      tue: W("T","Q1: Tempo 25′", `${warmupNote}\nTempo 25′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy + Strides", `Easy 45–60′ @E\nStrides 4–6×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      thu: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      sat: W("LONG","Long 18K", `Long 18K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W8 cutback
      tue: W("T","Q1: T 2×10′ (ผ่อน)", `${warmupNote}\nT 2×10′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      thu: W("E","Easy (E)", `Easy 35–50′ @E`, TARGETS.E),
      sat: W("LONG","Long 14K (ผ่อน)", `Long 14K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 6–8K", `Recovery 6–8K @E`, TARGETS.E),
    },

    // Phase B (W9–W16)
    { // W9
      tue: W("I","Q1: I 5×3′", `${warmupNote}\n5×3′ @I (พัก 2–3′ jog)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: T 3×8′", `${warmupNote}\nT 3×8′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 18K", `Long 18K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W10
      tue: W("T","Q1: T 4×1K", `${warmupNote}\n4×1K @T (พัก 1′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("I","Q2: I 6×2′", `${warmupNote}\n6×2′ @I (พัก 2′)\nคูล 10′`, TARGETS.I),
      sat: W("LONG","Long 19K", `Long 19K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W11
      tue: W("I","Q1: I 4×1K", `${warmupNote}\n4×1K @I (พัก 2–3′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: Tempo 25′", `${warmupNote}\nTempo 25′ @T\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 20K", `Long 20K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W12 cutback
      tue: W("T","Q1: T 2×10′", `${warmupNote}\nT 2×10′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy + Strides", `Easy 45–60′ @E\nStrides 4–6×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      thu: W("E","Easy (E)", `Easy 35–50′ @E`, TARGETS.E),
      sat: W("LONG","Long 16K (ผ่อน)", `Long 16K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },
    { // W13
      tue: W("I","Q1: I 6×3′", `${warmupNote}\n6×3′ @I (พัก 2–3′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: T 3×10′", `${warmupNote}\nT 3×10′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 20K", `Long 20K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W14
      tue: W("T","Q1: T 5×1K", `${warmupNote}\n5×1K @T (พัก 1′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("I","Q2: I 5×800m", `${warmupNote}\n5×800m @I (พัก 2–3′)\nคูล 10′`, TARGETS.I),
      sat: W("LONG","Long 21K", `Long 21K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W15
      tue: W("I","Q1: I 3×1600m", `${warmupNote}\n3×1600m @I (พัก 3′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: Tempo 30′", `${warmupNote}\nTempo 30′ @T\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 22K", `Long 22K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W16 cutback
      tue: W("T","Q1: T 2×12′", `${warmupNote}\nT 2×12′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      thu: W("E","Easy (E)", `Easy 35–50′ @E`, TARGETS.E),
      sat: W("LONG","Long 18K (ผ่อน)", `Long 18K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },

    // Phase C (W17–W26): Half Specific
    { // W17
      tue: W("T","Q1: T 4×1K", `${warmupNote}\n4×1K @T (พัก 1′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("HM","Q2: HM 3×2K", `${warmupNote}\n3×2K @HM (พัก 3′ easy)\nคูล 10′`, TARGETS.HM),
      sat: W("LONG","Long 20K", `Long 20K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W18
      tue: W("I","Q1: I 5×3′", `${warmupNote}\n5×3′ @I (พัก 2–3′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: Tempo 25′", `${warmupNote}\nTempo 25′ @T\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 22K", `Long 22K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W19 cutback-ish
      tue: W("HM","Q1: HM 2×3K", `${warmupNote}\n2×3K @HM (พัก 4′)\nคูล 10′`, TARGETS.HM),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("R","Q2: R 10×200m", `${warmupNote}\n10×200m @R (พัก 200 jog)\nคูล 10′`, TARGETS.R),
      sat: W("LONG","Long 18K (ผ่อน)", `Long 18K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },
    { // W20
      tue: W("T","Q1: T 3×12′", `${warmupNote}\nT 3×12′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("HM","Q2: HM 4–6K ต่อเนื่อง", `${warmupNote}\nวิ่งต่อเนื่อง 4–6K @HM\nคูล 10′`, TARGETS.HM),
      sat: W("LONG","Long 22K", `Long 22K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W21
      tue: W("I","Q1: I 4×1K", `${warmupNote}\n4×1K @I (พัก 2–3′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: T 4×1K", `${warmupNote}\n4×1K @T (พัก 1′)\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 23K", `Long 23K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W22 cutback
      tue: W("T","Q1: T 2×10′", `${warmupNote}\nT 2×10′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy + Strides", `Easy 45–60′ @E\nStrides 4–6×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      thu: W("E","Easy (E)", `Easy 35–50′ @E`, TARGETS.E),
      sat: W("LONG","Long 18K (ผ่อน)", `Long 18K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },
    { // W23
      tue: W("HM","Q1: HM 3×3K", `${warmupNote}\n3×3K @HM (พัก 4′)\nคูล 10′`, TARGETS.HM),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("T","Q2: Tempo 20′", `${warmupNote}\nTempo 20′ @T\nคูล 10′`, TARGETS.T),
      sat: W("LONG","Long 22K", `Long 22K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W24
      tue: W("I","Q1: I 6×2′", `${warmupNote}\n6×2′ @I (พัก 2′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("HM","Q2: HM 8K ต่อเนื่อง", `${warmupNote}\nวิ่งต่อเนื่อง 8K @HM\nคูล 10′`, TARGETS.HM),
      sat: W("LONG","Long 20K", `Long 20K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W25
      tue: W("T","Q1: Tempo 30′", `${warmupNote}\nTempo 30′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–60′ @E`, TARGETS.E),
      thu: W("R","Q2: 6×400m (R)", `${warmupNote}\n6×400m @R (พัก 400 jog)\nคูล 10′`, TARGETS.R),
      sat: W("LONG","Long 23K", `Long 23K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8–10K", `Recovery 8–10K @E`, TARGETS.E),
    },
    { // W26 cutback
      tue: W("T","Q1: T 2×12′", `${warmupNote}\nT 2×12′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      thu: W("E","Easy (E)", `Easy 35–50′ @E`, TARGETS.E),
      sat: W("LONG","Long 18–20K (ผ่อน)", `Long 18–20K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–9K", `Recovery 7–9K @E`, TARGETS.E),
    },

    // Phase D (W27–W31): Sharpen/Taper
    { // W27
      tue: W("I","Q1: I 4×1K", `${warmupNote}\n4×1K @I (พัก 2–3′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 45–55′ @E`, TARGETS.E),
      thu: W("HM","Q2: HM 6K ต่อเนื่อง", `${warmupNote}\nวิ่งต่อเนื่อง 6K @HM\nคูล 10′`, TARGETS.HM),
      sat: W("LONG","Long 20K", `Long 20K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 8K", `Recovery 8K @E`, TARGETS.E),
    },
    { // W28
      tue: W("T","Q1: T 3×10′", `${warmupNote}\nT 3×10′ @T (พัก 2′)\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 45–55′ @E`, TARGETS.E),
      thu: W("R","Q2: 8×200m (R)", `${warmupNote}\n8×200m @R\nคูล 10′`, TARGETS.R),
      sat: W("LONG","Long 18K", `Long 18K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 7–8K", `Recovery 7–8K @E`, TARGETS.E),
    },
    { // W29
      tue: W("I","Q1: I 5×2′", `${warmupNote}\n5×2′ @I (พัก 2′)\nคูล 10′`, TARGETS.I),
      wed: W("E","Easy (E)", `Easy 40–55′ @E`, TARGETS.E),
      thu: W("HM","Q2: HM 2×3K", `${warmupNote}\n2×3K @HM (พัก 4′)\nคูล 10′`, TARGETS.HM),
      sat: W("LONG","Long 16K", `Long 16K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 6–7K", `Recovery 6–7K @E`, TARGETS.E),
    },
    { // W30 taper
      tue: W("T","Q1: T 2×8′", `${warmupNote}\nT 2×8′ @T\nคูล 10′`, TARGETS.T),
      wed: W("E","Easy (E)", `Easy 40–50′ @E`, TARGETS.E),
      thu: W("R","Q2: Easy + 4 strides", `Easy 35–45′ @E\nStrides 4×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      sat: W("LONG","Long 12K (เบา)", `Long 12K @E`, `${TARGETS.E}\n${TARGETS.LONG}`),
      sun: W("E","Recovery 6K", `Recovery 6K @E`, TARGETS.E),
    },
    { // W31 race week (Race Sunday)
      tue: W("E","Easy 40′ + 4 strides", `Easy 40′ @E\nStrides 4×20″`, `${TARGETS.E}\n${TARGETS.R}`),
      wed: W("E","Easy 35–45′", `Easy 35–45′ @E`, TARGETS.E),
      thu: W("T","Q2: 3×1K @T (เบามือ)", `${warmupNote}\n3×1K @T (พัก 1′)\nคูล 10′`, TARGETS.T),
      sat: W("REST","พัก หรือจ็อก 20′", `พักเต็มที่ หรือจ็อกเบา 20′ @E`, TARGETS.E),
      sun: W("HM","RACE: Half Marathon", `แข่ง 21.1K\nแผนเพซ: เริ่มคุม 0–5K ~5:15–5:18 แล้วค่อยนิ่ง ~5:13\nท้ายค่อยกดตามแรง`, "HM pace ~5:13/กม.\nคุม RPE ให้ไม่พุ่งช่วงต้น"),
    },
  ];

  return weeks;
}

// ---- Create plan mapping date -> workout
function generatePlan(raceDateISO, startDateISO) {
  const raceDate = parseISO(raceDateISO);
  const weeks = buildWeekTemplates();

  // If startDateISO not provided, compute from race week (Monday) - 30 weeks
  let startMonday;
  if (startDateISO) {
    startMonday = parseISO(startDateISO);
  } else {
    const mondayRace = mondayOfWeek(raceDate);           // Monday of race week
    startMonday = addDays(mondayRace, -30*7);            // Week 1 Monday
  }

  // Ensure it's Monday
  startMonday = mondayOfWeek(startMonday);

  const plan = {}; // { "YYYY-MM-DD": {type,title,details,targets,week,weekday} }

  for (let w = 0; w < weeks.length; w++) {
    const weekStart = addDays(startMonday, w*7); // Monday
    const tpl = weeks[w];

    // map workouts by weekday
    // Monday=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6 (offset from Monday)
    const map = [
      { off:0, type:"REST", title:"REST + Strength", details:"พัก + ทำ strength 10–20 นาที (น่อง/อุ้งเท้า/สะโพก)", targets:"—" },
      { off:1, ...tpl.tue },
      { off:2, ...tpl.wed },
      { off:3, ...tpl.thu },
      { off:4, type:"REST", title:"REST / Mobility", details:"พัก หรือ mobility 10 นาที (ยืดน่อง/สะโพก)", targets:"—" },
      { off:5, ...tpl.sat },
      { off:6, ...tpl.sun },
    ];

    map.forEach(item => {
      const d = addDays(weekStart, item.off);
      const iso = toISO(d);
      plan[iso] = {
        ...item,
        week: w+1,
        weekday: item.off
      };
    });
  }

  // Save meta
  return {
    meta: {
      raceDateISO,
      startMondayISO: toISO(startMonday),
      generatedAt: new Date().toISOString(),
      weeks: 31
    },
    plan
  };
}

// ---- LocalStorage state
function loadState() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; }
  catch { return {}; }
}
function saveState(state) {
  localStorage.setItem(LS_KEY, JSON.stringify(state));
}
function loadPlan() {
  try { return JSON.parse(localStorage.getItem(LS_PLAN_KEY)); }
  catch { return null; }
}
function savePlan(planObj) {
  localStorage.setItem(LS_PLAN_KEY, JSON.stringify(planObj));
}

// ---- UI Elements
const calendarEl = document.getElementById("calendar");
const monthTitleEl = document.getElementById("monthTitle");
const raceDateLabelEl = document.getElementById("raceDateLabel");
const raceDateInput = document.getElementById("raceDateInput");
const startDateInput = document.getElementById("startDateInput");
const rebuildBtn = document.getElementById("rebuildBtn");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const todayBtn = document.getElementById("todayBtn");
const exportBtn = document.getElementById("exportBtn");
const importBtn = document.getElementById("importBtn");
const importFile = document.getElementById("importFile");

// Modal
const modalBackdrop = document.getElementById("modalBackdrop");
const modalCloseBtn = document.getElementById("modalCloseBtn");
const modalDateEl = document.getElementById("modalDate");
const modalTitleEl = document.getElementById("modalTitle");
const modalTagsEl = document.getElementById("modalTags");
const modalDetailsEl = document.getElementById("modalDetails");
const modalTargetsEl = document.getElementById("modalTargets");
const modalNotes = document.getElementById("modalNotes");
const doneBtn = document.getElementById("doneBtn");
const skipBtn = document.getElementById("skipBtn");
const resetBtn = document.getElementById("resetBtn");

// ---- App state
let viewDate = new Date(); // month being shown
let state = loadState();
let planObj = loadPlan();
let activeISO = null;

// ---- Initialize
function init() {
  // Defaults
  raceDateInput.value = DEFAULT_RACE_DATE;

  // If no plan saved, generate
  if (!planObj) {
    planObj = generatePlan(raceDateInput.value, null);
    savePlan(planObj);
  }

  // Fill inputs
  raceDateInput.value = planObj.meta.raceDateISO;
  startDateInput.value = planObj.meta.startMondayISO;

  raceDateLabelEl.textContent = fmtDateThai(parseISO(planObj.meta.raceDateISO));

  // Render current month
  renderMonth(viewDate);

  // Wire buttons
  prevBtn.onclick = () => { viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth()-1, 1); renderMonth(viewDate); };
  nextBtn.onclick = () => { viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth()+1, 1); renderMonth(viewDate); };
  todayBtn.onclick = () => { viewDate = new Date(); renderMonth(viewDate); };

  rebuildBtn.onclick = () => {
    const raceISO = raceDateInput.value || DEFAULT_RACE_DATE;
    const startISO = startDateInput.value || null;
    planObj = generatePlan(raceISO, startISO);
    savePlan(planObj);
    raceDateLabelEl.textContent = fmtDateThai(parseISO(planObj.meta.raceDateISO));
    renderMonth(viewDate);
    alert("สร้างแผนใหม่เรียบร้อย");
  };

  // Export/Import plan+state
  exportBtn.onclick = () => exportJSON();
  importBtn.onclick = () => importFile.click();
  importFile.onchange = (e) => handleImport(e);

  // Modal
  modalCloseBtn.onclick = closeModal;
  modalBackdrop.onclick = (e) => { if (e.target === modalBackdrop) closeModal(); };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  doneBtn.onclick = () => setStatus("done");
  skipBtn.onclick = () => setStatus("skip");
  resetBtn.onclick = () => setStatus("none");

  modalNotes.addEventListener("input", () => {
    if (!activeISO) return;
    state[activeISO] = state[activeISO] || {};
    state[activeISO].notes = modalNotes.value;
    saveState(state);
  });
}

function exportJSON() {
  const payload = {
    exportedAt: new Date().toISOString(),
    planObj,
    state
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type:"application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "half150_calendar_export.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function handleImport(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try{
      const payload = JSON.parse(reader.result);
      if (payload.planObj?.plan) {
        planObj = payload.planObj;
        savePlan(planObj);
      }
      if (payload.state) {
        state = payload.state;
        saveState(state);
      }
      raceDateInput.value = planObj.meta.raceDateISO;
      startDateInput.value = planObj.meta.startMondayISO;
      raceDateLabelEl.textContent = fmtDateThai(parseISO(planObj.meta.raceDateISO));
      renderMonth(viewDate);
      alert("Import สำเร็จ");
    } catch(err) {
      alert("ไฟล์ไม่ถูกต้อง หรืออ่านไม่ได้");
    }
  };
  reader.readAsText(file);
  importFile.value = "";
}

// ---- Calendar rendering
function renderMonth(date) {
  const y = date.getFullYear();
  const m = date.getMonth();
  const first = startOfMonth(date);
  const last = endOfMonth(date);

  // month title
  monthTitleEl.textContent = first.toLocaleDateString(LOCALE, { month:"long", year:"numeric" });

  // start from Monday of the grid
  const gridStart = mondayOfWeek(first);
  const gridEnd = addDays(mondayOfWeek(last), 6);

  calendarEl.innerHTML = "";

  // Build day cells
  for (let d = new Date(gridStart); d <= gridEnd; d = addDays(d, 1)) {
    const iso = toISO(d);
    const inMonth = (d.getMonth() === m);
    const plan = planObj?.plan?.[iso];
    const st = state?.[iso]?.status || "none";

    const cell = document.createElement("div");
    cell.className = "day" + (inMonth ? "" : " muted") + (st === "done" ? " done" : st === "skip" ? " skip" : "");
    cell.dataset.iso = iso;

    const strip = document.createElement("div");
    strip.className = "status-strip";
    cell.appendChild(strip);

    const head = document.createElement("div");
    head.className = "day-head";

    const dateNum = document.createElement("div");
    dateNum.className = "date-num";
    dateNum.textContent = d.getDate();

    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = plan ? `W${plan.week}` : "—";

    head.appendChild(dateNum);
    head.appendChild(badge);

    const workout = document.createElement("div");
    workout.className = "workout";

    const dot = document.createElement("div");
    dot.className = "dot";
    dot.style.background = TYPE_COLOR[plan?.type || "REST"] || "var(--rest)";

    const text = document.createElement("div");
    text.className = "workout-text";
    text.textContent = plan ? plan.title : "ไม่มีโปรแกรม";

    workout.appendChild(dot);
    workout.appendChild(text);

    const small = document.createElement("div");
    small.className = "small";
    if (plan) {
      small.textContent = shortHint(plan);
    } else {
      small.textContent = "";
    }

    cell.appendChild(head);
    cell.appendChild(workout);
    cell.appendChild(small);

    cell.onclick = () => openModal(iso);

    calendarEl.appendChild(cell);
  }
}

function shortHint(plan) {
  // Keep it short for calendar cell
  if (plan.type === "LONG") return "Long day";
  if (plan.type === "REST") return "พัก/Strength";
  if (plan.type === "T") return "งาน T";
  if (plan.type === "I") return "งาน I";
  if (plan.type === "R") return "งาน R";
  if (plan.type === "HM") return "HM pace";
  return "Easy";
}

// ---- Modal
function openModal(iso) {
  activeISO = iso;
  const d = parseISO(iso);
  const plan = planObj?.plan?.[iso];

  modalDateEl.textContent = fmtDateThai(d);
  modalTitleEl.textContent = plan ? plan.title : "ไม่มีโปรแกรม";
  modalTagsEl.innerHTML = "";

  const tags = [];
  if (plan?.type) tags.push(plan.type);
  if (plan?.week) tags.push(`Week ${plan.week}`);

  const status = state?.[iso]?.status || "none";
  if (status === "done") tags.push("✅ สำเร็จ");
  if (status === "skip") tags.push("⏭️ ข้าม");

  tags.forEach(t => {
    const el = document.createElement("span");
    el.className = "tag";
    el.textContent = t;
    modalTagsEl.appendChild(el);
  });

  modalDetailsEl.textContent = plan ? plan.details : "—";
  modalTargetsEl.textContent = plan ? plan.targets : "—";
  modalNotes.value = state?.[iso]?.notes || "";

  modalBackdrop.classList.add("show");
  modalBackdrop.setAttribute("aria-hidden", "false");
}

function closeModal() {
  modalBackdrop.classList.remove("show");
  modalBackdrop.setAttribute("aria-hidden", "true");
  activeISO = null;
}

function setStatus(newStatus) {
  if (!activeISO) return;
  state[activeISO] = state[activeISO] || {};

  if (newStatus === "none") {
    delete state[activeISO].status;
  } else {
    state[activeISO].status = newStatus;
  }

  saveState(state);
  renderMonth(viewDate); // refresh colors
  openModal(activeISO);  // refresh tags in modal
}

// Start app
init();
``