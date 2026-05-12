const TRANSLATIONS = {
  de: {
    about: "Info",
    map: "Karte",
    year: "Jahr",
    certainLocation: "Ort sicher<br>(historischer und moderner Name stimmen überein)",
    uncertainLocation: "Ort unsicher<br>(historischer Name kann nicht eindeutig zugeordnet werden)",
    dresdenMentions: "Dresden-Erwähnungen",
    footerProject: "<strong>Deep Mapping Dresden</strong> - Reiseberichte 1604-1900",
    footerGithub: 'Projekt auf <a href="https://github.com/LuisePohlmann/Deep-Mapping-Dresden/">Github</a> ansehen',
    languageButton: "English",
    aboutTitle: "Über dieses Projekt",
    aboutIntro: 'Diese interaktive Karte visualisiert Ortsnennungen in historischen Reiseberichten über Dresden. Sie ermöglicht es, zu erkunden, wie verschiedene Sehenswürdigkeiten in und um Dresden im Laufe der Zeit von Reisenden beschrieben wurden. Die Karte wurde im Rahmen des Studiengangs "Digital Humanities M.A." von Luise Pohlmann im März 2026 erstellt.',
    dataHeading: "Daten",
    dataText: 'Die für diese Visualisierung verwendeten Reiseberichte stammen aus der digitalen Sammlung von Reiseberichten über Sachsen des <a href="https://reise.isgv.de/" target="_blank">Instituts für Sächsische Geschichte und Volkskunde (ISGV)</a>.<br>Die Metadaten wurden von der Website ausgelesen und die Bilder der Reiseberichtsseiten mithilfe einem Lareg Language Model (LLM) transkribiert. Anschließend wurden Ortsnamen mit einem LLM extrahiert. Schließlich wurden die Ortsnamen georeferenziert, indem ihre Namen entweder über OpenStreetMap oder, falls dies keine Ergebnisse lieferte, über Nominatim gesucht wurden. Einige Orte konnten nicht georeferenziert werden; in diesen Fällen wurde ein LLM genutzt, um Transkriptionsfehler zu korrigieren oder Schreibweisen zu modernisieren. Diese Orte sind auf der Karte in gelb markiert. Insgesamt sind 1025 Ortsnennungen aus 80 Reiseberichten von 67 Autoren zwischen 1604 und 1900 enthalten (siehe vollständige Liste in der Bibliografie unten).<br><br>Weitere Informationen zu den Daten und Skripten finden sich im Repository des Projekts auf <a href="https://github.com/LuisePohlmann/Deep-Mapping-Dresden/" target="_blank">Github</a> oder per E-Mail an <a href="mailto:Luise.Pohlmann01@stud.uni-goettingen.de">Luise Pohlmann</a>.',
    howToHeading: "Nutzung",
    howTo1: "Nutzen Sie den Jahresregler, um Nennungen chronologisch zu erkunden.",
    howTo2: "Klicken Sie auf Kartenelemente, um Zitate zu diesem Ort zu lesen.",
    howTo3: 'Die Seitenleiste zeigt, was allgemein über "Dresden" geschrieben wurde.',
    howTo4: "Die Punkte verblassen, je weiter ihre Nennungen in der Vergangenheit liegen.",
    bibliographyIntro: "Für dieses Projekt wurden die folgenden Reiseberichte und Metadaten verwendet.",
    bibliographyLoading: "Bibliografie wird geladen...",
    bibliographyHeading: "Bibliografie der Reiseberichte",
    bibliographySource: "Quelle",
    bibliographyError: "Die Bibliografie konnte nicht geladen werden.",
    noMetadata: "Keine Metadaten vorhanden",
    authorUnknown: "Autor:in unbekannt",
    quote: "Zitat",
    title: "Titel",
    journeyTime: "Reisezeit",
    page: "Seite",
    source: "Quelle",
    openSource: "Beim Datenanbieter öffnen",
    noDresdenMentions: "Bis zu diesem Jahr gibt es keine Dresden-Erwähnungen.",
    boundaryPopup: "Befestigungsanlagen nach Karte von"
  },
  en: {
    about: "About",
    map: "Map",
    year: "Year",
    certainLocation: "certain of location<br>(historical and modern names match)",
    uncertainLocation: "unsure of location<br>(historical name cannot be certainly matched)",
    dresdenMentions: "Dresden Mentions",
    footerProject: "<strong>Deep Mapping Dresden</strong> - Travelogues 1604-1900",
    footerGithub: 'See project on <a href="https://github.com/LuisePohlmann/Deep-Mapping-Dresden/">Github</a>',
    languageButton: "Deutsch",
    aboutTitle: "About This Project",
    aboutIntro: 'This interactive map visualizes place mentions in historical travel writings about Dresden. The map allows exploration of how locations were described by travelers over time. The map was created as part of the study program "Digital Humanities M.A." by Luise Pohlmann in March 2026.',
    dataHeading: "Data",
    dataText: 'The travelogues used for this visualisation come from the digital collection of travelogues concerning Saxony provided by the <a href="https://reise.isgv.de/" target="_blank">Institut für Sächsische Geschichte und Volkskunde (isgv)</a>.<br>The Metadata was scraped from their site and the images of the travelogue pages were transribed using a large language model. Next, place names were extracted using a different large language model. Finally, the place names were georeferenced by looking up their names either using either Open Street Map, or in cases where this did not yield results, using nominatim. Some places could not be georeferenced, in these cases, a large language model was used to try to correct transcription errors or modernize the spelling. These are the places marked as "uncertain" on the map. Overall 1025 place mentions from 80 travelogues by 67 authors written between 1604 and 1900 are included (see fulll ist in the bibliography below).<br><br>For further information on the data and scripts, see the repository for this project on <a href="https://github.com/LuisePohlmann/Deep-Mapping-Dresden/" target="_blank">github</a> or send me an email <a href="mailto:Luise.Pohlmann01@stud.uni-goettingen.de">Luise Pohlmann</a>.',
    howToHeading: "How to Use",
    howTo1: "Use the year slider to explore references chronologically.",
    howTo2: "Click map features to read quotes mentioning that place.",
    howTo3: 'The sidebar shows what people wrote about "Dresden" in general.',
    howTo4: "The points fade in color as their mentions fade into the past.",
    bibliographyIntro: "The following travelogues and their metadata were used for this project.",
    bibliographyLoading: "Loading bibliography...",
    bibliographyHeading: "Bibliography of Travelogues",
    bibliographySource: "Source",
    bibliographyError: "Bibliography could not be loaded.",
    noMetadata: "No metadata available",
    authorUnknown: "Author unknown",
    quote: "Quote",
    title: "Title",
    journeyTime: "Journey Time",
    page: "Page",
    source: "Source",
    openSource: "Open on data provider's page",
    noDresdenMentions: "No Dresden mentions up to this year.",
    boundaryPopup: "Fortifications according to map from"
  }
};

window.currentLanguage = "de";

function t(key) {
  return TRANSLATIONS[window.currentLanguage]?.[key] || TRANSLATIONS.de[key] || key;
}

function applyTranslations() {
  document.documentElement.lang = window.currentLanguage;

  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = t(element.dataset.i18n);
  });

  document.querySelectorAll("[data-i18n-html]").forEach(element => {
    element.innerHTML = t(element.dataset.i18nHtml);
  });

  document.querySelectorAll("[data-i18n-toggle]").forEach(element => {
    element.textContent = t("languageButton");
  });
}

function refreshDynamicText() {
  if (typeof updateBoundaryPopupText === "function") updateBoundaryPopupText();
  if (typeof renderDresdenSidebar === "function") renderDresdenSidebar();
  if (typeof updateMap === "function" && window.allRows?.length) updateMap();
}

function toggleLanguage() {
  window.currentLanguage = window.currentLanguage === "de" ? "en" : "de";
  applyTranslations();
  document.dispatchEvent(new CustomEvent("languagechange"));
  refreshDynamicText();
}

document.addEventListener("DOMContentLoaded", () => {
  applyTranslations();
  document.querySelectorAll("[data-i18n-toggle]").forEach(button => {
    button.addEventListener("click", toggleLanguage);
  });
});
