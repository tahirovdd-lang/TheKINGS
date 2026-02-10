// web/app.js
(() => {
  // Если вдруг запустили через Node.js — выходим без ошибок
  if (typeof window === "undefined" || typeof document === "undefined") {
    console.log("This script is for browser (Telegram WebApp). Do not run with Node.js.");
    return;
  }

  const tg = window.Telegram?.WebApp || null;

  if (tg) {
    tg.ready();
    tg.expand();
  } else {
    console.log("Telegram WebApp not found. Running in normal browser mode.");
  }

  const MASTERS = [
    { id: 1, name: "Aziz" },
    { id: 2, name: "Javohir" },
    { id: 3, name: "Sardor" },
  ];

  const SERVICES = [
    { id: 1, name: "Стрижка", duration: 45, price: 60000 },
    { id: 2, name: "Борода", duration: 30, price: 40000 },
    { id: 3, name: "Стрижка + Борода", duration: 75, price: 90000 },
    { id: 4, name: "Укладка", duration: 20, price: 25000 },
  ];

  const PROMOS = [
    { title: "Скидка 10% студентам", text: "При предъявлении студенческого." },
    { title: "Каждый 5-й визит -20%", text: "Скидка на услугу по карте клиента." },
  ];

  const el = (id) => document.getElementById(id);

  const servicesEl = el("services");
  const masterEl = el("master");
  const dateEl = el("date");
  const timeEl = el("time");
  const nameEl = el("name");
  const phoneEl = el("phone");
  const commentEl = el("comment");
  const durEl = el("dur");
  const sumEl = el("sum");
  const msgEl = el("msg");
  const btnSend = el("btnSend");
  const promosEl = el("promos");

  let selected = new Set();

  function todayISO() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  function fmtSum(n) {
    const x = Number(n) || 0;
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function calc() {
    let total = 0, dur = 0;
    const chosen = [];

    for (const id of selected) {
      const s = SERVICES.find(x => x.id === id);
      if (!s) continue;
      total += s.price;
      dur += s.duration;
      chosen.push({ id: s.id, name: s.name, price: s.price, duration: s.duration, qty: 1 });
    }

    durEl.textContent = dur ? String(dur) : "—";
    sumEl.textContent = total ? `${fmtSum(total)} so'm` : "—";
    return { total, dur, chosen };
  }

  function buildTimes() {
    const start = 9 * 60, end = 22 * 60, step = 30;
    timeEl.innerHTML = "";
    for (let t = start; t < end; t += step) {
      const h = String(Math.floor(t / 60)).padStart(2, "0");
      const m = String(t % 60).padStart(2, "0");
      const opt = document.createElement("option");
      opt.value = `${h}:${m}`;
      opt.textContent = `${h}:${m}`;
      timeEl.appendChild(opt);
    }
  }

  function setMsg(t) { msgEl.textContent = t || ""; }
  function normalizePhone(p) { return (p || "").trim().replace(/[^\d+]/g, ""); }

  function init() {
    // услуги
    servicesEl.innerHTML = "";
    SERVICES.forEach(s => {
      const div = document.createElement("div");
      div.className = "chip";
      div.innerHTML = `<b>${s.name}</b><div class="chip-sub">${fmtSum(s.price)} so'm • ${s.duration} мин</div>`;
      div.onclick = () => {
        if (selected.has(s.id)) { selected.delete(s.id); div.classList.remove("active"); }
        else { selected.add(s.id); div.classList.add("active"); }
        calc();
      };
      servicesEl.appendChild(div);
    });

    // мастер
    masterEl.innerHTML = "";
    const def = document.createElement("option");
    def.value = "";
    def.textContent = "Выберите мастера";
    masterEl.appendChild(def);
    MASTERS.forEach(m => {
      const o = document.createElement("option");
      o.value = String(m.id);
      o.textContent = m.name;
      masterEl.appendChild(o);
    });

    // акции
    promosEl.innerHTML = "";
    PROMOS.forEach(p => {
      const d = document.createElement("div");
      d.className = "promo";
      d.innerHTML = `<b>${p.title}</b><div>${p.text}</div>`;
      promosEl.appendChild(d);
    });

    dateEl.value = todayISO();
    buildTimes();

    const u = tg?.initDataUnsafe?.user;
    if (u?.first_name && !nameEl.value) nameEl.value = u.first_name;

    calc();
  }

  btnSend.onclick = () => {
    setMsg("");
    const { total, dur, chosen } = calc();

    if (!chosen.length) return setMsg("Выберите услугу.");
    if (!masterEl.value) return setMsg("Выберите мастера.");
    if (!dateEl.value) return setMsg("Выберите дату.");
    if (!timeEl.value) return setMsg("Выберите время.");
    if (!nameEl.value.trim()) return setMsg("Введите имя.");

    const masterId = Number(masterEl.value);
    const masterName = (MASTERS.find(m => m.id === masterId)?.name) || "—";

    const payload = {
      booking_id: "BK-" + Date.now(),
      client_name: nameEl.value.trim(),
      phone: normalizePhone(phoneEl.value),
      comment: commentEl.value.trim(),
      master_id: masterId,
      master_name: masterName,
      date: dateEl.value,
      time: timeEl.value,
      services: chosen,
      total: total,
      duration_min: dur,
      client_ts: Date.now(),
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
    } else {
      console.log("Payload:", payload);
      setMsg("✅ (Тест) Откройте через Telegram WebApp чтобы отправить.");
    }
  };

  init();
})();
