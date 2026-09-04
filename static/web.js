let eventSource = null;
let isDownloading = false;
let isClosing = false;
let stopRequested = false;


/* =========================================================
 * DOM ELEMANLARI
 * ========================================================= */

const startBtn =
    document.getElementById("startBtn");

const cancelBtn =
    document.getElementById("cancelBtn");

const closeAppBtn =
    document.getElementById("closeAppBtn");

const selectFolderBtn =
    document.getElementById("selectFolderBtn");

const statusText =
    document.getElementById("statusText");

const urlInput =
    document.getElementById("urlInput");

const folderInput =
    document.getElementById("folderInput");

const profileSelect =
    document.getElementById("profileSelect");

const resSelect =
    document.getElementById("resSelect");

const resContainer =
    document.getElementById("resContainer");

const cookieNone =
    document.getElementById("cookieNone");

const cookieFirefox =
    document.getElementById("cookieFirefox");

const cookieFile =
    document.getElementById("cookieFile");

const cookieFileRow =
    document.getElementById("cookieFileRow");

const cookieFileInput =
    document.getElementById("cookieFileInput");

const selectCookieBtn =
    document.getElementById("selectCookieBtn");

const progressBar =
    document.getElementById("progressBar");

const progressText =
    document.getElementById("progressText");

const logText =
    document.getElementById("logText");


/* =========================================================
 * HATA ANİMASYONU
 * ========================================================= */

function triggerErrorAnimation(element) {

    if (!element) {
        return;
    }

    element.classList.remove(
        "input-error"
    );

    void element.offsetWidth;

    element.classList.add(
        "input-error"
    );
}


/* =========================================================
 * İNDİRME DURUMU
 * ========================================================= */

function setDownloadState(active) {

    isDownloading = active;

    startBtn.disabled =
        active || isClosing;

    cancelBtn.disabled =
        !active || isClosing;

    urlInput.disabled =
        active || isClosing;

    folderInput.disabled =
        active || isClosing;

    selectFolderBtn.disabled =
        active || isClosing;

    profileSelect.disabled =
        active || isClosing;

    resSelect.disabled =
        active || isClosing;

    cookieNone.disabled =
        active || isClosing;

    cookieFirefox.disabled =
        active || isClosing;

    cookieFile.disabled =
        active || isClosing;

    cookieFileInput.disabled =
        active || isClosing;

    selectCookieBtn.disabled =
        active || isClosing;
}


/* =========================================================
 * LOG
 * ========================================================= */

function appendLog(text) {

    if (
        text === undefined ||
        text === null
    ) {
        return;
    }

    const now = new Date();

    const timestamp =
        now.toLocaleTimeString(
            undefined,
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false,
            }
        );

    logText.textContent +=
        `[${timestamp}] ${String(text)}\n`;

    requestAnimationFrame(() => {

        logText.scrollTop =
            logText.scrollHeight;

    });
}


/* =========================================================
 * URL KONTROLÜ
 * ========================================================= */

function isValidURL(string) {

    try {

        const parsed =
            new URL(string);

        return true;

    } catch (error) {

        return false;
    }
}


/* =========================================================
 * KLASÖR SEÇİMİ
 * ========================================================= */

async function selectFolder() {

    if (
        isDownloading ||
        isClosing
    ) {
        return;
    }

    selectFolderBtn.disabled = true;

    statusText.textContent =
        "Klasör seçiliyor...";

    try {

        const response =
            await fetch(
                "/api/select-folder"
            );

        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        if (data.error) {

            throw new Error(
                data.error
            );
        }

        if (
            data.path &&
            !data.cancelled
        ) {

            folderInput.value =
                data.path;

            folderInput.classList.remove(
                "input-error"
            );

            selectFolderBtn.classList.remove(
                "input-error"
            );

            statusText.textContent =
                "Klasör seçildi.";

        } else {

            statusText.textContent =
                "Klasör seçimi iptal edildi.";
        }

    } catch (error) {

        appendLog(
            "[HATA] Klasör seçilemedi: " +
            error
        );

        statusText.textContent =
            "Klasör seçilemedi.";

        alert(
            "İndirme klasörü seçilemedi.\n\n" +
            error
        );

    } finally {

        selectFolderBtn.disabled =
            isDownloading ||
            isClosing;
    }
}


/* =========================================================
 * ÇEREZ GÖRÜNÜRLÜĞÜ
 * ========================================================= */

function updateCookieVisibility() {

    const selected =
        document.querySelector(
            'input[name="cookieMode"]:checked'
        );

    if (!selected) {
        return;
    }

    cookieFileRow.style.display =
        selected.value === "file"
            ? "flex"
            : "none";
}


/* =========================================================
 * ÇEREZ DOSYASI SEÇİMİ
 * ========================================================= */

async function selectCookie() {

    if (
        isDownloading ||
        isClosing
    ) {
        return;
    }

    selectCookieBtn.disabled = true;

    statusText.textContent =
        "Çerez dosyası seçiliyor...";

    try {

        const response =
            await fetch(
                "/api/select-cookie"
            );

        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        if (data.error) {

            throw new Error(
                data.error
            );
        }

        if (
            data.path &&
            !data.cancelled
        ) {

            cookieFileInput.value =
                data.path;

            cookieFileInput.classList.remove(
                "input-error"
            );

            selectCookieBtn.classList.remove(
                "input-error"
            );

            statusText.textContent =
                "Çerez dosyası seçildi.";

        } else {

            statusText.textContent =
                "Çerez dosyası seçimi iptal edildi.";
        }

    } catch (error) {

        appendLog(
            "[HATA] Çerez dosyası seçilemedi: " +
            error
        );

        statusText.textContent =
            "Çerez dosyası seçilemedi.";

        alert(
            "Çerez dosyası seçilemedi.\n\n" +
            error
        );

    } finally {

        selectCookieBtn.disabled =
            isDownloading ||
            isClosing;
    }
}


/* =========================================================
 * SEÇENEKLERİ YÜKLE
 * ========================================================= */

async function loadOptions() {

    try {

        const response =
            await fetch(
                "/api/options"
            );

        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        profileSelect.innerHTML = "";

        for (
            const [label, value]
            of Object.entries(
                data.profiles || {}
            )
        ) {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                value;

            option.textContent =
                label;

            profileSelect.appendChild(
                option
            );
        }

        resSelect.innerHTML = "";

        for (
            const resolution
            of data.resolutions || []
        ) {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                resolution;

            option.textContent =
                resolution;

            resSelect.appendChild(
                option
            );
        }

        updateResolutionVisibility();

    } catch (error) {

        appendLog(
            "[HATA] Seçenekler yüklenemedi: " +
            error
        );

        statusText.textContent =
            "Seçenekler yüklenemedi.";

        alert(
            "Seçenekler yüklenemedi.\n\n" +
            error
        );
    }
}


/* =========================================================
 * ÇÖZÜNÜRLÜK GÖRÜNÜRLÜĞÜ
 * ========================================================= */

function updateResolutionVisibility() {

    const shouldShow =
        profileSelect.value === "video";

    resContainer.style.display =
        shouldShow
            ? "inline-flex"
            : "none";
}


/* =========================================================
 * DOWNLOAD BAŞLAT
 * ========================================================= */

async function startDownload() {

    if (
        isDownloading ||
        isClosing
    ) {

        alert(
            "Devam eden indirme bitmeden " +
            "yeni indirme başlatılamaz."
        );

        return;
    }

    stopRequested = false;

    const url =
        urlInput.value.trim();


    /* URL kontrolü */

    if (
        !url ||
        !isValidURL(url)
    ) {

        triggerErrorAnimation(
            urlInput
        );

        alert(
            "Lütfen geçerli bir indirme linki girin."
        );

        urlInput.focus();

        return;
    }

    urlInput.classList.remove(
        "input-error"
    );


    /* Klasör kontrolü */

    const outputDir =
        folderInput.value.trim();

    if (
        !outputDir ||
        outputDir === "Klasör seçilmedi"
    ) {

        triggerErrorAnimation(
            folderInput
        );

        triggerErrorAnimation(
            selectFolderBtn
        );

        alert(
            "Lütfen bir indirme klasörü seçin."
        );

        selectFolderBtn.focus();

        return;
    }


    /* Çerez kontrolü */

    const cookieMode =
        document.querySelector(
            'input[name="cookieMode"]:checked'
        ).value;

    let cookieValue = "";

    if (cookieMode === "browser") {

        cookieValue = "firefox";

    } else if (cookieMode === "file") {

        cookieValue =
            cookieFileInput.value.trim();

        if (!cookieValue) {

            triggerErrorAnimation(
                cookieFileInput
            );

            triggerErrorAnimation(
                selectCookieBtn
            );

            alert(
                "Lütfen bir çerez dosyası seçin."
            );

            selectCookieBtn.focus();

            return;
        }
    }


    /* Eski SSE */

    if (eventSource) {

        try {

            eventSource.close();

        } catch (error) {
        }

        eventSource = null;
    }


    setDownloadState(true);

    progressBar.style.width =
        "0%";

    progressText.textContent =
        "İndirme başlatılıyor.";

    statusText.textContent =
        "İndiriliyor.";

    logText.textContent =
        "";

    appendLog(
        "[WEB] İndirme isteği başlatıldı."
    );


    const profileKey =
        profileSelect.value;

    const resolution =
        profileKey === "video"
            ? resSelect.value
            : "";


    const params =
        new URLSearchParams();

    params.set(
        "url",
        url
    );

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
        "cookie_mode",
        cookieMode
    );

    if (cookieValue) {

        params.set(
            "cookie_value",
            cookieValue
        );
    }


    const streamUrl =
        "/api/download/stream?" +
        params.toString();


    eventSource =
        new EventSource(
            streamUrl
        );


    /* =====================================================
     * SSE ONOPEN
     * ===================================================== */

    eventSource.onopen =
        function (event) {
        };


    /* =====================================================
     * SSE ONMESSAGE
     * ===================================================== */

    eventSource.onmessage =
        function (event) {

            let data;

            try {

                data =
                    JSON.parse(
                        event.data
                    );

            } catch (error) {

                appendLog(
                    "[HATA] Geçersiz SSE verisi: " +
                    event.data
                );

                alert(
                    "Sunucudan geçersiz veri alındı.\n\n" +
                    event.data
                );

                return;
            }


            switch (data.type) {

                /* -----------------------------------------
                 * LOG
                 * ----------------------------------------- */

                case "log":

                    if (!stopRequested) {

                        appendLog(
                            data.text
                        );
                    }

                    break;


                /* -----------------------------------------
                 * WARNING
                 * ----------------------------------------- */

                case "warning":

                    if (!stopRequested) {

                        appendLog(
                            "[UYARI] " +
                            data.text
                        );
                    }

                    break;


                /* -----------------------------------------
                 * ERROR
                 * ----------------------------------------- */

                case "error":

                    // 1. Log ve UI metinlerini güncelle
                    appendLog(
                        "[HATA] " +
                        data.text
                    );

                    statusText.textContent =
                        "Tamamlandı ancak bazı videolar indirilemedi.";

                    progressText.textContent =
                        "Tamamlandı ancak bazı videolar indirilemedi.";

                    // 2. Akış soketini temiz bir şekilde kapat
                    closeSSE();

                    // 3. Buton ve input durumlarını sıfırla
                    setDownloadState(
                        false
                    );

                    // 4. UI çiziminin (repaint) tamamlanmasını bekleyip alert'i bas
                    setTimeout(() => {
                        alert(data.text);
                    }, 0);

                    break;


                /* -----------------------------------------
                 * PLAYLIST
                 * ----------------------------------------- */

                case "playlist":

                    if (!stopRequested) {

                        progressBar.style.width =
                            "0%";

                        progressText.textContent =
                            data.text || "";
                    }

                    break;


                /* -----------------------------------------
                 * PROGRESS
                 * ----------------------------------------- */

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


                /* -----------------------------------------
                 * FILE DONE
                 * ----------------------------------------- */

                case "file_done":

                    progressBar.style.width =
                        "100%";

                    progressText.textContent =
                        data.text ||
                        "Dosya tamamlandı.";

                    break;


                /* -----------------------------------------
                 * STOPPED
                 * ----------------------------------------- */

                case "stopped":

                    // 1. Log ve UI metinlerini güncelle
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

                    // 2. Akış soketini temiz bir şekilde kapat
                    closeSSE();

                    // 3. Buton ve input durumlarını sıfırla
                    setDownloadState(
                        false
                    );

                    // 4. UI çiziminin (repaint) tamamlanmasını bekleyip alert'i bas
                    setTimeout(() => {
                        alert(
                            data.text ||
                            "İndirme kullanıcı tarafından durduruldu."
                        );
                    }, 0);

                    break;


                /* -----------------------------------------
                 * SUCCESS
                 * ----------------------------------------- */

                case "success":

                    appendLog(
                        "[OK] " +
                        data.text
                    );

                    statusText.textContent =
                        "Tamamlandı.";

                    closeSSE();

                    setDownloadState(
                        false
                    );

                    setTimeout(() => {
                        alert(data.text);
                    }, 0);

                    break;


                /* -----------------------------------------
                 * UNKNOWN
                 * ----------------------------------------- */

                default:

                    break;
            }
        };


    /* =====================================================
     * SSE ONERROR
     * ===================================================== */

    eventSource.onerror =
        function (error) {

            closeSSE();

            if (isClosing) {
                return;
            }

            if (isDownloading) {

                statusText.textContent =
                    "Bağlantı kapandı.";

                if (!stopRequested) {

                    appendLog(
                        "[WEB] SSE bağlantısı kapandı."
                    );

                    alert(
                        "İndirme sırasında sunucu bağlantısı kapandı."
                    );
                }
            }

            setDownloadState(
                false
            );
        };
}


/* =========================================================
 * SSE KAPAT
 * ========================================================= */

function closeSSE() {

    if (eventSource) {

        try {

            eventSource.close();

        } catch (error) {
        }

        eventSource = null;
    }
}


/* =========================================================
 * İNDİRMEYİ DURDUR
 * ========================================================= */

async function cancelDownload() {

    if (
        !isDownloading ||
        isClosing
    ) {
        return;
    }

    cancelBtn.disabled = true;

    statusText.textContent =
        "Durduruluyor.";

    appendLog(
        "[WEB] Durdurma isteği gönderiliyor..."
    );

    /*
     * SSE KAPATILMIYOR.
     */

    stopRequested = true;

    try {

        const response =
            await fetch(
                "/api/download/stop",
                {
                    method:
                        "POST"
                }
            );

        const data =
            await response.json();

    } catch (error) {

        appendLog(
            "[WEB] Durdurma isteğinde hata: " +
            error
        );

        alert(
            "İndirme durdurulamadı.\n\n" +
            error
        );

    } finally {

        progressBar.style.width =
            "0%";

        progressText.textContent =
            "İndirme durduruldu.";

        statusText.textContent =
            "Durduruldu. Yeni indirme başlatabilirsiniz.";

        setDownloadState(
            false
        );
    }
}


/* =========================================================
 * UYGULAMAYI KAPAT
 * ========================================================= */

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

    closeAppBtn.disabled =
        true;

    startBtn.disabled =
        true;

    cancelBtn.disabled =
        true;

    selectFolderBtn.disabled =
        true;

    urlInput.disabled =
        true;

    folderInput.disabled =
        true;

    profileSelect.disabled =
        true;

    resSelect.disabled =
        true;

    cookieNone.disabled =
        true;

    cookieFirefox.disabled =
        true;

    cookieFile.disabled =
        true;

    cookieFileInput.disabled =
        true;

    selectCookieBtn.disabled =
        true;

    document.body.classList.add(
        "app-closing"
    );

    statusText.textContent =
        "Uygulama kapatılıyor.";

    appendLog(
        "[WEB] Uygulama kapatma isteği gönderiliyor..."
    );

    closeSSE();

    try {

        const response =
            await fetch(
                "/api/app/exit",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    keepalive:
                        true
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

        } catch (error) {
        }

        statusText.textContent =
            "Uygulama kapatıldı.";

    }, 500);
}


/* =========================================================
 * EVENT LISTENERS
 * ========================================================= */

closeAppBtn.addEventListener(
    "click",
    function () {

        closeApplication();
    }
);


selectFolderBtn.addEventListener(
    "click",
    function () {

        selectFolder();
    }
);


selectCookieBtn.addEventListener(
    "click",
    function () {

        selectCookie();
    }
);


startBtn.addEventListener(
    "click",
    function () {

        startDownload();
    }
);


cancelBtn.addEventListener(
    "click",
    function () {

        cancelDownload();
    }
);


profileSelect.addEventListener(
    "change",
    function () {

        updateResolutionVisibility();
    }
);


cookieNone.addEventListener(
    "change",
    function () {

        updateCookieVisibility();
    }
);


cookieFirefox.addEventListener(
    "change",
    function () {

        updateCookieVisibility();
    }
);


cookieFile.addEventListener(
    "change",
    function () {

        updateCookieVisibility();
    }
);


urlInput.addEventListener(
    "keydown",
    function (e) {

        if (e.key === "Enter") {

            startDownload();
        }
    }
);


urlInput.addEventListener(
    "input",
    function () {

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


/* =========================================================
 * BEFOREUNLOAD
 * ========================================================= */

window.addEventListener(
    "beforeunload",
    function (event) {

        closeSSE();
    }
);


/* =========================================================
 * INIT
 * ========================================================= */

folderInput.value =
    "Klasör seçilmedi";

updateCookieVisibility();

loadOptions();