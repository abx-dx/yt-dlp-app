let eventSource = null;
let isDownloading = false;
let isClosing = false;
let stopRequested = false;

/* DOM Elemanları */
const startBtn = document.getElementById("startBtn");
const cancelBtn = document.getElementById("cancelBtn");
const closeAppBtn = document.getElementById("closeAppBtn");
const selectFolderBtn = document.getElementById("selectFolderBtn");
const statusText = document.getElementById("statusText");
const urlInput = document.getElementById("urlInput");
const folderInput = document.getElementById("folderInput");
const profileSelect = document.getElementById("profileSelect");
const resSelect = document.getElementById("resSelect");
const resContainer = document.getElementById("resContainer");
const cookiesCheck = document.getElementById("cookiesCheck");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const logText = document.getElementById("logText");


/* Hata animasyonu */
function triggerErrorAnimation(element) {
    element.classList.remove("input-error");

    void element.offsetWidth;

    element.classList.add("input-error");
}


/* İndirme durumu */
function setDownloadState(active) {
    isDownloading = active;

    startBtn.disabled = active || isClosing;
    cancelBtn.disabled = !active || isClosing;

    urlInput.disabled = active || isClosing;
    folderInput.disabled = active || isClosing;
    selectFolderBtn.disabled = active || isClosing;

    profileSelect.disabled = active || isClosing;
    resSelect.disabled = active || isClosing;
    cookiesCheck.disabled = active || isClosing;
}


/* Log ekleme */
function appendLog(text) {
    if (text === undefined || text === null) {
        return;
    }

    logText.textContent += String(text) + "\n";

    requestAnimationFrame(() => {
        logText.scrollTop = logText.scrollHeight;
    });
}


/* URL kontrolü */
function isValidURL(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}


/* Klasör seçimi */
async function selectFolder() {
    if (isDownloading || isClosing) {
        return;
    }

    selectFolderBtn.disabled = true;
    statusText.textContent = "Klasör seçiliyor...";

    try {
        const response = await fetch("/api/select-folder");

        if (!response.ok) {
            throw new Error("HTTP " + response.status);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (data.path && !data.cancelled) {
            folderInput.value = data.path;

            folderInput.classList.remove("input-error");
            selectFolderBtn.classList.remove("input-error");

            statusText.textContent = "Klasör seçildi.";
        } else {
            statusText.textContent = "Klasör seçimi iptal edildi.";
        }

    } catch (error) {
        appendLog("[HATA] Klasör seçilemedi: " + error);

        statusText.textContent = "Klasör seçilemedi.";

        alert(
            "İndirme klasörü seçilemedi.\n\n" +
            error
        );

    } finally {
        selectFolderBtn.disabled =
            isDownloading || isClosing;
    }
}


/* Seçenekleri yükle */
async function loadOptions() {
    try {
        const response = await fetch("/api/options");

        if (!response.ok) {
            throw new Error("HTTP " + response.status);
        }

        const data = await response.json();

        profileSelect.innerHTML = "";

        for (
            const [label, value]
            of Object.entries(data.profiles || {})
        ) {
            const option =
                document.createElement("option");

            option.value = value;
            option.textContent = label;

            profileSelect.appendChild(option);
        }

        resSelect.innerHTML = "";

        for (
            const resolution
            of data.resolutions || []
        ) {
            const option =
                document.createElement("option");

            option.value = resolution;
            option.textContent = resolution;

            resSelect.appendChild(option);
        }

        updateResolutionVisibility();

    } catch (error) {
        appendLog(
            "[HATA] Seçenekler yüklenemedi: " +
            error
        );

        statusText.textContent =
            "Seçenekler yüklenemedi.";
    }
}


/* Çözünürlük alanını göster/gizle */
function updateResolutionVisibility() {
    resContainer.style.display =
        profileSelect.value === "video"
            ? "inline-flex"
            : "none";
}


profileSelect.addEventListener(
    "change",
    updateResolutionVisibility
);


/* İndirme başlat */
async function startDownload() {
    if (isDownloading || isClosing) {
        return;
    }

    stopRequested = false;

    const url = urlInput.value.trim();


    /* URL kontrolü */
    if (!url || !isValidURL(url)) {
        triggerErrorAnimation(urlInput);

        alert(
            "Lütfen geçerli bir indirme linki girin."
        );

        urlInput.focus();

        return;
    }

    urlInput.classList.remove("input-error");


    /* Klasör kontrolü */
    const outputDir =
        folderInput.value.trim();

    if (
        !outputDir ||
        outputDir === "Klasör seçilmedi"
    ) {
        triggerErrorAnimation(folderInput);
        triggerErrorAnimation(selectFolderBtn);

        alert(
            "Lütfen önce bir indirme klasörü seçin."
        );

        selectFolderBtn.focus();

        return;
    }


    /* Eski SSE bağlantısını kapat */
    if (eventSource) {
        try {
            eventSource.close();
        } catch (_) {}

        eventSource = null;
    }


    setDownloadState(true);

    progressBar.style.width = "0%";

    progressText.textContent =
        "İndirme başlatılıyor...";

    statusText.textContent =
        "İndiriliyor...";

    logText.textContent = "";

    appendLog(
        "[WEB] İndirme isteği başlatıldı."
    );


    const profileKey =
        profileSelect.value;

    const resolution =
        profileKey === "video"
            ? resSelect.value
            : "";

    const useCookies =
        cookiesCheck.checked;


    const params =
        new URLSearchParams();

    params.set("url", url);

    params.set(
        "profile_key",
        profileKey
    );

    params.set(
        "output_dir",
        outputDir
    );

    if (resolution) {
        params.set(
            "resolution",
            resolution
        );
    }

    params.set(
        "use_firefox_cookies",
        useCookies
            ? "true"
            : "false"
    );


    eventSource =
        new EventSource(
            "/api/download/stream?" +
            params.toString()
        );


    eventSource.onmessage =
        function (event) {

            let data;

            try {
                data = JSON.parse(
                    event.data
                );
            } catch (error) {
                appendLog(
                    "[HATA] Geçersiz SSE verisi: " +
                    event.data
                );

                return;
            }


            switch (data.type) {

                case "log":

                    /*
                     * Durdurma isteğinden sonra
                     * gelen yeni normal logları
                     * kullanıcıya göstermiyoruz.
                     *
                     * Daha önce ekrana ulaşmış
                     * loglara dokunmuyoruz.
                     */
                    if (!stopRequested) {
                        appendLog(data.text);
                    }

                    break;


                case "warning":

                    if (!stopRequested) {
                        appendLog(
                            "[UYARI] " +
                            data.text
                        );
                    }

                    break;


                case "error":

                    appendLog(
                        "[HATA] " +
                        data.text
                    );

                    statusText.textContent =
                        "Hata oluştu.";

                    closeSSE();

                    setDownloadState(false);

                    break;


                case "playlist":

                    if (!stopRequested) {
                        progressBar.style.width =
                            "0%";

                        progressText.textContent =
                            data.text || "";
                    }

                    break;


                case "progress":

                    if (!stopRequested) {

                        if (
                            typeof data.percent ===
                            "number"
                        ) {
                            const percent =
                                Math.max(
                                    0,
                                    Math.min(
                                        100,
                                        data.percent
                                    )
                                );

                            progressBar.style.width =
                                percent + "%";
                        }

                        progressText.textContent =
                            data.text || "";
                    }

                    break;


                case "file_done":

                    /*
                     * FileDoneEvent özel rapor
                     * içerdiğinden filtrelemiyoruz.
                     */
                    progressBar.style.width =
                        "100%";

                    progressText.textContent =
                        data.text ||
                        "Dosya tamamlandı.";

                    break;


				case "stopped":

					appendLog(
						"[WEB] " +
						(
							data.text ||
							"İndirme durduruldu."
						)
					);

					appendLog(
						"[WEB] Yeni işlem başlatılabilir."
					);

					statusText.textContent =
						"Durduruldu.";

					closeSSE();

					setDownloadState(false);

					break;

                case "success":

                    appendLog(
                        "[OK] " +
                        data.text
                    );

                    statusText.textContent =
                        "Tamamlandı.";

                    setDownloadState(false);

                    closeSSE();

                    break;
            }
        };


    eventSource.onerror =
        function () {

            closeSSE();

            if (isClosing) {
                return;
            }

            if (isDownloading) {

                statusText.textContent =
                    "Bağlantı kapandı.";

                /*
                 * Stop sırasında SSE zaten
                 * kapatılmışsa gereksiz hata
                 * mesajı üretme.
                 */
                if (!stopRequested) {
                    appendLog(
                        "[WEB] SSE bağlantısı kapandı."
                    );
                }
            }

            setDownloadState(false);
        };
}


/* SSE kapat */
function closeSSE() {
    if (eventSource) {

        try {
            eventSource.close();
        } catch (_) {}

        eventSource = null;
    }
}


/* İndirmeyi durdur */
async function cancelDownload() {
    if (!isDownloading || isClosing) {
        return;
    }

    cancelBtn.disabled = true;

    statusText.textContent =
        "Durduruluyor...";

    appendLog(
        "[WEB] Durdurma isteği gönderiliyor..."
    );


    /*
     * SSE'yi KAPATMIYORUZ.
     *
     * Backend'deki active runner'ın
     * kaybolmaması gerekiyor.
     */
    stopRequested = true;


    try {

        const response =
            await fetch(
                "/api/download/stop",
                {
                    method: "POST"
                }
            );

        const data =
            await response.json();


        /*
         * API'nin cevabını normal log
         * olarak göstermiyoruz.
         *
         * Çünkü aşağıdaki stopped SSE
         * mesajı kullanıcıya nihai durumu
         * bildirecek.
         */

    } catch (error) {

        appendLog(
            "[WEB] Durdurma isteğinde hata: " +
            error
        );

    } finally {

        /*
         * Burada SSE'yi kapatmıyoruz.
         *
         * Backend'in "stopped" event'ini
         * göndermesine izin veriyoruz.
         */

        progressBar.style.width = "0%";

        progressText.textContent =
            "İndirme durduruldu.";

        statusText.textContent =
            "Durduruldu. Yeni indirme başlatabilirsiniz.";

        /*
         * Runner backend tarafında durduruldu.
         * UI yeni işleme hazırlanabilir.
         */
        setDownloadState(false);

    }
}


/* Uygulamayı kapat */
async function closeApplication() {
    if (isClosing) {
        return;
    }


    const confirmed =
        window.confirm(
            "Uygulama kapatılacak.\n\n" +
            "Aktif indirme varsa durdurulacak.\n" +
            "Devam etmek istiyor musunuz?"
        );


    if (!confirmed) {
        return;
    }


    isClosing = true;

    closeAppBtn.disabled = true;

    startBtn.disabled = true;
    cancelBtn.disabled = true;

    selectFolderBtn.disabled = true;

    urlInput.disabled = true;
    folderInput.disabled = true;

    profileSelect.disabled = true;
    resSelect.disabled = true;
    cookiesCheck.disabled = true;


    document.body.classList.add(
        "app-closing"
    );


    statusText.textContent =
        "Uygulama kapatılıyor...";


    appendLog(
        "[WEB] Uygulama kapatma isteği gönderiliyor..."
    );


    closeSSE();


    try {

        await fetch(
            "/api/app/exit",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                keepalive: true
            }
        );

    } catch (error) {

        console.log(
            "Uygulama kapanırken bağlantı kesildi:",
            error
        );
    }


    setTimeout(() => {

        try {
            window.close();
        } catch (_) {}

        statusText.textContent =
            "Uygulama kapatıldı.";

    }, 500);
}


/* Event Listeners */

closeAppBtn.addEventListener(
    "click",
    closeApplication
);

selectFolderBtn.addEventListener(
    "click",
    selectFolder
);

startBtn.addEventListener(
    "click",
    startDownload
);

cancelBtn.addEventListener(
    "click",
    cancelDownload
);


urlInput.addEventListener(
    "keydown",
    (e) => {
        if (e.key === "Enter") {
            startDownload();
        }
    }
);


/* URL geçerli olduğunda hata çerçevesini kaldır */
urlInput.addEventListener(
    "input",
    () => {

        const val =
            urlInput.value.trim();

        if (
            val &&
            isValidURL(val)
        ) {
            urlInput.classList.remove(
                "input-error"
            );
        }
    }
);


/* Sayfa kapanırken SSE'yi kapat */
window.addEventListener(
    "beforeunload",
    closeSSE
);


/* Init */

folderInput.value =
    "Klasör seçilmedi";

loadOptions();