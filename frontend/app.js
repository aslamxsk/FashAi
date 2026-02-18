// Smooth scroll from hero CTA to app section
const appSection = document.getElementById("app-section");
const heroCta = document.getElementById("hero-cta");
const navCta = document.getElementById("nav-cta");

function scrollToApp() {
  if (!appSection) return;
  appSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

if (heroCta) heroCta.addEventListener("click", scrollToApp);
if (navCta) navCta.addEventListener("click", scrollToApp);

// Upload & drag-and-drop handling
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const browseButton = document.getElementById("browse-button");
const thumbnail = document.getElementById("thumbnail");
const thumbnailImg = document.getElementById("thumbnail-img");

let currentImageDataUrl = null;
let selectedGender = null;
let selectedOccasion = null;

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

if (dropzone) {
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, preventDefaults, false);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(
      eventName,
      () => dropzone.classList.add("dragover"),
      false
    );
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(
      eventName,
      () => dropzone.classList.remove("dragover"),
      false
    );
  });

  dropzone.addEventListener("click", () => fileInput && fileInput.click());
  dropzone.addEventListener("drop", handleDrop);
}

if (browseButton && fileInput) {
  browseButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleFileInput);
}

function handleDrop(e) {
  const dt = e.dataTransfer;
  if (!dt || !dt.files || !dt.files.length) return;
  const file = dt.files[0];
  handleFile(file);
}

function handleFileInput(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  handleFile(file);
}

function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please upload an image file.");
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    const result = reader.result;
    if (typeof result === "string") {
      currentImageDataUrl = result;
      if (thumbnail && thumbnailImg) {
        thumbnailImg.src = result;
        thumbnail.hidden = false;
      }
    }
  };
  reader.onerror = () => {
    alert("Failed to read the image. Please try again.");
  };
  reader.readAsDataURL(file);
}

// Gender selection handling
const genderMale = document.getElementById("gender-male");
const genderFemale = document.getElementById("gender-female");
const occasionTagsContainer = document.getElementById("occasion-tags");
const hiddenOccasionSelect = document.getElementById("occasion");

const OCCASIONS = {
  male: [
    "Wedding",
    "Reception",
    "Casual Outing",
    "Office / Formal",
    "Party Night",
    "Date Night",
    "Festive",
    "College",
    "Vacation",
  ],
  female: [
    "Wedding Guest",
    "Reception",
    "Party",
    "Casual",
    "Office",
    "Date",
    "Festive",
    "Brunch",
    "Vacation",
    "Traditional Function",
  ],
};

function renderOccasionsFor(gender) {
  if (!occasionTagsContainer) return;
  occasionTagsContainer.innerHTML = "";
  const list = OCCASIONS[gender] || [];
  list.forEach((o) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "occasion-tag";
    btn.textContent = o;
    btn.addEventListener("click", () => {
      // toggle
      if (selectedOccasion === o) {
        selectedOccasion = null;
        btn.classList.remove("selected");
        if (hiddenOccasionSelect) hiddenOccasionSelect.value = "";
      } else {
        // clear previous selected
        occasionTagsContainer.querySelectorAll(".occasion-tag").forEach((n) => n.classList.remove("selected"));
        selectedOccasion = o;
        btn.classList.add("selected");
        if (hiddenOccasionSelect) hiddenOccasionSelect.value = o;
      }
    });
    occasionTagsContainer.appendChild(btn);
  });
}

function setGender(gender) {
  selectedGender = gender;
  // UI selection
  if (genderMale) genderMale.classList.toggle("selected", gender === "male");
  if (genderFemale) genderFemale.classList.toggle("selected", gender === "female");
  renderOccasionsFor(gender);
}

if (genderMale) genderMale.addEventListener("click", () => setGender("male"));
if (genderFemale) genderFemale.addEventListener("click", () => setGender("female"));


// Form submission & API call
const styleForm = document.getElementById("style-form");
const resultCard = document.getElementById("result-card");
const resultImage = document.getElementById("result-image");
const resultError = document.getElementById("result-error");
const resultLoader = document.getElementById("result-loader");
const generateButton = document.getElementById("generate-button");
const tryAgainButton = document.getElementById("try-again-button");
const downloadButton = document.getElementById("download-button");

async function handleSubmit(e) {
  e.preventDefault();

  if (!currentImageDataUrl) {
    alert("Please upload a photo first.");
    return;
  }

  if (!styleForm || !generateButton) return;

  // Collect form values
  const outfit = document.getElementById("outfit")?.value || "Modern outfit";
  const occasion = document.getElementById("occasion")?.value || "";
  const fit = document.getElementById("fit")?.value || "";
  const color = document.getElementById("color")?.value || "";
  const accessoriesRaw = document.getElementById("accessories")?.value || "";
  const vibe = document.getElementById("vibe")?.value || "";
  const aesthetic = document.getElementById("aesthetic")?.value || "";
  const variation = !!document.getElementById("variation")?.checked;

  const accessories = accessoriesRaw
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

  const payload = {
    image_b64: currentImageDataUrl,
    outfit,
    occasion: occasion || null,
    fit: fit || null,
    color: color || null,
    accessories: accessories.length ? accessories : null,
    vibe: vibe || null,
    aesthetic: aesthetic || null,
    variation,
    ratio: "4:5",
  };

  // UI state: show card & loader
  if (resultCard) resultCard.hidden = false;
  if (resultLoader) resultLoader.hidden = false;
  if (resultImage) resultImage.hidden = true;
  if (resultError) {
    resultError.hidden = true;
    resultError.textContent = "";
  }
  if (downloadButton) {
    downloadButton.disabled = true;
  }

  generateButton.disabled = true;
  generateButton.textContent = "Generating...";

  try {
    const response = await fetch("/api/fash-ai", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed with status ${response.status}`);
    }

    const data = await response.json();
    console.log("Fash AI response:", data);

    if (!data.success) {
      throw new Error(data.error || "Generation failed. Please try again.");
    }

    const list = data.result || [];
    const first = list[0] || {};

    // Prefer the final processed result URL, then fall back to other fields
    const imageUrl =
      first.result_url ||
      (Array.isArray(first.media_urls) && first.media_urls[0]) ||
      first.url ||
      first.image_url ||
      first.image ||
      null;

    if (!imageUrl) {
      throw new Error("No image URL found in the response.");
    }

    // Ensure loader is completely removed once we have a result
    if (resultLoader) {
      resultLoader.hidden = true;
      resultLoader.style.display = "none";
    }

    if (resultImage) {
      resultImage.src = imageUrl;
      resultImage.hidden = false;
    }

    if (downloadButton) {
      downloadButton.disabled = false;
      // Store URL on the button for later download
      downloadButton.dataset.url = imageUrl;
    }
  } catch (err) {
    console.error(err);
    if (resultError) {
      resultError.textContent =
        err instanceof Error ? err.message : "Something went wrong.";
      resultError.hidden = false;
    }
  } finally {
    if (resultLoader) resultLoader.hidden = true;
    generateButton.disabled = false;
    generateButton.textContent = "Generate My Look";
  }
}

if (styleForm) {
  styleForm.addEventListener("submit", handleSubmit);
}

// Try again: reset result and scroll back up
if (tryAgainButton) {
  tryAgainButton.addEventListener("click", () => {
    if (resultImage) {
      resultImage.hidden = true;
      resultImage.src = "";
    }
    if (resultError) {
      resultError.hidden = true;
      resultError.textContent = "";
    }
    if (resultLoader) {
      resultLoader.hidden = true;
    }
    if (downloadButton) {
      downloadButton.disabled = true;
      downloadButton.dataset.url = "";
    }
    scrollToApp();
  });
}

// Download button
if (downloadButton) {
  downloadButton.addEventListener("click", async () => {
    const url = downloadButton.dataset.url;
    if (!url) return;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to download image.");

      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = "fash-ai-look.png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error(err);
      alert("Could not download the image. Please try again.");
    }
  });
}

