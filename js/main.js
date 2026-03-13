window.metadata = {};
window.allRows = [];
window.currentYear = 0;

// Initialize map
var map = L.map('map').setView([51.0504, 13.7373], 14);
var Jawg_Sunny = L.tileLayer(
  `https://tile.jawg.io/jawg-light/{z}/{x}/{y}{r}.png?access-token=${window.JAWG_TOKEN}`, 
  { attribution: 'Tiles © Jawg Maps & OpenStreetMap contributors', minZoom:0, maxZoom:22 }
);
Jawg_Sunny.addTo(map);

window.pointLayer = L.layerGroup().addTo(map);
window.osmLayerGroup = L.layerGroup().addTo(map);
window.osmFeatureLayers = [];

// Load CSV
Papa.parse("Data/places_dresden_combined_with_sentences_with_osm_flag.csv", {
  download: true,
  header: true,
  delimiter: "|",
  complete: function(results) {
    allRows = results.data;
    allRows.forEach(row => {
      if (row.Entity_normed) {
        if (!metadata[row.Entity_normed]) metadata[row.Entity_normed] = [];
        metadata[row.Entity_normed].push(row);
      }
    });
    const years = allRows.map(r=>parseInt(r.Year)).filter(y=>!isNaN(y));
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    generateYearTicks(minYear, maxYear);
    let slider = document.getElementById("yearSlider");
    slider.min = minYear; slider.max = maxYear; slider.value = minYear;
    document.getElementById("yearLabel").innerText = minYear;
    currentYear = minYear;

    slider.addEventListener("input", function(e){
      currentYear = parseInt(e.target.value);
      document.getElementById("yearLabel").innerText = currentYear;
      updateMap(); // defined in functions.js or main.js
    });

    updateMap();
  }
});