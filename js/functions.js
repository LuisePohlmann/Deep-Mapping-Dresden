const COLORS = {
  certain: "#084808",
  uncertain: "#FFA500",
};

// -----------------------------
// 1. COLOR LOGIC
// -----------------------------
function getColorByCertainty(entries) {
  if (!entries || entries.length === 0) return COLORS.uncertain;
  return entries.some(e => (e.Certainty || "").toLowerCase() === "uncertain")
    ? COLORS.uncertain
    : COLORS.certain;
}

// -----------------------------
// 2. TIME SLIDER TICKS
// -----------------------------
function generateYearTicks(minYear, maxYear) {
  let container = document.getElementById("timelineTicks");
  if (!container) return;
  container.innerHTML = "";
  for (let y = Math.ceil(minYear / 50) * 50; y <= maxYear; y += 50) {
    let percent = ((y - minYear) / (maxYear - minYear)) * 100;
    let tick = document.createElement("div");
    tick.style.position = "absolute";
    tick.style.left = percent + "%";
    tick.style.transform = "translateX(-50%)";
    tick.style.fontSize = "11px";
    tick.innerText = y;
    container.appendChild(tick);
  }
}

// -----------------------------
// 3. POPUPS & CHARTS
// -----------------------------
function buildPopupContent(entries) {
  if (!entries || entries.length === 0) return "<b>No metadata available</b>";
  let html = `<div class="popup-title">${entries[0].geocode_query || ""}</div>`;
  entries.forEach((data, index) => {
    html += `${index === 0 ? `<canvas class="mentionChart" height="120"></canvas>` : ""}
      <div class="popup-entry">
        <div class="popup-subtitle">
          ${data.Author === "Kein Eintrag vorhanden" ? "Author unknown" : data.Author || ""} (${data.Year || ""})
        </div>
        <div><i>${data["historical spelling"] || ""}</i></div>
        <div class="popup-meta">
          <div class="popup-row">
            <div class="popup-label">Quote</div>
            <div class="popup-value"><i>${data["Full Sentence"] || ""}</i></div>
          </div>
          <div class="popup-row">
            <div class="popup-label">Title</div>
            <div class="popup-value">${data.Title || ""}</div>
          </div>
          <div class="popup-row">
            <div class="popup-label">Journey Time</div>
            <div class="popup-value">${data["Travel Period"] || ""}</div>
          </div>
          <div class="popup-row">
            <div class="popup-label">Page</div>
            <div class="popup-value">${data.Pages || ""}</div>
          </div>
          ${
            data.Link
              ? `<div class="popup-row">
                   <div class="popup-label">Source</div>
                   <div class="popup-value">
                     <a href="${data.Citable_URL}" target="_blank">Open on data provider's page</a>
                   </div>
                 </div>`
              : ""
          }
        </div>
      </div>
      ${index < entries.length - 1 ? "<hr>" : ""}`;
  });
  return `<div class="popup-scroll-container">${html}</div>`;
}

function renderMentionChart(entityName, container) {
  if (!container || !allRows) return;
  let bins = {};
  let entityLower = Array.isArray(entityName)
    ? (entityName[0].Entity || "").toLowerCase()
    : entityName.toLowerCase();
  allRows.forEach(row => {
    if (!row.Entity_normed) return;
    if (row.Entity_normed.toLowerCase() !== entityLower) return;
    let year = parseInt(row.Year);
    if (isNaN(year)) return;
    let bin = Math.floor(year / 50) * 50;
    bins[bin] = (bins[bin] || 0) + 1;
  });
  let labels = Object.keys(bins).sort((a,b)=>a-b);
  let values = labels.map(l => bins[l]);
  new Chart(container, {
    type: "bar",
    data: { labels, datasets: [{ data: values }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero:true, ticks:{precision:0} } } }
  });
}

// -----------------------------
// 4. TEMPORAL FEATURE HELPERS
// -----------------------------
function getFeatureTemporalState(entries) {
  if (!entries || entries.length === 0) return {opacity:0, firstYear:null};
  let years = entries.map(e=>parseInt(e.Year)).filter(y=>!isNaN(y));
  if (years.length === 0) return {opacity:0, firstYear:null};
  let firstYear = Math.min(...years);
  if (currentYear < firstYear) return {opacity:0, firstYear};
  let age = currentYear - firstYear;
  let maxFade = 80;
  let opacity = Math.max(0.15, Math.min(1, 1 - (age / maxFade)));
  return {opacity, firstYear};
}

function getFeatureOpacity(entries) {
  if (!entries || entries.length===0) return 0.1;
  let years = entries.map(e=>parseInt(e.Year)).filter(y=>!isNaN(y)&&y<=currentYear);
  if (years.length===0) return 0.1;
  let latestYear = Math.max(...years);
  let age = currentYear - latestYear;
  let maxFade = 80;
  return Math.max(0.15, Math.min(1, 1-(age/maxFade)));
}

// -----------------------------
// 5. UPDATE MAP
// -----------------------------
function updateMap() {
  pointLayer.clearLayers();
  osmLayerGroup.clearLayers();
  updateBoundaries();
  loadOSMFeatures();
  setTimeout(()=>{
    plotUnmatchedPoints();
    renderDresdenSidebar();
  }, 300);
}

// -----------------------------
// 6. HISTORICAL BOUNDARIES
// -----------------------------
let boundaryLayers = { altstadt1529:null, neustadt1529:null, altstadt1750:null, neustadt1750:null };
const boundaryStyle = { color:"#666", weight:2, opacity:0.7, fillColor:"#999", fillOpacity:0.2 };
const boundaryYear = { altstadt1529:1529, neustadt1529:1529, altstadt1750:1750, neustadt1750:1750 };

function loadBoundaryLayer(path, key){
  fetch(path).then(r=>r.json()).then(data=>{
    let year = boundaryYear[key] || "";
    let layer = L.geoJSON(data,{style:boundaryStyle,onEachFeature:(f,l)=>l.bindPopup(`Befestigungsanlagen nach Karte von ${year}`)});
    boundaryLayers[key]=layer;
    if(key.endsWith("1529")) layer.addTo(map);
  });
}

function updateBoundaries(){
  if(currentYear<1750){
    if(boundaryLayers.altstadt1529) boundaryLayers.altstadt1529.addTo(map);
    if(boundaryLayers.neustadt1529) boundaryLayers.neustadt1529.addTo(map);
    if(boundaryLayers.altstadt1750) map.removeLayer(boundaryLayers.altstadt1750);
    if(boundaryLayers.neustadt1750) map.removeLayer(boundaryLayers.neustadt1750);
  } else if(currentYear<1820){
    if(boundaryLayers.altstadt1529) map.removeLayer(boundaryLayers.altstadt1529);
    if(boundaryLayers.neustadt1529) map.removeLayer(boundaryLayers.neustadt1529);
    if(boundaryLayers.altstadt1750) boundaryLayers.altstadt1750.addTo(map);
    if(boundaryLayers.neustadt1750) boundaryLayers.neustadt1750.addTo(map);
  } else {
    Object.values(boundaryLayers).forEach(l=>{if(l) map.removeLayer(l)});
  }
}

// Initialize boundaries
loadBoundaryLayer("Data/historical_maps_dresden/Wall_Altstadt_1529_mit_Toren.geojson","altstadt1529");
loadBoundaryLayer("Data/historical_maps_dresden/Wall_Neustadt_1529_mit_Toren.geojson","neustadt1529");
loadBoundaryLayer("Data/historical_maps_dresden/Wall_Altstadt_1750_mit_Toren.geojson","altstadt1750");
loadBoundaryLayer("Data/historical_maps_dresden/Wall_Neustadt_1750_mit_Toren.geojson","neustadt1750");

// -----------------------------
// 7. DRESDEN SIDEBAR
// -----------------------------
function renderDresdenSidebar() {
  const container = document.getElementById("dresdenContent");
  container.innerHTML = "";

  // Collect all entries where Entity_normed is "Dresden"
  let validEntries = [];
  Object.values(metadata).forEach(entries => {
    entries.forEach(e => {
      if ((e.Entity_normed || "").toLowerCase() === "dresden") {
        validEntries.push(e);
      }
    });
  });

  // Filter by current year
  validEntries = validEntries
    .filter(e => !isNaN(parseInt(e.Year)))
    .filter(e => parseInt(e.Year) <= currentYear)
    .sort((a, b) => parseInt(a.Year) - parseInt(b.Year)); // chronological order

  if (validEntries.length === 0) {
    container.innerHTML = "<i>No Dresden mentions up to this year.</i>";
    return;
  }

  container.innerHTML = buildPopupContent(validEntries);
}

// -----------------------------
// 8. OSM FEATURES
// -----------------------------
function loadOSMFeatures(){
  const featureFiles=[
    "osm_features/streets.geojson","osm_features/churches.geojson","osm_features/buildings.geojson",
    "osm_features/bridges.geojson","osm_features/squares.geojson",
    "osm_features/parks.geojson","osm_features/historic_buildings.geojson",
    "osm_features/districts.geojson","osm_features/towns.geojson"
    //"osm_features/rivers.geojson","osm_features/water.geojson",
  ];

    const excludedEntities = ["Sachsens", "Sachsen"];

  featureFiles.forEach(file=>{
    fetch(file).then(res=>res.json()).then(data=>{
      let layer = L.geoJSON(data,{
        filter: f=>{
          let name = f.properties?.name;
          let entries = metadata[name];
          if(!entries) return false;
          if (excludedEntities.includes(name)) return false;
          let firstYear = Math.min(...entries.map(e=>parseInt(e.Year)).filter(y=>!isNaN(y)));
          return currentYear>=firstYear;
        },
        style: f=>{
          let name = f.properties?.name;
          let entries = metadata[name];
          let temporal = getFeatureTemporalState(entries);
          let validEntries = entries.filter(e=>parseInt(e.Year)<=currentYear);
          return {color:getColorByCertainty(validEntries), fillColor:getColorByCertainty(validEntries), opacity:temporal.opacity, fillOpacity:temporal.opacity*0.6, weight:2};
        },
        pointToLayer: (f,latlng)=>{
          let name = f.properties?.name;
          let entries = metadata[name]||[];
          let validEntries = entries.filter(e=>parseInt(e.Year)<=currentYear);
          return L.circleMarker(latlng,{radius:8, color:getColorByCertainty(validEntries), fillColor:getColorByCertainty(validEntries), fillOpacity:getFeatureOpacity(validEntries), opacity:getFeatureOpacity(validEntries), weight:1});
        },
        onEachFeature:(f,l)=>{
          let name = f.properties?.name;
          let entries = metadata[name];
          if(!entries) return;
          let validEntries = entries.filter(e=>parseInt(e.Year)<=currentYear);
          if(validEntries.length===0) return;
          l.bindPopup(buildPopupContent(validEntries));
          l.on("popupopen", e=>{
            let canvas = e.popup.getElement().querySelector(".mentionChart");
            renderMentionChart(name, canvas);
          });
        }
      });
      osmFeatureLayers.push(layer);
      layer.addTo(osmLayerGroup);

            // --- Add invisible thicker interaction layer ONLY for streets ---
    if (file.includes("streets")) {
        let interactiveLayer = L.geoJSON(data, {
        style: f => ({ color: "#333", weight: 10, opacity: 0 }), // invisible but thick
        interactive: true,
        onEachFeature: (f, l) => {
            const name = f.properties?.name;
            const entries = metadata[name];
            if (!entries) return;
            const validEntries = entries.filter(e => parseInt(e.Year) <= currentYear);
            if (validEntries.length === 0) return;

            l.bindPopup(buildPopupContent(validEntries));
            l.on("popupopen", e => {
            const canvas = e.popup.getElement().querySelector(".mentionChart");
            renderMentionChart(name, canvas);
            });
        }
        });
        osmFeatureLayers.push(interactiveLayer);
        interactiveLayer.addTo(osmLayerGroup);
    }
    });
  });
}

// -----------------------------
// 9. UNMATCHED POINTS
// -----------------------------
function plotUnmatchedPoints(){
  allRows.forEach(row=>{
    if(row.Entity==="Dresden") return;
    if((row.osm_feature_found==="False"||row.osm_feature_found===false) && row.latitude && row.longitude){
      if(parseInt(row.Year)>currentYear) return;
      let entries = metadata[row.Entity]||[];
      let validEntries = entries.filter(e=>parseInt(e.Year)<=currentYear);
      validEntries.forEach((entry,i)=>{
        let lat=parseFloat(row.latitude), lng=parseFloat(row.longitude);
        let marker = L.circleMarker([lat,lng],{
          radius:8, color:getColorByCertainty([entry]), fillColor:getColorByCertainty([entry]), fillOpacity:0.8, opacity:0.8, weight:1
        });
        marker.bindPopup(buildPopupContent([entry]));
        marker.on("popupopen", e=>{
          let canvas = e.popup.getElement().querySelector(".mentionChart");
          renderMentionChart(row.Entity, canvas);
        });
        marker.addTo(pointLayer);
      });
    }
  });
  pointLayer.addTo(map);
}