const form = document.querySelector("#memory-form");
const nameField = document.querySelector("#person-name");
const memoryField = document.querySelector("#memory");
const styleField = document.querySelector("#style");
const modelField = document.querySelector("#model");
const createButton = document.querySelector("#create-button");
const refreshButton = document.querySelector("#refresh-models");
const count = document.querySelector("#character-count");
const connectionPill = document.querySelector("#connection-pill");
const connectionLabel = document.querySelector("#connection-label");
const offeringContent = document.querySelector("#offering-content");
const generatedContent = document.querySelector("#generated-content");
const draftText = document.querySelector("#draft-text");
const draftTitle = document.querySelector("#draft-title");
const draftByline = document.querySelector("#draft-byline");
const toast = document.querySelector("#toast");
let toastTimer;

function showToast(message) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2800);
}

function setConnection(connected, message) {
  connectionPill.classList.toggle("connected", connected);
  connectionPill.classList.toggle("error", !connected);
  connectionLabel.textContent = message;
}

async function loadModels() {
  refreshButton.disabled = true;
  modelField.disabled = true;
  createButton.disabled = true;
  modelField.replaceChildren(new Option("Looking for Ollama…", ""));
  setConnection(false, "Connecting to Ollama");

  try {
    const response = await fetch("/api/models", { cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not load local models.");

    modelField.replaceChildren();
    if (result.models.length === 0) {
      modelField.add(new Option("No models installed", ""));
      setConnection(false, "Install a local model");
      return;
    }

    for (const model of result.models) {
      modelField.add(new Option(model, model));
    }
    if (result.models.includes(result.default)) {
      modelField.value = result.default;
    }
    modelField.disabled = false;
    createButton.disabled = false;
    setConnection(true, `${result.models.length} local model${result.models.length === 1 ? "" : "s"} ready`);
  } catch (error) {
    modelField.replaceChildren(new Option("Ollama not available", ""));
    setConnection(false, "Ollama is offline");
    showToast(error.message);
  } finally {
    refreshButton.disabled = false;
  }
}

memoryField.addEventListener("input", () => {
  count.textContent = `${memoryField.value.length.toLocaleString()} / 2,000`;
});

document.querySelector("#sample-button").addEventListener("click", () => {
  nameField.value = "Mara";
  memoryField.value =
    "Mara always left the last orange slice for whoever came home late. " +
    "On rainy afternoons she taught me to mend a loose button, humming along " +
    "with the radio. I still think of her when the kitchen smells like citrus.";
  memoryField.dispatchEvent(new Event("input"));
  memoryField.focus();
});

refreshButton.addEventListener("click", loadModels);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  createButton.disabled = true;
  createButton.querySelector("span:nth-child(2)").textContent = "Gathering your words…";
  setConnection(true, "Writing on this device");

  try {
    const response = await fetch("/api/compose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nameField.value,
        memory: memoryField.value,
        style: styleField.value,
        model: modelField.value,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The remembrance could not be created.");

    draftTitle.textContent = nameField.value.trim()
      ? `For ${nameField.value.trim()}`
      : "A remembrance";
    draftByline.textContent = `A draft, shaped with ${result.model}`;
    draftText.textContent = result.text;
    offeringContent.hidden = true;
    generatedContent.hidden = false;
    setConnection(true, "Draft ready on this device");
  } catch (error) {
    setConnection(false, "Model unavailable");
    showToast(error.message);
  } finally {
    createButton.disabled = false;
    createButton.querySelector("span:nth-child(2)").textContent = "Create a remembrance";
  }
});

document.querySelector("#copy-button").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(`${draftTitle.textContent}\n\n${draftText.textContent}`);
    showToast("Copied. Your draft is still only on this device.");
  } catch {
    showToast("Clipboard access is unavailable in this browser.");
  }
});

document.querySelector("#download-button").addEventListener("click", () => {
  const content = `${draftTitle.textContent}\n\n${draftText.textContent}\n`;
  const file = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = "memory-lantern-remembrance.txt";
  link.click();
  URL.revokeObjectURL(url);
  showToast("A text copy was saved to your downloads.");
});

loadModels();
