// frontend/script.js
document
  .getElementById("uploadForm")
  .addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById("file");
    if (!fileInput.files.length) {
      alert("Selecteer een bestand");
      return;
    }

    const fd = new FormData();
    fd.append("file", fileInput.files[0]); // sleutelnaam ↔️ backend

    const feedbackDiv = document.getElementById("feedback");
    feedbackDiv.textContent = "⏳ Uploaden & analyseren …";

    try {
      const res = await fetch("http://127.0.0.1:5000/upload", {
        method: "POST",
        body: fd,
      });
      const data = await res.json();

      if (res.ok) {
        // zet \n om in <br> zodat bullet-opsomming leesbaar blijft
        feedbackDiv.innerHTML =
          "<strong>Feedback van AI:</strong><br><br>" +
          data.feedback.replace(/\n/g, "<br>");
      } else {
        feedbackDiv.textContent = "Fout: " + data.error;
      }
    } catch (err) {
      feedbackDiv.textContent = "Netwerkfout: " + err.message;
    }
  });
