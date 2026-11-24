/* =====================================================================
   FlyHND — Client JS
   ===================================================================== */
(function () {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────────────────
  const form             = document.getElementById("searchForm");
  const originInput      = document.getElementById("originInput");
  const originId         = document.getElementById("originId");
  const originSugg       = document.getElementById("originSuggestions");
  const destInput        = document.getElementById("destInput");
  const destId           = document.getElementById("destId");
  const destSugg         = document.getElementById("destSuggestions");
  const dateInput        = document.getElementById("dateInput");
  const returnDateInput  = document.getElementById("returnDateInput");
  const returnDateGroup  = document.getElementById("returnDateGroup");
  const passInput        = document.getElementById("passengersInput");
  const currencyInput    = document.getElementById("currencyInput");
  const swapBtn          = document.getElementById("swapBtn");
  const searchBtn        = document.getElementById("searchBtn");
  const searchBtnText    = document.getElementById("searchBtnText");
  const searchBtnSpinner = document.getElementById("searchBtnSpinner");

  const resultsSection   = document.getElementById("resultsSection");
  const demoBanner       = document.getElementById("demoBanner");
  const errorBanner      = document.getElementById("errorBanner");

  // Outbound refs
  const outboundTitle    = document.getElementById("outboundTitle");
  const outboundSub      = document.getElementById("outboundSub");
  const flightList       = document.getElementById("flightList");
  const noResults        = document.getElementById("noResults");
  const tabBtns          = document.querySelectorAll(".tab-btn");

  // Return refs
  const returnBlock      = document.getElementById("returnBlock");
  const returnTitle      = document.getElementById("returnTitle");
  const returnSub        = document.getElementById("returnSub");
  const returnFlightList = document.getElementById("returnFlightList");
  const noReturnResults  = document.getElementById("noReturnResults");
  const tabBtnsR         = document.querySelectorAll(".tab-btn-r");

  const cardTemplate     = document.getElementById("flightCardTemplate");
  const modalBackdrop    = document.getElementById("modalBackdrop");

  // Track currently expanded card
  let activeCard = null;

  function closeActiveSpotlight() {
    if (!activeCard) return;
    const detailsEl = activeCard.querySelector(".card-details");
    const expandHint = activeCard.querySelector(".expand-hint");
    if (detailsEl) detailsEl.style.display = "none";
    activeCard.classList.remove("expanded", "active-spotlight");
    if (expandHint) expandHint.innerHTML = "Click for details &#9662;";
    activeCard = null;
    document.body.classList.remove("has-active-modal");
    if (modalBackdrop) modalBackdrop.style.display = "none";
  }

  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", () => {
      closeActiveSpotlight();
    });
  }

  // Also allow Escape key to close
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && activeCard) {
      closeActiveSpotlight();
    }
  });

  // ── State ─────────────────────────────────────────────────────────────
  let outboundOffers = [];
  let returnOffers   = [];
  let currentSort    = "price";
  let currentSortR   = "price";

  // ── Date min ──────────────────────────────────────────────────────────
  const today = new Date().toISOString().slice(0, 10);
  dateInput.setAttribute("min", today);
  returnDateInput.setAttribute("min", today);

  // ── Trip type toggle ──────────────────────────────────────────────────
  document.querySelectorAll("input[name='tripType']").forEach(radio => {
    radio.addEventListener("change", () => {
      const isReturn = radio.value === "return" && radio.checked;
      returnDateGroup.style.display = isReturn ? "" : "none";
      if (isReturn && dateInput.value) {
        returnDateInput.setAttribute("min", dateInput.value);
      }
    });
  });
  dateInput.addEventListener("change", () => {
    if (dateInput.value) returnDateInput.setAttribute("min", dateInput.value);
  });

  function isReturnTrip() {
    const r = document.querySelector("input[name='tripType']:checked");
    return r && r.value === "return";
  }

  // ── Autocomplete ──────────────────────────────────────────────────────
  function buildAutocomplete(textInput, hiddenInput, listEl) {
    let debounceTimer = null;

    textInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      hiddenInput.value = "";
      const q = textInput.value.trim();
      if (q.length < 2) { hideList(listEl); return; }
      debounceTimer = setTimeout(() => fetchSuggestions(q, textInput, hiddenInput, listEl), 300);
    });

    textInput.addEventListener("keydown", (e) => {
      if (listEl.hidden) return;
      const items = listEl.querySelectorAll("li[data-id]");
      const active = listEl.querySelector("li.active");
      let idx = Array.from(items).indexOf(active);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        idx = (idx + 1) % items.length;
        items.forEach((li, i) => li.classList.toggle("active", i === idx));
        items[idx]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        idx = (idx - 1 + items.length) % items.length;
        items.forEach((li, i) => li.classList.toggle("active", i === idx));
        items[idx]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (active) active.click();
      } else if (e.key === "Escape") {
        hideList(listEl);
      }
    });

    document.addEventListener("click", (e) => {
      if (!textInput.contains(e.target) && !listEl.contains(e.target)) hideList(listEl);
    });
  }

  async function fetchSuggestions(query, textInput, hiddenInput, listEl) {
    showLoading(listEl);
    try {
      const res  = await fetch(`/api/suggest?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (data.error && !data.suggestions.length) {
        showEmpty(listEl, data.error || "No suggestions available."); return;
      }
      renderSuggestions(data.suggestions, textInput, hiddenInput, listEl);
    } catch {
      showEmpty(listEl, "Could not load suggestions.");
    }
  }

  function renderSuggestions(items, textInput, hiddenInput, listEl) {
    listEl.innerHTML = "";
    if (!items.length) { showEmpty(listEl, "No matching places found."); return; }
    items.forEach(item => {
      const li = document.createElement("li");
      li.setAttribute("role", "option");
      li.setAttribute("data-id", item.id || item.label);
      li.innerHTML =
        `<span class="sug-label">${esc(item.label)}</span>` +
        (item.id ? `<span class="sug-id">${esc(item.id)}${item.type ? " \u00b7 " + esc(item.type) : ""}</span>` : "");
      li.addEventListener("click", () => {
        textInput.value   = item.label;
        hiddenInput.value = item.id || item.label;
        hideList(listEl);
      });
      listEl.appendChild(li);
    });
    listEl.hidden = false;
  }

  function showLoading(listEl) { listEl.innerHTML = `<li class="sug-loading">Searching\u2026</li>`; listEl.hidden = false; }
  function showEmpty(listEl, msg) { listEl.innerHTML = `<li class="sug-empty">${esc(msg)}</li>`; listEl.hidden = false; }
  function hideList(listEl) { listEl.hidden = true; listEl.innerHTML = ""; }

  buildAutocomplete(originInput, originId, originSugg);
  buildAutocomplete(destInput,   destId,   destSugg);

  // ── Swap ──────────────────────────────────────────────────────────────
  swapBtn.addEventListener("click", () => {
    [originInput.value, destInput.value] = [destInput.value, originInput.value];
    [originId.value,    destId.value]    = [destId.value,    originId.value];
  });

  // ── Form submit ───────────────────────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();

    // Fall back to typed text if user didn't pick from dropdown
    if (!originId.value && originInput.value.trim()) originId.value = originInput.value.trim();
    if (!destId.value   && destInput.value.trim())   destId.value   = destInput.value.trim();

    if (!originId.value || !destId.value || !dateInput.value) {
      showError("Please fill in origin, destination, and departure date.");
      return;
    }
    if (isReturnTrip() && !returnDateInput.value) {
      showError("Please select a return date."); return;
    }

    setLoading(true);
    resultsSection.hidden = true;

    const payload = {
      origin_id:    originId.value.trim(),
      origin_label: originInput.value.trim(),
      dest_id:      destId.value.trim(),
      dest_label:   destInput.value.trim(),
      date:         dateInput.value,
      return_date:  isReturnTrip() ? returnDateInput.value : null,
      passengers:   parseInt(passInput.value, 10) || 1,
      currency:     currencyInput.value,
    };

    try {
      const res  = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!data.ok) { showError((data.errors || ["Search failed."]).join(" ")); return; }
      renderResults(data, payload);
    } catch {
      showError("Network error — please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  });

  // ── Results rendering ─────────────────────────────────────────────────
  function renderResults(data, payload) {
    // ── Outbound ──
    outboundOffers = data.outbound?.offers || [];
    currentSort = "price";
    tabBtns.forEach(b => b.classList.toggle("active", b.dataset.sort === "price"));

    const outTotal = data.outbound?.total_found ?? outboundOffers.length;
    const cur      = data.currency || payload.currency || "";
    const pax      = payload.passengers;
    const paxStr   = `${pax} passenger${pax !== 1 ? "s" : ""}`;

    outboundTitle.textContent = `${outTotal} flight${outTotal !== 1 ? "s" : ""} \u2014 ${data.outbound?.route || ""}`;
    outboundSub.textContent   = `${payload.date} \u00b7 ${paxStr} \u00b7 ${cur}`;

    // Demo notice
    if (data.is_demo && data.demo_note) {
      demoBanner.textContent = data.demo_note;
      demoBanner.hidden = false;
    } else {
      demoBanner.hidden = true;
    }

    renderCards(outboundOffers, currentSort, flightList, noResults);

    // ── Return ──
    if (data.return && payload.return_date) {
      returnOffers = data.return?.offers || [];
      currentSortR = "price";
      tabBtnsR.forEach(b => b.classList.toggle("active", b.dataset.sort === "price"));

      const retTotal = data.return?.total_found ?? returnOffers.length;
      returnTitle.textContent = `${retTotal} flight${retTotal !== 1 ? "s" : ""} \u2014 ${data.return?.route || ""}`;
      returnSub.textContent   = `${payload.return_date} \u00b7 ${paxStr} \u00b7 ${cur}`;
      renderCards(returnOffers, currentSortR, returnFlightList, noReturnResults);
      returnBlock.hidden = false;
    } else {
      returnBlock.hidden = true;
    }

    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderCards(offers, sort, listEl, noResultsEl) {
    listEl.innerHTML = "";
    const sorted = sortOffers([...offers], sort);
    if (!sorted.length) { noResultsEl.hidden = false; return; }
    noResultsEl.hidden = true;

    sorted.forEach((offer, idx) => {
      const card = buildCard(offer, idx + 1);
      listEl.appendChild(card);
    });
  }

  function sortOffers(arr, sort) {
    if (sort === "price")    return arr.sort((a, b) => numFare(a) - numFare(b));
    if (sort === "duration") return arr.sort((a, b) => (a.duration_minutes || 9999) - (b.duration_minutes || 9999));
    if (sort === "best")     return arr.sort((a, b) => {
      const sd = (a.stops || 0) - (b.stops || 0);
      return sd !== 0 ? sd : numFare(a) - numFare(b);
    });
    return arr;
  }

  function numFare(o) { return parseFloat(o.total_fare_num ?? o.total_fare ?? 0); }

  function buildCard(offer, rank) {
    const frag = cardTemplate.content.cloneNode(true);
    const card = frag.querySelector(".flight-card");

    // Badges
    const badgesEl = card.querySelector(".card-badges");
    const badgeMap = {
      cheapest:   ["Cheapest",   "badge-cheapest"],
      fastest:    ["Fastest",    "badge-fastest"],
      best_value: ["Best Value", "badge-best-value"],
    };
    (offer.badges || []).forEach(b => {
      if (!badgeMap[b]) return;
      const span = document.createElement("span");
      span.className = `badge ${badgeMap[b][1]}`;
      span.textContent = badgeMap[b][0];
      badgesEl.appendChild(span);
    });
    const src = offer.source || "";
    if (src.includes("DEMO") || src.includes("CACHE")) {
      const span = document.createElement("span");
      span.className = "badge badge-demo";
      span.textContent = "Demo";
      badgesEl.appendChild(span);
    }

    card.querySelector(".airline-name").textContent  = offer.airline || "Airline";
    card.querySelector(".flight-number").textContent = offer.flight_number || "";

    // Price
    const fare = numFare(offer);
    card.querySelector(".price-currency").textContent = offer.currency || "";
    card.querySelector(".price-amount").textContent   = fmt(fare);
    const hasBreakdown = offer.fare_breakdown_available !== false && parseFloat(offer.tax_fees || 0) > 0;
    card.querySelector(".price-note").textContent = hasBreakdown
      ? `Base ${fmt(parseFloat(offer.base_fare || 0))} + Tax ${fmt(parseFloat(offer.tax_fees || 0))}`
      : "Total fare";

    // Times
    card.querySelector(".dep-time").textContent = fmtTime(offer.departure_time);
    card.querySelector(".dep-code").textContent = offer.origin || "";
    card.querySelector(".arr-time").textContent = fmtTime(offer.arrival_time);
    card.querySelector(".arr-code").textContent = offer.destination || "";

    card.querySelector(".route-duration").textContent = offer.duration || "";
    const stops = parseInt(offer.stops ?? 0, 10);
    card.querySelector(".route-stops").textContent =
      stops === 0 ? "Non-stop"
      : `${stops} stop${stops > 1 ? "s" : ""}${offer.layovers?.length ? " \u00b7 " + offer.layovers.join(", ") : ""}`;

    card.querySelector(".meta-cabin").textContent   = offer.cabin   || "Economy";
    card.querySelector(".meta-baggage").textContent = offer.baggage || "";
    card.querySelector(".meta-source").textContent  = offer.source_label || src;

    // ── Build Segment / Stop details ─────────────────────────────────────
    const detailsEl = card.querySelector(".card-details");
    const segContainer = card.querySelector(".segments-container");
    const expandHint = card.querySelector(".expand-hint");

    const segments = offer.segments || [];
    if (segments.length > 0) {
      segments.forEach((seg, sIdx) => {
        const segBox = document.createElement("div");
        segBox.className = "segment-box";

        const depAp = seg.departure_airport || {};
        const arrAp = seg.arrival_airport || {};

        segBox.innerHTML = `
          <div class="segment-header">
            <span class="segment-airline">${esc(seg.airline || offer.airline)} ${esc(seg.flight_number || "")}</span>
            <span class="segment-aircraft">${esc(seg.airplane || "")}${seg.travel_class ? " \u00b7 " + esc(seg.travel_class) : ""}</span>
          </div>
          <div class="segment-route-flow">
            <div class="segment-endpoint">
              <span class="endpoint-code">${esc(depAp.id || offer.origin)}</span>
              <span class="endpoint-time">${fmtTime(depAp.time)}</span>
              <span class="endpoint-name">${esc(depAp.name || "")}</span>
            </div>
            <div class="segment-arrow">
              <span>${esc(seg.duration || "")}</span>
              <div class="arrow-line">&xrarr;</div>
            </div>
            <div class="segment-endpoint" style="text-align: right;">
              <span class="endpoint-code">${esc(arrAp.id || offer.destination)}</span>
              <span class="endpoint-time">${fmtTime(arrAp.time)}</span>
              <span class="endpoint-name">${esc(arrAp.name || "")}</span>
            </div>
          </div>
        `;
        segContainer.appendChild(segBox);

        // Layover if any
        if (seg.layover_after) {
          const lo = seg.layover_after;
          const loDiv = document.createElement("div");
          loDiv.className = "layover-box";
          loDiv.innerHTML = `
            <span>&#9201; Layover in <strong>${esc(lo.id || "")}</strong> (${esc(lo.name || "")}) &mdash; <strong>${esc(lo.duration_str || "")}</strong></span>
          `;
          segContainer.appendChild(loDiv);
        }
      });
    } else {
      // Fallback if provider didn't return segments array
      const segBox = document.createElement("div");
      segBox.className = "segment-box";
      const stopsTxt = stops === 0 ? "Non-stop direct flight" : `${stops} stop(s) via ${offer.layovers?.join(", ") || "connecting airport"}`;
      segBox.innerHTML = `
        <div class="segment-route-flow">
          <div class="segment-endpoint">
            <span class="endpoint-code">${esc(offer.origin)}</span>
            <span class="endpoint-time">${fmtTime(offer.departure_time)}</span>
          </div>
          <div class="segment-arrow">
            <span>${esc(offer.duration || "")}</span>
            <div class="arrow-line">&xrarr;</div>
            <span>${stopsTxt}</span>
          </div>
          <div class="segment-endpoint" style="text-align: right;">
            <span class="endpoint-code">${esc(offer.destination)}</span>
            <span class="endpoint-time">${fmtTime(offer.arrival_time)}</span>
          </div>
        </div>
      `;
      segContainer.appendChild(segBox);
    }

    // Toggle on click with blur spotlight effect
    card.addEventListener("click", (evt) => {
      // Don't toggle if clicking links or interactive elements
      if (evt.target.closest("a, button, input")) return;
      const isOpen = detailsEl.style.display !== "none";

      if (isOpen) {
        closeActiveSpotlight();
      } else {
        // If another card is already open, close it first
        if (activeCard && activeCard !== card) {
          closeActiveSpotlight();
        }
        detailsEl.style.display = "block";
        card.classList.add("expanded", "active-spotlight");
        expandHint.innerHTML = "Hide details &#9652;";
        activeCard = card;

        document.body.classList.add("has-active-modal");
        if (modalBackdrop) modalBackdrop.style.display = "block";

        // Scroll slightly if needed to ensure entire expanded card is in view
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });

    return frag;
  }

  // ── Tab sort ──────────────────────────────────────────────────────────
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      currentSort = btn.dataset.sort;
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderCards(outboundOffers, currentSort, flightList, noResults);
    });
  });
  tabBtnsR.forEach(btn => {
    btn.addEventListener("click", () => {
      currentSortR = btn.dataset.sort;
      tabBtnsR.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderCards(returnOffers, currentSortR, returnFlightList, noReturnResults);
    });
  });

  // ── Helpers ───────────────────────────────────────────────────────────
  function showError(msg) { errorBanner.textContent = msg; errorBanner.hidden = false; errorBanner.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  function clearError()   { errorBanner.textContent = ""; errorBanner.hidden = true; }
  function setLoading(on) {
    searchBtn.disabled = on;
    searchBtnText.textContent = on ? "Searching…" : "Search Flights";
    if (searchBtnSpinner) {
      searchBtnSpinner.style.display = on ? "inline-block" : "none";
    }
  }

  function fmtTime(s) {
    if (!s) return "\u2014";
    try {
      const d = new Date(s);
      if (isNaN(d)) return s.length > 10 ? s.slice(11, 16) : s;
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    } catch { return s; }
  }

  function fmt(n) {
    if (isNaN(n)) return String(n);
    return Number(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

})();
