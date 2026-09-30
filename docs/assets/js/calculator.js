/* Vietnam Travel Guide — trip budget estimator.
   Data lives in src/data/costs.json and is inlined below at build time.
   Runs entirely in the browser; nothing is sent anywhere. */
(function () {
  "use strict";

  var DATA = window.VNT_COSTS;
  var form = document.getElementById("budget-calculator");
  if (!DATA || !form) { return; }

  var out = document.getElementById("calc-output");
  var fmt = function (n) {
    return "$" + Math.round(n).toLocaleString("en-US");
  };
  var range = function (lo, hi) {
    return fmt(lo) + "–" + fmt(hi);
  };

  function styleData() {
    var picked = form.querySelector('input[name="style"]:checked');
    return DATA.styles[picked ? picked.value : "mid"] || DATA.styles.mid;
  }

  function selectedCities() {
    return Array.prototype.slice
      .call(form.querySelectorAll('input[name="city"]:checked'))
      .map(function (el) { return el.value; })
      .map(function (id) {
        return DATA.cities.filter(function (c) { return c.id === id; })[0];
      })
      .filter(Boolean);
  }

  function cityIndex(cities) {
    if (!cities.length) { return 1; }
    var total = cities.reduce(function (sum, c) { return sum + (c.index || 1); }, 0);
    return total / cities.length;
  }

  function transferLegs(cities) {
    var legs = { count: 0, lo: 0, hi: 0 };
    for (var i = 1; i < cities.length; i++) {
      var same = cities[i - 1].region === cities[i].region;
      var band = same ? DATA.transfers.same_region : DATA.transfers.cross_region;
      legs.count++;
      legs.lo += band[0];
      legs.hi += band[1];
    }
    return legs;
  }

  function calculate() {
    var days = Math.max(1, Math.min(60, parseInt(form.days.value, 10) || 1));
    var people = Math.max(1, Math.min(20, parseInt(form.travelers.value, 10) || 1));
    var rooms = Math.ceil(people / 2);
    var style = styleData();
    var cities = selectedCities();
    var idx = cityIndex(cities);
    var legs = transferLegs(cities);
    var ex = DATA.extras;

    var rows = [
      { label: "Accommodation", detail: rooms + (rooms > 1 ? " rooms" : " room") + " × " + days + " nights",
        lo: style.room_night[0] * rooms * days * idx, hi: style.room_night[1] * rooms * days * idx, group: true },
      { label: "Food and drink", detail: people + (people > 1 ? " people" : " person") + " × " + days + " days",
        lo: style.food_day[0] * people * days * idx, hi: style.food_day[1] * people * days * idx, group: true },
      { label: "Local transport", detail: "taxis, Grab, buses, bikes",
        lo: style.local_day[0] * people * days, hi: style.local_day[1] * people * days, group: true },
      { label: "Tickets and activities", detail: "temples, museums, boats, tours",
        lo: style.activities_day[0] * people * days * idx, hi: style.activities_day[1] * people * days * idx, group: true },
      { label: "Getting between stops", detail: legs.count ? legs.count + (legs.count > 1 ? " legs" : " leg") + " between cities" : "one base, no transfers",
        lo: legs.lo * people, hi: legs.hi * people, group: true },
      { label: "SIM, tips and small extras", detail: "data plan, tipping, laundry, ATM fees",
        lo: (ex.sim_per_person[0] + (ex.tips_per_person_day[0] + ex.laundry_atm_per_person_day[0]) * days) * people,
        hi: (ex.sim_per_person[1] + (ex.tips_per_person_day[1] + ex.laundry_atm_per_person_day[1]) * days) * people,
        group: true }
    ];

    var totalLo = rows.reduce(function (s, r) { return s + r.lo; }, 0);
    var totalHi = rows.reduce(function (s, r) { return s + r.hi; }, 0);
    var perPersonLo = totalLo / people;
    var perPersonHi = totalHi / people;

    var html = "";
    html += '<div class="calc-total">';
    html += '<p class="label">Estimated trip cost</p>';
    html += '<p class="value">' + range(totalLo, totalHi) + "</p>";
    html += '<p class="sub">' + range(perPersonLo, perPersonHi) + " per person · " +
            range(perPersonLo / days, perPersonHi / days) + " per person per day · " +
            style.label.toLowerCase() + " style" + (cities.length ? ", " + cities.length + (cities.length > 1 ? " bases" : " base") : "") + "</p>";
    html += "</div>";

    html += '<div class="table-wrap"><table class="table table--budget">';
    html += "<caption>Planning estimate in US dollars, " + DATA.updated + ". Ranges reflect low and high season and how far ahead you book.</caption>";
    html += "<thead><tr><th scope=\"col\">Category</th><th scope=\"col\">Basis</th><th scope=\"col\">Low</th><th scope=\"col\">High</th></tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr><th scope=\"row\">" + r.label + "</th><td>" + r.detail + "</td><td>" + fmt(r.lo) + "</td><td>" + fmt(r.hi) + "</td></tr>";
    });
    html += '<tr><th scope="row">Total for the group</th><td>' + people + (people > 1 ? " people" : " person") + ", " + days + " days</td><td>" +
            fmt(totalLo) + "</td><td>" + fmt(totalHi) + "</td></tr>";
    html += "</tbody></table></div>";
    html += '<p class="note">' + DATA.note + "</p>";

    out.innerHTML = html;
  }

  var print = document.getElementById("calc-print");
  if (print) { print.addEventListener("click", function () { window.print(); }); }

  form.addEventListener("input", calculate);
  form.addEventListener("change", calculate);
  form.addEventListener("reset", function () { window.setTimeout(calculate, 0); });
  calculate();
})();
